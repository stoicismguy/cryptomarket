from decimal import Decimal
from typing import Optional, List, Tuple
from django.db import transaction
from django.db.models import F

from .models import LimitOrder, MarketOrder, Transaction, OrderStatus, Direction
from balance.models import Balance

class OrderMatcher:
    @staticmethod
    def _update_balances(buyer, seller, ticker: str, amount: int, price: int):
        """Обновляет балансы участников сделки"""
        with transaction.atomic():
            # Списываем деньги у покупателя
            Balance.objects.filter(user=buyer, ticker='USD').update(
                amount=F('amount') - (price * amount)
            )
            # Начисляем токены покупателю
            Balance.objects.filter(user=buyer, ticker=ticker).update(
                amount=F('amount') + amount
            )
            
            # Списываем токены у продавца
            Balance.objects.filter(user=seller, ticker=ticker).update(
                amount=F('amount') - amount
            )
            # Начисляем деньги продавцу
            Balance.objects.filter(user=seller, ticker='USD').update(
                amount=F('amount') + (price * amount)
            )

    @staticmethod
    def _create_transaction(buyer, seller, ticker: str, amount: int, price: int) -> Transaction:
        """Создает запись о совершенной сделке"""
        return Transaction.objects.create(
            ticker=ticker,
            amount=amount,
            price=price,
            buyer=buyer,
            seller=seller
        )

    @staticmethod
    def _update_order_status(order, filled_qty: int):
        """Обновляет статус ордера"""
        order.filled += filled_qty
        if order.filled >= order.qty:
            order.status = OrderStatus.EXECUTED
        elif order.filled > 0:
            order.status = OrderStatus.PARTIALLY_EXECUTED
        order.save()

    @staticmethod
    def _check_balance(user, ticker: str, amount: int, price: Optional[int] = None):
        """Проверяет достаточно ли средств для совершения сделки"""
        if price:  # Для покупателя проверяем USD
            balance = Balance.objects.filter(user=user, ticker='USD').first()
            return balance and balance.amount >= price * amount
        else:  # Для продавца проверяем токены
            balance = Balance.objects.filter(user=user, ticker=ticker).first()
            return balance and balance.amount >= amount

    @classmethod
    def match_limit_order(cls, order: LimitOrder) -> List[Transaction]:
        """Исполняет лимитный ордер"""
        transactions = []
        remaining_qty = order.qty

        # Ищем встречные ордера
        if order.direction == Direction.BUY:
            matching_orders = (
                LimitOrder.objects
                .filter(
                    ticker=order.ticker,
                    direction=Direction.SELL,
                    price__lte=order.price,
                    status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                )
                .exclude(user=order.user)
                .order_by('price', 'timestamp')
            )
        else:
            matching_orders = (
                LimitOrder.objects
                .filter(
                    ticker=order.ticker,
                    direction=Direction.BUY,
                    price__gte=order.price,
                    status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                )
                .exclude(user=order.user)
                .order_by('-price', 'timestamp')
            )

        for matching_order in matching_orders:
            if remaining_qty <= 0:
                break

            # Определяем количество и цену для сделки
            match_qty = min(remaining_qty, matching_order.qty - matching_order.filled)
            match_price = matching_order.price

            # Проверяем балансы обеих сторон
            buyer = order.user if order.direction == Direction.BUY else matching_order.user
            seller = matching_order.user if order.direction == Direction.BUY else order.user

            if not cls._check_balance(buyer, 'USD', match_qty, match_price) or \
               not cls._check_balance(seller, order.ticker, match_qty):
                continue

            with transaction.atomic():
                # Обновляем балансы
                cls._update_balances(buyer, seller, order.ticker, match_qty, match_price)
                
                # Создаем транзакцию
                tx = cls._create_transaction(buyer, seller, order.ticker, match_qty, match_price)
                transactions.append(tx)
                
                # Обновляем статусы ордеров
                cls._update_order_status(order, match_qty)
                cls._update_order_status(matching_order, match_qty)
                
                remaining_qty -= match_qty

        return transactions

    @classmethod
    def match_market_order(cls, order: MarketOrder) -> List[Transaction]:
        """Исполняет рыночный ордер"""
        transactions = []
        remaining_qty = order.qty

        # Ищем встречные лимитные ордера
        if order.direction == Direction.BUY:
            matching_orders = (
                LimitOrder.objects
                .filter(
                    ticker=order.ticker,
                    direction=Direction.SELL,
                    status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                )
                .exclude(user=order.user)
                .order_by('price', 'timestamp')
            )
        else:
            matching_orders = (
                LimitOrder.objects
                .filter(
                    ticker=order.ticker,
                    direction=Direction.BUY,
                    status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                )
                .exclude(user=order.user)
                .order_by('-price', 'timestamp')
            )

        for matching_order in matching_orders:
            if remaining_qty <= 0:
                break

            match_qty = min(remaining_qty, matching_order.qty - matching_order.filled)
            match_price = matching_order.price

            buyer = order.user if order.direction == Direction.BUY else matching_order.user
            seller = matching_order.user if order.direction == Direction.BUY else order.user

            if not cls._check_balance(buyer, 'USD', match_qty, match_price) or \
               not cls._check_balance(seller, order.ticker, match_qty):
                continue

            with transaction.atomic():
                cls._update_balances(buyer, seller, order.ticker, match_qty, match_price)
                tx = cls._create_transaction(buyer, seller, order.ticker, match_qty, match_price)
                transactions.append(tx)
                cls._update_order_status(order, match_qty)
                cls._update_order_status(matching_order, match_qty)
                remaining_qty -= match_qty

        # Если ордер не исполнен полностью, отменяем его
        if remaining_qty == order.qty:
            order.status = OrderStatus.CANCELLED
            order.save()
        
        return transactions 