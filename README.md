# aximcyber
A Multi-tenant Information Security GRC SaaS Application

## Developer setup

Install the pinned development tooling and configure the repository hooks:

```bash
python -m pip install -r requirements-dev.txt
make setup-hooks
```

The hooks run Ruff formatting and linting, Bandit, and the repository's other
pre-commit checks before commits. CI remains the authoritative check for every
pull request.
