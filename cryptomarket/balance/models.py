from django.db import models
from users.models import User
from order.models import Instrument
import uuid

class Balance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="balances")
    ticker = models.CharField(max_length=10)
    amount = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = "balances"
        unique_together = ['user', 'ticker']
        indexes = [
            models.Index(fields=['user']),
        ]
        
    def __str__(self):
        return f"{self.user.name}: {self.ticker} - {self.amount}"
