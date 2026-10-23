"""Enable login for the plumbline_checker role (migration 0006) with a fresh password and write
CHECKER_DATABASE_URL into secrets.env. Local admin only; prints no secrets.

    uv run --env-file .env python scripts/checker_role.py /Volumes/Plumbline/secrets.env
"""

import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql

secrets_file = Path(sys.argv[1])
admin_url = os.environ["DATABASE_URL"]
ref = os.environ["SUPABASE_URL"].split("//")[1].split(".")[0]
host = re.search(r"@([^:/]+)", admin_url).group(1)
password = secrets.token_urlsafe(32)
with psycopg.connect(admin_url, autocommit=True) as conn:
    conn.execute(
        sql.SQL("alter role plumbline_checker login password {}").format(sql.Literal(password))
    )
url = f"postgresql://plumbline_checker.{ref}:{quote(password, safe='')}@{host}:5432/postgres"
lines = [
    ln for ln in secrets_file.read_text().splitlines() if not ln.startswith("CHECKER_DATABASE_URL=")
]
lines.append(f"CHECKER_DATABASE_URL={url}")
secrets_file.write_text("\n".join(lines) + "\n")
print("plumbline_checker can log in; CHECKER_DATABASE_URL written to", secrets_file)
