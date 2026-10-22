SECRETS ?= /Volumes/Plumbline/secrets.env
CHECKER = services/checker
CHECKER_URL ?= https://plumbline-checker.onrender.com

.PHONY: env types doctor test test-db db-push-test db-push seed lint dev-checker dev-web e2e

e2e:
	pnpm -C apps/web exec playwright test

# Copies secrets into the gitignored env files each app reads.
env:
	install -m 600 $(SECRETS) $(CHECKER)/.env
	{ grep -E '^(SUPABASE_URL|SUPABASE_ANON_KEY)=' $(SECRETS) | sed 's/^/NEXT_PUBLIC_/'; \
	  echo "NEXT_PUBLIC_CHECKER_URL=$(CHECKER_URL)"; \
	  grep -E '^DEMO_USER_PASSWORD=' $(SECRETS); } > apps/web/.env.local
	chmod 600 apps/web/.env.local

# Regenerate the web app's API types from the deployed checker's OpenAPI schema.
types:
	pnpm -C apps/web exec openapi-typescript $(CHECKER_URL)/openapi.json -o lib/types.gen.ts

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

seed:
	cd $(CHECKER) && uv run --env-file .env python scripts/seed.py

lint:
	cd $(CHECKER) && uv run ruff check . && uv run ruff format --check .

dev-checker:
	cd $(CHECKER) && uv run --env-file .env uvicorn plumbline.api:app --reload --port 8000

dev-web:
	pnpm -C apps/web dev
