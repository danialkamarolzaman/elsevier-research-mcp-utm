# Troubleshooting

Start with `doctor` (terminal) or *"check my Elsevier access"* (Claude). It shows where the key came from, the access tier and advice.

| Symptom | Meaning | Fix |
|---|---|---|
| `API key set: no (from none)` | no key found anywhere | run `setup`, fill in the plugin settings, or add `ELSEVIER_API_KEY=...` to the config file ([setup](setup.md)); restart the app |
| key set in the shell, but `from none` in the Claude desktop app | the desktop app does not pass your shell environment to plugins | use the plugin settings, `setup` or the config file |
| `401 AUTHENTICATION_ERROR`, "API key rejected" | the key is wrong, revoked, or has a stray space | copy it again from dev.elsevier.com; check `from env/plugin/file` to see which copy is being used |
| a fixed key is still rejected | an older key higher up wins (env, then plugin, then file) | fix or remove the old one; `doctor` shows its source |
| `401 AUTHORIZATION_ERROR`, "not entitled to this view" | key is fine; this network has no abstract access | normal off-campus; see [institutional access](institutional-access.md) |
| `403`, "Requestor configuration settings insufficient" | key is fine; no full-text access from this network or token | campus Wi-Fi or an insttoken |
| `403` on campus VPN | split-tunnel VPN; Elsevier sees your home IP | check your public IP; use campus Wi-Fi or an insttoken |
| `429`, "quota or throttle limit" | Elsevier weekly quota or rate limit reached | wait until the time shown; searches are cached, so repeats are free |
| "limit: 5/5 articles in 15 min" (or MB, or daily) | the tool's library-rule guard | wait until the time shown; do not raise the limits unless your library allows it |
| no abstract for an Elsevier paper | Elsevier withholds abstracts from free sources | normal off-campus; open `proxy_url` in your browser, or use campus / insttoken |
| `NOT_PDF` | the server sent a web page instead of a PDF | open `proxy_url` in your browser |
| "This repository isn't a marketplace" | old plugin version or wrong name | `/plugin marketplace add danialkamarolzaman/elsevier-research-mcp-utm` (owner/repo) |
| `uvx: command not found` / `'uvx' is not recognized` | uv not installed or not on PATH | install uv, open a new terminal, restart the app |
| server fails to start after an update | stale uv cache | run the uvx command once with `--refresh` |
| `setup needs a real terminal` | `setup` was run through an assistant or a pipe | open a terminal window and run it there |
| `config file is readable by other users` | the file is not private (macOS / Linux) | `chmod 600 <file>` |
| `config file line N: ... skipped` | a line without `=` or with a bad name | fix that line; the message never shows the value |

Still stuck? Open an issue with the `doctor` output. It never contains your key, but check before posting.
