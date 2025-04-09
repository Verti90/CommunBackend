from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.timezone import make_aware, is_naive
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
import pytz
from pytz import utc

from .models import (
    TransportationRequest, MealSelection, Activity, MaintenanceRequest,
    Alert, WellnessReminder, BillingStatement, ActivityInstance
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

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data['password'])
            user.save()
            return Response({'status': 'user created'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = User.objects.filter(username=username).first()
        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response({
                'token': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

def list(self, request, *args, **kwargs):
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    local_tz = pytz.timezone('America/Chicago')

    if start_date_str:
        start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"), local_tz)
    else:
        start_date = datetime.now(local_tz)

    if end_date_str:
        end_date = make_aware(datetime.combine(datetime.strptime(end_date_str, "%Y-%m-%d"), datetime.max.time()), local_tz)
    else:
        end_date = start_date + timedelta(days=30)

    start_date_utc = start_date.astimezone(utc)
    end_date_utc = end_date.astimezone(utc)

    activities = Activity.objects.all()
    expanded_activities = []

    for activity in activities:
        current_date = activity.date_time
        if is_naive(current_date):
            current_date = make_aware(current_date, utc)

        while current_date <= end_date_utc:
            local_current_date = current_date.astimezone(local_tz)

            # Explicitly handle midnight events to align with proper day
            if local_current_date.hour == 0:
                local_current_date = local_current_date.replace(minute=0, second=0, microsecond=0)

            # Recalculate week range explicitly per event date
            event_week_start = local_current_date - timedelta(days=local_current_date.weekday() + 1 % 7)
            event_week_end = event_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            if event_week_start.date() <= local_current_date.date() <= event_week_end.date():
                if start_date.date() <= local_current_date.date() <= end_date.date():
                    instance, _ = ActivityInstance.objects.get_or_create(
                        activity=activity, occurrence_date=current_date
                    )
                    participants_list = list(instance.participants.values_list('id', flat=True))

                    expanded_activities.append({
                        'id': activity.id,
                        'name': activity.name,
                        'description': activity.description,
                        'date_time': local_current_date.isoformat(),
                        'location': activity.location,
                        'recurrence': activity.recurrence,
                        'participants': participants_list,
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
