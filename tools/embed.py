#!/usr/bin/env python3
"""
embed.py -- build the vector side of the hybrid index.

Curated keys handle the phrasings we anticipated; embeddings cover the ones we
did not. Static embeddings (model2vec) are used deliberately: no GPU, no torch,
millisecond queries, and the index rebuilds in seconds -- which matters because
intent_text changes every time the lexicon is edited.
"""
from __future__ import annotations

import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np
import sqlite_vec
from model2vec import StaticModel

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "out" / "base.db"
MODEL = "minishlab/potion-base-8M"
CACHE = ROOT / "data" / "model"


def get_model() -> StaticModel:
    if CACHE.exists():
        return StaticModel.from_pretrained(str(CACHE))
    m = StaticModel.from_pretrained(MODEL)
    m.save_pretrained(str(CACHE))
    return m


def open_db(locale: str = "en") -> sqlite3.Connection:
    con = sqlite3.connect(ROOT / "out" / f"pack_{locale}.db")
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    con.execute("ATTACH DATABASE ? AS base", (str(BASE),))
    return con


def main(locale: str = "en"):
    model = get_model()
    con = open_db(locale)

    # Embed each declaration together with its concept's canonical term and
    # every alias reaching it -- the vector stage exists to catch phrasings
    # nobody wrote down, so it must see the ones that were.
    rows = con.execute("""
        SELECT e.id,
               e.qualified_name || ' ' ||
               COALESCE((SELECT t.intent_text FROM entry_text t
                         WHERE t.entry_id = e.id), '') || ' ' ||
               COALESCE((SELECT group_concat(c.canonical_term, '. ')
                         FROM binding b JOIN concept c ON c.id = b.concept_id
                         WHERE b.entry_id = e.id), '') || ' ' ||
               COALESCE((SELECT group_concat(replace(k.key,'-',' '), '. ')
                         FROM semantic_key k
                         WHERE k.entry_id = e.id
                            OR k.concept_id IN (SELECT b2.concept_id
                                 FROM binding b2 WHERE b2.entry_id = e.id)), '')
        FROM base.entry e
    """).fetchall()
    ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]
    print(f"embedding {len(texts)} entries with {MODEL} ...", flush=True)

    vecs = model.encode(texts, show_progress_bar=True)
    vecs = np.asarray(vecs, dtype=np.float32)
    vecs /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
    dim = vecs.shape[1]

    con.execute("DROP TABLE IF EXISTS vec_entry")
    con.execute(
        f"CREATE VIRTUAL TABLE vec_entry USING vec0("
        f"entry_id INTEGER PRIMARY KEY, embedding FLOAT[{dim}])")
    con.executemany(
        "INSERT INTO vec_entry(entry_id, embedding) VALUES (?, ?)",
        [(i, v.tobytes()) for i, v in zip(ids, vecs)])
    con.execute("CREATE TABLE IF NOT EXISTS vec_meta(model TEXT, dim INTEGER)")
    con.execute("DELETE FROM vec_meta")
    con.execute("INSERT INTO vec_meta VALUES (?,?)", (MODEL, dim))
    con.commit()
    print(f"indexed {len(ids)} vectors, dim={dim}")


if __name__ == "__main__":
    main(*sys.argv[1:])
