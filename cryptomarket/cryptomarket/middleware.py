import json
import logging
from django.utils import timezone
import colorlog

# Создаем логгер
logger = logging.getLogger('api_requests')
logger.setLevel(logging.INFO)

# Создаем форматтер для логов
formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(message)s%(reset)s',
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    }
)

# Создаем обработчик для записи в файл
file_handler = logging.FileHandler('api_requests.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Создаем обработчик для консоли
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

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
        return response 