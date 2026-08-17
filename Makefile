.PHONY: install proto-gen test test-unit lint format typecheck dev-db dev-db-down

install:
	poetry install

proto-gen:
	poetry run python -m grpc_tools.protoc \
		-I proto \
		--python_out=src \
		--grpc_python_out=src \
		--pyi_out=src \
		proto/spiritvpn/customer/v1/customer.proto

test:
	poetry run pytest

test-unit:
	poetry run pytest tests/unit

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

typecheck:
	poetry run mypy -p spiritvpn_bot

dev-db:
	docker compose -f docker-compose.dev.yml up -d --wait

dev-db-down:
	docker compose -f docker-compose.dev.yml down -v
