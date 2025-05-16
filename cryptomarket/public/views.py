from django.shortcuts import render, get_object_or_404
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from cryptomarket.permissions import IsAdmin
from users.authentication import APITokenAuthentication

from order.models import (
    Instrument,
    LimitOrder,
    Transaction,
    Direction,
    OrderStatus
)
from order.serializers import (
    InstrumentSerializer,
    L2OrderBookSerializer,
    TransactionSerializer,
    LevelSerializer,
    OkSerializer
)

class InstrumentListView(views.APIView):
    """
    API для получения списка доступных инструментов
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Список доступных инструментов"""
        instruments = Instrument.objects.all()
        serializer = InstrumentSerializer(instruments, many=True)
        return Response(serializer.data)

class OrderBookView(views.APIView):
    """
    API для получения текущих заявок (Order Book)
    """
    permission_classes = [AllowAny]
    
    def get(self, request, ticker):
        """Текущие заявки"""
        # Проверяем, что инструмент существует
        instrument = get_object_or_404(Instrument, ticker=ticker)
        
        # Получаем лимит записей (максимум 25, по умолчанию 10)
        limit = min(int(request.query_params.get('limit', 10)), 25)
        
        # Получаем активные лимитные ордера
        active_orders = LimitOrder.objects.filter(
            ticker=ticker,
            status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
        )
        
        # Разделяем на bid (покупка) и ask (продажа)
        bid_orders = active_orders.filter(direction=Direction.BUY).order_by('-price')[:limit]
        ask_orders = active_orders.filter(direction=Direction.SELL).order_by('price')[:limit]
        
        # Агрегируем ордера по ценовым уровням
        bid_levels = []
        ask_levels = []
        
        # Создаем уровни цен для покупок (bid)
        bid_price_map = {}
        for order in bid_orders:
            if order.price in bid_price_map:
                bid_price_map[order.price] += order.qty - order.filled
            else:
                bid_price_map[order.price] = order.qty - order.filled
        
        for price, qty in bid_price_map.items():
            bid_levels.append({'price': price, 'qty': qty})
        
        # Создаем уровни цен для продаж (ask)
        ask_price_map = {}
        for order in ask_orders:
            if order.price in ask_price_map:
                ask_price_map[order.price] += order.qty - order.filled
            else:
                ask_price_map[order.price] = order.qty - order.filled
        
        for price, qty in ask_price_map.items():
            ask_levels.append({'price': price, 'qty': qty})
        
        # Сортируем уровни
        bid_levels.sort(key=lambda x: x['price'], reverse=True)
        ask_levels.sort(key=lambda x: x['price'])
        
        # Ограничиваем количество уровней
        bid_levels = bid_levels[:limit]
        ask_levels = ask_levels[:limit]
        
        # Формируем ответ
        orderbook = {
            'bid_levels': bid_levels,
            'ask_levels': ask_levels
        }
        
        serializer = L2OrderBookSerializer(orderbook)
        return Response(serializer.data)

class TransactionHistoryView(views.APIView):
    """
    API для получения истории сделок
    """
    permission_classes = [AllowAny]
    
    def get(self, request, ticker):
        """История сделок"""
        # Проверяем, что инструмент существует
        instrument = get_object_or_404(Instrument, ticker=ticker)
        
        # Получаем лимит записей (максимум 100, по умолчанию 10)
        limit = min(int(request.query_params.get('limit', 10)), 100)
        
        # Получаем транзакции для данного тикера
        transactions = Transaction.objects.filter(ticker=ticker).order_by('-timestamp')[:limit]
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class AdminInstrumentView(views.APIView):
    """
    API для добавления инструмента (только для админов)
    """
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Добавление инструмента"""
        serializer = InstrumentSerializer(data=request.data)
        
        if serializer.is_valid():
            # Проверка формата тикера (только заглавные буквы, от 2 до 10 символов)
            ticker = serializer.validated_data['ticker']
            if not ticker.isalpha() or not ticker.isupper() or len(ticker) < 2 or len(ticker) > 10:
                return Response(
                    {"detail": "Тикер должен содержать только заглавные буквы от 2 до 10 символов"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Создаем новый инструмент
            serializer.save()
            
            return Response(OkSerializer({"success": True}).data)
        
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class AdminInstrumentDetailView(views.APIView):
    """
    API для удаления инструмента (только для админов)
    """
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAdmin]
    
    def delete(self, request, ticker):
        """Удаление инструмента"""
        instrument = get_object_or_404(Instrument, ticker=ticker)
        
        # Проверяем, есть ли активные ордера или транзакции с этим инструментом
        active_orders_exist = LimitOrder.objects.filter(
            ticker=ticker, 
            status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
        ).exists()
        
        if active_orders_exist:
            return Response(
                {"detail": "Невозможно удалить инструмент с активными ордерами"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Удаляем инструмент
        instrument.delete()
        
        return Response(OkSerializer({"success": True}).data)
