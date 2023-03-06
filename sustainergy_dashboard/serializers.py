from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from sustainergy_dashboard.models import Building, Panel, Circuit, DailyData, CircuitCategory, Facility, \
    PanelMeterChannel, PanelMeter,PanelImage

from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import InvalidToken


class JwtRefreshSerializer(TokenRefreshSerializer):
    refresh = None
    def validate(self, attrs):
        attrs['refresh'] = self.context['request'].COOKIES.get('refresh_token')
        if attrs['refresh']:
            return super().validate(attrs)
        else:
            raise InvalidToken('No valid token found in cookie \'refresh_token\'')


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ('type', 'image')

class BuildingSerializer(serializers.HyperlinkedModelSerializer):
    facility = FacilitySerializer(many=False)
    class Meta:
        model = Building
        fields = ['idbuildings', 'description', 'facility', 'year_built', 'age', 'squarefootage', 'window_squarefootage', 'roof_squarefootage', 'exterior_wall_squarefootage', 'square_meters', 'address_line_1', 'address_line_2', 'city', 'province', 'postal_code']

class PanelImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PanelImage
        fields = ['id', 'panel_id','image']
        
class PanelSerializer(serializers.HyperlinkedModelSerializer):

    # Add meter_name field to the serializer
    meter_name = serializers.SerializerMethodField()
    
    # for getting panel images
    panel_images = PanelImageSerializer(many=True)

    class Meta:
        model = Panel
        fields = ['panel_name', 'building_id', 'panel_id', 'panel_type', 'panel_voltage', 'panel_image', 'meter_name','panel_images']

    def get_meter_name(self, obj):
        # Get the panel_id from the current object
        panel_id = obj.panel_id
        try:
            # Try to get the corresponding PanelMeter object for the panel_id
            panel_meter = PanelMeter.objects.get(panel=panel_id)
            return panel_meter.name     # return the meter name if found
        except PanelMeter.DoesNotExist:
            return None     # return None if no corresponding PanelMeter object found

class CircuitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circuit
        fields = ['id', 'circuit_name', 'circuit_number', 'circuit_category', 'circuit_amps', 'panel_id', 'category_color']


class CustomCircuitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circuit
        fields = ['circuit_name']


class CircuitCategorySerializer(serializers.ModelSerializer):
    circuit_set = CustomCircuitSerializer(many=True)
    class Meta:
        model = CircuitCategory
        fields = ['name', 'colour', 'circuit_set']


class VerbosePanelSerializer(serializers.ModelSerializer):
    circuits = CircuitSerializer(many=True)
    class Meta:
        model = Circuit
        fields = ['panel_name', 'building_id', 'panel_id', 'panel_type', 'panel_voltage', 'panel_image']

class VerboseBuildingSerializer(serializers.ModelSerializer):
    panels = PanelSerializer(many=True)
    class Meta:
        model = Building
        fields = ['idbuildings', 'address_line_1', 'address_line_2', 'city', 'province', 'postal_code', 'description', 'panels']


class DailyDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyData
        fields = ['id', 'event_date', 'start_time', 'end_time', 'is_closed', 'is_repeat',
                  "days_of_week", "is_daily", "is_weekly", "building"]
        optional_fields = ['days_of_week', 'is_closed', 'is_repeat', 'start_time', 'end_time']

    start_time = serializers.TimeField(required=False, input_formats=None)
    end_time = serializers.TimeField(required=False, input_formats=None)
    days_of_week = serializers.ListField( child=serializers.CharField(max_length=200) )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_role'] = self.user.role

        return data


class VirtualMeterCircuitCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = CircuitCategory
        fields = ['colour']


class VirtualMeterCircuitSerializer(serializers.ModelSerializer):

    category = VirtualMeterCircuitCategorySerializer(source='circuit_category')

    class Meta:
        model = Circuit
        fields = ['circuit_name', 'circuit_number', 'category']


class PanelMeterChannelSerializer(serializers.ModelSerializer):

    circuit = VirtualMeterCircuitSerializer(source='circuit_id')
    circuit_no = serializers.CharField(write_only=True)
    panel_id =  serializers.CharField(write_only=True)
    class Meta:
        model = PanelMeterChannel
        fields = ['id', 'expansion_type', 'expansion_number', 'circuit', 'circuit_no', 
            'panel_id', 'current', 'voltage_refrence_type', 'voltage_refrence_value', 'power']


class VirtualMeterCircuitPatchSerializer(serializers.ModelSerializer):

    class Meta:
        model = Circuit
        fields = ['circuit_name', 'circuit_number']

class PanelMeterChannelPatchSerializer(serializers.ModelSerializer):

    circuit = VirtualMeterCircuitPatchSerializer(source='circuit_id')
    circuit_no = serializers.CharField(write_only=True)
    panel_id =  serializers.CharField(write_only=True)
    class Meta:
        model = PanelMeterChannel
        fields = ['id', 'expansion_type', 'expansion_number', 'circuit', 'circuit_no', 
            'panel_id', 'current', 'voltage_refrence_type', 'voltage_refrence_value', 'power']

    def to_representation(self, instance):
        # Call the parent to_representation() method to serialize the instance
        ret = super().to_representation(instance)

        # Retrieve the 'circuit' value from the serialized data
        circuit = ret.get('circuit')

        # Check if the circuit is None, and return an empty dictionary if it is
        if circuit is None:
            return {}

        # Create a new dictionary with the desired key-value pairs
        data = {
            "expansion_type": ret.get('expansion_type'),
            "expansion_number": ret.get('expansion_number'),
            "circuit": circuit,
            "current": ret.get('current'),
            "power": ret.get('power'),
        }

        # Return the new dictionary
        return data

    def update(self, instance, validated_data):
        # Retrieve the data from the validated data object and pop them out
        circuit_no = validated_data.pop('circuit_no', '')
        panel_id = validated_data.pop('panel_id', '')
        current = validated_data.pop('current', '')
        voltage_refrence_type = validated_data.pop('voltage_refrence_type', '')
        voltage_refrence_value = validated_data.pop('voltage_refrence_value', '')

        # Update the instance with any new values provided for the relevant fields
        if current:
            instance.current = current

        if voltage_refrence_type:
            instance.voltage_refrence_type = voltage_refrence_type

        if voltage_refrence_value:
            instance.voltage_refrence_value = voltage_refrence_value

        if circuit_no:
            circuit_ids = Circuit.objects.filter(panel=panel_id, circuit_number=circuit_no)
            if circuit_ids.exists():
                circuit_id = circuit_ids.first()

                # Check if the circuit is already used by another PanelMeterChannel object
                if PanelMeterChannel.objects.filter(circuit_id=circuit_id).exclude(id=instance.id).exists():
                    raise ValidationError('Circuit number is already used by another channel.')

                instance.circuit_id = circuit_id
            else:
                raise ValidationError('Circuit number not exists in panel.')

        # Save the updated instance and return it
        instance.save()

        # Build the response data with the updated instance
        data = {
            "expansion_type": instance.expansion_type,
            "expansion_number": instance.expansion_number,
            "circuit": instance.circuit_id,
            "current": instance.current,
        }

        return data

class PanelMeterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanelMeter
        fields = '__all__'
