# Contributing to Pflegra

First off — thank you for considering a contribution. This project exists to help families navigate the German care system, and every improvement matters.

---

## Ways to contribute

### Bug reports
Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your deployment (HA Add-on / Docker / direct)

### Benefit amount updates
German care law (SGB XI) changes regularly. If you notice outdated amounts:
- All amounts live in `app/pflege_rules.py`
- Please include a source (e.g. link to the relevant law or Pflegekasse announcement)
- Open a PR or issue

### Feature requests
Open an issue describing:
- The use case (what problem does it solve?)
- Who would benefit
- Any relevant legal context (§ SGB XI reference if applicable)

### Code contributions
1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run the tests: `cd app && pytest tests/ -v`
5. All tests must pass — no regressions
6. Open a Pull Request with a clear description

---

## Development setup

```bash
# Clone
git clone https://github.com/Pflegra/core.git
cd core

# Install dependencies
pip install -r app/requirements_web.txt

# Run tests
cd app && pytest tests/ -v

# Run dev server
uvicorn web.app:app --reload --port 8000 --app-dir app
```

---

## Code style

- Python: standard `black` formatting, type hints where practical
- No external frontend frameworks — plain HTML/CSS/JS
- New features should include tests
- Fachlogik (care rules, calculations) must have tests
- German variable/function names for domain logic, English for infrastructure
- Commit messages in English (since v46)

---

## Key files to know

| File | Purpose |
|---|---|
| `app/pflege_rules.py` | All legal amounts — start here for benefit changes |
| `app/calculations.py` | Budget calculations and prognosis |
| `app/pflegegrad_rechner.py` | NBA care level calculator (§ 15 SGB XI) |
| `app/leistungsfinder.py` | Benefit finder logic |
| `app/db/schema.py` | DB schema v14, migrations |
| `app/models.py` | DB facade — imports from all db/ modules |
| `app/tests/` | pytest test suite |
| `app/web/routers/deps.py` | base_ctx, get_db, get_owner_id — canonical |
| `app/web/routers/` | FastAPI route handlers |
| `app/web/templates/` | Jinja2 HTML templates |
| `app/translations/` | DE/EN translation JSON files |

---

## Sensitive areas

- **Auth and security** (`app/web/auth.py`) — changes here need careful review
- **DB migrations** (`app/db/schema.py → DbSchema.migrate()`) — always additive, never destructive
- **pflege_rules.py** — changes here affect all calculations; always include source and year

---

## License

By contributing, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](LICENSE).
