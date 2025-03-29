from django.shortcuts import render
from django.utils.timezone import make_aware, is_naive
from datetime import datetime, timedelta
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
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

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.now()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else start_date + timedelta(days=30)

        start_date = make_aware(start_date)
        end_date = make_aware(datetime.combine(end_date, datetime.max.time()))

        activities = Activity.objects.all()
        expanded_activities = []

        for activity in activities:
            current_date = activity.date_time
            if is_naive(current_date):
                current_date = make_aware(current_date)

            while current_date <= end_date:
                if current_date >= start_date:
                    expanded_activities.append({
                        'id': activity.id,
                        'name': activity.name,
                        'description': activity.description,
                        'date_time': current_date,
                        'location': activity.location,
                        'recurrence': activity.recurrence,
                    })

                if activity.recurrence == "Daily":
                    current_date += timedelta(days=1)
                elif activity.recurrence == "Weekly":
                    current_date += timedelta(weeks=1)
                elif activity.recurrence == "Monthly":
                    month = current_date.month + 1 if current_date.month < 12 else 1
                    year = current_date.year if current_date.month < 12 else current_date.year + 1
                    try:
                        current_date = current_date.replace(year=year, month=month)
                    except ValueError:
                        current_date += timedelta(weeks=4)
                else:
                    break

        return Response(expanded_activities)

    @action(detail=True, methods=['post'])
    def signup(self, request, pk=None):
        activity = self.get_object()
        if request.user in activity.participants.all():
            return Response({'detail': 'Already signed up.'}, status=status.HTTP_400_BAD_REQUEST)

        activity.participants.add(request.user)
        return Response({'status': 'signed up'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def unregister(self, request, pk=None):
        activity = self.get_object()
        if request.user not in activity.participants.all():
            return Response({'detail': 'Not registered for activity.'}, status=status.HTTP_400_BAD_REQUEST)

        activity.participants.remove(request.user)
        return Response({'status': 'unregistered'}, status=status.HTTP_200_OK)

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
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

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

@api_view(['GET'])
def profile_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
