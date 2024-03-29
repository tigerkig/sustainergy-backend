# Generated by Django 4.0.6 on 2022-12-16 09:36

import colorfield.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sustainergy_dashboard', '0015_user_role'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='circuitcategory',
            name='color',
        ),
        migrations.AddField(
            model_name='circuitcategory',
            name='colour',
            field=colorfield.fields.ColorField(default='#3649a8', image_field=None, max_length=18, samples=[('#3649a8', 'Dark Blue'), ('#ee8f37', 'Orange'), ('#DB4B46', 'Red'), ('#3bcdee', 'Sky Blue'), ('#777777', 'Grey'), ('#994f9b', 'Purple'), ('#ffadc9', 'Light Pink'), ('#000000', 'Black'), ('#F7CA50', 'Yellow'), ('#98C355', 'Green'), ('#911120', 'Brown'), ('#C5BFE6', 'Light Purple'), ('#006ba9', 'Dark Sky'), ('#4DAAE8', 'Blue'), ('#FFFFE0', 'Light Yellow')]),
        ),
    ]
