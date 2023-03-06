import datetime
from calendar import monthrange
import pytz
import logging
import decimal
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
logger = logging.getLogger(__name__)

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)


class Schedule():
    def __init__(self, model, start_date=None, end_date=None):
        from sustainergy_dashboard.models import DailyData, Building, Panel, EyedroPanel, Circuit

        # Gets schedule for range if both dates are provided. Otherwise, gets schedule for month of date.
        if start_date and end_date:
            # Provides full range
            self.start_date = start_date
            self.end_date = end_date
        elif start_date and bool(end_date) == False:
            days_in_month = monthrange(start_date.year, start_date.month)[1]
            self.start_date = start_date.replace(day=1)
            self.end_date = start_date.replace(day=days_in_month)
        elif bool(start_date) == False and bool(end_date) == False:
            self.start_date = datetime.date(2022, 8, 1)
            today = datetime.date.today()
            end = today + datetime.timedelta(days=60)
            days_in_month = monthrange(end.year, end.month)[1]
            self.end_date = end.replace(day=days_in_month)

        if type(model) == Building:
            self.building = model
        elif type(model) == Panel or type(model) == EyedroPanel:
            self.building = model.building
        elif type(model) == Circuit:
            self.building = model.panel.building
        else:
            return None

        self.timezone = pytz.timezone(self.building.timezone)

        # Below is solution to N+1 Query Problem. Iterate over the below dailydata_set.all() call to find the data.
        # Don't call get or any other function, or it will hit the database.
        dd_query = DailyData.objects.filter(event_date__range=(self.start_date, self.end_date)).order_by('event_date')
        self._dailydata = Building.objects.prefetch_related(Prefetch('dailydata_set', queryset=dd_query)).get(idbuildings=self.building.idbuildings).dailydata_set.all()

        self.events = self.handle_repeats()

        # Override it on the child.
        self.days = self.create_days(self.events)

    def create_days(self, events):
        days = {}
        for single_date in daterange(self.start_date, self.end_date):
            days[single_date] = Day(single_date, self,  events[single_date])
        return days



    def handle_repeats(self):
        events = {}
        repeat = { 1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None }

        for single_date in daterange(self.start_date, self.end_date):
            data = None
            for item in self._dailydata:
                if item.event_date == single_date:
                    data = item
                    break

            if single_date.day == 1:
                for i in range(1, 8):
                    repeat[i] = None

            if data:                                events[single_date] = data
            elif repeat[single_date.isoweekday()]:  events[single_date] = repeat[single_date.isoweekday()]
            else:                                   events[single_date] = None

            if data and data.is_repeat:
                if data.is_daily:
                    for i in range(1, 8):
                        repeat[i] = data
                elif data.is_weekly:
                    for day in data.days_of_week:
                        if day == "MO":   repeat[1] = data
                        elif day == "TU": repeat[2] = data
                        elif day == "WE": repeat[3] = data
                        elif day == "TH": repeat[4] = data
                        elif day == "FR": repeat[5] = data
                        elif day == "SA": repeat[6] = data
                        elif day == "SU": repeat[7] = data

        return events

class Day():
    def __init__(self, event_date, schedule, daily_data):
        self.utc = pytz.timezone('utc')
        self.event_date = event_date
        self.timezone = schedule.timezone
        self.schedule = schedule

        if daily_data:
            self.start_time = daily_data.start_time
            self.end_time = daily_data.end_time
            self.is_closed = daily_data.is_closed
            self.daily_data = daily_data

        else:
            self.start_time = None
            self.end_time = None
            self.is_closed = None
            self.daily_data = None


class UsageSchedule(Schedule):
    def __init__(self, model, start_date, end_date, usage_data):
        self.usage_data = usage_data
        super().__init__(model, start_date, end_date)

    def create_days(self, events):
        days = {}
        for single_date in daterange(self.start_date, self.end_date):
            days[single_date] = DailyEnergyUsage(single_date, self,  events[single_date], self.usage_data)
        return days

