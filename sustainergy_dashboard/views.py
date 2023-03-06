import json
import os
from functools import partial
from decimal import Decimal

from sustainergy_backend import settings

import pygal
from django.http import HttpResponse
from django.template.defaultfilters import register
from django.template.loader import get_template
from pygal.style import Style
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from weasyprint import HTML

from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken

from sustainergy_dashboard.forms import UtilityBillForm
from sustainergy_dashboard.models import Building, Panel, Circuit, DailyData, CircuitCategory, \
    unique_rand_building, unique_rand_panel, unique_rand_company, ReportEncoder, UtilityBill, Utility, Meter, \
    PanelMeterChannel,  PanelMeter, PanelImage
from sustainergy_dashboard.permissions import IsInstallerMixin

from sustainergy_dashboard.serializers import BuildingSerializer, PanelSerializer, CircuitSerializer, \
    DailyDataSerializer, JwtRefreshSerializer, VerboseBuildingSerializer, CircuitCategorySerializer, \
    CustomTokenObtainPairSerializer, PanelMeterChannelSerializer, PanelMeterSerializer, PanelMeterChannelPatchSerializer
from django.db.models import Q, Sum, Max
from django.utils.safestring import mark_safe
from wkhtmltopdf.views import PDFTemplateView, PDFTemplateResponse
from wkhtmltopdf.utils import wkhtmltopdf
import datetime
from django.core import serializers
from django.contrib.sites.shortcuts import get_current_site
import pdfkit
from django import forms
from django.urls import path
from django.shortcuts import render
from django.shortcuts import redirect
import csv
import pandas as pd
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Prefetch


import logging
logger = logging.getLogger(__name__)



def new_model_id(request, model):
    print(model.lower())
    if model.lower() == 'building':
        return HttpResponse(unique_rand_building())
    elif model.lower() == 'panel':
        return HttpResponse(unique_rand_panel())
    else:
        return HttpResponse("error")

class CsvImportForm(forms.Form):
    xlsx_file = forms.FileField()

def import_xlsx(request):
        form = CsvImportForm()
        if request.method == "POST":
            try:
                # Get building id from the query string
                building_id = request.META['QUERY_STRING']
                # Get xlsx file from the request
                xlsx_file = request.FILES["xlsx_file"]
                # Get Sheets from xlsx file
                sheets_dict = pd.read_excel(xlsx_file, sheet_name=None)
                pd.options.display.max_columns = None
                
                # Make transactions atomic, so that in case of any error it will rollback
                # transactions that have been completed
                with transaction.atomic():
                    for name, sheet in sheets_dict.items():
                        # Check if panel already exists, if it does, delete it
                        if Panel.objects.filter(building_id=building_id, panel_name=name).exists():
                            Panel.objects.filter(building_id=building_id, panel_name=name).delete()
                        # Create panel
                        panel = Panel.objects.create(building_id=building_id, panel_name=name)
                        # Read sheet data to create circuits
                        for index, row in sheet.iterrows():
                            if row[0] == "row_number " or row[0] == "circuit_number ":
                                continue
                            circuit_number, circuit_category, circuit_amps = None, None, ''
                            # Get circuit name
                            circuit_name = None if row[1] != row[1] else row[1]

                            # If circuit name is empty, don't create circuit
                            if circuit_name is None:
                                continue

                            # Get circuit row number
                            # If it's not an integer, set None
                            if isinstance(row[0], str) or row[0] != row[0]:
                                circuit_number = None
                            else:
                                circuit_number = row[0]

                            # Get category
                            if row.size > 2 and row[2] == row[2]:
                                circuit_category = row[2]

                            if circuit_category:
                                # Check if category exists
                                if CircuitCategory.objects.filter(name=row[2]).exists():
                                    # Get category object
                                    circuit_category = CircuitCategory.objects.get(name=row[2])
                                else:
                                    # Create category object
                                    circuit_category = CircuitCategory.objects.create(name=row[2])

                            # Create circuit amps
                            if row.size > 3 and row[3] == row[3]:
                                circuit_amps = row[3]

                            # Finaly create circuits
                            Circuit.objects.create(panel_id=panel.panel_id, circuit_name=circuit_name,
                                circuit_category=circuit_category, circuit_amps=circuit_amps,
                                circuit_number=circuit_number)
                    messages.success(request, "File has been uploaded successfully")
                    return HttpResponseRedirect(reverse('admin:index'))
            except Exception as e:
                messages.error(request, str(e))
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    token_obtain_pair = TokenObtainPairView.as_view()


