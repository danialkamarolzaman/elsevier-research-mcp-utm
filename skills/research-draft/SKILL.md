---
name: research-draft
description: Draft a document (literature review, background chapter, related work, short report, summary) grounded only in papers retrieved with the elsevier-research tools, with IEEE citations, evidence labels, an independent claim-by-claim verification by the claim-verifier agent, and rework of anything false. Use when the user asks to "draft", "write" or "summarise" a review, background, related work or report "from papers", "from the literature", or "on <topic>" with references.
---

# Research draft (grounded, verified)

Every claim in the final draft must come from a paper a tool returned in this session, and must pass an independent check. Follow the `literature-review` skill for search syntax and the institution download-limit rules; they apply here in full.

## Defaults (the user may override any)

- **Years:** the last 5 years counted from today's date: the current year and the 4 before it.
- **Papers:** about 20.
- **Ranking:** two searches with the same query: (1) `sort='citations'` over the whole window = foundational papers, tagged `[cited]`; (2) `sort='date'` over the last 2 years = recent papers that have not had time to collect citations, tagged `[recent]`.
- **Citation style:** IEEE: [1], [2] in the text, numbered by first appearance; reference list in that order.
- **Length:** as asked; otherwise about 1,500 words.

## Rules for the drafter (you)

1. Cite only papers whose DOI was returned by a tool call in this session. Never cite from memory; never invent or "correct" a DOI, author, year, title or journal.
2. Every factual sentence ends with a citation. Your own synthesis starts with "Overall," or "Taken together," and cites the papers it combines.
3. Label every citation: [FT] = you read the full text, [AB] = abstract only, e.g. `... degradation [3, FT]`. A paper known only by its title is never used for a claim.
4. Numbers (accuracy, error, sizes, datasets) only from [FT], or from [AB] when the abstract states them; copy them exactly with units.
5. If the papers do not cover a point the user asked about, write "No retrieved source covers this" and suggest a search. Never fill gaps from general knowledge.
6. Limits: open access first (`find_open_access`, `download_pdf`); institutional full text in batches of at most 5; on a limit refusal tell the user the `next_allowed` time and stop. Never retry in a loop.

## Steps

1. **Scope.** Confirm topic, document type, years, number of papers, length.
2. **Query, pause 1.** Write the Scopus query and show it with the year window. **Wait for the user's OK.**
3. **Search.** Run the two searches. Show one screening table: tag ([cited]/[recent]), year, first author, title, journal, citations, open access, relevant yes/no with a one-line reason from `get_abstract`.
4. **Paper list, pause 2.** **Wait for the user to confirm the papers.**
5. **Read.** `get_abstract` for every chosen paper. Full text where possible: open-access PDFs via `download_pdf` (read the PDF), ScienceDirect via `get_fulltext` when entitled. Note for each paper where its full text came from.
6. **Draft.** Write the document to `drafts/<short-topic>-draft-v1.md` (create the folder in the current working directory). Structure to suit the document type. End the file with:
   - **References** (IEEE, cited papers only, each with DOI).
   - **Sources** table: `n | DOI | evidence ([FT]/[AB]) | full text from (pdf:<path> / sciencedirect / -)`.
   - **Verification table**: `claim | citation | [FT]/[AB] | supporting quote or section`.
   - **Gaps**: questions the papers did not answer.
7. **Verify.** Launch the `claim-verifier` agent (from this plugin; it may be listed as `elsevier-research-mcp-utm:claim-verifier`) with only the draft path and the instruction to verify it. Do not pass your notes or reasoning: the check must be independent. If subagents are not available, do the same checks yourself in a separate pass, re-reading each source rather than your notes.
8. **Rework.** If the verdict is FAIL, fix every blocking issue as the report says: correct the wording or number, weaken overreaching claims, re-cite, or remove the claim. Never "fix" by adding a new citation that was not retrieved and read. Fix `PARTIAL` items too, by narrowing the wording. Save as `-v2.md`, then verify again with a fresh `claim-verifier`. At most **2 rework rounds**.
9. **Report.** Show the user:
   - the final draft path and the final verdict (PASS, or FAIL with the remaining issues listed openly, never hidden);
   - a short verification summary: claims checked, fixed, removed, uncheckable;
   - the Gaps list;
   - `export_references` to BibTeX, with the file path.

Save each verifier report next to the draft (`-verify-v1.md`, `-verify-v2.md`) so the user can audit the changes.
