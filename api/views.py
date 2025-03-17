from django.shortcuts import render
from django.utils.timezone import make_aware, is_aware, is_naive
from datetime import datetime, timedelta
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from .models import (
    TransportationRequest, MealSelection, Activity, MaintenanceRequest, 
    Alert, WellnessReminder, BillingStatement
)
from .serializers import (
    TransportationRequestSerializer, MealSelectionSerializer, ActivitySerializer, 
    MaintenanceRequestSerializer, AlertSerializer, WellnessReminderSerializer, 
    BillingStatementSerializer, UserSerializer
)

def backend_home(request):
    return render(request, 'backend_home.html')

class TransportationRequestViewSet(viewsets.ModelViewSet):
    queryset = TransportationRequest.objects.all()
    serializer_class = TransportationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class MealSelectionViewSet(viewsets.ModelViewSet):
    queryset = MealSelection.objects.all()
    serializer_class = MealSelectionSerializer
    permission_classes = [permissions.IsAuthenticated]

class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                start_date = make_aware(start_date) if not is_aware(start_date) else start_date
                end_date = make_aware(datetime.combine(end_date, datetime.max.time()))
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        else:
            now = datetime.now()
            start_date = make_aware(now) if is_naive(now) else now
            end_date = start_date + timedelta(days=30)

        activities = Activity.objects.all()
        expanded_activities = []

        for activity in activities:
            current_date = activity.date_time
            if is_naive(current_date):
                current_date = make_aware(current_date)

            while current_date <= end_date:
                if current_date >= start_date:
                    cloned_activity = Activity(
                        id=activity.id,  # Keeping ID for reference
                        name=activity.name,
                        description=activity.description,
                        date_time=current_date,
                        location=activity.location,
                        recurrence=activity.recurrence,
                    )
                    cloned_activity.save()
                    cloned_activity.participants.set(activity.participants.all())
                    expanded_activities.append(cloned_activity)

                # Handle recurrence logic
                if activity.recurrence == "Daily":
                    current_date += timedelta(days=1)
                elif activity.recurrence == "Weekly":
                    current_date += timedelta(weeks=1)
                elif activity.recurrence == "Monthly":
                    current_date += timedelta(weeks=4)
                else:
                    break  # No recurrence, break after first iteration

        serializer = ActivitySerializer(expanded_activities, many=True)
        return Response(serializer.data)

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()  # Explicitly define queryset
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return MaintenanceRequest.objects.all()
        return MaintenanceRequest.objects.filter(submitter=user)

    def perform_create(self, serializer):
        serializer.save(submitter=self.request.user)

class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

class WellnessReminderViewSet(viewsets.ModelViewSet):
    queryset = WellnessReminder.objects.all()
    serializer_class = WellnessReminderSerializer
    permission_classes = [permissions.IsAuthenticated]

class BillingStatementViewSet(viewsets.ModelViewSet):
    queryset = BillingStatement.objects.all()
    serializer_class = BillingStatementSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
