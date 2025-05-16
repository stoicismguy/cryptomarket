FROM python:3.12-slim

# Установка зависимостей системы, если нужны
RUN apt-get update && apt-get install -y \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN useradd --user-group -ms /bin/bash app

# Переменные окружения
ENV PYTHONUNBUFFERED=1 HOME=/home/app

WORKDIR $HOME

# Установка pip и poetry
RUN pip install --upgrade pip poetry

# Копирование только файлов зависимостей для кеширования
COPY --chown=app:app ./pyproject.toml ./poetry.lock* $HOME/

# Установка зависимостей
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction

# Копирование всего проекта
COPY --chown=app:app . $HOME/

# Порт
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/home/app/docker-entrypoint.sh"]