class JwtObtainPairView(CustomTokenObtainPairView):
    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get('refresh'):
            cookie_max_age = 3600 * 24 * 14
            response.set_cookie('refresh_token', response.data['refresh'], max_age=cookie_max_age, httponly=True, samesite='Strict')
            del response.data['refresh']

        return super().finalize_response(request, response, *args, **kwargs)


class JwtRefreshView(TokenRefreshView):
    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get('refresh'):
            cookie_max_age = 3600 * 24 * 14
            response.set_cookie('refresh_token', response.data['refresh'], max_age=cookie_max_age, httponly=True, samesite='Strict')
            del response.data['refresh']
        return super().finalize_response(request, response, *args, **kwargs)
    serializer_class = JwtRefreshSerializer


class BuildingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']
    def get_queryset(self):
        user = self.request.user
        query = Building.objects.filter(staff__id=user.id) & Building.objects.filter(company__staff__id=user.id)
        
        qs1 = Building.objects.filter(staff__id=user.id)
        qs2 = Building.objects.filter(company__staff__id=user.id)
        return qs1.union(qs2)

class PanelViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Panel.objects.all().order_by('-panel_name')
    serializer_class = PanelSerializer
    # permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def get_queryset(self):
        if self.request.query_params.get('building_id'): 
            queryset = self.queryset.filter(building_id=self.request.query_params.get('building_id'))
        elif self.request.query_params.get('panel_id'): 
            queryset = self.queryset.filter(panel_id=self.request.query_params.get('panel_id'))
        else:
            queryset = self.queryset.all()
        return queryset

class CircuitViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Circuit.objects.all().order_by('-circuit_name')
    serializer_class = CircuitSerializer
    http_method_names = ['get']

    def get_queryset(self):
        queryset = self.queryset
        query_set = queryset.filter(panel_id=self.request.query_params.get('panel_id'))
        return query_set

    permission_classes = [IsAuthenticated]


class CircuitCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CircuitCategorySerializer
    http_method_names = ['get']

    def get_queryset(self):
        # Retrieve building id from request params
        building_id = self.request.query_params.get('building_id')

        # Retrieve circuits belonging to the selected Panels from the given building_id
        circuits = Circuit.objects.filter(panel__building=building_id)

        # Retrieve circuit_category_ids belonging to the retrieved circuits
        circuit_cat = circuits.values_list('circuit_category')

        # Retrieve circuit categories belonging to the retrieved circuits
        circuit_cat_qs = CircuitCategory.objects.filter(id__in=circuit_cat)

        # Retrieve Queryset for circuit categories belonging to the retrieved circuits
        qs = circuit_cat_qs.prefetch_related(Prefetch("circuit_set", queryset=circuits))

        return qs


