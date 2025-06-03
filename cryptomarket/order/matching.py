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
            # Создаем или получаем балансы, если их нет
            buyer_rub, _ = Balance.objects.get_or_create(user=buyer, ticker='RUB', defaults={'amount': 0})
            buyer_token, _ = Balance.objects.get_or_create(user=buyer, ticker=ticker, defaults={'amount': 0})
            seller_rub, _ = Balance.objects.get_or_create(user=seller, ticker='RUB', defaults={'amount': 0})
            seller_token, _ = Balance.objects.get_or_create(user=seller, ticker=ticker, defaults={'amount': 0})

            # Проверяем достаточность средств
            if buyer_rub.amount < price * amount or seller_token.amount < amount:
                raise ValueError("Insufficient funds")

            # Обновляем балансы
            buyer_rub.amount -= price * amount
            buyer_token.amount += amount
            seller_rub.amount += price * amount
            seller_token.amount -= amount

            # Сохраняем изменения
            buyer_rub.save()
            buyer_token.save()
            seller_rub.save()
            seller_token.save()

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
        with transaction.atomic():
            if price:  # Для покупателя проверяем RUB
                balance, _ = Balance.objects.get_or_create(user=user, ticker='RUB', defaults={'amount': 0})
                return balance.amount >= price * amount
            else:  # Для продавца проверяем токены
                balance, _ = Balance.objects.get_or_create(user=user, ticker=ticker, defaults={'amount': 0})
                return balance.amount >= amount

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
                # Для рыночного ордера на покупку нам нужно сначала проверить,
                # есть ли вообще подходящие ордера и хватит ли денег по худшей цене
                if order.direction == Direction.BUY:
                    # Находим все подходящие ордера на продажу
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
                    
                    # Проверяем, достаточно ли ордеров для исполнения
                    available_qty = sum(o.qty - o.filled for o in matching_orders)
                    if available_qty < order.qty:
                        order.status = OrderStatus.CANCELLED
                        order.save()
                        return transactions
                    
                    # Вычисляем необходимую сумму RUB для исполнения
                    required_rub = 0
                    remaining = order.qty
                    for o in matching_orders:
                        match_qty = min(remaining, o.qty - o.filled)
                        required_rub += match_qty * o.price
                        remaining -= match_qty
                        if remaining <= 0:
                            break
                    
                    # Проверяем баланс RUB
                    if not cls._check_balance(order.user, 'RUB', order.qty, required_rub // order.qty):
                        order.status = OrderStatus.CANCELLED
                        order.save()
                        return transactions

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

                    try:
                        # Проверяем балансы и обновляем их
                        cls._update_balances(buyer, seller, order.ticker, match_qty, match_price)
                        
                        # Создаем транзакцию
                        tx = cls._create_transaction(buyer, seller, order.ticker, match_qty, match_price)
                        transactions.append(tx)

                        # Обновляем статусы
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
                    except ValueError:
                        # Если не хватает средств, отменяем встречный ордер и продолжаем
                        matching_order.status = OrderStatus.CANCELLED
                        matching_order.save()
                        continue

        except Exception as e:
            print(f"Error during order matching: {e}")
            return []

        return transactions 