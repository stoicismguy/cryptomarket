# Generated by Django 5.2 on 2025-06-11 06:13

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('balance', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='balance',
            index=models.Index(fields=['user'], name='balances_user_id_62ea2c_idx'),
        ),
    ]
