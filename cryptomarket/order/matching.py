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
            Balance.objects.filter(user=buyer, ticker='RUB').update(
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
            Balance.objects.filter(user=seller, ticker='RUB').update(
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
        elif order.filled == 0:
            order.status = OrderStatus.NEW
        order.save()

    @staticmethod
    def _check_balance(user, ticker: str, amount: int, price: Optional[int] = None):
        """Проверяет достаточно ли средств для совершения сделки"""
        if price:  # Для покупателя проверяем RUB
            balance = Balance.objects.filter(user=user, ticker='RUB').first()
            return balance and balance.amount >= price * amount
        else:  # Для продавца проверяем токены
            balance = Balance.objects.filter(user=user, ticker=ticker).first()
            return balance and balance.amount >= amount

    @classmethod
    def match_limit_order(cls, order: LimitOrder) -> List[Transaction]:
        """
        Исполняет лимитный ордер по биржевым правилам:
        - Для BUY ордеров ищем самые дешевые предложения SELL
        - Для SELL ордеров ищем самые дорогие предложения BUY
        - Соблюдаем Price-Time Priority
        """
        transactions = []
        
        try:
            with transaction.atomic():
                # Проверяем баланс для всего ордера
                if order.direction == Direction.BUY:
                    if not cls._check_balance(order.user, 'RUB', order.qty, order.price):
                        order.status = OrderStatus.CANCELLED
                        order.save()
                        return transactions
                else:
                    if not cls._check_balance(order.user, order.ticker, order.qty):
                        order.status = OrderStatus.CANCELLED
                        order.save()
                        return transactions

                remaining_qty = order.qty

                while remaining_qty > 0:
                    # Ищем встречный ордер с лучшей ценой
                    if order.direction == Direction.BUY:
                        # Для покупки ищем самые дешевые предложения продажи
                        matching_order = (
                            LimitOrder.objects
                            .select_for_update()  # Блокируем строки для атомарности
                            .filter(
                                ticker=order.ticker,
                                direction=Direction.SELL,
                                price__lte=order.price,  # Цена не выше нашей максимальной
                                status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                            )
                            .exclude(user=order.user)
                            .order_by('price', 'timestamp')  # Сначала самые дешевые, потом по времени
                            .first()
                        )
                    else:
                        # Для продажи ищем самые дорогие предложения покупки
                        matching_order = (
                            LimitOrder.objects
                            .select_for_update()  # Блокируем строки для атомарности
                            .filter(
                                ticker=order.ticker,
                                direction=Direction.BUY,
                                price__gte=order.price,  # Цена не ниже нашей минимальной
                                status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                            )
                            .exclude(user=order.user)
                            .order_by('-price', 'timestamp')  # Сначала самые дорогие, потом по времени
                            .first()
                        )

                    if not matching_order:
                        # Нет подходящих ордеров - оставляем в статусе NEW или PARTIALLY_EXECUTED
                        break

                    # Определяем количество и цену для сделки
                    match_qty = min(remaining_qty, matching_order.qty - matching_order.filled)
                    
                    # Цена исполнения - это цена ордера, который был в стакане первым
                    match_price = matching_order.price
                    
                    # Определяем покупателя и продавца
                    buyer = order.user if order.direction == Direction.BUY else matching_order.user
                    seller = matching_order.user if order.direction == Direction.BUY else order.user

                    # Проверяем балансы обеих сторон
                    if not cls._check_balance(buyer, 'RUB', match_qty, match_price) or \
                       not cls._check_balance(seller, order.ticker, match_qty):
                        # Если у какой-то стороны не хватает средств - отменяем встречный ордер
                        matching_order.status = OrderStatus.CANCELLED
                        matching_order.save()
                        continue

                    # Обновляем балансы
                    cls._update_balances(buyer, seller, order.ticker, match_qty, match_price)
                    
                    # Создаем транзакцию
                    tx = cls._create_transaction(buyer, seller, order.ticker, match_qty, match_price)
                    transactions.append(tx)
                    
                    # Обновляем статусы ордеров
                    order.filled += match_qty
                    matching_order.filled += match_qty
                    
                    # Обновляем статус нашего ордера
                    if order.filled >= order.qty:
                        order.status = OrderStatus.EXECUTED
                    else:
                        order.status = OrderStatus.PARTIALLY_EXECUTED
                    
                    # Обновляем статус встречного ордера
                    if matching_order.filled >= matching_order.qty:
                        matching_order.status = OrderStatus.EXECUTED
                    else:
                        matching_order.status = OrderStatus.PARTIALLY_EXECUTED
                    
                    order.save()
                    matching_order.save()
                    
                    remaining_qty -= match_qty

        except Exception as e:
            print(f"Error during order matching: {e}")
            # В случае ошибки транзакция откатится автоматически
            return []

        return transactions

    @classmethod
    def match_market_order(cls, order: MarketOrder) -> List[Transaction]:
        """
        Исполняет рыночный ордер по биржевым правилам:
        - Для BUY берем лучшие предложения SELL по возрастанию цены
        - Для SELL берем лучшие предложения BUY по убыванию цены
        - Исполняем по ценам в стакане
        """
        transactions = []
        
        try:
            with transaction.atomic():
                remaining_qty = order.qty

                while remaining_qty > 0:
                    # Ищем встречный ордер с лучшей ценой
                    if order.direction == Direction.BUY:
                        matching_order = (
                            LimitOrder.objects
                            .select_for_update()
                            .filter(
                                ticker=order.ticker,
                                direction=Direction.SELL,
                                status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                            )
                            .exclude(user=order.user)
                            .order_by('price', 'timestamp')
                            .first()
                        )
                    else:
                        matching_order = (
                            LimitOrder.objects
                            .select_for_update()
                            .filter(
                                ticker=order.ticker,
                                direction=Direction.BUY,
                                status__in=[OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]
                            )
                            .exclude(user=order.user)
                            .order_by('-price', 'timestamp')
                            .first()
                        )

                    if not matching_order:
                        # Нет подходящих ордеров - отменяем остаток
                        if order.filled == 0:
                            order.status = OrderStatus.CANCELLED
                        elif order.filled < order.qty:
                            order.status = OrderStatus.PARTIALLY_EXECUTED
                        order.save()
                        break

                    match_qty = min(remaining_qty, matching_order.qty - matching_order.filled)
                    match_price = matching_order.price

                    buyer = order.user if order.direction == Direction.BUY else matching_order.user
                    seller = matching_order.user if order.direction == Direction.BUY else order.user

                    if not cls._check_balance(buyer, 'RUB', match_qty, match_price) or \
                       not cls._check_balance(seller, order.ticker, match_qty):
                        matching_order.status = OrderStatus.CANCELLED
                        matching_order.save()
                        continue

                    cls._update_balances(buyer, seller, order.ticker, match_qty, match_price)
                    tx = cls._create_transaction(buyer, seller, order.ticker, match_qty, match_price)
                    transactions.append(tx)

                    order.filled += match_qty
                    matching_order.filled += match_qty

                    if order.filled >= order.qty:
                        order.status = OrderStatus.EXECUTED
                    else:
                        order.status = OrderStatus.PARTIALLY_EXECUTED

                    if matching_order.filled >= matching_order.qty:
                        matching_order.status = OrderStatus.EXECUTED
                    else:
                        matching_order.status = OrderStatus.PARTIALLY_EXECUTED

                    order.save()
                    matching_order.save()

                    remaining_qty -= match_qty

        except Exception as e:
            print(f"Error during order matching: {e}")
            return []

        return transactions 