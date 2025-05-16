from rest_framework import serializers
from .models import Balance
from order.serializers import OkSerializer

class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Balance
        fields = ['ticker', 'amount']

class BalanceResponseSerializer(serializers.Serializer):
    """
    Сериализатор для ответа на запрос баланса
    Пример: {"MEMCOIN": 0, "DODGE": 100500}
    """
    def to_representation(self, instance):
        return {balance.ticker: balance.amount for balance in instance}

class DepositWithdrawSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    ticker = serializers.CharField()
    amount = serializers.IntegerField(min_value=1) 