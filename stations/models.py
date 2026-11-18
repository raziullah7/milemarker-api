"""The one database table: fuel stations, loaded once from the supplied CSV."""

from django.db import models


class FuelStation(models.Model):
    """One truck stop, with the position of its city (the CSV has no coordinates)."""

    opis_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    # Stored exactly as the CSV has it (up to 8 decimal places), so no digit is lost.
    price = models.DecimalField(max_digits=11, decimal_places=8)
    lat = models.FloatField()
    lng = models.FloatField()

    def __str__(self) -> str:
        return f"{self.opis_id} {self.name}, {self.city}, {self.state}"