class DownloadReports(viewsets.ModelViewSet):
    # permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def get_date_from_params(self):
        # If invalid options provided, or no parameters, defaults to current month/year
        requested_year = self.request.query_params.get('year')
        requested_month = self.request.query_params.get('month')
        today = datetime.date.today()
        if (isinstance(requested_year, str) and requested_year.isdigit() and len(requested_year) == 4):
            year = int(requested_year)
        else:
            year = today.year
        if (isinstance(requested_month, str) and requested_month.isdigit() and len(requested_month) >= 1 and len(requested_month) <= 2):
            monthInt = int(requested_month)
        else:
            monthInt = today.month

        month = {"int": monthInt,
                 "short": datetime.date(year, monthInt, 1).strftime("%b"),
                 "long": datetime.date(year, monthInt, 1).strftime("%B")}

        return { "year": year, "month": month }

    def generate_filename(self, report_type):
        return "2022_08_11_panel_report"

    @action(methods=['get'], detail=False, url_path=r'building/(?P<building_id>[\w-]+)/download', url_name='buildingid')
    def get_panel_report_for_building(self, request, building_id):

        if (request.GET.get('as', '') == 'html'):

            current_panel_ids = []
            data = []
            date = self.get_date_from_params()

            building_info = Building.objects.get(idbuildings=building_id)

            buildingEnergyUsage = building_info.energy_usage_data(datetime.date(date['year'], date['month']['int'], 1))
            buildingEnergyReport = buildingEnergyUsage.report()
            buildingEnergyReportJSON = buildingEnergyUsage.report_json()

            daily = buildingEnergyReport['daily']
            dailyEnergyBreakdown = {}
            for key in daily.keys():
                dailyEnergyBreakdown[key.strftime("%b %d, %a")] = daily[key]

            panels = buildingEnergyReport['panels']
            panelEnergyReports = []
            for key in panels:
                panel = panels[key]
                panelEnergyReports.append(panel)
            panelEnergyReports = sorted(panelEnergyReports, key=lambda k: k['total_usage'], reverse=True)


            if request.is_secure():
                prefix = "https://"
            else:
                prefix = "http://"
            baseURL = str(get_current_site(request))

            return self.html_generation({
                "building_info": building_info,
                "date": date,
                "siteURL": '{prefix}{base}'.format(prefix=prefix, base=baseURL),
                'cover_image': '{prefix}{base}/static/reports/opti-mized-banner.png'.format(prefix=prefix, base=baseURL),
                'report': buildingEnergyReport,
                'report_json': buildingEnergyReportJSON,
                'building': buildingEnergyReport['building'],
                'schedule': buildingEnergyReport['schedule'],
                'panels': buildingEnergyReport['panels'],
                'daily': buildingEnergyReport['daily'],
                'dailyEnergyBreakdown': dailyEnergyBreakdown,
                'panelEnergyReports': panelEnergyReports
                })
        else:
            return self.pdf_from_html(request)

    def pdf_from_html(self, request):
        if request.is_secure():
            prefix = "https://"
        else:
            prefix = "http://"
        baseURL = str(get_current_site(request))
        fullPath = str(request.get_full_path())
        fullURL = prefix + baseURL + fullPath

        if bool(request.query_params):
            fullURL = fullURL + "&as=html"
        else:
            fullURL = fullURL + "?as=html"

        cmd_options = {
            'javascript-delay': 2000,
            'debug-javascript': True,
            'enable-javascript': True,
            'no-stop-slow-scripts': True,
            'enable-local-file-access': True ,
            'margin-left': '0mm',
            'margin-right': '0mm',
            'margin-top': '15mm',
            'page-size': 'Letter',
            'footer-html': '{prefix}{base}/static/reports/footer.html'.format(prefix=prefix, base=baseURL),
        }

        pdf = pdfkit.from_url(fullURL, False, cmd_options)
        response = HttpResponse(pdf, content_type='application/pdf')

        # TODO: Re-enable below line before deploy, so that people can get the file as an attachment
        response['Content-Disposition'] = 'attachment; filename="test.pdf"'


        return response


    """
    # This function is for the original PDF generation mechanism, using Weasyprint. I had issues with being able to debug javascript using it, use static files, etc.
    # Left in for posterity
    def pdf_generation(self, data):
        cwd = os.getcwd()
        html_template = get_template(
            os.path.join(cwd, 'sustainergy_dashboard/templates/generate_panel_report.html')).render(data)
        pdf_file = HTML(string=html_template).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="panel_report.pdf"'
        return response
    """

    def html_generation(self, data):
        cwd = os.getcwd()
        html_template = get_template(
            os.path.join(cwd, 'sustainergy_dashboard/templates/generate_panel_report.html')).render(data)
        response = HttpResponse(html_template, content_type='text/html')
        return response

    # def get_queryset(self):
    #     return Panel.objects.all().order_by('-panel_name')


class OperatingHoursViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    pagination_class = None
    queryset = DailyData.objects.all().order_by('-event_date')
    serializer_class = DailyDataSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        is_repeat = request.query_params.get('is_repeat')
        if is_repeat == 'true':
            all_month_data = DailyData.objects.filter(event_date__month=instance.event_date.month)
            all_month_data.delete()
        elif is_repeat == 'false':
            instance.delete()
        return Response(status=204)


class ScheduleEncoder(json.JSONEncoder):
    def _preprocess_data(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, DailyData):
            return DailyDataSerializer(obj).data
        elif isinstance(obj, dict):
            return {self._preprocess_data(k): self._preprocess_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._preprocess_data(i) for i in obj]
        return obj

    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, DailyData):
            return DailyDataSerializer(obj).data
        return super().default(obj)

    def iterencode(self, obj, _one_shot):
        return super().iterencode(self._preprocess_data(obj))


