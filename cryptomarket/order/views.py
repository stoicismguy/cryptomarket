from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from users.authentication import APITokenAuthentication
from django.db import transaction

from .models import (
    LimitOrder,
    MarketOrder,
    OrderStatus,
    Transaction,
    Instrument,
    Direction
)
from .serializers import (
    LimitOrderSerializer,
    MarketOrderSerializer,
    LimitOrderBodySerializer,
    MarketOrderBodySerializer,
    CreateOrderResponseSerializer,
    TransactionSerializer,
    OkSerializer,
    L2OrderBookSerializer,
    InstrumentSerializer
)
from .matching import OrderMatcher

class OrderView(views.APIView):
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all orders for the authenticated user"""
        limit_orders = request.user.limit_orders.all()
        market_orders = request.user.market_orders.all()
        
        limit_serializer = LimitOrderSerializer(limit_orders, many=True)
        market_serializer = MarketOrderSerializer(market_orders, many=True)
        
        return Response(limit_serializer.data + market_serializer.data)
    
    def post(self, request):
        """Create a new order"""
        data = request.data
        
        if 'price' in data:
            # Это лимитный ордер
            serializer = LimitOrderBodySerializer(data=data)
        else:
            # Это рыночный ордер
            serializer = MarketOrderBodySerializer(data=data)
        
        if serializer.is_valid():
            with transaction.atomic():
                if 'price' in data:
                    order = LimitOrder.objects.create(
                        user=request.user,
                        ticker=serializer.validated_data['ticker'],
                        direction=serializer.validated_data['direction'],
                        qty=serializer.validated_data['qty'],
                        price=serializer.validated_data['price']
                    )
                    # Пытаемся исполнить лимитный ордер
                    OrderMatcher.match_limit_order(order)
                else:
                    order = MarketOrder.objects.create(
                        user=request.user,
                        ticker=serializer.validated_data['ticker'],
                        direction=serializer.validated_data['direction'],
                        qty=serializer.validated_data['qty']
                    )
                    # Пытаемся исполнить рыночный ордер
                    OrderMatcher.match_market_order(order)
            
            response_serializer = CreateOrderResponseSerializer({
                'success': True,
                'order_id': order.id
            })
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class OrderDetailView(views.APIView):
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_order(self, order_id):
        """Helper method to get order by ID"""
        # Try to find limit order first
        try:
            return LimitOrder.objects.get(id=order_id)
        except LimitOrder.DoesNotExist:
            try:
                return MarketOrder.objects.get(id=order_id)
            except MarketOrder.DoesNotExist:
                return None
    
    def get(self, request, order_id):
        """Get order details by ID"""
        order = self.get_order(order_id)
        
        if not order:
            return Response(
                {"detail": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.user != request.user:
            return Response(
                {"detail": "Not authorized to view this order"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if isinstance(order, LimitOrder):
            serializer = LimitOrderSerializer(order)
        else:
            serializer = MarketOrderSerializer(order)
        
        return Response(serializer.data)
    
    def delete(self, request, order_id):
        """Cancel an order"""
        order = self.get_order(order_id)
        
        if not order:
            return Response(
                {"detail": "Order not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.user != request.user:
            return Response(
                {"detail": "Not authorized to cancel this order"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
            return Response(
                {"detail": f"Cannot cancel order in {order.status} status"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = OrderStatus.CANCELLED
        order.save()
        
        return Response(OkSerializer({"success": True}).data)
