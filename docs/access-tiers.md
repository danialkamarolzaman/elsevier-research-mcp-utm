# Access tiers

What you can get depends on the network you are on and whether you have an insttoken, not on the tool. `doctor` and `check_access` test this live (nothing is downloaded or counted).

| Tier | What works | Typical situation |
|---|---|---|
| `none` | nothing | no key, or the key is rejected |
| `metadata` | Scopus search: titles, authors, DOI, PII, citations; open-access papers; abstracts of most non-Elsevier papers (OpenAlex / Semantic Scholar) | home or mobile network, API key only |
| `abstracts` | + Elsevier abstracts | subscribed network or insttoken (rare without full text) |
| `fulltext` | + ScienceDirect full text and PDFs of subscribed journals | campus Wi-Fi, or an insttoken |

## How the check works

1. **Key**: one Scopus search. `401 AUTHENTICATION_ERROR` = the key is wrong.
2. **Abstracts**: one Abstract Retrieval call. `401 AUTHORIZATION_ERROR` = the key is fine, this network is not entitled to that view. This is normal off-campus and not an error with your key.
3. **Full text**: the free entitlement endpoint for one paper. `403` with "Requestor configuration settings insufficient" = this network or token is not entitled.

## What "headless" means here

The tool only uses the official Elsevier APIs. It never logs in to EZproxy, never scrapes ScienceDirect, and never opens browser tabs. Each paper includes a `proxy_url` (for UTM: `https://ezproxy.utm.my/login?url=...`) so **you** can open it in your browser and use the library login as normal. See [institutional access](institutional-access.md) for how to reach the `fulltext` tier.

## Why most Elsevier papers have no abstract off-campus

Elsevier does not share its abstracts with OpenAlex or Semantic Scholar, so the free fallbacks return nothing for most `10.1016/...` DOIs. You still get full metadata and the EZproxy link. On campus or with an insttoken, Elsevier returns the abstract directly.
