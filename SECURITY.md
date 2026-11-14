# Security policy

## Supported versions

Only the latest release on `main` gets fixes.

## What counts as a security issue

- An API key or insttoken leaking: in tool output, error messages, logs, the cache, exported files or test fixtures.
- A way to make the tool exceed the download limits, run fetches in parallel, or fetch without the entitlement check, which could get a user's institution account suspended.
- Writing files outside the download folder (path traversal through file names or `path`), or overwriting unrelated files.
- A way for content returned by an API (titles, abstracts, full text) to make the tool do something it was not asked to do.

## How to report

Use GitHub's **private vulnerability reporting**: the repository's **Security** tab, then **Report a vulnerability**. Please do not open a public issue or pull request for a security problem.

Include the version (`elsevier-research-mcp-utm version`), steps to reproduce, and what you expected. **Never include a real API key or insttoken**; use a fake one like `testkey123`.

You should get a first reply within 7 days. Fixes are released on `main` and noted in `CHANGELOG.md`, with credit if you want it.

## If your own key leaked

Regenerate it at <https://dev.elsevier.com> (and tell your library if an insttoken leaked), then update it with `setup`, the plugin settings or the config file.
