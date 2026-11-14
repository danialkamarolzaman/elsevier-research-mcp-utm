# Research workflow: grounded drafts with independent verification

The `research-draft` skill (Claude Code plugin) writes a draft from real papers only, then has a separate agent fact-check it. With other MCP clients, use the prompts in the [README](../README.md#research-prompt-grounded-drafts-from-real-papers).

## Steps

1. **Scope.** Topic, document type, length. Defaults: last 5 years counted from today, about 20 papers, about 1,500 words, IEEE citations.
2. **Pause 1: the query.** You approve or change the Scopus query and year window.
3. **Search, twice.**
   - `[cited]`: sorted by citations over the whole window (the established work).
   - `[recent]`: sorted by date over the last 2 years (new work that has not collected citations yet).

   You get one screening table: tag, year, first author, title, journal, citations, open access, relevant yes/no with a reason from the abstract.
4. **Pause 2: the papers.** You confirm which ones to use.
5. **Read.** Abstracts for all; full text where possible, open access first, then Elsevier within the download limits.
6. **Draft** to `drafts/<topic>-draft-v1.md`: every factual sentence cited as `[n, FT]` (full text read) or `[n, AB]` (abstract only). It ends with References (IEEE, with DOI), a Sources table, a Verification table (claim, citation, quote or section) and Gaps.
7. **Verify.** The `claim-verifier` agent gets only the draft file, not the drafter's notes, and checks it against the sources itself.
8. **Rework.** Every blocking issue is corrected, weakened or removed, never "fixed" by citing a paper that was not retrieved. A fresh verifier runs again. At most 2 rounds.
9. **Report.** Final draft, verdict, what was changed, anything still unresolved, and a BibTeX file.

## What the verifier checks

| Check | Fails as |
|---|---|
| DOI exists; title, first author, year, journal match | `FAKE_REFERENCE`, `METADATA_MISMATCH` |
| every `[n]` points to a reference; numbered in order of first use | `CITATION_ERROR` |
| each claim against the source text | `SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `CONTRADICTED`, `UNCHECKABLE` |
| factual sentence with no citation | `UNCITED_CLAIM` |
| every number, exactly, with units | `NUMBER_MISMATCH` |
| `[FT]` used where only the abstract was read | `MISLABELED` |

The verdict is `PASS` only with zero blocking issues. The verifier is read-only: it never downloads anything new, so it cannot use up your download limits. It re-reads full text only from the cache or from PDFs already saved.

## Reading a verify report

Each round's report is saved next to the draft (`...-verify-v1.md`, `...-verify-v2.md`). Compare `-v1` and `-v2` to see what was changed and why.

## Limits of this approach

- It strongly reduces invented references and claims, and makes the rest visible, but **cannot guarantee zero errors**. A claim can be technically supported by a sentence and still be misleading in context.
- `[AB]` claims rest on an abstract only. Off-campus, many Elsevier papers have no abstract available at all, so the draft may lean on open-access and non-Elsevier papers. The Gaps section says so.
- It only knows what the search returned. Check that the query did not miss key work in your field.

Read the verification report and spot-check claims before you use any draft in a thesis or paper.
