# Generated by Django 4.0.6 on 2023-02-07 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sustainergy_dashboard', '0034_alter_panel_panel_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilityprovider',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='utility_providers'),
        ),
    ]
