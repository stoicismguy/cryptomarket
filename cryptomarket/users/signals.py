from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.db import transaction
import uuid
from users.models import User
from order.models import Instrument
from balance.models import Balance

@receiver(post_migrate)
def create_initial_data(sender, **kwargs):
    """
    Создает начальные данные после миграции:
    1. Администратора системы
    2. Базовую валюту (RUB)
    3. Начальный баланс админа
    """
    # Проверяем, что сигнал пришел от нужного приложения
    if sender.name != 'users':
        return

    with transaction.atomic():
        # Создаем админа, если его еще нет
        admin, created = User.objects.get_or_create(
            name='admin',
            defaults={
                'role': 'ADMIN',
                'api_key': '13a5df5f-a5e4-4531-9c09-2a141b634c0e',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True
            }
        )
        
        # Устанавливаем пароль только если пользователь был создан
        if created:
            admin.set_password('1aaa1aaa')
            admin.save()
            print('Created admin user')
            print(f'Admin API key: {admin.api_key}')

        # Создаем базовую валюту RUB, если её еще нет
        rub, created = Instrument.objects.get_or_create(
            ticker='RUB',
            defaults={
                'name': 'Russian Ruble'
            }
        )
        
        # Создаем начальный баланс RUB для админа
        balance, created = Balance.objects.get_or_create(
            user=admin,
            ticker='RUB',
            amount=99999999999999,
        )
        
        if created:
            print('Created initial admin balance')

@receiver(post_save, sender=User)
def create_user_balance(sender, instance, created, **kwargs):
    """
    Создает начальный баланс RUB для нового пользователя
    """
    if created:  # Только для новых пользователей
        Balance.objects.get_or_create(
            user=instance,
            ticker='RUB',
            defaults={'amount': 0}  # Начальный баланс 0 RUB
        ) 