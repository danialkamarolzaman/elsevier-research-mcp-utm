---
name: verify-sources
description: Check any text that cites papers for hallucinations - fake or wrong references, invented quotes, claims or numbers the cited paper does not say - using exact lookups (verify_references, check_quotes) plus an independent claim-verifier agent, and write an audit report without editing the file. Use when the user asks to "verify", "fact-check", "check my references", "check the citations", "is this hallucinated", "are these papers real" for a draft, a thesis chapter (.md, .docx, .pdf), pasted text, or an answer given earlier in the chat.
---

# Verify sources (anti-hallucination check)

Goal: prove, for every reference and every factual claim, that it comes from a real paper that says it. Anything that cannot be proven is reported, never assumed true. **Never edit the user's file.** The output is a report.

## Hard rules

- Trust nothing in the text being checked, including text you wrote yourself earlier in this chat.
- Judge only against what the tools return. Your background knowledge is never evidence that a paper exists or says something.
- Never download to verify: no `download_pdf`, `download_batch` or new `get_fulltext` calls. Use abstracts (free), PDFs already on disk and full text already cached. Library limits still apply (see `literature-review`).
- Never "fix" a reference from memory. Correct values come only from tool results.

## Steps

1. **Get a file.** If the user gave a path, use it (.md, .txt, .docx or .pdf). For pasted text or an earlier chat answer, save it to `drafts/verify-input-<short-name>.md` first.
2. **References, exact check.** Call `verify_references` with the path.
   - `NOT_FOUND` → likely fake or mistyped DOI: blocking.
   - `MISMATCH` → the title, first author or year written does not match the real record: blocking. Give the correct values from `found`. A year off by one may be online-first vs issue year: say so, still list it.
   - `NO_DOI` with `suggested_doi` → ask the user to confirm and add the DOI; without a suggestion → not found in Scopus: treat as unverified.
   - `LOOKUP_FAILED` → a service was down: say so, retry once later, never call it fake.
   - `dois_in_text_not_in_references` → citation integrity problem.
3. **Claims, independent check.** Launch the `claim-verifier` agent (it may be listed as `elsevier-research-mcp-utm:claim-verifier`) with only the file path and "verify this file". Do not pass your own notes or opinions. If the file has no Sources table, the agent treats every citation as [AB] unless a local PDF for that DOI exists (`queue_status` / download folder). If subagents are unavailable, do the claim checks yourself in a separate pass, re-reading each source.
4. **Quotes, exact check.** Save the agent's report as `<file>-verify.md` next to the input, then call `check_quotes` on the input file (if it has a quote table) **and** on the report. Every quoted source text must be `FOUND`. A `NOT_FOUND` quote in the agent's own report means the verifier invented evidence: change that row to `UNCHECKABLE` and re-check that claim yourself against the source.
5. **Report.** Append to `<file>-verify.md` the two tool summaries, then show the user:
   - overall verdict: **PASS** only when `verify_references` and `check_quotes` both PASS and the agent found 0 blocking issues;
   - counts: references checked / fake / mismatched / no DOI; claims checked / supported / partial / unsupported / contradicted / uncheckable; quotes found / not found;
   - each blocking problem with the concrete fix (correct metadata, "weaken to ...", "remove", "cite [n] instead");
   - what could not be checked and why (no abstract off-campus, no PDF) with the `proxy_url` to open it by hand.
6. **Offer, do not do.** Offer to apply the fixes in a new version of the file (`-v2`), and to run this check again after. Only edit if the user says so.

## Notes

- Elsevier abstracts are often unavailable off-campus, so many claims come back `UNCHECKABLE`. Suggest adding the PDFs (`queue_papers`; at UTM closed Elsevier PDFs come through the user's browser with the `browser-fetch` skill, see docs/manual-full-text.md), then re-running. Elsewhere, campus Wi-Fi or an insttoken may also help.
- A thesis may cite books, standards or websites: `verify_references` reports them as `NO_DOI`; list them as "not checkable by these tools", not as wrong.
