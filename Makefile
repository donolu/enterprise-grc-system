up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f web worker beat
migrate:
	docker compose exec web python manage.py migrate
createsuper:
	docker compose exec web python manage.py createsuperuser
shell:
	docker compose exec web python manage.py shell_plus || docker compose exec web python manage.py shell
test:
	docker compose exec web pytest -q
