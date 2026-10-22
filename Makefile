SECRETS ?= /Volumes/Plumbline/secrets.env
CHECKER = services/checker

.PHONY: env doctor test test-db db-push-test db-push lint dev-checker dev-web

# Copies secrets into the gitignored env files each app reads.
env:
	install -m 600 $(SECRETS) $(CHECKER)/.env
	{ grep -E '^(SUPABASE_URL|SUPABASE_ANON_KEY)=' $(SECRETS) | sed 's/^/NEXT_PUBLIC_/'; } > apps/web/.env.local
	chmod 600 apps/web/.env.local

doctor:
	cd $(CHECKER) && uv run --env-file .env python scripts/doctor.py

test:
	cd $(CHECKER) && uv run pytest -q

test-db:
	cd $(CHECKER) && uv run --env-file .env pytest -m db -q

# Migrations via the Supabase CLI; db-push-test first, always.
SUPABASE = pnpm dlx supabase@2.121.0
db-push-test:
	cd $(CHECKER) && uv run --env-file .env sh -c 'cd ../.. && $(SUPABASE) db push --yes --db-url "$$TEST_DATABASE_URL"'

db-push:
	cd $(CHECKER) && uv run --env-file .env sh -c 'cd ../.. && $(SUPABASE) db push --yes --db-url "$$DATABASE_URL"'

lint:
	cd $(CHECKER) && uv run ruff check . && uv run ruff format --check .

dev-checker:
	cd $(CHECKER) && uv run --env-file .env uvicorn plumbline.api:app --reload --port 8000

dev-web:
	pnpm -C apps/web dev
