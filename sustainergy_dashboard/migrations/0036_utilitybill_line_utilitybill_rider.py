# Generated by Django 4.0.6 on 2023-02-07 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sustainergy_dashboard', '0035_utilityprovider_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilitybill',
            name='line',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='utilitybill',
            name='rider',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
