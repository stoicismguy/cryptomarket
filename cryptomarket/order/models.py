from django.db import models
import uuid
from django.utils import timezone
from users.models import User

class Direction(models.TextChoices):
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"

class OrderStatus(models.TextChoices):
    NEW = "NEW", "New"
    EXECUTED = "EXECUTED", "Executed"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED", "Partially Executed"
    CANCELLED = "CANCELLED", "Cancelled"

class Instrument(models.Model):
    name = models.CharField(max_length=255)
    ticker = models.CharField(max_length=10, primary_key=True)
    
    def __str__(self):
        return f"{self.ticker} - {self.name}"
    
    class Meta:
        db_table = "instruments"

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticker = models.CharField(max_length=10)
    direction = models.CharField(max_length=4, choices=Direction.choices)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.NEW)
    timestamp = models.DateTimeField(default=timezone.now)
    filled = models.PositiveIntegerField(default=0)
    
    class Meta:
        abstract = True

class LimitOrder(Order):
    price = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="limit_orders")
    
    def __str__(self):
        return f"{self.id} - {self.ticker} {self.direction} {self.qty}@{self.price}"
    
    class Meta:
        db_table = "limit_orders"
        indexes = [
            models.Index(fields=['ticker', 'direction', 'status', 'price', 'timestamp']),
            models.Index(fields=['user']),
        ]

class MarketOrder(Order):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="market_orders")
    
    def __str__(self):
        return f"{self.id} - {self.ticker} {self.direction} {self.qty}"
    
    class Meta:
        db_table = "market_orders"
        indexes = [
            models.Index(fields=['user']),
        ]

class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticker = models.CharField(max_length=10)
    amount = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buy_transactions")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sell_transactions")
    
    def __str__(self):
        return f"{self.ticker} {self.amount}@{self.price}"
    
    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=['buyer']),
            models.Index(fields=['seller']),
            models.Index(fields=['ticker', 'timestamp']),
        ]
