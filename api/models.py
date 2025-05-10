from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class TransportationRequest(models.Model):
    resident_name = models.CharField(max_length=100)
    pickup_time = models.DateTimeField()
    destination = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Completed', 'Completed')])

    def __str__(self):
        return f"{self.resident_name} - {self.destination} at {self.pickup_time}"

class DailyMenu(models.Model):
    MEAL_TYPE_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
    ]

    meal_type = models.CharField(max_length=10, choices=MEAL_TYPE_CHOICES)
    date = models.DateField()
    items = models.JSONField(default=list, blank=True, help_text="List of menu items")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['meal_type', 'date']

    def __str__(self):
        return f"{self.meal_type} - {self.date}"

    def item_list(self):
        return self.items.split(",") if self.items else []

class MealSelection(models.Model):
    resident = models.ForeignKey(User, on_delete=models.CASCADE)
    meal_time = models.CharField(max_length=10, choices=[('Breakfast', 'Breakfast'), ('Lunch', 'Lunch'), ('Dinner', 'Dinner')])
    main_item = models.CharField(max_length=100, blank=True, null=True)
    protein = models.CharField(max_length=100, blank=True, null=True)
    drinks = models.TextField(default="")  # comma-separated
    room_service = models.BooleanField(default=False)
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_meal = models.CharField(max_length=100, blank=True, null=True)
    allergies = models.TextField(default="")  # comma-separated
    created_at = models.DateTimeField(auto_now_add=True)

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
    recurrence = models.CharField(
        max_length=10,
        choices=RecurrenceChoices.choices,
        default=RecurrenceChoices.NONE
    )
    capacity = models.PositiveIntegerField(default=0)  # 0 = unlimited

    def __str__(self):
        return self.name

class ActivityInstance(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    occurrence_date = models.DateTimeField()
    participants = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return f"{self.activity.name} - {self.occurrence_date}"

class MaintenanceRequest(models.Model):
    resident = models.ForeignKey(User, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=50, choices=[('Maintenance', 'Maintenance'), ('Housekeeping', 'Housekeeping')])
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resident_name} - {self.request_type}"

class Alert(models.Model):
    alert_type = models.CharField(max_length=50, choices=[('Emergency', 'Emergency'), ('Community', 'Community'), ('Weather', 'Weather')])
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert_type} - {self.timestamp}"

class WellnessReminder(models.Model):
    reminder_type = models.CharField(max_length=50, choices=[('Hydration', 'Hydration'), ('Medication', 'Medication'), ('General', 'General')])
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

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
