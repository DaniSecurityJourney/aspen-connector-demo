# AI Code Assistant: Secure Coding & Generation Instructions (SQLi / CWE-89 Focus)

## High-level Revision Plan
- Enforce prohibition of constructing SQL from untrusted inputs via string concatenation or interpolation; require parameterized queries or ORM usage.
- Provide explicit safe code patterns (parameterized queries, ORM examples) and prohibit unsafe examples.
- Add taint-source detection rules for the assistant and CI static checks (bandit/pip-audit + custom grep) to catch SQL concatenation patterns.
- Require input validation/whitelisting for identifiers and strong typing for parameters; document when raw SQL is acceptable and the required safeguards.
- Integrate automated security tests and a PR checklist to ensure reviews verify adherence before merge.

## Scope and Purpose
These instructions govern outputs from the AI Code Assistant tool with the explicit goal of preventing generation of SQL Injection (CWE-89) vulnerabilities. They apply whenever the assistant suggests, generates, or modifies code that interacts with databases or constructs SQL.

## Mandatory Security Policies (must-follow)
- Never generate code that constructs SQL queries by concatenating or interpolating untrusted input (request params, form data, cookies, headers, environment variables, CLI args, or any external input).
- Always prefer parameterized queries (prepared statements) or ORM query-building APIs. When raw SQL is required, use parameter binding and strict whitelisting for any identifiers (table/column names).
- Treat the following as tainted/untrusted by default: request.args, request.form, request.values, request.get_json(), request.headers, request.cookies, os.environ, sys.argv, input(), any data from external services/HTTP endpoints.
- Enforce least-privilege DB credentials and limit DB user permissions in examples (e.g., read-only for queries that only read).
- Include input validation (type checks, length limits) and allowlist (whitelist) checks where user-controlled values influence SQL identifiers or clauses (ORDER BY, LIMIT, table/column names).
- When generating examples, include comments documenting why the pattern is safe and cite the mitigation (e.g., parameterized query prevents injection).

## Taint Detection Rules for the Assistant
- Flag any SQL string constructed via:
  - f-strings, format(), concatenation (+), or % interpolation when variables originate from taint sources.
  - string.join or other templating where tainted values are inserted directly into SQL text.
- If taint is detected, refuse to output the unsafe pattern. Instead:
  - Suggest a parameterized alternative or ORM-based approach.
  - If the user explicitly requests raw SQL with dynamic identifiers, require an explicit allowlist and demonstrate safe mapping.
- Always ask clarifying questions if the provenance (trusted vs untrusted) of data is unclear.

## Safe Coding Patterns (examples to follow in generated code)
- Use DB API parameterization (do not string-format variables into SQL).

PostgreSQL example (psycopg2):
```python
import psycopg2

conn = psycopg2.connect(dsn)
with conn.cursor() as cur:
    # Safe: parameterized query prevents SQL injection
    cur.execute("SELECT id, name FROM users WHERE email = %s AND active = %s", (email, True))
    rows = cur.fetchall()
```

SQLite example (sqlite3):
```python
import sqlite3

conn = sqlite3.connect("db.sqlite")
cur = conn.cursor()
# Safe: use ? placeholders and pass params as a tuple
cur.execute("SELECT * FROM products WHERE sku = ?", (sku,))
result = cur.fetchall()
```

SQLAlchemy ORM example:
```python
from sqlalchemy import select
from models import User  # ORM model

stmt = select(User).where(User.email == email)  # safe ORM binding
result = session.execute(stmt).scalars().all()
```

Whitelisting identifiers (only use when absolutely needed):
```python
# Example: allowlist for ORDER BY column
ALLOWED_SORT_COLUMNS = {"name", "created_at", "price"}

def build_order_clause(sort_col):
    if sort_col not in ALLOWED_SORT_COLUMNS:
        raise ValueError("Invalid sort column")
    # safe: identifier chosen from an allowlist, not from raw input
    return f"ORDER BY {sort_col}"

# Then use parameterized query for values
```