class BuildingScheduleView(APIView):
    http_method_names = ['get']

    def get(self, request, building_id):
        building = Building.objects.all().filter(idbuildings=building_id).first()
        schedule = building.schedule()
        raw_data = json.loads(json.dumps(schedule.events, sort_keys=True, indent=None, cls=ScheduleEncoder))
        data = []

        # Altering response to be an array of objects, pre-filtered to remove empty dates, and with correct event_dates
        # substituted for the actual daily_data date. It's fine, with the ID changes can still be put through "correctly".
        for key in raw_data:
            item = raw_data[key]
            # Run bool check on the key. If true continue, if false break, and do not include in response.
            if (bool(item) == False):
                continue
            # Next, check to see if the event_date is the same on the data as the key. If not, set event date to key.
            if (item['event_date'] != key):
                item['event_date'] = key
            data.append(item)

        return Response(json.dumps(data))


@register.filter
def get_value_from_dict(h, key):
    return h.get(key)


@register.filter(is_safe=True)
def jsonify(data):
    return json.dumps(data)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def date_to_str(d):
    return d.strftime("%b %d, %a")

@register.filter
def match_id(l, id):
    for item in l:
        if item['id'] == id:
            return item


class UtilityDetailsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        utility = request.query_params.get('utility')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        building_id = request.query_params.get('building_id')
        status = 200

        data = {'year': year, 'utility': utility, 'building_id': building_id}

        if month is None:  # per year
            utility_bill = UtilityBill.objects.filter(meter__meter_type__name=utility, meter__building=building_id, statement_date__year=year).order_by('statement_date')
            if utility_bill.exists():
                message = "Successfully fetched data."
                bill = utility_bill.first()
                yearly_usage = utility_bill.aggregate(Sum('usage'))['usage__sum']
                yearly_cost = utility_bill.aggregate(Sum('total_bill'))['total_bill__sum']
                data['total_cost'] = "0"
                data['total_cost_decimal'] = ".0"
                data['total_usage'] = "0"
                data['total_usage_decimal'] = ".0"
                data['usage_breakdown_in_ft'] = "0"
                data['usage_breakdown_in_meter'] = "0"
                data['cost_breakdown_in_ft'] = "0"
                data['cost_breakdown_in_meter'] = "0"
                if yearly_usage is not None:
                    data['total_usage'] = "{:,.2f}".format(yearly_usage).split(".")[0]
                    data['total_usage_decimal'] = "." + "{:,.2f}".format(yearly_usage).split(".")[1]
                if yearly_cost is not None:
                    data['total_cost'] = "{:,.2f}".format(yearly_cost).split(".")[0]
                    data['total_cost_decimal'] = "." + "{:,.2f}".format(yearly_cost).split(".")[1]

                data['carbon'] = str(utility_bill.aggregate(Sum('carbon_levy'))['carbon_levy__sum'])
                max_usage_of_year = utility_bill.aggregate(Max('usage'))['usage__max']
                data['max_usage'] = str(max_usage_of_year)

                if bill.meter.building.squarefootage != 0 and yearly_usage is not None:
                    usage_breakdown_in_ft = yearly_usage / Decimal(bill.meter.building.squarefootage)
                    usage_breakdown_in_meter = yearly_usage / Decimal(bill.meter.building.square_meters())
                    cost_breakdown_in_ft = yearly_cost / Decimal(bill.meter.building.squarefootage)
                    cost_breakdown_in_meter = yearly_cost / Decimal(bill.meter.building.square_meters())

                    data['usage_breakdown_in_ft'] = f'{usage_breakdown_in_ft:.3f}'
                    data['usage_breakdown_in_meter'] = f'{usage_breakdown_in_meter:.3f}'
                    data['cost_breakdown_in_ft'] = f'{cost_breakdown_in_ft:.3f}'
                    data['cost_breakdown_in_meter'] = f'{cost_breakdown_in_meter:.3f}'
                else:
                    message += " Building area not exists or usage is blank."

                monthly_usage = {}
                for bill in utility_bill:
                    monthly_usage[bill.statement_date.strftime('%B')] = str(bill.usage)

                data['monthly_usage'] = monthly_usage
            else:
                message = "Requested data does not exists."
                status= 400

        else:  # per month
            utility_bill = UtilityBill.objects.filter(meter__meter_type__name=utility, meter__building=building_id, statement_date__year=year, statement_date__month=month)
            if utility_bill.exists():
                message = "Successfully fetched data."
                utility_bill = utility_bill.first()
                data['month'] = utility_bill.statement_date.strftime('%B')
                data['carbon'] = str(utility_bill.carbon_levy) if utility_bill.carbon_levy else "0"
                data['current_usage'] = "0"
                data['usage'] = "0"
                data['usage_decimal'] = ".0"
                data['cost'] = "0"
                data['cost_decimal'] = ".0"
                data['usage_breakdown_in_ft'] = "0"
                data['usage_breakdown_in_meter'] = "0"
                data['cost_breakdown_in_ft'] = "0"
                data['cost_breakdown_in_meter'] = "0"
                if utility_bill.usage is not None:
                    data['current_usage'] = str(utility_bill.usage)  # without comma
                    data['usage'] = "{:,.2f}".format(utility_bill.usage).split(".")[0]
                    data['usage_decimal'] = "." + "{:,.2f}".format(utility_bill.usage).split(".")[1]
                if utility_bill.total_bill is not None:
                    data['cost'] = "{:,.2f}".format(utility_bill.total_bill).split(".")[0]
                    data['cost_decimal'] = "." + "{:,.2f}".format(utility_bill.total_bill).split(".")[1]

                bills_of_year = UtilityBill.objects.filter(meter__meter_type__name=utility, meter__building=building_id,
                                           statement_date__year=year).order_by('statement_date')
                max_usage_of_year = bills_of_year.aggregate(Max('usage'))['usage__max']
                data['max_usage'] = str(max_usage_of_year)
                monthly_usage = {}
                for bill in bills_of_year:
                    monthly_usage[bill.statement_date.strftime('%B')] = str(bill.usage)
                data['monthly_usage'] = monthly_usage

                if utility_bill.meter.building.squarefootage != 0 and utility_bill.usage is not None \
                        and utility_bill.total_bill is not None:

                    building_fts = utility_bill.meter.building.squarefootage
                    building_meters = utility_bill.meter.building.square_meters()
                    usage_breakdown_in_ft = utility_bill.usage / Decimal(building_fts)
                    usage_breakdown_in_meter = utility_bill.usage / Decimal(building_meters)
                    cost_breakdown_in_ft = utility_bill.total_bill / Decimal(building_fts)
                    cost_breakdown_in_meter = utility_bill.total_bill / Decimal(building_meters)

                    data['usage_breakdown_in_ft'] = f'{usage_breakdown_in_ft:.3f}'
                    data['usage_breakdown_in_meter'] = f'{usage_breakdown_in_meter:.3f}'
                    data['cost_breakdown_in_ft'] = f'{cost_breakdown_in_ft:.3f}'
                    data['cost_breakdown_in_meter'] = f'{cost_breakdown_in_meter:.3f}'
                else:
                    message += " Building area not exists or usage is blank."
            else:
                message = "Requested data does not exists."
                status = 400

        return Response({
            "status": status,
            "message": message,
            "data": data,
        })