class DailyEnergyUsage(Day):
    def __init__(self, event_date, schedule, daily_data, usage_data):
        super(DailyEnergyUsage, self).__init__(event_date, schedule, daily_data)
        self.first_timestamp = self.timezone.localize(datetime.datetime.combine(self.event_date, datetime.time(0, 10)))
        self.last_timestamp = self.timezone.localize(datetime.datetime.combine((self.event_date + datetime.timedelta(days=1)), datetime.time(0, 0)))
        self.hours_in_day = int( ( self.last_timestamp.astimezone(self.utc) - self.first_timestamp.astimezone(self.utc) + datetime.timedelta(seconds=600) ).total_seconds() / 3600 )
        self.data = self.parse_data(usage_data)

    def usage_data(self):
        def calculate_all_hours_data():
            delta = datetime.timedelta(minutes=10)
            current = self.first_timestamp
            total = Decimal(0)

            while current <= self.last_timestamp:
                total += self.data[current]['kwh_4']
                current += delta
            average = total / self.hours_in_day

            return {"hourly_total": total, "hourly_average": average}

        def calculate_on_hours_data():
            if self.start_time and self.end_time and self.is_closed != True:
                start_oh = self.timezone.localize(datetime.datetime.combine(self.event_date, self.start_time))

                start_stamp = start_oh + datetime.timedelta(minutes=10)

                if self.start_time and self.end_time == datetime.time(0, 0):
                    end_operating_stamp = self.timezone.localize(datetime.datetime.combine(self.event_date + datetime.timedelta(days=1), self.end_time))
                else:
                    end_operating_stamp = self.timezone.localize(datetime.datetime.combine(self.event_date, self.end_time))

                operating_hours_count = Decimal((end_operating_stamp - start_oh).total_seconds() / 3600)

                delta = datetime.timedelta(minutes=10)
                current = start_stamp
                total = Decimal(0)

                while current <= end_operating_stamp:
                    total += self.data[current]['kwh_4']
                    current += delta
                total_on_hours = total
                average_on_hours = total / operating_hours_count
            else:
                total_on_hours = 0
                average_on_hours = 0

            return {"on_hours_total": total_on_hours, "on_hours_average": average_on_hours}

        def calculate_off_hours_data():

            if self.start_time and self.end_time and self.is_closed != True:
                total = Decimal(0)
                average = Decimal(0)

                start_operating = self.timezone.localize(datetime.datetime.combine(self.event_date, self.start_time))

                if self.start_time and self.end_time == datetime.time(0, 0):
                    end_operating = self.timezone.localize(datetime.datetime.combine(self.event_date + datetime.timedelta(days=1), self.end_time))
                else:
                    end_operating = self.timezone.localize(datetime.datetime.combine(self.event_date, self.end_time))


                try:
                    operating_hours_count = Decimal((end_operating - start_operating).total_seconds() / 3600)
                except:
                    breakpoint()

                for key in self.data.keys():
                    if key <= start_operating or key > end_operating:
                        total += self.data[key]['kwh_4']
                average = total / Decimal(self.hours_in_day - operating_hours_count)

            else:
                total = Decimal(0)
                current = self.first_timestamp
                while current <= self.last_timestamp:
                    total += self.data[current]["kwh_4"]
                    current += datetime.timedelta(minutes=10)

                average = total / Decimal(self.hours_in_day)

            return {"off_hours_total": total, "off_hours_average": average}

        output = {}
        on_hours_data = calculate_on_hours_data()
        off_hours_data = calculate_off_hours_data()
        all_hours_data = calculate_all_hours_data()

        output['total_usage'] = all_hours_data['hourly_total']
        output['total_on_hours'] = on_hours_data['on_hours_total']
        output['total_off_hours'] = off_hours_data['off_hours_total']

        output['hourly_average'] = all_hours_data['hourly_average']
        output['hourly_average_on'] = on_hours_data['on_hours_average']
        output['hourly_average_off'] = off_hours_data['off_hours_average']

        if bool(output['total_on_hours'] == False):
            output['percent_usage_on'] = Decimal(0)
            output['percent_usage_off'] = Decimal(100)
        else:
            output['percent_usage_on'] = (output['total_on_hours'] / output['total_usage']) * Decimal(100)
            output['percent_usage_off'] = (output['total_off_hours'] / output['total_usage']) * Decimal(100)

        return output

    def parse_data(self, data):
        start = self.first_timestamp.astimezone(self.utc)
        end = self.last_timestamp.astimezone(self.utc)
        delta = datetime.timedelta(minutes=10)

        result = {}
        current = start
        while current <= end:
            local = current.astimezone(self.timezone)
            result[local] = data[current]
            current = current + delta
        return result
