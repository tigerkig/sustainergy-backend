import calendar

from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.forms import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
# Register your models here.
from sustainergy_dashboard.models import Building, Panel, Circuit, User, Company, CircuitCategory, Facility, Utility, \
    Meter, UtilityBill, UtilityProvider, PanelMeter, PanelMeterChannel, PanelImage
import nested_admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.db.models.functions import ExtractYear, ExtractMonth
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.html import format_html
from django.db import models

@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    model = Circuit
    list_display = ('circuit_number','circuit_name', 'panel', 'circuit_amps', 'circuit_category')
    search_fields = [ 'panel', 'circuit_category' ]
    readonly_fields = ['circuit_number']


class InlineCircuitForm(forms.ModelForm):
    class Meta:
        model = Circuit
        fields = ('id','circuit_number' ,'circuit_name', 'circuit_amps', 'circuit_category')
        readonly_fields = ['circuit_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # var = self.fields['id']
        self.fields['circuit_number'].widget.attrs['readonly'] = True


class CircuitInline(admin.TabularInline):
    model = Circuit
    fk_name = 'panel'
    form = InlineCircuitForm
    show_change_link = True
    extra = 0


class InlinePanelImageForm(forms.ModelForm):
    class Meta:
        model = PanelImage
        fields = ('id','panel', 'image')
        readonly_fields = ['image']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # var = self.fields['id']
        self.fields['image'].widget.attrs['readonly'] = True
        # var2 = self.fields['test_panel_images'].widget.attrs['readonly'] = True

class CustomAdminFileWidget(AdminFileWidget):
    def render(self, name, value, attrs=None, renderer=None):
        result = []
        if hasattr(value, "url"):
            result.append(
                f'''<a href="{value.url}" target="_blank">
                      <img 
                        src="{value.url}" alt="{value}" 
                        width="100" height="100"
                        style="object-fit: cover;"
                      />
                    </a>'''
            )
        result.append(super().render(name, value, attrs, renderer))
        return format_html("".join(result))
        
class PanelImageInline(admin.TabularInline):
    model = PanelImage
    formfield_overrides = {
        models.ImageField: {'widget': CustomAdminFileWidget}
    }
    fk_name = 'panel'
    form = InlinePanelImageForm
    show_change_link = True
    extra = 0
    
# @admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    model = Panel
    show_change_link = True
    list_display = ('panel_name', 'building', 'panel_voltage', 'panel_type')
    readonly_fields = ["panel_id", "building_link"]
    fields = [('panel_name', 'panel_id', 'colour'), ('provider', 'serial', 'panel_voltage'), ('building', 'building_link'), ('panel_type')]
    inlines = [ CircuitInline,PanelImageInline  ]
    search_fields = ['building', 'panel_voltage',]

    def building_link(self, obj):
        app_label = obj._meta.app_label
        model_label = obj.building._meta.model_name
        url = reverse(
            f'admin:{app_label}_{model_label}_change', args=(obj.building.idbuildings,)
        )
        return mark_safe(f'<a href="{url}">{obj.building}</a>')

    building_link.allow_tags = True
    building_link.short_description = 'View Building'

    def response_change(self, request, obj):
        app_label = obj._meta.app_label
        model_label = obj._meta.model_name
        url = reverse(
            f'admin:{app_label}_{model_label}_change',
            args=(obj.panel_id,)
        )
        return redirect(url)


class InlinePanelForm(forms.ModelForm):
    circuit_count = forms.IntegerField(disabled=True)
    add_panel_image = forms.ImageField(required=False,widget=forms.ClearableFileInput(attrs={'multiple':True}))
    
    class Meta:
        model = Panel
        fields = ('panel_id', 'panel_name', 'panel_voltage', 'building', 'circuit_count', 'provider', 'serial', 'colour', 'add_panel_image', )  
    
    def get_initial_for_field(self, field, field_name):
        if field_name == 'circuit_count':
            if self.instance:
                return self.instance.circuit_count()
            return None
        return super().get_initial_for_field(field, field_name)
   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        var = self.fields['panel_id']
        var.widget.attrs['readonly'] = True


class PanelInline(admin.TabularInline):
    model = Panel
    show_change_link = True
    form = InlinePanelForm
    fk_name = 'building'
    # fields = [('panel_name', 'panel_voltage', 'building', 'panel_type')]
    show_change_link = True
    readonly_fields = ['img_preview',]
    extra = 0
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super(PanelInline, self).get_formset(request, obj, **kwargs)
        formset.request = request
        return formset
        
class InlineBuildingForm(forms.ModelForm):
    panel_count = forms.IntegerField(disabled=True)

    class Meta:
        model = Building
        # fields = ('idbuildings', 'description', 'city', 'address', 'company', 'panel_count')
        fields = ('idbuildings', 'description', 'company', 'panel_count')

    def get_initial_for_field(self, field, field_name):
        if field_name == 'panel_count':
            if self.instance:
                return self.instance.panel_count()
            return None
        if field_name == 'building_id':
            if self.instance:
                return self.instance.building_id()
            return None
        return super().get_initial_for_field(field, field_name)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        var = self.fields['idbuildings']
        var.widget.attrs['readonly'] = True


class BuildingInline(admin.TabularInline):
    model = Building
    fk_name = 'company'
    inline = [ PanelInline, ]
    show_change_link = True
    # readonly_fields = ('idbuildings',)
    form = InlineBuildingForm
    extra = 0
    exclude = ['staff']


class UtilityFilteredFormset(BaseInlineFormSet):

    def get_queryset(self):
        qs = super(UtilityFilteredFormset, self).get_queryset()
        return qs.order_by('meter__meter_type', 'statement_date')


class UtilityInline(admin.TabularInline):
    model = UtilityBill
    readonly_fields = ['utility', 'billing_month', 'meter_name']
    fields = ['utility', 'billing_month', 'meter_name', 'usage', 'price_per_unit', 'total_commodity', 'distribution', 'line', 'rider', 'carbon_levy', 'gst',
              'total_bill', 'statement_date', 'invoice_number']
    extra = 0
    formset = UtilityFilteredFormset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        building_id = request.resolver_match.kwargs.get('object_id')
        if db_field.name == "meter":
            kwargs["queryset"] = Meter.objects.filter(building=building_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        year = request.GET.get('year')
        meter = request.GET.get('meter')
        qs = super().get_queryset(request)
        if year:
            qs = qs.filter(statement_date__year=year)
        if meter:
            qs = qs.filter(meter=meter)
        return qs


class BuildingAdmin(admin.ModelAdmin):
    model = Building
    # list_display = ('description', 'facility_type', 'company',''' 'city', 'address',''' 'idbuildings')
    list_display = ('idbuildings', 'description', 'facility_type', 'company', 'city', 'province')

    search_fields = ['company', 'city']
    readonly_fields = ['idbuildings', 'company_link', 'age', 'import_xlsx', 'utility_bills']
    show_change_link = True
    # fields = [('description', 'idbuildings'), ('city', 'address'), 'company', 'staff', 'occupants', ('occupies_days_per_week', 'length_of_occupied_day'), ('start_hour', 'end_hour'), ('number_of_doors', 'squarefootage', 'exterior_wall_squarefootage', 'window_squarfootage', 'roof_squarefootage'), ('price_per_gj', 'price_per_kwh'), ('vist_duration', 'calculated')]
    fieldsets = (
        (None, {
            # 'fields': (('description', 'idbuildings'),''' ('city', 'address'),''' ('company', 'company_link'), ('facility', 'year_built', 'age'))
            'fields': (('description', 'idbuildings'), ('company', 'company_link'), ('facility', 'year_built', 'age', 'squarefootage'))

        }),
        ('Address', {
            'fields': [('address_line_1', 'address_line_2', 'city'), ('province', 'postal_code')]
        }),
        ('Occupancy', {
            'classes': ('collapse grp-collapse grp-closed',),
            'fields': [('occupants', 'occupies_days_per_week'), ('length_of_occupied_day', 'start_hour', 'end_hour')]
        }),
        ('Building Footprint', {
            'classes': ('collapse grp-collapse grp-closed',),
            'fields': [('exterior_wall_squarefootage', 'window_squarefootage'), ('roof_squarefootage', 'number_of_doors')]
        }),
        ('Additional', {
            'classes': ('collapse grp-collapse grp-closed',),
            'fields': [('price_per_gj', 'price_per_kwh'), ('vist_duration', 'calculated')]
        }),
        ('Staff', {
            'classes': ('collapse grp-collapse grp-closed',),
            'fields': ['staff']
        }),
        ('Bulk Import Circuits', {
            'fields': ['import_xlsx']
        }),
        ('Utility Bills', {
            'fields': ['utility_bills']
        }),
    )
    filter_horizontal = ['staff']
    inlines = [PanelInline]
    def company_link(self, obj):
        app_label = obj._meta.app_label
        model_label = obj.company._meta.model_name
        url = reverse(
            f'admin:{app_label}_{model_label}_change', args=(obj.company.company_id,)
        )
        return mark_safe(f'<a href="{url}">{obj.company}</a>')

    company_link.allow_tags = True
    company_link.short_description = 'View Company'

    def response_change(self, request, obj):
        app_label = obj._meta.app_label
        model_label = obj._meta.model_name
        url = reverse(
            f'admin:{app_label}_{model_label}_change', args=(obj.idbuildings,)
        )
        return redirect(url)

    def save_formset(self, request, form, formset, change):
        # i = 0
        instances = formset.save(commit=False) # gets instance from memory and add to it before saving it
        
        for i in range(len(formset)):
            if(request.FILES.getlist("panel_set-"+str(i)+"-add_panel_image")):
                images = request.FILES.getlist("panel_set-"+str(i)+"-add_panel_image")
                formset[i].instance.add_panel_images(images)
                
        super().save_formset(request, form, formset, change)
        
# @admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    model = Company
    list_display = ('name', 'address', 'city', 'postal_code', 'company_id')
    inlines = [ BuildingInline, ]
    fieldsets = (
        (None, {
            'fields': (('name', 'company_id'), ('headquarters', 'city'), ('address', 'postal_code'), ('image', 'image_tag'))
        }),
         ("Staff", {
             'classes': ('collapse grp-collapse grp-closed',),
             'fields': ('staff',)
         })
    )

    readonly_fields = ['company_id', 'image_tag']
    filter_horizontal = ['staff']
    def response_change(self, request, obj):
        app_label = obj._meta.app_label
        model_label = obj._meta.model_name
        url = reverse(
            f'admin:{app_label}_{model_label}_change', args=(obj.company_id,)
        )
        return redirect(url)

admin.site.register(Panel, PanelAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(Company, CompanyAdmin)


# admin.site.register(Company)
# admin.site.register(Building)
# admin.site.register(Panel)
# admin.site.register(Circuit)

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom user model with no username field."""

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important Dates'), {'fields': ('last_login', 'date_joined')}),
        (_('User Role'), {'fields': ('role',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2',)
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'role')
    search_fields = ('email', 'first_name', 'last_name',)
    ordering = ('last_name',)

class FacilityAdmin(admin.ModelAdmin):
    list_display = ["type", "image_tag", "image"]
    readonly_fields = ["image_tag"]
    fields = ["type", "image_tag", "image"]


class CircuitCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'colour', 'icon']
    list_editable = ['colour', 'icon']


class SearchByYear(admin.SimpleListFilter):
    title = _('By Year')
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        year_list = UtilityBill.objects.annotate(
            y=ExtractYear('statement_date')
        ).order_by('y').values_list('y', flat=True).distinct()
        return [
            (str(y), _(str(y))) for y in year_list
        ]

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(statement_date__year=self.value())
        return queryset


class SearchByMonth(admin.SimpleListFilter):
    title = _('By Month')
    parameter_name = 'month'

    def lookups(self, request, model_admin):
        month_list = UtilityBill.objects.annotate(
            m=ExtractMonth('statement_date')
        ).order_by('m').values_list('m', flat=True).distinct()
        return [
            (str(m), _(str(calendar.month_name[m]))) for m in month_list
        ]

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(statement_date__month=self.value())
        return queryset


class UtilityBillAdmin(admin.ModelAdmin):
    exclude = ['building']
    list_filter = ['meter__meter_type', SearchByYear, SearchByMonth]

class UtilityBills(Building):
    class Meta:
        proxy = True
        verbose_name_plural = 'Utility Bills'

class MyBuildingAdmin(BuildingAdmin):
    readonly_fields = ['idbuildings']
    search_fields = ['idbuildings']
    fieldsets = []
    fields = ['idbuildings']
    inlines = [UtilityInline]
    change_form_template = 'admin/sustainergy_dashboard/utility_bills/change_form.html'

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    def response_change(self, request, obj):
        building_id = request.resolver_match.kwargs.get('object_id')
        year = request.GET.get('year')
        meter = request.GET.get('meter')
        utility = Meter.objects.get(pk=meter).meter_type.name
        url = '/utility_bills?building=' + building_id + '&year=' + year + '&utility=' + utility
        return redirect(url)


class MeterAdmin(admin.ModelAdmin):

    fields = ['building', 'meter_id', 'meter_type', 'account_number', 'utility_provider']


    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['building', 'meter_id', 'account_number']
        else:
            return []


class NewMeter(Meter):
    class Meta:
        proxy = True
        verbose_name_plural = 'Meters'


class NewMeterAdmin(admin.ModelAdmin):
    fields = ['building', 'meter_id', 'meter_type', 'account_number', 'utility_provider']
    change_form_template = 'admin/sustainergy_dashboard/new_meter/change_form.html'
    save_as = True

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['meter_id', 'account_number']
        else:
            return []


    def response_add(self, request, obj, post_url_continue=None):
        if request.GET.get('building'):
            url = "/create_utility_bills?building=" + str(obj.building.idbuildings)
            return redirect(url)
        else:
            return super().response_add(request, obj, post_url_continue)

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


admin.site.register(CircuitCategory, CircuitCategoryAdmin)
admin.site.register(Facility, FacilityAdmin)
admin.site.register(Utility)
admin.site.register(Meter, MeterAdmin)
admin.site.register(UtilityBill, UtilityBillAdmin)
admin.site.register(UtilityProvider)
admin.site.register(UtilityBills, MyBuildingAdmin)
admin.site.register(NewMeter, NewMeterAdmin)
admin.site.register(PanelMeter)
admin.site.register(PanelMeterChannel)