## Unsafe Patterns (explicitly prohibited)
- Never generate code like the following:
```python
# Unsafe - DO NOT GENERATE
query = "SELECT * FROM users WHERE username = '" + request.args.get('user') + "'"
cursor.execute(query)
```
```python
# Unsafe - DO NOT GENERATE
query = f"SELECT * FROM products WHERE name = '{product_name}'"
cursor.execute(query)
```
- Avoid any example that inserts raw user input into SQL text for clauses, conditions, table or column names without strict allowlisting and validation.

## When Raw SQL Is Required (strict rules)
- Require documented justification in the code comment and PR.
- Mandatory safeguards:
  - Use parameter binding for values (never inline values).
  - For dynamic identifiers, use a pre-approved allowlist mapping user-provided tokens to known safe identifiers.
  - Validate types, lengths, and acceptable ranges for numeric inputs.
  - Log and monitor queries and failures; prefer database-side roles with restrictive permissions.
- Provide a minimal example pattern:
```python
# Only allowed with justification: dynamic column sort using allowlist
ALLOWED_COLUMNS = {"name": "name", "date": "created_at"}

sort_key = request.args.get("sort", "name")
if sort_key not in ALLOWED_COLUMNS:
    raise ValueError("Invalid sort parameter")

sql = "SELECT id, name FROM items WHERE category = %s ORDER BY " + ALLOWED_COLUMNS[sort_key]
cursor.execute(sql, (category,))
```

## AI Assistant Behavior Requirements
- If user-provided code contains unsafe SQL patterns, the assistant must:
  - Highlight the exact vulnerability and propose a secure replacement.
  - Automatically output the secure refactor (parameterized/ORM) and include a brief explanation.
- If asked to produce insecure code, refuse and provide secure alternatives.
- Always include in the generated code:
  - A comment indicating the data sources treated as untrusted.
  - The mitigation used (parameterized query, allowlist, ORM).
- If generating new database-using code, include at least one unit test or test scaffold that demonstrates correct handling of untrusted input.

## Static Analysis & CI Integration (required snippets)
- Ensure repository CI runs the following checks on PRs:
  - Python security linters: bandit
  - Dependency vulnerability scanners: pip-audit or safety
  - Custom grep/regex check for forbidden SQL construction patterns
- Example GitHub Actions workflow (add to .github/workflows/security.yml):
```yaml
name: Security Checks

on: [pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install bandit pip-audit
      - name: Run bandit
        run: bandit -r .
      - name: Run pip-audit
        run: pip-audit --bare
      - name: Check for SQL string concat patterns
        run: |
          # Fail if direct SQL building from common taint sources is detected
          if grep -R --line-number -E "(f?\".*SELECT|f?\".*INSERT|f?\".*UPDATE|\\+.*request\\.args|\\+.*request\\.form|f\\\".*request\\.args|%\\s*\\(" .; then
            echo "Potential unsafe SQL construction detected. Please use parameterized queries or ORM."
            exit 1
          fi
```
- Customize grep/regex to match project patterns; false positives allowed but must be reviewed.

## Testing and Review Requirements
- Every PR that adds or changes DB access must:
  - Include unit tests that assert safe handling of malicious-like inputs (e.g., inputs containing SQL meta-characters should not alter query semantics).
  - Include a short security note in PR description describing how inputs are validated/whitelisted and why the pattern is safe.
  - Pass CI security checks before merge.
- Security code review checklist (to include in PR template):
  - Are all queries parameterized or built via ORM?
  - Are all user-controllable identifiers validated against an allowlist?
  - Are tainted sources documented and validated?
  - Are DB credentials least-privilege and stored securely (secrets manager, not in code)?

## PR Template Snippet (to include in .github/PULL_REQUEST_TEMPLATE.md)
```markdown
### Security checklist
- [ ] All SQL queries are parameterized or use ORM APIs.
- [ ] Any dynamic identifiers are validated via allowlist with justification.
- [ ] Unit tests cover malicious input cases.
- [ ] CI bandit/pip-audit checks pass.
- [ ] Short note: how user input is treated and why this is safe.
```

## References
- CWE-89: SQL Injection — https://cwe.mitre.org/data/definitions/89.html
- OWASP SQL Injection Prevention Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html

-- End of instruction file.