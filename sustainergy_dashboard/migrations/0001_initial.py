# Generated by Django 4.0.6 on 2022-10-21 19:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_mysql.models
import sustainergy_dashboard.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', sustainergy_dashboard.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line_1', models.CharField(max_length=30)),
                ('line_2', models.CharField(blank=True, max_length=30, null=True)),
                ('city', models.CharField(max_length=28)),
                ('province', models.CharField(choices=[('AB', 'Alberta'), ('BC', 'British Columbia'), ('MB', 'Manitoba'), ('NB', 'New Brunswick'), ('NL', 'Newfoundland and Labrador'), ('NS', 'Nova Scotia'), ('ON', 'Ontario'), ('PE', 'Prince Edward Island'), ('QC', 'Quebec'), ('SK', 'Saskatchewan'), ('NT', 'Northwest Territories'), ('NU', 'Nunavut'), ('YT', 'Yukon')], default='AB', max_length=2)),
                ('postal_code', models.CharField(max_length=7)),
            ],
            options={
                'verbose_name_plural': 'Addresses',
                'db_table': 'addresses',
            },
        ),
        migrations.CreateModel(
            name='Building',
            fields=[
                ('idbuildings', models.CharField(default=sustainergy_dashboard.models.unique_rand_building, max_length=30, primary_key=True, serialize=False, unique=True)),
                ('client_id', models.CharField(blank=True, max_length=30)),
                ('description', models.CharField(max_length=30)),
                ('occupants', models.CharField(blank=True, max_length=30)),
                ('occupies_days_per_week', models.CharField(blank=True, max_length=30)),
                ('length_of_occupied_day', models.CharField(blank=True, max_length=30)),
                ('start_hour', models.CharField(blank=True, max_length=30)),
                ('end_hour', models.CharField(blank=True, max_length=30)),
                ('number_of_doors', models.CharField(blank=True, max_length=30)),
                ('squarefootage', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('exterior_wall_squarefootage', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('window_squarefootage', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('roof_squarefootage', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('year_built', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('price_per_gj', models.CharField(blank=True, max_length=30)),
                ('price_per_kwh', models.CharField(blank=True, max_length=30)),
                ('vist_duration', models.CharField(blank=True, max_length=30)),
                ('calculated', models.BooleanField(default=False)),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.address')),
            ],
            options={
                'db_table': 'buildings',
            },
        ),
        migrations.CreateModel(
            name='CircuitCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=30, unique=True)),
                ('color', models.CharField(max_length=30)),
            ],
            options={
                'verbose_name_plural': 'Circuit Categories',
                'db_table': 'circuit_categories',
            },
        ),
        migrations.CreateModel(
            name='DailyData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_closed', models.BooleanField()),
                ('is_repeat', models.BooleanField()),
                ('days_of_week', django_mysql.models.ListCharField(models.CharField(blank=True, max_length=10, null=True), max_length=66, size=6)),
                ('is_daily', models.BooleanField()),
                ('is_weekly', models.BooleanField()),
            ],
            options={
                'db_table': 'daily_data',
            },
        ),
        migrations.CreateModel(
            name='Facility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=30, unique=True)),
                ('image', models.ImageField(upload_to='facilities')),
            ],
            options={
                'verbose_name_plural': 'Facilities',
                'db_table': 'facilities',
            },
        ),
        migrations.CreateModel(
            name='Panel',
            fields=[
                ('panel_name', models.CharField(max_length=30)),
                ('panel_id', models.CharField(default=sustainergy_dashboard.models.unique_rand_panel, max_length=30, primary_key=True, serialize=False, unique=True)),
                ('panel_type', models.CharField(blank=True, max_length=30)),
                ('panel_voltage', models.CharField(choices=[('208v', '120V/208V'), ('240v', '120V/240V'), ('480v', '277V/480V'), ('600v', '347V/600V'), ('STD', 'Standard')], default='STD', max_length=4)),
                ('panel_image', models.CharField(blank=True, max_length=50)),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.building')),
            ],
            options={
                'db_table': 'panel_data',
            },
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('company_id', models.CharField(default=sustainergy_dashboard.models.unique_rand_company, max_length=30, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=30)),
                ('headquarters', models.CharField(max_length=30)),
                ('address', models.CharField(max_length=30)),
                ('postal_code', models.CharField(max_length=30)),
                ('city', models.CharField(max_length=30)),
                ('staff', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Companies',
                'db_table': 'companies',
            },
        ),
        migrations.CreateModel(
            name='Circuit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('circuit_name', models.CharField(max_length=30)),
                ('circuit_amps', models.CharField(blank=True, max_length=30)),
                ('circuit_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.circuitcategory')),
                ('panel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.panel')),
            ],
            options={
                'db_table': 'circuit_data',
            },
        ),
        migrations.AddField(
            model_name='building',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.company'),
        ),
        migrations.AddField(
            model_name='building',
            name='facility',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='sustainergy_dashboard.facility'),
        ),
        migrations.AddField(
            model_name='building',
            name='staff',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
