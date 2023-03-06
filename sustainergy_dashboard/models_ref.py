import shortuuid
from django.db import models


class Building(models.Model):
    class Meta:
        db_table = "buildings"

    idbuildings = models.CharField(max_length=30, primary_key=True, default=shortuuid.ShortUUID().random(length=8))
    client_id = models.CharField(max_length=30)
    address = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
    description = models.CharField(max_length=30)
    occupants = models.CharField(max_length=30)
    occupies_days_per_week = models.CharField(max_length=30)
    length_of_occupied_day = models.CharField(max_length=30)
    start_hour = models.CharField(max_length=30)
    end_hour = models.CharField(max_length=30)
    number_of_doors = models.CharField(max_length=30)
    squarefootage = models.CharField(max_length=30)
    exterior_wall_squarefootage = models.CharField(max_length=30)
    window_squarfootage = models.CharField(max_length=30)
    roof_squarefootage = models.CharField(max_length=30)
    price_per_gj = models.CharField(max_length=30)
    price_per_kwh = models.CharField(max_length=30)
    vist_duration = models.CharField(max_length=30)
    calculated = models.BooleanField(default=False)


class Panel(models.Model):
    class Meta:
        db_table = "panel_data"

    panel_name = models.CharField(max_length=30)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, to_field='idbuildings')
    panel_id = models.CharField(max_length=30, primary_key=True, default=shortuuid.ShortUUID().random(length=8))
    panel_type = models.CharField(max_length=30)
    panel_voltage = models.CharField(max_length=30)
    panel_image = models.CharField(max_length=50)


class Circuit(models.Model):
    class Meta:
        db_table = "circuit_data"

    circuit_name = models.CharField(max_length=30)
    circuit_category = models.CharField(max_length=30)
    circuit_amps = models.CharField(max_length=30)
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, to_field='panel_id')


class DailyData(models.Model):
    class Meta:
        db_table = "daily_data"

    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
