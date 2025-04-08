from rest_framework import serializers
from .models import (
    TransportationRequest, MealSelection, Activity,
    MaintenanceRequest, Alert, WellnessReminder, BillingStatement
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

class MealSelectionSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = MealSelection
        fields = ['id', 'resident_name', 'meal_time', 'menu_item', 'special_requests', 'items']

    def get_items(self, obj):
        return obj.menu_item.split('\n') if obj.menu_item else []

from django.utils.timezone import make_aware, is_naive
import pytz

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
