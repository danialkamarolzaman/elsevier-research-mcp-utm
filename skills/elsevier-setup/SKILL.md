---
name: elsevier-setup
description: First-run setup and health check for the elsevier-research-mcp-utm tools. Use when the user wants to set up, configure or troubleshoot Elsevier / Scopus / ScienceDirect access, asks "is my Elsevier key working", "why can't I get full text", "what access do I have", or when any elsevier tool returns a key, 401, 403 or quota error.
---

# Elsevier setup

Goal: the user ends with a working API key, knows their access tier, and knows the download limits that protect their institution account.

## Rules

- **Never ask the user to paste an API key or insttoken into the chat.** Keys go into the plugin settings prompt, the `setup` command (run by the user in their own terminal), the config file or environment variables. If the user pastes one anyway, tell them it is now in the conversation history and suggest regenerating it at dev.elsevier.com.
- Never print a key, even partly.
- Do not change the download limits to higher values unless the user says their library allows it.

## Steps

1. **Check.** Call `check_access`. Read `api_key_set`, `api_key_source` (env, plugin, file or none), `api_key_valid`, `config_file`, `config_file_found`, `tier`, `quota`, `limits`, `advice`, `config_problems`.
2. **No key** (`api_key_set` false): tell the user to create a key at <https://dev.elsevier.com> (sign in, "Create API Key", any label and website). This step is theirs; it cannot be automated. Then offer the ways to save it, easiest first:
   - **Claude Code plugin settings**: disable and re-enable the plugin (`/plugin`), and Claude Code asks for the key with hidden input and stores it in the system credential store.
   - **`setup` command**, which the user runs **in their own terminal window** (not via you, not with `!`: it needs a real terminal for hidden input). It opens the key page, checks the key with one Scopus search, and saves it to the config file:
     ```
     uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm setup
     ```
   - **Config file**, by hand, at the exact `config_file` path that `check_access` returned (works in every host, including the Claude desktop app, which does not pass shell environment variables to plugin servers). macOS / Linux:
     ```
     mkdir -p ~/.config/elsevier-research-mcp-utm
     printf 'ELSEVIER_API_KEY=%s\n' 'PASTE-KEY-HERE' > ~/.config/elsevier-research-mcp-utm/.env
     chmod 600 ~/.config/elsevier-research-mcp-utm/.env
     ```
     Windows: create `%APPDATA%\elsevier-research-mcp-utm\.env` in Notepad with the line `ELSEVIER_API_KEY=PASTE-KEY-HERE`.
   - **Environment variable** `ELSEVIER_API_KEY`, where the host passes the environment through (Claude Code started from a terminal).
   - Order of precedence: environment variable, then plugin settings, then config file. `api_key_source` says which one is in use (`env`, `plugin`, `file`). If the user fixed the key in one place but an older one higher up still wins, tell them to fix or remove that one.
   - Then fully quit and restart the app, and run `check_access` again.
   - If `config_problems` mentions `chmod 600`, tell the user to run it.
3. **Key rejected** (`api_key_valid` false): the key is mistyped, revoked or has a stray space. Have them copy it again from dev.elsevier.com.
4. **Explain the tier** in plain words:
   - `metadata`: search works; Elsevier abstracts and full text do not. Normal off-campus.
   - `abstracts`: Elsevier abstracts work; full text does not.
   - `fulltext`: everything works on this network.
5. **If not `fulltext`**:
   - **UTM users** (`proxy_url` on `ezproxy.utm.my`): do not suggest an insttoken or campus Wi-Fi. UTM issues no insttoken and the API refuses full text on campus too (tested November 2026). Explain the browser way (docs/manual-full-text.md): open-access copies come through the API; closed papers through the user's own logged-in browser, with the `browser-fetch` skill (Claude in Chrome, one paper at a time, `browser_fetch_start` / `browser_fetch_done`) or by hand in Safari or any browser. The user always logs in themselves.
   - Other institutions, in this order:
   1. Ask the library for an Elsevier **insttoken** linked to the key, then add `ELSEVIER_INSTTOKEN=...` to the same config file. Offer to draft the email (purpose, roughly how many papers, that the tool enforces the library's limits; never include the key itself).
   2. Use campus Wi-Fi. A VPN may not help: many university VPNs are split tunnel and Elsevier still sees the home IP.
   3. Meanwhile, open-access papers work everywhere (`find_open_access`, `download_pdf`).
6. **Limits.** Show the `limits` line and explain: full text and PDFs from Elsevier count; searches, abstracts, open-access PDFs and exports do not. UTM defaults: 5 articles and 100 MB per 15 minutes, 20 per day, 10 s apart. Users at other institutions set `ERM_MAX_*` to their library's rules.
7. **Optional settings** (only if relevant): `ERM_DOWNLOAD_DIR` (where PDFs go), `ERM_PDF_NAME` (file name template), `OPENALEX_MAILTO`, `SEMANTIC_SCHOLAR_API_KEY`, `ERM_PROXY_HOST` (EZproxy links; empty turns them off).
8. Finish with one line: tier, insttoken yes/no, limits, and what to do next.
