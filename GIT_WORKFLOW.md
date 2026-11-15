# Git Workflow (for the "Excelled" Git rubric row)

The rubric wants: git used, **feature branches**, **pull requests merged**,
and **branches cleaned up**. Do this in your repo, one feature at a time.

## 0. Initial setup

```bash
git init -b main
git add README.md requirements.txt .gitignore inventory/__init__.py tests/__init__.py
git commit -m "chore: project skeleton, README, requirements"
# Create an empty repo on GitHub, then:
git remote add origin https://github.com/<you>/inventory-management.git
git push -u origin main
```

## 1. One branch per feature

| Branch | Files | Commit message |
|--------|-------|----------------|
| `feature/crud-api` | `inventory/app.py` (CRUD + helper routes), `tests/test_api.py` | `feat: add CRUD routes and low-stock helper` |
| `feature/openfoodfacts` | `inventory/openfoodfacts.py`, `tests/test_openfoodfacts.py`, `tests/test_external_routes.py`, external/import routes in `app.py` | `feat: integrate OpenFoodFacts lookup and import` |
| `feature/cli` | `inventory/cli.py`, `tests/test_cli.py` | `feat: add argparse CLI` |

Tip: `mock_data.py` goes with `feature/openfoodfacts`; docs and Postman collection go on a `docs/route-plan` branch. To split `app.py` across the first two branches, commit the CRUD portion
first (leave the `# ---------- external API routes ----------` section and the
`from inventory import openfoodfacts as off` import out), then add them on the
second branch.

For each branch:

```bash
git checkout main && git pull
git checkout -b feature/crud-api
# ...add the files, run tests...
python -m unittest discover -s tests -t .
git add <files>
git commit -m "feat: add CRUD routes and low-stock helper"
git push -u origin feature/crud-api
```

## 2. Open and merge a Pull Request on GitHub

1. On GitHub click **Compare & pull request** for the pushed branch.
2. Write a short description (what changed, how it was tested).
3. Click **Merge pull request**, then **Delete branch**.

## 3. Clean up locally

```bash
git checkout main
git pull
git branch -d feature/crud-api
git fetch --prune        # removes stale remote-tracking refs
```

Repeat for the other two branches, and finally merge a `docs/readme` branch
if you edit the README later. At the end `git branch -a` should show only
`main`, and the GitHub **Pull requests > Closed** tab should list your merged PRs.
