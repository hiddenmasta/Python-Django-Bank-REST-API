from django.db import models
import json

class Client(models.Model):
    name = models.CharField(max_length=20)
    address = models.CharField(max_length=50)
    birthdate = models.DateField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    def to_json(self):
        return {'id': self.id,
        'name': self.name,
        'birthdate': self.birthdate,
        'address': self.address,
        'latitude': self.latitude,
        'longitude': self.longitude}

class Account(models.Model):
    ACCOUNT_TYPES = (
        ("CREDI CARD", "Credit card"),
        ("DEBIT CARD", "Debit card")
    )
    balance = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    number = models.CharField(max_length=16, unique=True)
    account_type = models.CharField(
                  choices=ACCOUNT_TYPES,
                  default="CREDI CARD")
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    def to_json(self):
        return {
        'id': self.id,
        'account_type': self.account_type,
        'number': self.number,
        'balance': self.balance }