PY := ./.venv/bin/python
PACK ?= en

.PHONY: all scan base pack embed lint eval check rebuild clean

## The normal loop after editing a pack's lexicon.
all: pack embed lint

## scan  -- re-parse libstdc++ (~4 min). Only after a toolchain change or an
##          edit to the header list in tools/scan_cpp.py.
scan:
	$(PY) tools/scan_cpp.py

## base  -- the SHARED syntax layer: declarations, ports, emit templates,
##          language constructs, advisory edges. Every pack ATTACHes this.
base:
	$(PY) tools/build_base.py $(PACK)

## pack  -- semantics for ONE human language. Rebuilding a pack DROPS its
##          vector index, so `embed` must follow; `make all` does both.
pack:
	$(PY) tools/build_pack.py $(PACK)

embed:
	$(PY) tools/embed.py $(PACK)

lint:
	$(PY) tools/lint.py $(PACK)

eval:
	$(PY) tools/eval.py

check: pack embed lint eval

## rebuild -- everything from the scan down.
rebuild: scan base pack embed lint

clean:
	rm -f out/*.db out/*.db-wal out/*.db-shm

q:
	@$(PY) tools/query.py $(Q)
