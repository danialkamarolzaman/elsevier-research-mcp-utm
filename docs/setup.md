# Setup

You need three things: [uv](https://docs.astral.sh/uv/), an Elsevier API key, and an MCP client (Claude Code, Claude Desktop, Cursor, VS Code, ...).

## 1. Install uv

- macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Open a new terminal afterwards so `uv` and `uvx` are on your PATH.

## 2. Get an API key

Sign in at <https://dev.elsevier.com>, click **Create API Key**, give it any label and website, and accept the terms. Creating the key is the one step that cannot be automated: it is your account and your agreement with Elsevier.

**Never paste the key into a chat with an AI assistant.** Use one of the three ways below.

## 3. Save the key (pick one)

### A. Claude Code plugin settings (easiest in Claude Code)

```
/plugin marketplace add danialkamarolzaman/elsevier-research-mcp-utm
/plugin install elsevier-research-mcp-utm@elsevier-research-mcp-utm
```

When the plugin is enabled, Claude Code asks for:

| Field | Stored | Needed |
|---|---|---|
| Elsevier API key | system credential store (hidden input) | yes, unless you use B or C |
| Elsevier insttoken | system credential store (hidden input) | no |
| Email for OpenAlex | Claude Code `settings.json` | no |

Leave a field empty if you already use the config file or environment variables. Restart Claude Code afterwards.

### B. `setup` command (any MCP client)

Run this **in your own terminal** (not through an AI assistant, the key prompt needs a real terminal):

```
uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm setup
```

It:

1. opens the Elsevier key page in your browser;
2. asks for the key with hidden input;
3. checks it with one Scopus search (metadata only, does not count toward the download limits); a rejected key can be re-entered, up to 3 times, and nothing is saved until a key works;
4. optionally asks for an insttoken (also checked) and an OpenAlex email;
5. saves them to the config file (below), keeping any other lines, private to you (`chmod 600` on macOS / Linux);
6. runs `doctor` and shows your access tier.

If a key is already saved, it asks before replacing it.

### C. Config file or environment variable (manual)

| OS | Config file |
|---|---|
| macOS / Linux | `~/.config/elsevier-research-mcp-utm/.env` (or `$XDG_CONFIG_HOME/elsevier-research-mcp-utm/.env`) |
| Windows | `%APPDATA%\elsevier-research-mcp-utm\.env` |

One `KEY=value` per line; `#` comments and quotes are fine. All settings are in [`.env.example`](../.env.example).

```
ELSEVIER_API_KEY=your-key-here
```

macOS / Linux:

```
mkdir -p ~/.config/elsevier-research-mcp-utm
printf 'ELSEVIER_API_KEY=%s\n' 'your-key-here' > ~/.config/elsevier-research-mcp-utm/.env
chmod 600 ~/.config/elsevier-research-mcp-utm/.env
```

Or as an environment variable, where the host passes your environment through (Claude Code started from a terminal):

- Windows (PowerShell): `[Environment]::SetEnvironmentVariable('ELSEVIER_API_KEY', '<key>', 'User')`
- macOS / Linux: `export ELSEVIER_API_KEY=<key>` in your shell profile

The Claude desktop app does **not** pass your shell environment to plugins; use A, B or the config file there. Set `ERM_CONFIG_FILE` to use a different file path.

### Which one wins

1. environment variable (`ELSEVIER_API_KEY`, ...)
2. Claude Code plugin settings
3. config file

`doctor` and `check_access` show where the key came from (`env`, `plugin`, `file` or `none`), never the key itself. If you fix a key in one place but an older one is still set higher up the list, the old one keeps winning.

## 4. Check

```
uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm doctor
```

or in Claude: *"check my Elsevier access"*. See [access tiers](access-tiers.md) for what the result means.

## 5. Add to other MCP clients

Claude Code without the plugin:

```
claude mcp add elsevier -- uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm
```

Other clients (Claude Desktop, Cursor, VS Code): command `uvx`, args `--from`, `git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm`, `elsevier-research-mcp-utm`. Use option B or C for the key.

## Updating

- Plugin: `/plugin marketplace update elsevier-research-mcp-utm`, then `/plugin update elsevier-research-mcp-utm`, then restart.
- uvx: `uvx` caches builds; add `--refresh` once to pick up a new version.

## Changing the key later

- Plugin settings: the key field is not shown in `/config` (sensitive fields are hidden). Disable and re-enable the plugin to be asked again, or use the config file instead and leave the plugin field empty. *(Not yet confirmed on every Claude Code version; please open an issue if it behaves differently.)*
- Config file: run `setup` again, or edit the file.
- Then restart the app.
