import datetime
import math

from django.db import connection
import mysql.connector
from django.shortcuts import render
from flask import render_template, request, make_response, app, Flask
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
import pdfkit
from flask_weasyprint import HTML, render_pdf


class OperatingHoursForm(FlaskForm):
    month = StringField("Month")
    changed = StringField("Changed")
    newstart = IntegerField("NewStart")
    newend = IntegerField("NewEnd")
    datenumber = IntegerField("DateNumber")


app = Flask(__name__)
import os

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


def generatereport(building_id):
    with app.request_context({"wsgi.url_scheme": "/", "REQUEST_METHOD": "GET"}):
        form = OperatingHoursForm()
        building_id = building_id
        building_ids = 12
        year = 2021
        days_per_week = 5
        start_hour = 8
        end_hour = 17
        starthours = []
        endhours = []
        startam = []
        endam = []
        startminutes = []
        endminutes = []
        month = 10
        changed = ''
        mydb = mysql.connector.connect(
            host="db-building-storage.cfo00s1jgsd6.us-east-2.rds.amazonaws.com",
            user="readOnly",
            password="JSfB55vpSL",
            database="db_mysql_sustainergy_alldata"
        )
        mycursor = mydb.cursor()
        sql = "SELECT address, description FROM buildings WHERE idbuildings = %s"

        mycursor.execute(sql, (building_id,))
        myresult = mycursor.fetchall()
        for result in myresult:
            building_address = result[0]
            buidling_description = result[1]

        # calendar_init(building_id, year, days_per_week, start_hour, end_hour)
        if request.method == "POST":
            month = request.form['month']
            starthours = []
            endhours = []
            startam = []
            endam = []
            changed = request.form.get('changed')
            datenumber = request.form.get('datenumber')
            bulk = request.form.get('bulk')

        month = int(month)
        cal_month = month + 1
        cal_db = calendar_pull(building_ids, year, cal_month)
        if changed == "true":
            if bulk == "single":
                newstart = request.form.get('newstart')
                newend = request.form.get('newend')
                datenumber = int(datenumber)
                startmins = request.form.get('startmins')
                endmins = request.form.get('endmins')
                starttime = newstart + ':' + startmins
                endtime = newend + ':' + endmins
                datechange = datetime.date(year, cal_month, datenumber)
                cal_db = calendar_edit(cal_db, datechange, starttime, endtime)
                calendar_update(building_ids, year, cal_db)
            if bulk == "weekday":
                newstart = request.form.get('newstart')
                newend = request.form.get('newend')
                datenumber = int(datenumber)
                startmins = request.form.get('startmins')
                endmins = request.form.get('endmins')
                starttime = newstart + ':' + startmins
                endtime = newend + ':' + endmins
                datechange = datetime.datetime(year, cal_month, datenumber)
                datechange = datechange.weekday()
                cal_db = edit_weekday_calendar(cal_db, datechange, starttime, endtime)
                calendar_update(building_ids, year, cal_db)

            if bulk == "everyday":
                newstart = request.form.get('newstart')
                newend = request.form.get('newend')
                datenumber = int(datenumber)
                startmins = request.form.get('startmins')
                endmins = request.form.get('endmins')
                starttime = newstart + ':' + startmins
                endtime = newend + ':' + endmins
                for i in range(0, 6):
                    cal_db = edit_weekday_calendar(cal_db, i, starttime, endtime)
                    calendar_update(building_ids, year, cal_db)

            if bulk == "everyweekday":
                newstart = request.form.get('newstart')
                newend = request.form.get('newend')
                datenumber = int(datenumber)
                startmins = request.form.get('startmins')
                endmins = request.form.get('endmins')
                starttime = newstart + ':' + startmins
                endtime = newend + ':' + endmins
                for i in range(0, 5):
                    cal_db = edit_weekday_calendar(cal_db, i, starttime, endtime)
                    calendar_update(building_ids, year, cal_db)
        for date in cal_db:
            string = date
            starthours.append(string['start_hours'])
            endhours.append(string['end_hours'])
        d = datetime.datetime(2021, cal_month, 1)
        offset = d.weekday()
        offset += 1
        starthours = rotate(starthours, offset)
        endhours = rotate(endhours, offset)

        i = 0
        for hour in starthours:
            if type(hour) == str and hour[1] == ':':
                starthours[i] = hour[0]
                starthours[i] = int(starthours[i])
                startminutes.append(hour[2] + hour[3])
            elif type(hour) == str and hour[1] != ':':
                starthours[i] = hour[0] + hour[1]
                starthours[i] = int(starthours[i])
                startminutes.append(hour[3] + hour[4])
            else:
                startminutes.append('00')
            i += 1

        i = 0
        for hour in endhours:
            if type(hour) == str and hour[1] == ':':
                endhours[i] = hour[0]
                endhours[i] = int(endhours[i])
                endminutes.append(hour[2] + hour[3])
            elif type(hour) == str and hour[1] != ':':
                endhours[i] = hour[0] + hour[1]
                endhours[i] = int(endhours[i])
                endminutes.append(hour[3] + hour[4])
            else:
                endminutes.append('00')
            i += 1

        for i in range(len(starthours)):
            if starthours[i] is not None and starthours[i] < 13:
                startam.append("am")
            if starthours[i] is not None and starthours[i] >= 13:
                startam.append("pm")
                starthours[i] = starthours[i] - 12
            if starthours[i] is None:
                startam.append(endhours[i])

            if endhours[i] is not None and endhours[i] < 13:
                endam.append("am")
            if endhours[i] is not None and endhours[i] >= 13:
                endam.append("pm")
                endhours[i] = endhours[i] - 12
            if endhours[i] is None:
                endam.append(endhours[i])

        sql = "SELECT yearlyGas FROM utilities WHERE year = 2017"

        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        for x in myresult:
            tempstring = ','.join(x)
        gasdata = tempstring.split(',')

        mycursor = mydb.cursor()
        sql = "SELECT yearlyElectrical FROM utilities WHERE year = 2017"

        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        for x in myresult:
            tempstring = ','.join(x)
        electricaldata = tempstring.split(',')

        electrialusage = float(electricaldata[month])
        electricalrate = 0.071
        electricalcost = "{:.2f}".format(electrialusage * electricalrate)
        electrialusage = "{:.2f}".format(electrialusage)

        gasuage = float(gasdata[month])
        gasrate = 4.35
        gascost = "{:.2f}".format(gasuage * gasrate)
        gasuage = "{:.2f}".format(gasuage)
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December"]

        monthname = months[month]

        sql = "SELECT panel_id, panel_name, panel_voltage,panel_type FROM panel_data WHERE building_id = %s"

        mycursor.execute(sql, (building_id,))
        myresult = mycursor.fetchall()

        panel_name_list = []
        voltage_list = []
        type_list = []
        circuit_name_list = []
        panel_name_ids = []
        category_list = []
        lighting_count = []
        hvac_count = []
        dhw_count = []
        plug_count = []
        other_count = []
        boiler_count = []
        spare_count = []
        energy_meter_cost = '449.50'
        misc_cost = '94.55'
        lead_cost = '45.66'
        circuit_cost = '15.78'
        electrical_cost = '94.55'
        comissioning_cost = '94.55'
        cost_list = []
        panel_cost_list = []
        panel_mains_cost_list = []

        sql = "SELECT meter_price, misc_price, lead_price, circuit_price, electrical_price, commission_price FROM panel_price WHERE building_id = %s"
        mycursor.execute(sql, (building_id,))
        prices = mycursor.fetchall()

        for price in prices:
            if price[0] == '':
                nochange = True
            else:
                energy_meter_cost = price[0]
                misc_cost = price[1]
                lead_cost = price[2]
                circuit_cost = price[3]
                electrical_cost = price[4]
                comissioning_cost = price[5]

        for result in myresult:
            panel_id = result[0]
            panel_name = result[1]
            panel_voltage = result[2]
            panel_type = result[3]

            sql = "SELECT circuit_name, circuit_category FROM circuit_data WHERE panel_id = %s"

            mycursor.execute(sql, (panel_id,))
            circuitresult = mycursor.fetchall()
            circuitlist = []
            circuit_category = []
            for circuit in circuitresult:
                circuitlist.append(circuit[0])
                circuit_category.append(circuit[1])

            category_list.append(circuit_category)

            lighting = 0
            hvac = 0
            dhw = 0
            plugload = 0
            other = 0
            spare = 0
            boiler = 0
            for category in circuit_category:
                if category == 'Lighting' or category == 'Lighting ':
                    lighting += 1
                elif category == 'HVAC' or category == 'HVAC ':
                    hvac += 1
                elif category == 'DHW':
                    dhw += 1
                elif category == 'Plug-Load' or category == 'Plug-Load ':
                    plugload += 1
                elif category == 'Spare/Inactive' or category == 'Space' or category == 'Spare/ In-active' or category == 'nan' or category == 'Spare/in-active ' or category == 'Spare/in-active':
                    spare += 1
                elif category == 'Boiler / DHW':
                    boiler += 1
                else:
                    other += 1

            num_circuits = len(circuit_category)

            if num_circuits == 0:
                current_panel_cost = 0
                current_mains_cost = 0

            else:
                num_energy_meters = int(math.ceil((num_circuits + 3)) / 14)
                print(num_energy_meters)
                current_panel_cost = (float(num_energy_meters) * float(energy_meter_cost)) + float(misc_cost) + (
                        float(lead_cost) * 3) + (float(circuit_cost) * float(num_circuits)) + (
                                             float(electrical_cost) * 2) + float(comissioning_cost)
                current_mains_cost = (float(num_energy_meters) * float(energy_meter_cost)) + float(misc_cost) + (
                        float(lead_cost) * 3) + float(electrical_cost) + float(comissioning_cost)

            panel_cost_list.append("{:.2f}".format(current_panel_cost))
            panel_mains_cost_list.append("{:.2f}".format(current_mains_cost))

            lighting_count.append(lighting)
            hvac_count.append(hvac)
            dhw_count.append(dhw)
            plug_count.append(plugload)
            other_count.append(other)
            spare_count.append(spare)
            boiler_count.append(boiler)
            panel_name_list.append(panel_name)
            voltage_list.append(panel_voltage)
            type_list.append(panel_type)
            circuit_name_list.append(circuitlist)

        for panelname in panel_name_list:
            panelname = panelname.replace(' ', '_')
            panel_name_ids.append(panelname)

        mains_total = 0
        mcc_mains_total = 0
        i = 0
        for panel in panel_mains_cost_list:
            if type_list[i] != 'MCC Unit':
                mains_total += float(panel)
            elif type_list[i] == 'MCC Unit':
                mcc_mains_total += float(panel)
            i += 1

        circuits_total = 0
        mcc_circuits_total = 0
        i = 0
        for panel in panel_cost_list:
            if type_list[i] != 'MCC Unit':
                circuits_total += float(panel)
            elif type_list[i] == 'MCC Unit':
                mcc_circuits_total += float(panel)
            i += 1

        num_panels = len(panel_name_list)
        total_num_circuits_panels = 0
        total_num_circuits_mcc = 0
        for i in range(0, len(circuit_name_list)):
            if type_list[i] != 'MCC Unit':
                total_num_circuits_panels += len(circuit_name_list[i])
            elif type_list[i] == 'MCC Unit':
                total_num_circuits_mcc += len(circuit_name_list[i])

        mains_total = "{:.2f}".format(mains_total)
        circuits_total = "{:.2f}".format(circuits_total)
        mcc_circuits_total = "{:.2f}".format(mcc_circuits_total)
        mcc_mains_total = "{:.2f}".format(mcc_mains_total)

        num_standard_panels = 0
        num_mcc_panels = 0
        for i in range(0, len(panel_name_list)):
            if type_list[i] != 'MCC Unit':
                num_standard_panels += 1
            elif type_list[i] == 'MCC Unit':
                num_mcc_panels += 1
        html = render_template('generatereport.html', num_mcc_panels=num_mcc_panels,
                               num_standard_panels=num_standard_panels, mcc_mains_total=mcc_mains_total,
                               mcc_circuits_total=mcc_circuits_total, type_list=type_list,
                               energy_meter_cost=energy_meter_cost, misc_cost=misc_cost, lead_cost=lead_cost,
                               circuit_cost=circuit_cost, electrical_cost=electrical_cost,
                               comissioning_cost=comissioning_cost, num_panels=num_panels,
                               total_num_circuits_mcc=total_num_circuits_mcc,
                               total_num_circuits_panels=total_num_circuits_panels, circuits_total=circuits_total,
                               mains_total=mains_total, panel_mains_cost_list=panel_mains_cost_list,
                               panel_cost_list=panel_cost_list, boiler_count=boiler_count, spare_count=spare_count,
                               sorted_categories=[], category_list=category_list, other_count=other_count,
                               plug_count=plug_count, dhw_count=dhw_count, hvac_count=hvac_count,
                               lighting_count=lighting_count, panel_name_ids=panel_name_ids,
                               circuit_name_list=circuit_name_list, voltage_list=voltage_list,
                               panel_name_list=panel_name_list, panel_voltage=panel_voltage, len=len(panel_name_list),
                               panel_name=panel_name, circuitlist=circuitlist, monthname=monthname, gascost=gascost,
                               gasrate=gasrate, gasuage=gasuage, electricalcost=electricalcost,
                               electricalrate=electricalrate, electrialusage=electrialusage,
                               building_address=building_address, buidling_description=buidling_description,
                               building_id=building_id, startminutes=startminutes, endminutes=endminutes, form=form,
                               month=month, starthours=starthours, endhours=endhours, startam=startam, endam=endam)
        response = HttpResponse(content_type='application/pdf')
        pisa.CreatePDF(
            src=StringIO(html),  # the HTML to convert
            dest=response)  # file handle to receive result
        response.headers["Content-Disposition"] = "inline; filename=output.pdf"
        # return True on success and False on errors
        return response
        # return render_pdf(html=HTML(string=html), download_filename='output.pdf')


