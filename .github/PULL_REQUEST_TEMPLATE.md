## What and why

<!-- One change per PR. Link the issue if there is one. -->

## Checklist

- [ ] `uv run pytest -q` passes
- [ ] `uv run ruff check .` passes
- [ ] `claude plugin validate .` passes (if the plugin, skills or agent changed)
- [ ] Tests added or updated (mocked HTTP, invented fixture data)
- [ ] `CHANGELOG.md` updated
- [ ] Docs updated (`docs/`, README) if behaviour or settings changed
- [ ] No API key, insttoken, `.env`, PDF, full text or cache committed
- [ ] Official APIs only; download limits, entitlement check and minimum gap unchanged (or the change is explained above)
