install:
	pip install -r requirements.txt

run:
	python manage.py runserver

check:
	python manage.py check --database default

migrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

createsuperuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput