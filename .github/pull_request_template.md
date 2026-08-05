## What this changes

<!-- One kind of change per PR: phrasings and advisory edges do not belong together. -->

- [ ] semantic phrasings
- [ ] canonical terms
- [ ] advisory edges
- [ ] scanner / coverage
- [ ] language pack
- [ ] other

## Measured

<!-- CI runs these too, but paste them: it shows you looked. -->

```
before   top-1 __%   top-5 __%
after    top-1 __%   top-5 __%
lint     __ errors
```

## What I verified — and what I did not

<!-- Say plainly what you did not check. That is more useful than a claim of
     completeness, and it is what a reviewer needs to know where to look. -->

## For canonical terms and advisory edges only

- [ ] Every rationale I wrote is **true** — no invented preconditions
- [ ] Severity is honest (`unsafe` is a real hazard, not a style preference)
