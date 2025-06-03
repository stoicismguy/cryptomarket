import json
import logging
from django.utils import timezone

# Получаем уже настроенный логгер
logger = logging.getLogger('api_requests')

class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Логируем только если это API запрос
        if request.path.startswith('/api/'):
            # Получаем тело запроса
            body = None
            if request.body:
                try:
                    body = json.loads(request.body)
                except json.JSONDecodeError:
                    body = request.body.decode('utf-8')

            # Логируем запрос
            logger.info(f"{request.method} {request.path} - {json.dumps(body, ensure_ascii=False) if body else 'No body'}")

        response = self.get_response(request)

        # Логируем ответ для API запросов
        if request.path.startswith('/api/'):
            # Получаем тело ответа
            response_body = None
            if hasattr(response, 'content'):
                try:
                    response_body = json.loads(response.content)
                except json.JSONDecodeError:
                    try:
                        response_body = response.content.decode('utf-8')
                    except:
                        response_body = 'Binary content'

            # Используем разные цвета в зависимости от статуса
            if 200 <= response.status_code < 300:
                log_level = logging.INFO
            elif 400 <= response.status_code < 500:
                log_level = logging.WARNING
            else:
                log_level = logging.ERROR

            logger.log(log_level, f"Response {response.status_code}: {json.dumps(response_body, ensure_ascii=False) if response_body else 'No content'}")

        return response 