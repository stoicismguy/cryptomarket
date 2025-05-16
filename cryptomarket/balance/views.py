from django.shortcuts import render, get_object_or_404
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from users.models import User, UserRole
from users.authentication import APITokenAuthentication
from cryptomarket.permissions import IsAdmin

from .models import Balance
from .serializers import (
    BalanceSerializer,
    BalanceResponseSerializer,
    DepositWithdrawSerializer
)
from order.serializers import OkSerializer

class BalanceView(views.APIView):
    """API для получения балансов пользователя"""
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получить баланс авторизованного пользователя"""
        balances = Balance.objects.filter(user=request.user)
        serializer = BalanceResponseSerializer(balances)
        return Response(serializer.data)

class AdminBalanceDepositView(views.APIView):
    """API для пополнения баланса (только для админов)"""
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Пополнение баланса пользователя"""
        serializer = DepositWithdrawSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            ticker = serializer.validated_data['ticker']
            amount = serializer.validated_data['amount']
            
            user = get_object_or_404(User, id=user_id)
            
            balance, created = Balance.objects.get_or_create(
                user=user,
                ticker=ticker,
                defaults={'amount': 0}
            )
            
            balance.amount += amount
            balance.save()
            
            return Response(OkSerializer({"success": True}).data)
        
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class AdminBalanceWithdrawView(views.APIView):
    """API для вывода средств с баланса (только для админов)"""
    authentication_classes = [APITokenAuthentication]
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Вывод средств с баланса пользователя"""
        serializer = DepositWithdrawSerializer(data=request.data)
        
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            ticker = serializer.validated_data['ticker']
            amount = serializer.validated_data['amount']
            
            user = get_object_or_404(User, id=user_id)
            
            try:
                balance = Balance.objects.get(user=user, ticker=ticker)
            except Balance.DoesNotExist:
                return Response(
                    {"detail": f"Пользователь не имеет баланса {ticker}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if balance.amount < amount:
                return Response(
                    {"detail": f"Недостаточно средств. Доступно: {balance.amount}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            balance.amount -= amount
            balance.save()
            
            return Response(OkSerializer({"success": True}).data)
        
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
