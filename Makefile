.PHONY: db-up db-stop db-status db-logs db-shell db-check db-setup migrate create-admin api dev

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
