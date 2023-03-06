import requests
from datetime import datetime, date, time, timezone, timedelta
import pytz
from calendar import monthrange

class EyedroAPI:
    API_URL = "https://04szt6hg05.execute-api.us-east-1.amazonaws.com/default/rawdataAPI"
    utc = pytz.utc
    fmt = "%Y-%m-%d %H:%M:%S"

    def __init__(self, timezone):
        self.tz = pytz.timezone(timezone)

    def get_month(self, device_id, month, year):
        r = self.get_range_for_month(year, month)
        start_date = r['start_time']
        end_date = r['end_time']
        tz = self.tz
        device_id = device_id
        raw_data = self.api_call(start_date, end_date, device_id)
        result = EyedroData(tz=tz,
                            device_id=device_id,
                            start_date=start_date,
                            end_date=end_date,
                            raw_data=raw_data,
                            year=year,
                            month=month)
        return result
        # return self.api_call(range['start_time'], range['end_time'], device_id)

    def get_range_for_month(self, year, month):
        start_time = self.tz.localize(datetime(year, month, 1, 0, 10, 0))

        if month == 12:
            end_time = self.tz.localize(datetime(year + 1, 1, 1, 0, 0, 0))
        else:
            end_time = self.tz.localize(datetime(year, month+1, 1, 0, 0, 0))

        api_start_time = start_time.astimezone(self.utc).strftime(self.fmt)
        api_end_time = end_time.astimezone(self.utc).strftime(self.fmt)

        data = {"start_time": api_start_time,
                "end_time": api_end_time}
        return data

    def api_call(self, start_time, end_time, device_id):
        HEADERS = {"x-api-key": "KUTfYpYtEQ8HkhzHWNQQ69Y5Eb9jYsAK1WyjaaWp",
                   "Content-Type": "application/json"}

        DATA = {'start_time': start_time,
                'end_time': end_time,
                'device_id': device_id}

        r = requests.get(self.API_URL, json=DATA, headers=HEADERS)

        return r.json()

class EyedroData:
    fmt = "%Y-%m-%d %H:%M:%S"
    def __init__(self, tz, device_id, start_date, end_date, raw_data, year, month):
        self.tz = tz
        self.device_id = device_id
        self.start_date = start_date
        self.end_date = end_date
        self.raw_data = raw_data
        self.year = year
        self.month = month



    def transform_data(self):
        data = self.raw_data["data"]
        fmt_o = self.fmt
        fmt_i = fmt_o + ".000%f"
        output = {}

        for timestamp in data:
            dt = datetime.strptime(timestamp['time'], fmt_i)
            ts = dt.strftime(fmt_o)
            output[ts] = {"kw_1": timestamp["kw_1"],
                          "kw_2": timestamp["kw_2"],
                          "kw_3": timestamp["kw_3"],
                          "kw_4": timestamp["kw_4"]}
        return output

    def daily_data(self):
        output = {}

    def validate_timestamps(self):
        data = self.transform_data()
        fmt = self.fmt
        start_string = self.start_date
        end_string = self.end_date

        dt = datetime.strptime(start_string, fmt)
        dts = dt.strftime(fmt)
        end_dt = datetime.strptime(end_string, fmt)
        end_dts = end_dt.strftime(fmt)
        delta = timedelta(minutes=10)

        err = None
        while dt <= end_dt:
            try:
                bool(data[dts])
                if bool(err):
                    print("missing range from {start} to {end} for {device}".format(start=err["start"],
                                                                                    end=err["end"],
                                                                                    device=err["device_id"]))
                    err = None

            except KeyError:
                if err == None:
                    err = {"device_id": self.device_id,
                                    "start": dt,
                                    "end": dt}
                elif bool(err):
                    if err["end"].day == dt.day and err["end"] + delta == dt:
                        err["end"] = dt
                    else:
                        print("missing range from {start} to {end} for {device}".format(start=err["start"],
                                                                                        end=err["end"],
                                                                                        device=err["device_id"]))
                        err = None

            dt = dt + delta
            dts = dt.strftime(fmt)

device_id = "B14-00107"
month = 8
year = 2022
mytz = 'America/Edmonton'
tz = pytz.timezone(mytz)

utc = pytz.timezone('utc')
api = EyedroAPI(mytz)
data = api.get_month(device_id, month, year)
days_in_month = monthrange(year, month)[1]
delta = timedelta(minutes=10)


def daily_data():
    data = api.get_month(device_id, month, year)
    data = data.transform_data()
    output = {}
    day = 1
    while day <= days_in_month:
        dt_s = tz.localize(datetime(year, month, day, 0, 10, 0))
        key = datetime(year, month, day, 0, 0, 0).strftime("%Y-%m-%d")
        output[key] = {"timestamps": {}}
        if day == days_in_month:
            dt_e = tz.localize(datetime(year, month + 1, 1, 0, 0, 0))
        else:
            dt_e = tz.localize(datetime(year, month, day + 1, 0, 0, 0))

        current_stamp = dt_s
        while current_stamp <= dt_e:
            utc_current = current_stamp.astimezone(utc)
            tz_stamp = current_stamp.strftime("%Y-%m-%d %H:%M:%S")

            utc_stamp = utc_current.strftime('%Y-%m-%d %H:%M:%S')
            output[key]["timestamps"][utc_stamp] = data[utc_stamp]

            current_stamp = current_stamp + delta
        day = day + 1
    return output



def test_timestamp_dataset():
    WORKING_SERIALS = ['B14-00107','B14-00106','B14-00108','B14-0010B','B14-0010D','B14-00114',
                       'B14-0010E','B14-00110','B14-00111','B14-00112','B14-00113']
    BROKEN_SERIALS = ['B14-00101','B14-00118','B14-0011A','B14-00102', 'B14-00119']

    tz = 'America/Edmonton'
    api = EyedroAPI(tz)
    month_start = 10
    year = 2022
    now = pytz.timezone('America/Edmonton').localize(datetime.now())
    if now.year == year:
        month_end = now.month - 1
    else:
        month_end = 12

    current_month = month_start
    while current_month <= month_end:
        first_serial = True
        for serial in WORKING_SERIALS:
            data = api.get_month(serial, current_month, year)

            if first_serial:
                print("---------------------------------------------------------------------------\n")
                print("Date range: {start_date} - {end_date}\n".format(start_date=data.start_date, end_date=data.end_date))
                print("---------------------------------------------------------------------------\n")
                first_serial = False

            data.validate_timestamps()
            print("\n")
        current_month = current_month + 1
