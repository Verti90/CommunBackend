from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver


# Common enums
class RequestStatus(models.TextChoices):
    PENDING = 'Pending', 'Pending'
    COMPLETED = 'Completed', 'Completed'
    CANCELLED = 'Cancelled', 'Cancelled'


class TransportationType(models.TextChoices):
    MEDICAL = 'Medical', 'Medical'
    PERSONAL = 'Personal', 'Personal'


class MealType(models.TextChoices):
    BREAKFAST = 'Breakfast', 'Breakfast'
    LUNCH = 'Lunch', 'Lunch'
    DINNER = 'Dinner', 'Dinner'


class MaintenanceType(models.TextChoices):
    MAINTENANCE = 'Maintenance', 'Maintenance'
    HOUSEKEEPING = 'Housekeeping', 'Housekeeping'


class AlertType(models.TextChoices):
    EMERGENCY = 'Emergency', 'Emergency'
    COMMUNITY = 'Community', 'Community'
    WEATHER = 'Weather', 'Weather'


class ReminderType(models.TextChoices):
    HYDRATION = 'Hydration', 'Hydration'
    MEDICATION = 'Medication', 'Medication'
    GENERAL = 'General', 'General'


# Core models
class TransportationRequest(models.Model):
    resident_name = models.CharField(max_length=100)
    room_number = models.CharField(max_length=20)
    request_type = models.CharField(max_length=20, choices=TransportationType.choices)
    doctor_name = models.CharField(max_length=100, blank=True, null=True)
    appointment_time = models.CharField(max_length=100, blank=True, null=True)
    destination_name = models.CharField(max_length=255, blank=True, null=True)
    pickup_time = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    staff_comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resident_name} - {self.request_type}"


class MaintenanceRequest(models.Model):
    resident_name = models.CharField(max_length=100)
    room_number = models.CharField(max_length=20)
    request_type = models.CharField(max_length=50, choices=MaintenanceType.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    staff_comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resident_name} - {self.request_type}"


class DailyMenu(models.Model):
    meal_type = models.CharField(max_length=10, choices=MealType.choices)
    date = models.DateField()
    items = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['meal_type', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.meal_type} - {self.date}"


class MealSelection(models.Model):
    resident = models.ForeignKey(User, on_delete=models.CASCADE)
    meal_time = models.CharField(max_length=10, choices=MealType.choices)
    main_item = models.CharField(max_length=100, blank=True, null=True)
    protein = models.CharField(max_length=100, blank=True, null=True)
    drinks = models.TextField(default="")  # comma-separated
    room_service = models.BooleanField(default=False)
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_meal = models.CharField(max_length=100, blank=True, null=True)
    allergies = models.TextField(default="")  # comma-separated
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resident.username} - {self.meal_time}"


class Activity(models.Model):
    class RecurrenceChoices(models.TextChoices):
        NONE = "None", _("None")
        DAILY = "Daily", _("Daily")
        WEEKLY = "Weekly", _("Weekly")
        MONTHLY = "Monthly", _("Monthly")

    name = models.CharField(max_length=255)
    date_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    participants = models.ManyToManyField(User, blank=True)
    recurrence = models.CharField(max_length=10, choices=RecurrenceChoices.choices, default=RecurrenceChoices.NONE)
    capacity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class ActivityInstance(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    occurrence_date = models.DateTimeField()
    participants = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return f"{self.activity.name} - {self.occurrence_date}"


class Alert(models.Model):
    alert_type = models.CharField(max_length=50, choices=AlertType.choices)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.alert_type} - {self.timestamp}"


class WellnessReminder(models.Model):
    reminder_type = models.CharField(max_length=50, choices=ReminderType.choices)
    message = models.TextField()
    schedule_time = models.DateTimeField()

    def __str__(self):
        return f"{self.reminder_type} - {self.schedule_time}"


class BillingStatement(models.Model):
    resident_name = models.CharField(max_length=100)
    statement_date = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid')])

    def __str__(self):
        return f"{self.resident_name} - {self.statement_date}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    default_allergies = models.TextField(blank=True, default="")  # comma-separated
    default_guest_name = models.CharField(max_length=100, blank=True, null=True)
    default_guest_meal = models.CharField(max_length=100, blank=True, null=True)
    room_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"