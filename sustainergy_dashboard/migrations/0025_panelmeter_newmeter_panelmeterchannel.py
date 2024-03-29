# Generated by Django 4.0.6 on 2023-01-25 07:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sustainergy_dashboard', '0024_utilitybills_alter_utilitybill_carbon_levy_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PanelMeter',
            fields=[
                ('name', models.CharField(max_length=12, primary_key=True, serialize=False)),
                ('panel', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.panel')),
            ],
        ),
        migrations.CreateModel(
            name='NewMeter',
            fields=[
            ],
            options={
                'verbose_name_plural': 'Meters',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('sustainergy_dashboard.meter',),
        ),
        migrations.CreateModel(
            name='PanelMeterChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expansion_type', models.CharField(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], max_length=1)),
                ('expansion_number', models.CharField(choices=[('A-1', 'A-1'), ('A-2', 'A-2'), ('A-3', 'A-3'), ('A-4', 'A-4'), ('A-5', 'A-5'), ('A-6', 'A-6'), ('A-7', 'A-7'), ('A-8', 'A-8'), ('A-9', 'A-9'), ('A-10', 'A-10'), ('A-11', 'A-11'), ('A-12', 'A-12'), ('A-13', 'A-13'), ('A-14', 'A-14'), ('A-15', 'A-15'), ('A-16', 'A-16'), ('B-1', 'B-1'), ('B-2', 'B-2'), ('B-3', 'B-3'), ('B-4', 'B-4'), ('B-5', 'B-5'), ('B-6', 'B-6'), ('B-7', 'B-7'), ('B-8', 'B-8'), ('B-9', 'B-9'), ('B-10', 'B-10'), ('B-11', 'B-11'), ('B-12', 'B-12'), ('B-13', 'B-13'), ('B-14', 'B-14'), ('B-15', 'B-15'), ('B-16', 'B-16'), ('C-1', 'C-1'), ('C-2', 'C-2'), ('C-3', 'C-3'), ('C-4', 'C-4'), ('C-5', 'C-5'), ('C-6', 'C-6'), ('C-7', 'C-7'), ('C-8', 'C-8'), ('C-9', 'C-9'), ('C-10', 'C-10'), ('C-11', 'C-11'), ('C-12', 'C-12'), ('C-13', 'C-13'), ('C-14', 'C-14'), ('C-15', 'C-15'), ('C-16', 'C-16'), ('D-1', 'D-1'), ('D-2', 'D-2'), ('D-3', 'D-3'), ('D-4', 'D-4'), ('D-5', 'D-5'), ('D-6', 'D-6'), ('D-7', 'D-7'), ('D-8', 'D-8'), ('D-9', 'D-9'), ('D-10', 'D-10'), ('D-11', 'D-11'), ('D-12', 'D-12'), ('D-13', 'D-13'), ('D-14', 'D-14'), ('D-15', 'D-15'), ('D-16', 'D-16')], max_length=6)),
                ('circuit_number', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.circuit')),
                ('panel_meter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.panelmeter')),
            ],
        ),
    ]
