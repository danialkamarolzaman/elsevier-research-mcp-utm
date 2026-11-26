# Closed papers through your browser

**At UTM this is the way to get Elsevier full text.** Tested on campus Wi-Fi in November 2026: the ScienceDirect Article API refuses full text (`403`, "Requestor configuration settings insufficient"), even for open-access Elsevier papers, and UTM Library does not issue an Elsevier insttoken. So the API cannot fetch paywalled Elsevier papers at UTM, on or off campus.

Everything else still works through the API: Scopus search, citations, DOIs, open-access PDFs from any publisher, most non-Elsevier abstracts, reference export and the verify tools. Closed papers come through **your own logged-in browser session**, in one of two ways.

## Option A: Claude in Chrome does the clicking (recommended)

You log in; Claude opens one paper at a time in one tab and saves the PDF. The `browser-fetch` skill runs it; just ask *"download the closed papers through my browser"*.

1. **Once:** install the Claude in Chrome extension and in Chrome set *Settings › Privacy and security › Site settings › Additional content settings › PDF documents* to **Download PDFs**.
2. Claude opens the first paper's EZproxy link (`https://ezproxy.utm.my/login?url=...`). **You log in** with your UTM library account. Claude never types your password or solves a CAPTCHA.
3. For each paper, Claude calls `browser_fetch_start` (checks the limits, waits the 10 s gap, counts the paper), opens the link, clicks **View PDF / Download PDF**, then `browser_fetch_done` (finds the PDF in your Downloads folder, checks it is a real PDF, moves it into the download folder under a clean name, records its size, marks the queue item done).
4. At a limit it stops and tells you when the next paper is allowed.

## Option B: by hand (Safari or any browser)

1. Ask Claude for the list (or open `_open_manually.md`, written by the background worker): each paper has its EZproxy link and the file name to save under.
2. Open the links yourself **one at a time**, log in, download the PDF.
3. Save it into the download folder under the given name (the worker picks it up), or tell Claude where it is: `browser_fetch_done` files it and counts it.

## Keep to the library rules

UTM Library warns that these can get your UTM ID suspended. They apply to browser downloads too, and the tools enforce them for both options:

- one tab at a time, no opening many papers at once;
- at most 5 articles at once, and at most 100 MB in any 15 minutes (plus the tool's 20 per day and 10 s gap);
- no download managers, scripts or bulk downloading.

**Your risk:** publishers' terms restrict automated downloading, and the downloads run on your login. Option A keeps to human pace inside the library limits, but the responsibility stays with you. Stop at once if a page shows an unusual-traffic or access warning.

## Other institutions

If your library issues an insttoken, or your campus network is entitled through the API, the tool fetches full text headless: see [institutional access](institutional-access.md). Run *"check my Elsevier access"*; if the tier never reads `fulltext`, use this page.