def show_utility_bills(request):
    if request.user.is_authenticated:
        building = request.GET.get('building')
        utility = request.GET.get('utility') or ''
        year = request.GET.get('year') or ''
        bills = UtilityBill.objects.filter(meter__building=building)
        utilities = Utility.objects.all()
        years = bills.values_list('statement_date__year', flat=True).order_by('-statement_date__year').distinct()

        if utility:
            bills = bills.filter(meter__meter_type__name=utility)
        if year:
            bills = bills.filter(statement_date__year=year)

        bills = bills.order_by('meter__meter_type', '-statement_date__year', 'statement_date__month')

        if not utility and not year:
            bills = []

        payload = {
            "utilities": utilities,
            "bills": bills,
            "building": building,
            "years": years,
            "selected_utility": utility,
            "selected_year": year
        }
        return render(
            request, "admin/sustainergy_dashboard/utility_bills.html", payload
        )

    else:
        return redirect('/admin/')


def create_all_bills_of_year(year, meter):
    meter = Meter.objects.get(pk=meter)
    for month in range(1, 13):
        if not UtilityBill.objects.filter(statement_date__year=year,
                                          statement_date__month=month, meter=meter).exists():
            date = str(month) + '-01-' + str(year)
            statement_date = datetime.datetime.strptime(date, "%m-%d-%Y").date()
            UtilityBill.objects.create(statement_date=statement_date, meter=meter)


