import shortuuid
from django.core.exceptions import ValidationError
from django.db import models
from django_mysql.models import ListCharField
from django.core.validators import int_list_validator
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models import Max
from django.urls import reverse
from calendar import monthrange

from django.utils.html import format_html
from sustainergy_dashboard.schedule import Schedule, UsageSchedule, daterange
import datetime
import requests
import pytz
import logging
logger = logging.getLogger(__name__)
import decimal
from decimal import Decimal
from calendar import monthrange
import json
from colorfield.fields import ColorField

class AddressedModel(models.Model):
    PROVINCES = [
        ("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
        ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
        ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
        ("QC","Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
        ("NU", "Nunavut"), ("YT", "Yukon")]
    class Meta:
        abstract = True
    address_line_1 = models.CharField(max_length=30)
    address_line_2 = models.CharField(max_length=30, blank=True, null=True)
    city = models.CharField(max_length=28)
    province = models.CharField(max_length=2, choices=PROVINCES, default="AB")
    postal_code = models.CharField(max_length=7)

class AddressedModelMixin(AddressedModel):
    class Meta:
        abstract = True

class ColouredModel(models.Model):
    class Meta:
        abstract = True
    COLOUR_PALETTE = [
        ("#3649a8", "Dark Blue"), ("#ee8f37", "Orange"), ("#DB4B46", "Red"), ("#3bcdee", "Sky Blue"),
        ("#777777", "Grey"), ("#994f9b", "Purple"), ("#ffadc9", "Light Pink"), ("#000000", "Black"),
        ("#F7CA50", "Yellow"), ("#98C355", "Green"), ("#911120", "Brown"), ("#C5BFE6", "Light Purple"),
        ("#006ba9", "Dark Sky"), ("#4DAAE8", "Blue"), ("#FFFFE0", "Light Yellow")
    ]
    colour = ColorField(samples=COLOUR_PALETTE, blank=False, null=False, default="#3649a8")


class ColouredModelMixin(ColouredModel):
    class Meta:
        abstract=True

def unique_rand_building():
    while True:
        uuid = shortuuid.ShortUUID().random(length=8)
        if not Building.objects.filter(idbuildings = uuid).exists():
            return uuid

def unique_rand_panel():
    while True:
        uuid = shortuuid.ShortUUID().random(length=8)
        if not Panel.objects.filter(panel_id = uuid).exists():
            return uuid

def unique_rand_company():
    while True:
        uuid = shortuuid.ShortUUID().random(length=8)
        if not Company.objects.filter(company_id = uuid).exists():
            return uuid


class UserManager(BaseUserManager):
    """Define a model manger for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields._create_user(email, password, **extra_fields)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    STANDARD_USER = "STANDARD_USER", "Standard User"
    INSTALLER_USER = "INSTALLER_USER", "Installer User"


class User(AbstractUser):
    """User model."""

    username = None
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STANDARD_USER)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def is_installer(self):
        return self.role == UserRole.INSTALLER_USER


class Company(models.Model):
    class Meta:
        db_table = "companies"
        verbose_name_plural = "Companies"

    company_id = models.CharField(max_length=30, primary_key=True, default=unique_rand_company, serialize=True, unique=True)
    name = models.CharField(max_length=30)
    headquarters = models.CharField(max_length=30)
    address = models.CharField(max_length=30)
    postal_code = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
    staff = models.ManyToManyField(User, blank=True)
    image = models.ImageField(upload_to='companies', blank=True, null=True)

    def image_tag(self):
        return mark_safe('<img src="%s" width="232" height="232" />' % (self.image.url))

    def __str__(self):
        return "{0} ({1})".format(self.name, self.company_id)


class Facility(models.Model):
    class Meta:
        db_table = "facilities"
        verbose_name_plural = "Facilities"
    type = models.CharField(max_length=30, blank=False, unique=True)
    image = models.ImageField(upload_to='facilities')

    def image_tag(self):
        return mark_safe('<img src="%s" width="232" height="232" />' % (self.image.url))

    def __str__(self):
        return "{0}".format(self.type)


class Building(AddressedModelMixin, models.Model):
    class Meta:
        db_table = "buildings"

    TIMEZONES = [
        ('America/St_Johns', 'St. Johns'), ('America/Halifax','Halifax'), ('Americca/Glace_Bay','Glace Bay'),
        ('America/Moncton','Moncton'), ('America/Goose_Bay','Goose Bay'), ('America/Blanc-Sablon','Blanc Sablon'),
        ('America/Toronto','Toronto'), ('America/Nipigon','Nipigon'), ('America/Thunder_Bay','Thunder Bay'),
        ('America/Iqaluit','Iqaluit'), ('America/Pangnirtung','Pangnirtung'), ('America/Atikokan','Atikokan'),
        ('America/Winnipeg','Winnipeg'), ('America/Rainy_River','Rainy Riger'), ('America/Resolute','Resolute'),
        ('America/Rankin_Inlet','Rankin Inlet'), ('America/Regina','Regina'), ('America/Swift_Current','Swift Current'),
        ('America/Edmonton','Edmonton'), ('America/Cambridge_Bay','Cambridge Bay'), ('America/Yellowknife','Yellowknife'),
        ('America/Inuvik','Inuvik'), ('America/Creston','Creston'), ('America/Dawson_Creek','Dawson Creek'),
        ('America/Fort_Nelson','Fort Nelson'), ('America/Whitehorse','Whitehorse'), ('America/Dawson','Dawson'),
        ('America/Vancouver','Vancouver')
    ]

    timezone = models.CharField(max_length=30, choices=TIMEZONES, default="America/Edmonton")

    idbuildings = models.CharField(max_length=30, primary_key=True, default=unique_rand_building, serialize=True, unique=True)
    company = models.ForeignKey(Company, on_delete = models.CASCADE)
    facility = models.ForeignKey(Facility, on_delete = models.CASCADE, blank=False, default=1)
    staff = models.ManyToManyField(User, blank=True)

    client_id = models.CharField(max_length=30, blank=True)

    description = models.CharField(max_length=30, blank=False)

    occupants = models.CharField(max_length=30, blank=True)
    occupies_days_per_week = models.CharField(max_length=30, blank=True)
    length_of_occupied_day = models.CharField(max_length=30, blank=True)
    start_hour = models.CharField(max_length=30, blank=True)
    end_hour = models.CharField(max_length=30, blank=True)
    number_of_doors = models.CharField(max_length=30, blank=True)

    squarefootage = models.PositiveIntegerField( blank=True, null=True, default=0)
    exterior_wall_squarefootage = models.PositiveIntegerField(blank=True, null=True, default=0)
    window_squarefootage = models.PositiveIntegerField(blank=True, null=True, default=0)
    roof_squarefootage = models.PositiveIntegerField(blank=True, null=True, default=0)
    year_built = models.PositiveSmallIntegerField( blank=True, null=True )

    price_per_gj = models.CharField(max_length=30, blank=True)
    price_per_kwh = models.CharField(max_length=30, blank=True)
    vist_duration = models.CharField(max_length=30, blank=True)
    calculated = models.BooleanField(default=False)

    def import_xlsx(self):
        url = reverse('import_xlsx')
        return mark_safe('<a href="%s?%s">Click to import</a>'% (url, self.idbuildings) )

    import_xlsx.allow_tags = True
    import_xlsx.short_description = 'Import xlsx file'

    def utility_bills(self):
        url = reverse('utility_bills')
        return mark_safe('<a href="%s?building=%s">Show Utility Bills</a>'% (url, self.idbuildings) )

    utility_bills.allow_tags = True

    def panel_count(self):
        building_id = self.idbuildings
        panels = Panel.objects.filter(building=building_id)
        return len(panels)

    def square_meters(self):
        if self.squarefootage:
            raw_meters = Decimal(self.squarefootage) * Decimal(0.092903)
            return round(raw_meters, 2)
        else:
            return None

    def age(self):
       if self.year_built:
           return datetime.date.today().year - self.year_built
       else:
           return None

    def facility_type(self):
        return self.facility.type
    def facility_image(self):
        return self.facility.image_tag

    def __str__(self):
        return "{0} - {1}".format(self.description, self.idbuildings)

    def building_id(self):
        return self.idbuildings

    def schedule(self, start_date=None, end_date=None):
        return Schedule(self, start_date, end_date)

    def energy_usage_data(self, start_date, end_date=None):
        if bool(end_date) == False:
            last_day_of_month = monthrange(start_date.year, start_date.month)[1]
            end_date = start_date.replace(day=last_day_of_month)
        else:
            end_date = end_date
        return BuildingEnergyUsage(self, start_date, end_date)
    

class BuildingEnergyUsage():
    def __init__(self, building, start_date, end_date):
        self.building = building
        self.panels = EyedroPanel.objects.filter(building_id=building.idbuildings)

        self.start_date = start_date
        self.end_date = end_date
        self.schedule = Schedule(self.building, self.start_date, self.end_date)

        self.panel_data = self.get_panel_data()

    def get_panel_data(self):
        output = []
        for panel in self.panels:
            panel_data = panel.energy_usage_data(self.start_date, self.end_date)
            output.append(panel_data)
        return output

    def round_numbers(self, obj, dec):
        if isinstance(obj, Decimal):
            return round(obj, dec)
        elif isinstance(obj, dict):
            return {self.round_numbers(k, dec): self.round_numbers(v, dec) for k, v in obj.items()}
        elif isinstance(obj, list):
            return[self.round_numbers(i, dec) for i in obj]
        return obj


    def report(self):
        building = {}
        building_fields = ['total_usage', 'total_on_hours', 'total_off_hours', 'percent_usage_on',
                           'percent_usage_off', 'hourly_average_on', 'daily_average_on', 'hourly_average_off',
                           'daily_average_off', 'peak_usage', 'hourly_average', 'daily_average']
        for field in building_fields:
            building[field] = Decimal(0)

        output_panel_report = {}

        daily_breakdown = {}
        for panel in self.panel_data:
            report = panel.report()
            panel_report_data = report['panel_usage']
            panel_daily_data = report['daily_usage']

            building['total_usage'] += panel_report_data['total_usage']
            building['total_on_hours'] += panel_report_data['total_on_hours']
            building['total_off_hours'] += panel_report_data['total_off_hours']

            panel_object = {
                "name": panel.panel.panel_name,
                "id" : panel.panel.panel_id,
                "total_usage": panel_report_data['total_usage'],
                "total_on_hours": panel_report_data['total_on_hours'],
                "total_off_hours": panel_report_data['total_off_hours'],
                "peak_usage": panel_report_data['peak_usage'],
                "hourly_average": panel_report_data['hourly_average'],
                "hourly_average_on": panel_report_data['hourly_average_on'],
                "hourly_average_off": panel_report_data['hourly_average_off'],
                "daily_average": panel_report_data['daily_average'],
                "daily_average_on": panel_report_data['daily_average_on'],
                "daily_average_off": panel_report_data['daily_average_off'],
                "percent_usage_on": panel_report_data['percent_usage_on'],
                "percent_usage_off": panel_report_data['percent_usage_off'],
                "colour": panel_report_data['colour'],
                "daily_usage": panel_daily_data
            }

            output_panel_report[panel_object["id"]] = panel_object

            daily_data = report['daily_usage']
            for day in panel.schedule.days:
                if day in daily_breakdown:
                    daily_breakdown[day]["total_usage"] += daily_data[day]['total_usage']
                    daily_breakdown[day]["total_on_hours"] += daily_data[day]["total_on_hours"]
                    daily_breakdown[day]["total_off_hours"] += daily_data[day]["total_off_hours"]
                else:
                    daily_breakdown[day] = {}
                    daily_breakdown[day]["total_usage"] = daily_data[day]['total_usage']
                    daily_breakdown[day]["total_on_hours"] = daily_data[day]["total_on_hours"]
                    daily_breakdown[day]["total_off_hours"] = daily_data[day]["total_off_hours"]

        for day in self.schedule.days:
            if bool(daily_breakdown[day]['total_on_hours']) == False:
                daily_breakdown[day]['percent_usage_on'] = Decimal(0)
                daily_breakdown[day]['percent_usage_off'] = Decimal(100)
            else:
                daily_breakdown[day]['percent_usage_on'] = (daily_breakdown[day]['total_on_hours'] / daily_breakdown[day]['total_usage']) * Decimal(100)
                daily_breakdown[day]['percent_usage_off'] = (daily_breakdown[day]['total_off_hours'] / daily_breakdown[day]['total_usage']) * Decimal(100)
            if daily_breakdown[day]['total_usage'] > building['peak_usage']:
                building['peak_usage'] = daily_breakdown[day]['total_usage']


        for panel in  self.panel_data:
            panel_report_data = panel.report()['panel_usage']
            output_panel_report[panel.panel.panel_id]['percentage_total_energy'] = (panel_report_data['total_usage'] / building['total_usage']) * Decimal(100)
            keyset = ['hourly_average_on', 'daily_average_on', 'hourly_average_off', 'daily_average_off', 'hourly_average', 'daily_average']
            for key in keyset:
                building[key] += panel_report_data[key]

        building['percent_usage_on'] = (building['total_on_hours'] / building['total_usage']) * 100
        building['percent_usage_off'] = (building['total_off_hours'] / building['total_usage']) * 100

        schedule = {}
        for day in self.schedule.days:
            schedule[day] = {
                'event_date': self.schedule.days[day].event_date,
                'start_time': self.schedule.days[day].start_time,
                'end_time': self.schedule.days[day].end_time,
                'is_closed': self.schedule.days[day].is_closed,
                'building_id': self.building.idbuildings
            }

        response = {
            "building": building,
            "schedule": schedule,
            "panels": output_panel_report,
            "daily": daily_breakdown
        }

        for key in response:
            response[key] = self.round_numbers(response[key], 1)

        return response



    def report_json(self):
        report = self.report()
        return json.dumps(
            report,
            sort_keys=True,
            indent=None,
            cls=ReportEncoder)



class ReportEncoder(json.JSONEncoder):
    def _preprocess_date(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, datetime.time):
            return obj.strftime("%H:%M")
        elif isinstance(obj, datetime.datetime):
            if obj.tzinfo == None:
                return obj.strftime("%Y-%m-%D %H:%M:%S")
            else:
                return obj.strftime("%Y-%m-%D %H:%M:%S.%f")
        elif isinstance(obj, dict):
            return {self._preprocess_date(k): self._preprocess_date(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._preprocess_date(i) for i in obj]
        return obj

    def default(self, obj):
        if isinstance(obj, Decimal):
            rounded = round(obj, 2)
            return str(rounded)
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, datetime.datetime):
            if obj.tzinfo == None:
                return obj.strftime("%Y-%m-%D %H:%M:%S")
            else:
                return obj.strftime("%Y-%m-%D %H:%M:%S.%f")
        return super().default(obj)

    def iterencode(self, obj, _one_shot):
        return super().iterencode(self._preprocess_date(obj))


class Panel(ColouredModelMixin, models.Model):
    class Meta:
        db_table = "panel_data"
    def __str__(self):
        return "{0} - {1} ({2})".format(self.panel_name, self.building.description, self.panel_id)

    VOLTAGES = [
        ('208v', '120V/208V'),
        ('240v', '120V/240V'),
        ('480v', '277V/480V'),
        ('600v', '347V/600V'),
        ('STD',  'Standard')
    ]
    PROVIDERS = [
        ('None', 'None'),
        ('Eyedro', 'Eyedro'),
        ('Opti-Mized', 'Opti-Mized')
    ]

    panel_name = models.CharField(max_length=256)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, to_field='idbuildings')
    panel_id = models.CharField(max_length=30, primary_key=True, default=unique_rand_panel, unique=True)
    panel_type = models.CharField(max_length=30, blank=True)
    panel_voltage = models.CharField(max_length=4, choices=VOLTAGES, default='STD')
    panel_image = models.ImageField(upload_to='panels', blank=True, null=True)
    provider = models.CharField(max_length=30, choices=PROVIDERS, default='None')
    serial = models.CharField(max_length=30, blank=True)

    def circuit_count(self):
        panel_id = self.panel_id
        circuits = Circuit.objects.filter(panel=panel_id)
        return len(circuits)

    def schedule(self, start_date, end_date=None):
        return Schedule(self, start_date, end_date)
    
    def add_panel_images(self,images):
        for image in images:
            PanelImage.objects.create(panel_id=self.panel_id,image=image)
        print("image uploaded successfuly")
    
    add_panel_images.allow_tags = True
    
    def img_preview(self): #new
        panel_images = PanelImage.objects.filter(panel=self.panel_id)
        images = ""
        url = "https://srg-be-prod.s3.us-west-2.amazonaws.com/"
        for image in panel_images:
            images += '<br>' + mark_safe(f'<a href="https://srg-be-prod.s3.us-west-2.amazonaws.com/{image.image}" target="_blank"><img src = "https://srg-be-prod.s3.us-west-2.amazonaws.com/{image.image}"  width="70" height="50" border="5" style="object-fit: cover;"/></a>')
        return format_html(images)
    
    img_preview.allow_tags = True
    

class PanelImage(models.Model):
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, to_field='panel_id',related_name='panel_images')
    image = models.ImageField(upload_to='panel_images')
    

class EyedroPanelManager(models.Manager):
    def get_queryset(self):
        return super(EyedroPanelManager, self).get_queryset().filter(provider='Eyedro')

class EyedroPanel(Panel):
    objects = EyedroPanelManager()
    class Meta:
        proxy = True

    def generate_request_timestamps(self, start_date, end_date):
        timezone = pytz.timezone(self.building.timezone)
        utc = pytz.timezone('utc')

        local_start = timezone.localize(datetime.datetime.combine(start_date, datetime.time(0, 10)))
        local_end = timezone.localize(datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time(0, 0)))

        utc_start_time = local_start.astimezone(utc)
        utc_end_time = local_end.astimezone(utc)

        return { "start_datetime": utc_start_time, "end_datetime": utc_end_time}


    def energy_usage_data(self, start_date, end_date=None):
        if bool(end_date) == False:
            last_day_of_month = monthrange(start_date.year, start_date.month)[1]
            start_date = start_date.replace(day=1)
            end_date = start_date.replace(day=last_day_of_month)

        data_range = self.generate_request_timestamps(start_date, end_date)
        data = self.api_call(data_range["start_datetime"], data_range["end_datetime"])
        response = PanelUsageData(self, data, start_date, end_date)

        return response


    def api_call(self, start_datetime, end_datetime):
        fmt = "%Y-%m-%d %H:%M:%S"
        API_URL = "https://04szt6hg05.execute-api.us-east-1.amazonaws.com/default/rawdataAPI"
        HEADERS = { "x-api-key": "KUTfYpYtEQ8HkhzHWNQQ69Y5Eb9jYsAK1WyjaaWp",
                    "Content-Type": "application/json"}
        DATA = {'start_time': start_datetime.strftime(fmt),
                'end_time': end_datetime.strftime(fmt),
                'device_id': self.serial }

        logger.info("Making Eyedro API Request at {timestamp}".format(timestamp=datetime.datetime.now()))
        raw_data =  requests.get(API_URL, json=DATA, headers=HEADERS)

        return raw_data.json()


class PanelUsageData():
    def __init__(self, panel, data, start_date, end_date):
        self.panel = panel
        self.raw_data = data
        self.start_date = start_date
        self.end_date = end_date
        self.data = self.process_raw_data(data)
        self.timezone = pytz.timezone(panel.building.timezone)
        self.utc = pytz.timezone('utc')
        self.schedule = UsageSchedule(self.panel, self.start_date, self.end_date, self.data)


    def report(self):
        days = self.schedule.days

        total_usage = total_on_hours = total_off_hours = peak_usage = Decimal(0)
        hourly_average = hourly_average_on = hourly_average_off = Decimal(0)
        daily_average = daily_average_on = daily_average_off = Decimal(0)

        daily_usage = {}
        number_of_days = len(self.schedule.days)

        for day in days:
            data = days[day]

            usage_data = data.usage_data()
            daily_usage[day] = usage_data

            total_usage += usage_data['total_usage']
            total_on_hours += usage_data['total_on_hours']
            total_off_hours += usage_data['total_off_hours']
            if peak_usage < usage_data['total_usage']:
                peak_usage = usage_data['total_usage']

            hourly_average += (usage_data['hourly_average'] * Decimal(1 / number_of_days))
            hourly_average_on += (usage_data['hourly_average_on'] * Decimal(1 / number_of_days))
            hourly_average_off += (usage_data['hourly_average_off'] * Decimal(1 /number_of_days))

            daily_average += (usage_data['total_usage'] * Decimal(1 / number_of_days))
            daily_average_on += (usage_data['total_on_hours'] * Decimal(1 / number_of_days))
            daily_average_off += (usage_data['total_off_hours'] * Decimal(1 / number_of_days))

        percent_usage_on = (total_on_hours / total_usage) * Decimal(100)
        percent_usage_off = (total_off_hours / total_usage) * Decimal(100)

        output = {
            "panel_usage": {
                "total_usage": total_usage,
                "total_on_hours": total_on_hours,
                "total_off_hours": total_off_hours,
                "peak_usage": peak_usage,
                "hourly_average": hourly_average,
                "hourly_average_on": hourly_average_on,
                "hourly_average_off": hourly_average_off,
                "daily_average": daily_average,
                "daily_average_on": daily_average_on,
                "daily_average_off": daily_average_off,
                "percent_usage_on": percent_usage_on,
                "percent_usage_off": percent_usage_off,
                "colour": self.panel.colour
            },
            "daily_usage": daily_usage
        }
        return output


    def process_raw_data(self, data):
        try:
            if "data" in self.raw_data:
                data = self.raw_data["data"]
            else:
                data = self.raw_data
        except:
            breakpoint()
        fmt = "%Y-%m-%d %H:%M:%S.000%f"
        utc = pytz.timezone('utc')
        output = {}
        divisor = Decimal(1/6)

        for datapoint in data:
            dt = datetime.datetime.strptime(datapoint['time'], fmt)
            utc_dt = utc.localize(dt)

            output[utc_dt] = {'kw_1':  Decimal(datapoint['kw_1']),
                              'kwh_1': divisor * Decimal(datapoint['kw_1']),
                              'kw_2':  Decimal(datapoint['kw_2']),
                              'kwh_2': divisor * Decimal(datapoint['kw_2']),
                              'kw_3':  Decimal(datapoint['kw_3']),
                              'kwh_3': divisor * Decimal(datapoint['kw_3']),
                              'kw_4':  Decimal(datapoint['kw_4']),
                              'kwh_4': divisor * Decimal(datapoint['kw_4'])}
        return output


class CircuitCategory(ColouredModelMixin, models.Model):
    class Meta:
        db_table = "circuit_categories"
        verbose_name_plural = "Circuit Categories"
    def __str__(self):
        return self.name

    name = models.CharField(max_length=30, default="", unique=True)
    icon = models.ImageField(upload_to='categories', blank=True, null=True)


class Circuit(models.Model):
    class Meta:
        db_table = "circuit_data"
    def __str__(self):
        return "{0} - {1} - {2} ({3})".format(self.circuit_number, self.circuit_name, self.panel.panel_name, self.panel_id)

    circuit_number = models.IntegerField(blank=True, null=True)
    circuit_name = models.CharField(max_length=256)
    circuit_category = models.ForeignKey(CircuitCategory, blank=True, null=True, on_delete=models.CASCADE)
    circuit_amps = models.CharField(max_length=60, blank=True)
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, to_field='panel_id')

    def schedule(self, start_date, end_date=None):
        return Schedule(self, start_date, end_date)

    def category_color(self):
        return self.circuit_category.colour if self.circuit_category else ""


@receiver(pre_save, sender = Circuit)
def pre_save_call_for_circuits(sender,instance, **kwargs):
    
    if instance.circuit_number is None:
        row_count = Circuit.objects.filter(panel_id=instance.panel.pk).aggregate(Max('circuit_number'))['circuit_number__max']
        if row_count is None:
            row_count = 0
        instance.circuit_number = row_count + 1
    else:
        pass


class DailyData(models.Model):
    class Meta:
        db_table = "daily_data"

    building = models.ForeignKey(Building, blank=False, null=False, on_delete=models.CASCADE,)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_closed = models.BooleanField()
    is_repeat = models.BooleanField()
    days_of_week = ListCharField(
        base_field=models.CharField(max_length=10, blank=True,null=True),
        size=6,
        max_length=(6 * 11),  # 6 * 10 character nominals, plus commas
    )
    is_daily = models.BooleanField()
    is_weekly = models.BooleanField()

    def save(self, *args, **kwargs):
        if self.is_repeat:
            last_day_of_month = monthrange(self.event_date.year, self.event_date.month)[1]
            end_date = self.event_date.replace(day=last_day_of_month)

            for event_date in daterange(self.event_date, end_date):
                day = str(str(event_date.strftime("%a")).upper()[:-1])  # it gets MO or TU, etc
                if self.is_daily or (self.is_weekly and day in self.days_of_week):
                    daily_data = DailyData.objects.filter(building=self.building, event_date=event_date)
                    if daily_data.exists():
                        for data in daily_data:
                            data.start_time=self.start_time
                            data.end_time=self.end_time
                            data.is_closed=self.is_closed
                            data.is_repeat = False
                            data.is_daily = False
                            data.is_weekly = False
                            data.save()
                    else:
                        DailyData.objects.create(building=self.building, event_date=event_date,
                                                 start_time=self.start_time, end_time=self.end_time,
                                                 is_closed=self.is_closed, days_of_week=[day],
                                                 is_repeat=False, is_daily=False, is_weekly=False)
        else:
            super(DailyData, self).save(*args, **kwargs)


class Utility(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False)

    def __str__(self):
        return self.name


class UtilityProvider(models.Model):
    name = models.CharField(max_length=30, null=True, blank=True)
    logo = models.ImageField(upload_to='utility_providers', blank=True, null=True)

    def __str__(self):
        return self.name


class Meter(models.Model):

    name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    meter_id = models.CharField(max_length=20, primary_key=True)
    meter_type = models.ForeignKey(Utility, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=30, null=True, blank=True)
    utility_provider = models.ForeignKey(UtilityProvider, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.meter_id + " - " + self.meter_type.name

    class Meta:
        verbose_name_plural = "Utility Meters"



class UtilityBill(models.Model):
    price_per_unit = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True)
    usage = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True)
    total_commodity = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True, verbose_name='Total cost')
    distribution = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True)
    carbon_levy = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True)
    gst = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True)
    total_bill = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True)
    statement_date = models.DateField()
    invoice_number = models.CharField(max_length=20, null=True, blank=True)
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True, blank=True)
    line = models.CharField(max_length=100, null=True, blank=True)
    rider = models.CharField(max_length=100, null=True, blank=True)

    def billing_month(self):
        return self.statement_date.strftime('%B, %y')

    def utility(self):
        return self.meter.meter_type.name

    def meter_name(self):
        return self.meter.meter_id + " - " + self.utility()

    def __str__(self):
        return self.meter.meter_id

    def clean(self):
        if (not self.id) and self.statement_date and hasattr(self, 'meter'):
            if UtilityBill.objects.filter(statement_date__month=self.statement_date.month,
                                          statement_date__year=self.statement_date.year,
                                          meter__meter_type__name=self.meter.meter_type.name,
                                          meter__building=self.meter.building).exists():
                raise ValidationError({'statement_date': 'Utility bill for this month already exists.'})
        super(UtilityBill, self).clean()

    def save(self, *args, **kwargs):
        self.clean()
        self.building = self.meter.building
        super(UtilityBill, self).save(*args, **kwargs)


def get_expansion_numbers():
    expansion_types = ["A", "B", "C", "D"]
    expansion_numbers = []
    for exp_type in expansion_types:
        for num in range(1, 17):  # for 1 to 16
            expansion_numbers.append((exp_type + "-" + str(num), exp_type + "-" + str(num)))
    return expansion_numbers


class PanelMeter(models.Model):

    PHASE_CHOICES = (
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
    )
    name = models.CharField(max_length=30, unique=True)
    panel = models.OneToOneField(Panel, on_delete=models.CASCADE)
    number_of_phases = models.CharField(max_length=50, choices=PHASE_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.name + " - " + self.panel.panel_name


    def save(self, *args, **kwargs):
        if not self.id:  # for creation only
            super(PanelMeter, self).save(*args, **kwargs)
            self.create_related_meter_channels()
        else:
            super(PanelMeter, self).save(*args, **kwargs)

    def create_related_meter_channels(self):
        expansion_numbers = get_expansion_numbers()
        for expansion_number in expansion_numbers:
            PanelMeterChannel.objects.create(panel_meter=self, expansion_type=expansion_number[0].split("-")[0],
                                             expansion_number=expansion_number[0])


class PanelMeterChannel(models.Model):

    expansion_type_choices = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    )

    VOLTAGE_REF_TYPE_CHOICES = (
        ("V1", "V1"),
        ("V2", "V2"),
        ("V3", "V3"),
    )

    expansion_number_choices = get_expansion_numbers()  # it gets a list like [('A-1', 'A-1'), ...]

    panel_meter = models.ForeignKey(PanelMeter, on_delete=models.CASCADE)
    expansion_type = models.CharField(choices=expansion_type_choices, max_length=1)
    expansion_number = models.CharField(choices=expansion_number_choices, max_length=6)
    circuit_id = models.ForeignKey(Circuit, on_delete=models.CASCADE, null=True)
    current = models.FloatField(default=0.0, null=True, blank=True)
    voltage_refrence_type = models.CharField(max_length=50, choices=VOLTAGE_REF_TYPE_CHOICES, null=True, blank=True)
    voltage_refrence_value = models.FloatField(default=0.0, null=True, blank=True)

    def __str__(self):
        return self.panel_meter.name + " - " + self.expansion_number

    @property
    def power(self):
        # power = V * I (voltage * current)
        return self.current*self.voltage_refrence_value
