# Access tiers

What you can get depends on the network you are on and whether you have an insttoken, not on the tool. `doctor` and `check_access` test this live (nothing is downloaded or counted).

| Tier | What works | Typical situation |
|---|---|---|
| `none` | nothing | no key, or the key is rejected |
| `metadata` | Scopus search: titles, authors, DOI, PII, citations; open-access papers; abstracts of most non-Elsevier papers (OpenAlex / Semantic Scholar) | home or mobile network, API key only |
| `abstracts` | + Elsevier abstracts | subscribed network or insttoken (rare without full text) |
| `fulltext` | + ScienceDirect full text and PDFs of subscribed journals | campus Wi-Fi, or an insttoken |

**At UTM** the tier never reaches `fulltext`, on campus either (tested November 2026: off campus `metadata`, on campus at most Elsevier abstracts), and no insttoken is issued. Closed papers come through your browser: see [closed papers through your browser](manual-full-text.md).

## How the check works

1. **Key**: one Scopus search. `401 AUTHENTICATION_ERROR` = the key is wrong.
2. **Abstracts**: one Abstract Retrieval call. `401 AUTHORIZATION_ERROR` = the key is fine, this network is not entitled to that view. This is normal off-campus and not an error with your key.
3. **Full text**: the free entitlement endpoint for one paper. `403` with "Requestor configuration settings insufficient" = this network or token is not entitled.

## What "headless" means here

The MCP server only uses the official Elsevier APIs. It never logs in to EZproxy, never scrapes ScienceDirect and never opens browser tabs itself; closed papers go through your own logged-in browser (the `browser-fetch` skill with Claude in Chrome, or by hand). Each paper includes a `proxy_url` (for UTM: `https://ezproxy.utm.my/login?url=...`) so **you** can open it in your browser and use the library login as normal ([closed papers through your browser](manual-full-text.md)). See [institutional access](institutional-access.md) for how other institutions reach the `fulltext` tier.

## Why most Elsevier papers have no abstract off-campus

Elsevier does not share its abstracts with OpenAlex or Semantic Scholar, so the free fallbacks return nothing for most `10.1016/...` DOIs. You still get full metadata and the EZproxy link. Where the network or an insttoken is entitled, Elsevier returns the abstract directly; at UTM, open `proxy_url` in your browser to read it.
