from rest_framework import serializers
from .models import (
    TransportationRequest, MealSelection, Activity,
    MaintenanceRequest, Alert, WellnessReminder, BillingStatement, DailyMenu, MealSelection, UserProfile, Feed
)
from django.contrib.auth.models import User
from django.utils.timezone import is_naive, make_aware
from pytz import timezone as pytz_timezone, utc

class UserSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'is_staff', 'room_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_staff': {'read_only': True},
        }

    def create(self, validated_data):
        room_number = validated_data.pop('room_number', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )

        if room_number:
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.room_number = room_number
            profile.save()

        return user

class TransportationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportationRequest
        fields = '__all__'

class ActivitySerializer(serializers.ModelSerializer):
    def validate_date_time(self, value):
        if is_naive(value):
            local_tz = pytz_timezone('America/Chicago')
            value = make_aware(value, local_tz)
        return value.astimezone(utc)

    class Meta:
        model = Activity
        fields = ['id', 'name', 'date_time', 'location', 'participants', 'recurrence', 'capacity']

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
    categorized_items = serializers.SerializerMethodField()

    class Meta:
        model = DailyMenu
        fields = ['id', 'meal_type', 'date', 'items', 'categorized_items', 'created_by']
        read_only_fields = ['id', 'created_by']

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def get_categorized_items(self, obj):
        from collections import defaultdict
        result = defaultdict(dict)

        for item in obj.items:
            try:
                parts = item.split(":")
                header = parts[0].strip()  # e.g., "Main Course Option A"
                value = parts[1].strip()   # e.g., "Eggs"
                category, option = header.rsplit(" Option ", 1)
                result[category][option] = value
            except Exception:
                continue

        return result

class CommaSeparatedListField(serializers.Field):
    def to_representation(self, value):
        return value.split(",") if value else []

    def to_internal_value(self, data):
        if isinstance(data, list):
            return ",".join(data)
        raise serializers.ValidationError("Expected a list of strings.")


class MealSelectionSerializer(serializers.ModelSerializer):
    drinks = CommaSeparatedListField()
    allergies = CommaSeparatedListField()

    def validate_meal_time(self, value):
        allowed = ['Breakfast', 'Lunch', 'Dinner']
        if value not in allowed:
            raise serializers.ValidationError(f"meal_time must be one of {allowed}")
        return value

    class Meta:
        model = MealSelection
        fields = [
            'id', 'resident', 'meal_time', 'date', 'main_item', 'protein',
            'drinks',
            'room_service', 'guest_name', 'guest_meal',
            'allergies',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'resident']

class UserProfileSerializer(serializers.ModelSerializer):
    default_allergies = serializers.ListField(child=serializers.CharField(), required=False)
    room_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ['default_allergies', 'default_guest_name', 'default_guest_meal', 'room_number']

    def to_internal_value(self, data):
        val = super().to_internal_value(data)

        # Only convert if it's actually a list; otherwise skip
        if isinstance(data.get('default_allergies'), list):
            val['default_allergies'] = ",".join(data['default_allergies'])
        elif isinstance(data.get('default_allergies'), str):
            val['default_allergies'] = data['default_allergies']

        return val

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['default_allergies'] = instance.default_allergies.split(",") if instance.default_allergies else []
        return ret
    
class FeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feed
        fields = ['id', 'title', 'content', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']

class MealReportSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='resident.get_full_name')
    room_number = serializers.CharField(source='resident.userprofile.room_number')
    drinks = CommaSeparatedListField()
    allergies = CommaSeparatedListField()

    class Meta:
        model = MealSelection
        fields = [
            'meal_time', 'main_item', 'protein', 'drinks',
            'room_service', 'guest_name', 'guest_meal', 'allergies',
            'name', 'room_number'
        ]

class ActivityReportSerializer(serializers.Serializer):
    name = serializers.CharField()
    date_time = serializers.DateTimeField()
    location = serializers.CharField()
    participants = serializers.SerializerMethodField()

    def get_participants(self, obj):
        return [
            {
                'name': f"{user.first_name} {user.last_name}".strip(),
                'room_number': getattr(user.userprofile, 'room_number', 'N/A')
            }
            for user in obj['instance'].participants.all()
        ]