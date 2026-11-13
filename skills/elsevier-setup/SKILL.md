---
name: elsevier-setup
description: First-run setup and health check for the elsevier-research-mcp-utm tools. Use when the user wants to set up, configure or troubleshoot Elsevier / Scopus / ScienceDirect access, asks "is my Elsevier key working", "why can't I get full text", "what access do I have", or when any elsevier tool returns a key, 401, 403 or quota error.
---

# Elsevier setup

Goal: the user ends with a working API key, knows their access tier, and knows the download limits that protect their institution account.

## Rules

- **Never ask the user to paste an API key or insttoken into the chat.** Keys go into environment variables only. If the user pastes one anyway, tell them it is now in the conversation history and suggest regenerating it at dev.elsevier.com.
- Never print a key, even partly.
- Do not change the download limits to higher values unless the user says their library allows it.

## Steps

1. **Check.** Call `check_access`. Read `api_key_set`, `api_key_source` (env, file or none), `api_key_valid`, `config_file`, `config_file_found`, `tier`, `quota`, `limits`, `advice`, `config_problems`.
2. **No key** (`api_key_set` false): tell the user to
   - create a key at <https://dev.elsevier.com> (sign in, "Create API Key", any label and website), then
   - save it in the **config file** at the exact `config_file` path that `check_access` returned. This works in every host, including the Claude desktop app, which does not pass shell or launchd environment variables to plugin servers. The user runs these themselves (never put the key into a command you run):
     - macOS / Linux:
       ```
       mkdir -p ~/.config/elsevier-research-mcp-utm
       printf 'ELSEVIER_API_KEY=%s\n' 'PASTE-KEY-HERE' > ~/.config/elsevier-research-mcp-utm/.env
       chmod 600 ~/.config/elsevier-research-mcp-utm/.env
       ```
     - Windows: create `%APPDATA%\elsevier-research-mcp-utm\.env` in Notepad with the line `ELSEVIER_API_KEY=PASTE-KEY-HERE`.
   - Alternative where the host passes the environment through (Claude Code in a terminal): environment variable `ELSEVIER_API_KEY`. It wins over the file.
   - Then fully quit and restart the app, and run `check_access` again.
   - If `api_key_source` says `env` but the key is wrong, an old environment variable is overriding the file: remove it or fix it.
   - If `config_problems` mentions `chmod 600`, tell the user to run it.
3. **Key rejected** (`api_key_valid` false): the key is mistyped, revoked or has a stray space. Have them copy it again from dev.elsevier.com.
4. **Explain the tier** in plain words:
   - `metadata`: search works; Elsevier abstracts and full text do not. Normal off-campus.
   - `abstracts`: Elsevier abstracts work; full text does not.
   - `fulltext`: everything works on this network.
5. **If not `fulltext`**, give the options in this order:
   1. Ask the library for an Elsevier **insttoken** linked to the key, then add `ELSEVIER_INSTTOKEN=...` to the same config file. UTM: libsupport@utm.my. Offer to draft the email (purpose, roughly how many papers, that the tool enforces the library's limits; never include the key itself).
   2. Use campus Wi-Fi. A VPN may not help: many university VPNs are split tunnel and Elsevier still sees the home IP.
   3. Meanwhile, open-access papers work everywhere (`find_open_access`, `download_pdf`).
6. **Limits.** Show the `limits` line and explain: full text and PDFs from Elsevier count; searches, abstracts, open-access PDFs and exports do not. UTM defaults: 5 articles and 100 MB per 15 minutes, 20 per day, 10 s apart. Users at other institutions set `ERM_MAX_*` to their library's rules.
7. **Optional settings** (only if relevant): `ERM_DOWNLOAD_DIR` (where PDFs go), `ERM_PDF_NAME` (file name template), `OPENALEX_MAILTO`, `SEMANTIC_SCHOLAR_API_KEY`, `ERM_PROXY_HOST` (EZproxy links; empty turns them off).
8. Finish with one line: tier, insttoken yes/no, limits, and what to do next.