def create_utility_bills(request):
    if request.user.is_authenticated:
        if request.method == 'GET':
            building = request.GET.get('building')
            bill_form = UtilityBillForm(request.POST or None)
            meters = Meter.objects.filter(building=building)
            payload = {
                "building": building,
                "meters": meters,
                "form": bill_form
            }
            return render(
                request, "admin/sustainergy_dashboard/create_bill.html", payload
            )
        else:
            building = request.POST.get('building')
            year = request.POST.get('year')
            meter = request.POST.get('meter')
            create_all_bills_of_year(year, meter)
            url = '/admin/sustainergy_dashboard/utilitybills/' + building + '/change/' + "?year=" + year + "&meter=" + meter
            return redirect(url)
    else:
        return redirect('/admin/')


class PanelMeterChannelViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    permission_classes = [IsAuthenticated, IsInstallerMixin]
    serializer_class = PanelMeterChannelSerializer
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        # Retrieve panel id from request params
        panel_id = self.request.query_params.get('panel_id')

        # If panel id not in query params, try to retrieve it from request data
        if not panel_id:
            panel_id = self.request.data.get('panel_id', None)

        # Retrieve expansions belonging to the the given panel_id
        expansions = PanelMeterChannel.objects.filter(panel_meter__panel__panel_id=panel_id).order_by('id')

        return expansions

    def get_serializer_class(self):
        # check if the HTTP request method is PATCH
        if self.request.method == 'PATCH':
            # if the request method is PATCH, return the PanelMeterChannelPatchSerializer
            return PanelMeterChannelPatchSerializer

        # if the request method is not PATCH, call the get_serializer_class() method of the superclass
        # this will return the default serializer class for the view
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        panel_id = request.query_params.get('panel_id')
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        panel_meter = PanelMeter.objects.get(panel=panel_id)
        data = {
            'meter_name': panel_meter.name,
            'meter_id': panel_meter.id,
            'number_of_phases': panel_meter.number_of_phases,
            'count': serializer.data.__len__(),
            'results': serializer.data,
        }

        return Response(data)

    def perform_update(self, serializer):
        """
        Updates an existing instance of the serializer's associated model, and saves it to the database.

        Args:
            serializer: The instance of the serializer being updated.

        Returns:
            None
        """
        serializer.save()
    
    def expansion_generator(self, obj):
        """
        Generator function that yields the necessary expansion data for each expansion in the input object.

        :param obj: The input object containing the panel ID and expansion data.
        :return: A generator that yields dictionaries containing the required data for each expansion.
        """
        for expansions in obj['expansions']:
            # Yield a dictionary containing the panel ID, and additional key for the current expansion
            yield {
                'panel_id': obj['panel_id'],
                **{key: val for key, val in expansions.items()}
            }

    def update(self, request, *args, **kwargs):
        self.lookup_field = 'panel_id'  # change lookup field to panel_id for PATCH

        # Retrieve panel id from request data
        panel_id = request.data.get('panel_id')

        # Retrieve expansions belonging to the the given panel_id
        expansions = self.get_queryset().filter(panel_meter__panel__panel_id=panel_id).order_by('id')

        try:
            # Get the PanelMeter instance that corresponds to the panel_id
            panel_meter = PanelMeter.objects.get(panel=panel_id)
        except PanelMeter.DoesNotExist:
            raise ValidationError("PanelMeter does not exist.")

        data_items = []
        # Loop over each expansion in the request data and update the corresponding expansion in the database
        for exp in self.expansion_generator(request.data):
            instance = expansions.get(expansion_number=exp['expansion_number'])
            serializer = self.get_serializer(instance, data=exp, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            # Serialize the queryset of expansions
            serializer = self.get_serializer(expansions, many=True)
        data_items = serializer.data


        # Calculate the total power by summing up the 'power' values of all serialized data items
        total_power = round(sum(item.get('power', 0) for item in data_items), 3)

        # For each serialized data item, calculate its power percentage relative to the total power
        for data in data_items:
            if 'power' in data:
                if total_power > 0:
                    data['power_percentage'] = (data['power'] * 100) / total_power
                    data['power_percentage'] = round(data['power_percentage'], 2)
                else:
                    data['power_percentage'] = 0

        # Assemble the final response data
        data = {
            'total_power': total_power,
            'meter_name': panel_meter.name,
            'number_of_phases': panel_meter.number_of_phases,
            'count': len(data_items),
            'results': data_items,
        }

        # Return the response
        return Response(data)


class PanelMeterViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows crud operations on panel meters.
    """
    permission_classes = [IsAuthenticated, IsInstallerMixin]
    serializer_class = PanelMeterSerializer
    queryset = PanelMeter.objects.all()
