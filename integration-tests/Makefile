build:
	docker-compose build

test: down build
	docker-compose run tests poetry run pytest

down:
	docker-compose down