# elsevier-research-mcp-utm

A Claude Code plugin and MCP server for searching Scopus and fetching ScienceDirect papers through the official Elsevier APIs, with **institution download limits built in**. The defaults follow the UTM Library e-resource rules.

> **Unofficial.** Not affiliated with or endorsed by Elsevier or Universiti Teknologi Malaysia. Content you fetch is governed by Elsevier's terms and your institution's licence: do not share or redistribute it.

**Status: 0.4 (early).**

## Install in Claude Code

Needs [uv](https://docs.astral.sh/uv/) and an Elsevier API key saved in the config file or as `ELSEVIER_API_KEY` (see [Setup](#setup)).

```
/plugin marketplace add danialkamarolzaman/elsevier-research-mcp-utm
/plugin install elsevier-research-mcp-utm@elsevier-research-mcp-utm
```

Restart Claude Code, then ask: *"check my Elsevier access"*. The plugin adds:

- the MCP server `elsevier` (the tools below)
- skills: `elsevier-setup` (first-run check), `literature-review` (search → screen → fetch → export, within the limits), `research-draft` (grounded, verified drafts, see below)
- the `claim-verifier` agent, which fact-checks drafts independently

## Research prompt: grounded drafts from real papers

With the plugin, just ask, e.g. *"Draft a 1,500-word literature review on knowledge graphs for predictive maintenance"*; the `research-draft` skill runs the whole process. With other MCP clients, paste one of the prompts below and fill in the `{...}` parts.

What it does:

- searches the **last 5 years** (from today): the **most-cited** papers plus a few **recent** ones from the last 2 years, which have not had time to collect citations;
- pauses twice for your OK: on the search query, and on the list of papers;
- cites only papers a tool actually returned, in **IEEE** style, with every citation marked **[FT]** (full text read) or **[AB]** (abstract only);
- has an **independent verifier** re-check every reference, claim and number against the sources, then fixes what fails (up to 2 rounds) and shows you anything still unresolved.

> This approach greatly reduces made-up content and makes the rest easy to spot, but no prompt can guarantee zero errors. Read the verification report and spot-check claims before you use the draft.

### Full prompt

````text
You are my research assistant. Use only the elsevier-research tools (search_scopus, get_abstract,
find_open_access, get_fulltext, download_pdf, export_references) as your source of facts.

TASK
- Topic / question: {what you want to know}
- Document to draft: {literature review section | background chapter | related work | short report}
- Scope: last {5} years from today (or {2022-2026}), about {20} papers, {articles and reviews}
- Citation style: IEEE (numbered [1], [2] in order of first citation)
- Length: {about 1,500 words}

RULES (no exceptions)
1. Cite only papers whose DOI was returned by a tool call in this session. Never cite from memory,
   never invent or "correct" a DOI, author, year, title or journal.
2. Every factual sentence ends with a citation. Sentences that are your own synthesis start with
   "Overall," or "Taken together," and cite the papers they combine.
3. Mark each citation [FT] (you read the full text) or [AB] (abstract only), e.g. [3, FT].
   Never use a paper you only know by its title for any claim.
4. Numbers (accuracy, error, dataset or sample size) only from [FT], or from [AB] if the abstract
   states them. Copy them exactly, with units.
5. If the retrieved papers do not cover a point, write "No retrieved source covers this" and
   suggest a search. Do not fill the gap from general knowledge.
6. Respect my institution's download limits: find_open_access first, full text in batches of at
   most 5; if a tool refuses because of a limit, stop and tell me the time it gives. Never retry
   in a loop.

STEPS
1. Show me the Scopus query and the year window, then wait for my OK.
2. Run it twice: sorted by citations over the whole window, and sorted by date over the last
   2 years. Show one screening table: [cited]/[recent], year, first author, title, journal,
   citations, open access, relevant (yes/no + one-line reason from the abstract).
3. Wait for me to confirm the papers.
4. Read the abstracts of all of them, and the full text where available (open access first).
5. Write the draft. End it with: References (IEEE, with DOI); Sources table (n, DOI, [FT]/[AB],
   where the full text came from); Verification table (claim, citation, [FT]/[AB], supporting
   quote or section); Gaps (questions the papers did not answer).
6. VERIFY: if you can start a subagent, give a fresh one only the draft and these tools and have
   it check every reference (DOI exists, title/author/year/journal match), every citation, every
   claim (supported / partial / unsupported / contradicted) and every number against the source
   text. Otherwise do this yourself in a separate pass, re-reading each source, not your notes.
7. REWORK: fix every problem found (correct, weaken or remove the claim; never add a citation you
   did not retrieve and read), then verify again. At most 2 rounds. Then show me the final draft,
   the verification summary, and any problem still unresolved.
8. export_references to BibTeX and give me the file path.
````

### Short prompt

````text
Using only the elsevier-research tools, draft {a 500-word literature summary} on {topic} from the
last 5 years: most-cited papers plus a few recent ones. Show me the query and the paper list first
and wait for my OK. Cite in IEEE style only papers whose DOI a tool returned, mark each citation
[FT] (full text read) or [AB] (abstract only), never use numbers you did not read, write "No
retrieved source covers this" for gaps, and stay within the download limits. Then have an
independent verifier (a fresh subagent, or a separate pass re-reading the sources) check every
reference, claim and number, fix anything false (up to 2 rounds), and end with the reference list,
a claim -> source verification table and any problem still unresolved.
````

## Tools

| Tool | What it does | Counts toward limits |
|---|---|---|
| `check_access` | key valid?, access tier, Elsevier quota, limit usage | no |
| `search_scopus` | Scopus advanced search, sorted by citations, date or relevance | no |
| `get_abstract` | abstract + metadata for a DOI: Elsevier (if entitled) → OpenAlex → Semantic Scholar | no |
| `find_open_access` | free legal copy (PDF link, licence, version) via OpenAlex | no |
| `get_fulltext` | ScienceDirect full text as plain text, paged; re-reading is free from cache | **yes** |
| `download_pdf` | one PDF: open-access copy first (not counted), else Elsevier if entitled | **yes** (Elsevier only) |
| `download_batch` | up to 5 PDFs one after another; stops at the first limit refusal | **yes** (Elsevier only) |
| `export_references` | BibTeX, RIS (EndNote / Zotero / Mendeley) or CSV for up to 100 DOIs | no |

Before any counted fetch the tool checks entitlement (free). With no access nothing is downloaded and nothing is counted. PDFs are named `{first_author} {year} - {title}.pdf` (`ERM_PDF_NAME`), saved in `ERM_DOWNLOAD_DIR`, and never downloaded twice; two different papers with the same name are both kept (the second gets its DOI appended).

**About abstracts off-campus:** Elsevier withholds its own abstracts from OpenAlex and Semantic Scholar. Off-campus without an insttoken, most Elsevier papers therefore come back with full metadata but no abstract; the result says so and gives an EZproxy link. Open-access and most non-Elsevier papers do get abstracts.

## Why the limits matter

UTM Library warns that the following can get your UTM ID suspended:

- opening multiple tabs at the same time
- downloading more than 5 articles at once
- downloading more than 100 MB in 15 minutes

Every full-text or PDF fetch is logged locally. The tool refuses a fetch that would break a limit and tells you when the next one is allowed. Searches and metadata do not count.

| Setting | Default |
|---|---|
| `ERM_MAX_ARTICLES_PER_WINDOW` | 5 |
| `ERM_MAX_MB_PER_WINDOW` | 100 |
| `ERM_WINDOW_MINUTES` | 15 |
| `ERM_MAX_ARTICLES_PER_DAY` | 20 |
| `ERM_MIN_DELAY_SECONDS` | 10 |

Users at other institutions should set these to match their own library's rules.

## Access tiers

| Tier | What you get | How |
|---|---|---|
| metadata | titles, authors, DOI, PII, citations | any network, API key only |
| abstracts | + Elsevier abstracts (others come from free sources at every tier) | subscribed network or insttoken |
| fulltext | + ScienceDirect full text | subscribed network (campus Wi-Fi) or insttoken |

The tool is **headless only through the API**. It never scrapes ScienceDirect or logs in to EZproxy. Each paper includes a `proxy_url` (EZproxy link) that you can open yourself in a browser.

## Setup

1. Get an API key at <https://dev.elsevier.com> and save it in the **config file** (works in every app, including the Claude desktop app, which does not pass your shell environment to plugins):

   | OS | Config file |
   |---|---|
   | macOS / Linux | `~/.config/elsevier-research-mcp-utm/.env` (or `$XDG_CONFIG_HOME/elsevier-research-mcp-utm/.env`) |
   | Windows | `%APPDATA%\elsevier-research-mcp-utm\.env` |

   ```
   ELSEVIER_API_KEY=your-key-here
   ```

   macOS / Linux, in a terminal:

   ```
   mkdir -p ~/.config/elsevier-research-mcp-utm
   printf 'ELSEVIER_API_KEY=%s\n' 'your-key-here' > ~/.config/elsevier-research-mcp-utm/.env
   chmod 600 ~/.config/elsevier-research-mcp-utm/.env
   ```

   The file takes any setting from [`.env.example`](.env.example), one `KEY=value` per line; `#` comments and quotes are fine. **Environment variables win over the file**, so the old method still works where the host passes your environment through (Claude Code in a terminal):
   - Windows (PowerShell): `[Environment]::SetEnvironmentVariable('ELSEVIER_API_KEY', '<key>', 'User')`
   - macOS / Linux: `export ELSEVIER_API_KEY=<key>` in your shell profile

   `doctor` / `check_access` show where the key was found (`env`, `file` or `none`), never the key itself. Restart the app after changing the file. Set `ERM_CONFIG_FILE` to use a different path.
2. Optional: ask your library for an Elsevier **insttoken** and add `ELSEVIER_INSTTOKEN=...` to the same file. UTM: libsupport@utm.my.
3. Install [uv](https://docs.astral.sh/uv/), then check your setup:

   ```
   uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm doctor
   ```

4. Add it to Claude Code as a plugin (above), or as a plain MCP server for any MCP client:

   ```
   claude mcp add elsevier -- uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm
   ```

   Other clients (Claude Desktop, Cursor, VS Code) use the same command: `uvx` with args `--from`, `git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm`, `elsevier-research-mcp-utm`.

All settings are listed in [`.env.example`](.env.example).

## Development

```
uv sync
uv run pytest -q          # mocked tests, no key needed
uv run ruff check .
ERM_LIVE=1 uv run pytest tests/test_live.py   # real API, uses your key
```

## License

MIT for the code. See [LICENSE](LICENSE).
