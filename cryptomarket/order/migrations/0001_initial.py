# Generated by Django 5.2 on 2025-05-11 09:38

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('name', models.CharField(max_length=255)),
                ('ticker', models.CharField(max_length=10, primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'instruments',
            },
        ),
        migrations.CreateModel(
            name='LimitOrder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ticker', models.CharField(max_length=10)),
                ('direction', models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell')], max_length=4)),
                ('qty', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('NEW', 'New'), ('EXECUTED', 'Executed'), ('PARTIALLY_EXECUTED', 'Partially Executed'), ('CANCELLED', 'Cancelled')], default='NEW', max_length=20)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('filled', models.PositiveIntegerField(default=0)),
                ('price', models.PositiveIntegerField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='limit_orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'limit_orders',
            },
        ),
        migrations.CreateModel(
            name='MarketOrder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ticker', models.CharField(max_length=10)),
                ('direction', models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell')], max_length=4)),
                ('qty', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('NEW', 'New'), ('EXECUTED', 'Executed'), ('PARTIALLY_EXECUTED', 'Partially Executed'), ('CANCELLED', 'Cancelled')], default='NEW', max_length=20)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('filled', models.PositiveIntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='market_orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'market_orders',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ticker', models.CharField(max_length=10)),
                ('amount', models.PositiveIntegerField()),
                ('price', models.PositiveIntegerField()),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buy_transactions', to=settings.AUTH_USER_MODEL)),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sell_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'transactions',
            },
        ),
    ]
