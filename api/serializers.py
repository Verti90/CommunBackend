from rest_framework import serializers
from .models import (
    TransportationRequest, MealSelection, Activity,
    MaintenanceRequest, Alert, WellnessReminder, BillingStatement, DailyMenu, MealSelection, UserProfile
)
from django.contrib.auth.models import User
from django.utils.timezone import is_naive
from pytz import timezone as pytz_timezone, utc

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return user

class TransportationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportationRequest
        fields = '__all__'

class ActivitySerializer(serializers.ModelSerializer):
    def validate_date_time(self, value):
        if is_naive(value):
            local_tz = pytz.timezone('America/Chicago')  # Explicitly your timezone
            value = make_aware(value, local_tz)
        return value.astimezone(pytz.utc)

    class Meta:
        model = Activity
        fields = '__all__'

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'

class WellnessReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessReminder
        fields = '__all__'

class BillingStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingStatement
        fields = '__all__'

class DailyMenuSerializer(serializers.ModelSerializer):
    items = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = DailyMenu
        fields = ['id', 'meal_type', 'date', 'items', 'created_by']
        read_only_fields = ['id', 'created_by']

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        validated_data["items"] = ",".join(items)
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['items'] = instance.item_list()
        return rep

class MealSelectionSerializer(serializers.ModelSerializer):
    drinks = serializers.ListField(child=serializers.CharField(), write_only=True)
    allergies = serializers.ListField(child=serializers.CharField(), write_only=True)
    drinks_display = serializers.SerializerMethodField()
    allergies_display = serializers.SerializerMethodField()

    class Meta:
        model = MealSelection
        fields = [
            'id', 'resident', 'meal_time', 'main_item', 'protein',
            'drinks', 'drinks_display',
            'room_service', 'guest_name', 'guest_meal',
            'allergies', 'allergies_display',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_drinks_display(self, obj):
        return obj.drinks.split(",") if obj.drinks else []

    def get_allergies_display(self, obj):
        return obj.allergies.split(",") if obj.allergies else []

    def create(self, validated_data):
        drinks = validated_data.pop("drinks", [])
        allergies = validated_data.pop("allergies", [])
        validated_data["drinks"] = ",".join(drinks)
        validated_data["allergies"] = ",".join(allergies)
        return super().create(validated_data)

from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    default_allergies = serializers.ListField(child=serializers.CharField(), required=False)
    
    class Meta:
        model = UserProfile
        fields = ['default_allergies', 'default_guest_name', 'default_guest_meal']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['default_allergies'] = instance.default_allergies.split(",") if instance.default_allergies else []
        return rep

    def to_internal_value(self, data):
        val = super().to_internal_value(data)
        if isinstance(val.get('default_allergies'), list):
            val['default_allergies'] = ",".join(val['default_allergies'])
        return val
