#!/bin/bash
set -e  # Выход при ошибке
source .env
poetry install

poetry run python src/manage.py migrate

echo "SUKA PYTHON"

echo $DEBUG
if [ "$DEBUG" == 1 ]; then
    echo "Запуск сервера в режиме разработки"
    exec poetry run python src/manage.py runserver 0.0.0.0:8000
else
    echo "Запуск сервера в режиме продакшена"
    exec poetry run gunicorn --bind 0.0.0.0:8000 cryptomarket.wsgi:application
fi