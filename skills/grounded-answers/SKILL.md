---
name: grounded-answers
description: Rules that stop invented papers, DOIs, authors, numbers and findings whenever research questions are answered in chat with the elsevier-research tools. Use whenever the user asks what papers say, which papers exist, for results, accuracies, datasets, methods or gaps in the literature, asks "is there a paper on ...", "what does <paper> find", "give me references for ...", or asks for a quick answer, comparison or table from Scopus / ScienceDirect papers rather than a full draft.
---

# Grounded answers in chat

Every paper, DOI, author, year, number and finding you state must come from a tool result returned **in this session**. This applies to short chat answers and tables, not only to drafts.

## Rules

1. **No paper without a tool result.** Mention a paper only if `search_scopus`, `get_abstract`, `get_fulltext` or a PDF you read returned it. If you think you remember a relevant paper, search for it first; if no tool returns it, do not mention it.
2. **Copy, never reconstruct.** Title, authors, year, journal and DOI are copied from the tool result. Never complete a partial DOI, guess a year or "correct" an author.
3. **Label the evidence** on each claim: [AB] = from the abstract, [FT] = from the full text or a PDF you read, [META] = title/metadata only. A [META] paper may be listed as existing, but never used for what it found.
4. **Numbers only from text you read**, copied exactly with units, and say where they came from (abstract or full text).
5. **Say what is missing.** If the retrieved papers do not answer the question, say "Not found in the retrieved sources" and suggest a search or the paper to read. Never fill the gap from general knowledge. If you add general background, mark it clearly as *not from the retrieved papers* and keep it out of any citation.
6. **Do not overstate.** Keep the paper's own hedging ("suggests", "in a case study", "on one dataset"). Do not generalise one paper into "studies show".
7. **End with sources.** Close every research answer with a short **Sources used** list: `[n] first author, year, title, DOI, [AB]/[FT]`.
8. **Offer the check.** For anything the user may reuse in writing (a reference list, a paragraph, a table of results), offer to run the `verify-sources` skill on it. When you build a reference list, run `verify_references` with its DOIs before showing it.

## When you are unsure

Prefer "I could not confirm this from the papers I retrieved" over a confident sentence. An honest gap is always better than a plausible invention.