def edit_weekday_calendar(calendar, weekday, start_hour, end_hour):
    if weekday > 6 and weekday < 0:
        print("Error: edit_weekday_calendar, weekday needs to be between 0-6")
        return

    for day in calendar:
        if day['weekday'] == weekday:
            if day['on-hours'] == False:
                day['on-hours'] = True
            day['start_hours'] = start_hour
            day['end_hours'] = end_hour

    return calendar


def calendar_update(building_id, year, new_calendar):
    connection = mysql.connector.connect(
        host='db-building-storage.cfo00s1jgsd6.us-east-2.rds.amazonaws.com',
        user='admin',
        password='rvqb2JymBB5CaNn',
        db='db_mysql_sustainergy_alldata'
    )

    cursor = connection.cursor(buffered=True)

    # find the month the calendar is to replace

    date = new_calendar[0]['day']

    month = date.month

    if month == 1:
        month_name = 'january'
    elif month == 2:
        month_name = 'february'
    elif month == 3:
        month_name = 'march'
    elif month == 4:
        month_name = 'april'
    elif month == 5:
        month_name = 'may'
    elif month == 6:
        month_name = 'june'
    elif month == 7:
        month_name = 'july'
    elif month == 8:
        month_name = 'august'
    elif month == 9:
        month_name = 'september'
    elif month == 10:
        month_name = 'october'
    elif month == 11:
        month_name = 'november'
    elif month == 12:
        month_name = 'december'

    insert_line = "UPDATE calendar SET " + month_name + " = (%s) WHERE building_id = (%s) AND year = (%s);"

    values = (str(new_calendar), building_id, year)

    cursor.execute(insert_line, values)

    connection.commit()

    cursor.close()

    return


