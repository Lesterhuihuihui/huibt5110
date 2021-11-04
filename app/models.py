from django.db import models


# Create your models here.
class Greeting(models.Model):
    id = models.AutoField(primary_key=True)
    when = models.DateTimeField("date created", auto_now_add=True)


class ShipType(models.Model):
    name = models.CharField(max_length=255)


class Date(models.Model):
    date = models.DateField()


class VerifierCity(models.Model):
    name = models.CharField(max_length=255)


class Information(models.Model):
    imo = models.CharField(verbose_name='IMO', max_length=255)
    eedi = models.FloatField()
    total_co2 = models.FloatField()
    total_time = models.FloatField()
    total_fuel = models.FloatField()
    ship_type = models.ForeignKey(ShipType, on_delete=models.CASCADE)
    date = models.ForeignKey(Date, on_delete=models.CASCADE)
    verifier_city = models.ForeignKey(VerifierCity, on_delete=models.CASCADE)

    def __str__(self):
        return self.imo
