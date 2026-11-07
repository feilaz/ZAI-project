.PHONY: db-up db-stop db-status db-logs db-shell db-check db-setup migrate create-admin api dev test

db-up:
	docker compose up -d --wait db

db-stop:
	docker compose stop db

db-status:
	docker compose ps

db-logs:
	docker compose logs --tail=100 db

db-shell:
	docker compose exec db sh -c 'exec psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

db-check:
	docker compose exec -T db sh -c 'PGPASSWORD="$$POSTGRES_PASSWORD" psql -h 127.0.0.1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1' < database/check.sql

db-setup: db-up
	docker compose exec -T db sh -c 'PGPASSWORD="$$POSTGRES_PASSWORD" exec psql -X -h 127.0.0.1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 --single-transaction --file=-' < database/setup.sql

migrate: db-setup

create-admin: db-setup
	PYTHONPATH=backend .venv/bin/python -m app.create_admin

api:
	.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload

dev: db-setup
	$(MAKE) api

test: db-up
	PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
	.venv/bin/python -m unittest discover -s generator -p 'test_*.py' -v

PROD_COMPOSE = docker compose -f compose.production.yaml

.PHONY: prod-build prod-db-setup prod-create-admin prod-http prod-cert-issue prod-up prod-status prod-logs prod-stop prod-cert-renew prod-cert-check prod-install-renewal

prod-build:
	$(PROD_COMPOSE) build api

prod-db-setup:
	$(PROD_COMPOSE) up -d --wait db
	$(PROD_COMPOSE) exec -T db sh -c 'PGPASSWORD="$$POSTGRES_PASSWORD" exec psql -X -h 127.0.0.1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 --single-transaction --file=-' < database/setup.sql

prod-create-admin: prod-db-setup
	$(PROD_COMPOSE) run --rm --no-deps api python -m app.create_admin

# First deployment only: serve the certificate challenge before HTTPS exists.
prod-http:
	CADDY_CONFIG=Caddyfile.http $(PROD_COMPOSE) up -d caddy

prod-cert-issue:
	$(PROD_COMPOSE) run --rm certbot issue

prod-up: prod-db-setup
	$(PROD_COMPOSE) up -d --build --wait api caddy

prod-status:
	$(PROD_COMPOSE) ps

prod-logs:
	$(PROD_COMPOSE) logs --tail=100 db api caddy

prod-stop:
	$(PROD_COMPOSE) stop

prod-cert-renew:
	$(PROD_COMPOSE) run --rm certbot renew --non-interactive
	$(PROD_COMPOSE) exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile --force

prod-cert-check:
	$(PROD_COMPOSE) run --rm certbot renew --dry-run

prod-install-renewal:
	sudo sh deploy/install-renewal.sh

.PHONY: frontend frontend-build

frontend:
	npm --prefix frontend run dev

frontend-build:
	npm --prefix frontend run build