def calendar_edit(calendar, date_change, start_hour, end_hour):
    new_calendar = calendar

    # we need to check if the date_change is of a date time type
    day = None
    try:
        day = date_change.day
        month = date_change.month
        year = date_change.year
    except:
        pass

    try:
        day = date_change[2]
        month = date_change[1]
        year = date_change[0]
    except:
        pass

    for d in new_calendar:
        cal_day = d['day']

        if cal_day.day == day and cal_day.month == month and cal_day.year == year:
            if d['on-hours'] == False:
                d['on-hours'] = True

            d['start_hours'] = start_hour
            d['end_hours'] = end_hour

    return new_calendar


def calendar_pull(building_id, year, month):
    connection = mysql.connector.connect(
        host='db-building-storage.cfo00s1jgsd6.us-east-2.rds.amazonaws.com',
        user='admin',
        password='rvqb2JymBB5CaNn',
        db='db_mysql_sustainergy_alldata'
    )

    connection.cursor()

    if type(month) == str:
        month_name = month.lower()

    if month == 1:
        month_name = 'january'
    elif month == 2:
        month_name = 'february'
    elif month == 3:
        month_name = 'march'
    elif month == 4:
        month_name = 'april'
    elif month == 5:
        month_name = 'may'
    elif month == 6:
        month_name = 'june'
    elif month == 7:
        month_name = 'july'
    elif month == 8:
        month_name = 'august'
    elif month == 9:
        month_name = 'september'
    elif month == 10:
        month_name = 'october'
    elif month == 11:
        month_name = 'november'
    elif month == 12:
        month_name = 'december'

    insert_line = "SELECT {month_name} FROM calendar WHERE building_id = {building_id} AND year = {year};"
    cursor = connection.cursor()
    cursor.execute(insert_line)

    results = cursor.fetchall()

    results_list = results[0]

    cursor.close()

    return eval(results_list[0])


# class OperatingHoursForm(forms.Form):
#     month = forms.CharField(label="Month")
#     changed = forms.CharField(label="Changed")
#     newstart = forms.CharField(label="NewStart")
#     newend = forms.CharField(label="NewEnd")
#     datenumber = forms.CharField(label="DateNumber")
def rotate(l, n):
    return l[-n:] + l[:-n]


from io import BytesIO, StringIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


# defining the function to convert an HTML file to a PDF file
def html_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None
