# Project rules for Claude

## Before opening a PR

Run the CI checks locally and fix every failure before pushing or opening
a pull request. Do not push or open a PR if any of these fail:

```bash
hatch fmt --linter --check     # ruff lint (CI: `lint` job, step "Lint")
hatch run mypy:check           # mypy   (CI: `lint` job, step "Type Check")
hatch build                    # sdist + wheel build  (CI: step "Check Buildable")
hatch test                     # pytest suite (CI: `tests` matrix)
```

When the user reports a CI failure, fix it locally and re-verify all four
before re-pushing. Do not bypass formatting/lint rules with broad `# noqa`
suppressions unless the failure is a deliberate, narrow exception (e.g. an
intentionally-ambiguous Unicode literal), and always pair the suppression
with a comment explaining why.
