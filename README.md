# aximcyber
A Multi-tenant Information Security GRC SaaS Application

## Developer setup

Create the repository's Python 3.12 environment, install frontend dependencies,
and configure the repository hooks:

```bash
make bootstrap
```

`make bootstrap` uses `.venv312`, installs `requirements-dev.txt` and
`frontend/package-lock.json`, then installs both commit and push hooks. It uses
npm's legacy peer resolver temporarily while the ESLint and Next.js peer-range
conflict is addressed in #409. The pre-push hook validates the branch name and
runs frontend linting, type checking and unit tests for frontend changes;
backend type checking uses the same repository environment. CI remains the
authoritative check for every pull request.

To recreate the environment after changing dependencies, remove `.venv312` and
`frontend/node_modules`, then run `make bootstrap` again.
