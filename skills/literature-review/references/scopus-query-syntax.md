# Scopus query syntax (cheat sheet)

Used in the `query` of `search_scopus`. Years are easier with the tool's `year_from` / `year_to`.

## Field codes

| Code | Searches |
|---|---|
| `TITLE-ABS-KEY(x)` | title, abstract and keywords (the usual starting point) |
| `TITLE(x)` | title only (narrow, precise) |
| `ABS(x)` | abstract only |
| `KEY(x)` | author and indexed keywords |
| `AUTH(x)` | author name, e.g. `AUTH(smith j)` |
| `AUTHLASTNAME(x)` | author surname |
| `AU-ID(n)` | Scopus author ID |
| `AFFIL(x)` | affiliation, e.g. `AFFIL("universiti teknologi malaysia")` |
| `SRCTITLE(x)` | journal or source title |
| `DOI(x)` | one DOI |
| `PUBYEAR > 2020` | publication year (`>`, `<`, `=`; no `>=`) |
| `DOCTYPE(ar)` | document type: `ar` article, `re` review, `cp` conference paper, `ch` book chapter |
| `LANGUAGE(english)` | language |
| `SUBJAREA(ENGI)` | subject area, e.g. `ENGI`, `COMP`, `MATE`, `ENER` |
| `OPENACCESS(1)` | open-access only |

## Operators

| Operator | Meaning |
|---|---|
| `AND`, `OR`, `AND NOT` | boolean; use brackets to group. `AND NOT` should come last |
| `W/n` | within n words, any order: `maintenance W/3 recommendation` |
| `PRE/n` | first word precedes the second within n words |
| `"two words"` | loose phrase (ignores punctuation and plurals) |
| `{exact phrase}` | exact phrase, punctuation included |
| `*` | any number of characters: `predict*` |
| `?` | one character: `wom?n` |

Precedence: `OR` binds before `AND`, which binds before `AND NOT`. Always use brackets anyway.

## Patterns

Concept blocks joined by AND, synonyms by OR:

```
TITLE-ABS-KEY(("knowledge graph*" OR "knowledge base*" OR ontolog*)
  AND ("predictive maintenance" OR "maintenance recommendation" OR "fault diagnos*")
  AND (cement OR "process industr*"))
AND DOCTYPE(ar OR re) AND LANGUAGE(english)
```

Recent reviews only:

```
TITLE-ABS-KEY("remaining useful life" AND (review OR survey)) AND DOCTYPE(re)
```

## Tips

- Too many results: move a concept from `TITLE-ABS-KEY` to `TITLE`, add a third concept, or add `DOCTYPE`.
- Too few: add synonyms and wildcards, drop the narrowest concept.
- Sort by `citations` for foundational work, `date` for the latest.
- A search returns 25 per page; page with `start` = 25, 50, ...
