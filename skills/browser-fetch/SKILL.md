---
name: browser-fetch
description: Download closed (paywalled) papers through the user's own logged-in browser, one at a time, inside the library limits. Use when the user asks to "download the closed papers", "get the paywalled ones", "fetch through EZproxy", "get the full text" and the API has no full-text access (always at UTM), or when _open_manually.md lists papers. Needs Claude in Chrome; Safari and other browsers are by hand.
---

# Browser-assisted fetch of closed papers

At UTM the Elsevier API gives no full text (tested on campus Wi-Fi, November 2026; no insttoken is issued), so closed papers come through the user's own browser session: **the user logs in to EZproxy, Claude opens one paper at a time and saves the PDF.** The `browser_fetch_start` / `browser_fetch_done` tools keep the library limits and file the PDF.

## Rules (no exceptions)

- **The user logs in.** Never type, ask for or read a password, OTP or UTM ID. Never solve a CAPTCHA or a "verify you are human" check: stop and ask the user to do it.
- **One tab.** Open one tab for the whole run and reuse it. Never open papers in parallel.
- **Every paper goes through `browser_fetch_start` first.** If it refuses (limit, daily cap, busy), stop and tell the user the `next_allowed` time. Never retry in a loop, never work around it.
- **Only the papers the user chose.** No crawling, no "download all issues", no supplementary files unless asked.
- **Open access first.** Before the browser, try `download_pdf` (or the queue worker): open-access copies are free and not counted.
- If a page shows an access-denied, rate-limit or unusual-traffic warning, stop at once and tell the user.

## Steps

1. **List the papers.** From the user, from `queue_status` (`manual` and `blocked` papers) or from `_open_manually.md`. Remove any already saved or open access.
2. **Load Claude in Chrome** with one ToolSearch call (`tabs_context_mcp`, `tabs_create_mcp`, `navigate`, `find`, `read_page`, `computer`). No Chrome tools (Safari, other browsers)? Give the user the `open_url` and `save_as` of each paper to download by hand, then call `browser_fetch_done` for each.
3. **One-time Chrome setting.** Ask the user to set *Settings › Privacy and security › Site settings › Additional content settings › PDF documents* to **Download PDFs**, so a PDF link saves a file instead of opening the viewer. Ask once; skip if they already did.
4. **Login.** Create one tab, navigate to the first paper's `open_url`. If EZproxy shows the UTM login page, ask the user to log in in that tab and wait for their OK.
5. **For each paper, one after another:**
   1. `browser_fetch_start(doi)`. Refused: stop (rule above). `already_saved`: skip.
   2. Navigate the tab to `open_url`. On the ScienceDirect article page, `find` the **View PDF** / **Download PDF** link and click it once.
   3. `browser_fetch_done(doi)`. It waits for the download, checks it is a real PDF, moves it to the download folder as `save_as`, records its size and marks the queue item done.
   4. `NOT_PDF` or "no new PDF": check the tab (login expired? no subscription for this journal: "Get access" / "Purchase PDF"?). Do not buy anything; tell the user and move on to the next paper.
6. **Finish.** Report: saved (paths), skipped and why, limit usage, and when the next batch is allowed if the window filled. Leave the tab open for the user.

After this, `check_quotes`, `verify_references`, the `claim-verifier` and `research-draft` read the PDFs, so those papers can be cited as `[FT]`.
