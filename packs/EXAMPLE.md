# Adding a language pack (not yet done — English is the only pack)

A second pack is a sibling of `packs/en/`, never a translation of it:

    packs/cs/
      pack.yaml     locale: cs · name: Čeština · connectives
      lexicon.py    the tables in PACK_CONTRACT.md, authored in Czech

Then:

    build_pack.py cs   ->  out/pack_cs.db

It reads `out/base.db` (declarations, ports, parameter roles) and nothing else.
It does not read `pack_en.db`, so the Czech concept partition is Czech's own —
Czech is not obliged to split `sort_heap` the way English did.

Reading an English codebase in Czech needs no English row: the join key is the
declaration (`std::sort`), which every pack maps independently.

Authoring a pack is a native-speaker job. A machine-translated pack reproduces
the source language's conceptual carving in the target language's vocabulary,
which is the failure this structure exists to prevent.
