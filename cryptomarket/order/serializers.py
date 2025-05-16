from rest_framework import serializers
from .models import (
    LimitOrder, 
    MarketOrder, 
    Transaction, 
    Instrument, 
    Direction, 
    OrderStatus
)
import uuid

class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ['name', 'ticker']

class LevelSerializer(serializers.Serializer):
    price = serializers.IntegerField()
    qty = serializers.IntegerField()

class L2OrderBookSerializer(serializers.Serializer):
    bid_levels = LevelSerializer(many=True)
    ask_levels = LevelSerializer(many=True)

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['ticker', 'amount', 'price', 'timestamp']

class LimitOrderBodySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=Direction.choices)
    ticker = serializers.CharField()
    qty = serializers.IntegerField(min_value=1)
    price = serializers.IntegerField(min_value=1)

class MarketOrderBodySerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=Direction.choices)
    ticker = serializers.CharField()
    qty = serializers.IntegerField(min_value=1)

class LimitOrderSerializer(serializers.ModelSerializer):
    body = LimitOrderBodySerializer(source='*')
    
    class Meta:
        model = LimitOrder
        fields = ['id', 'status', 'user_id', 'timestamp', 'body', 'filled']
        read_only_fields = ['id', 'status', 'user_id', 'timestamp', 'filled']
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        body = ret.pop('body')
        ret['body'] = {
            'direction': body['direction'],
            'ticker': body['ticker'],
            'qty': body['qty'],
            'price': body['price']
        }
        return ret

class MarketOrderSerializer(serializers.ModelSerializer):
    body = MarketOrderBodySerializer(source='*')
    
    class Meta:
        model = MarketOrder
        fields = ['id', 'status', 'user_id', 'timestamp', 'body']
        read_only_fields = ['id', 'status', 'user_id', 'timestamp']
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        body = ret.pop('body')
        ret['body'] = {
            'direction': body['direction'],
            'ticker': body['ticker'],
            'qty': body['qty']
        }
        return ret

class CreateOrderResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    order_id = serializers.UUIDField()

class OkSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True) 