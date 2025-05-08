from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.timezone import make_aware, is_naive, now
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

from .models import DailyMenu
from .serializers import DailyMenuSerializer

class DailyMenuViewSet(viewsets.ModelViewSet):
    queryset = DailyMenu.objects.all()
    serializer_class = DailyMenuSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        date = self.request.query_params.get('date')

        if date:
            return DailyMenu.objects.filter(date=date)

        if not user.is_staff:
            from django.utils.timezone import now
            return DailyMenu.objects.filter(date__gte=now().date())

        return DailyMenu.objects.all()

    def create(self, request, *args, **kwargs):
        date = request.data.get('date')
        meal_type = request.data.get('meal_type')
        new_items = request.data.get('items', [])

        if not (date and meal_type and isinstance(new_items, list)):
            return Response({'error': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            existing = DailyMenu.objects.get(date=date, meal_type=meal_type)
            existing.items.extend([item for item in new_items if item not in existing.items])
            existing.save()
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DailyMenu.DoesNotExist:
            return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        menu = self.get_object()
        item_index = request.data.get('item_index')

        if item_index is None:
            return super().destroy(request, *args, **kwargs)

        try:
            item_index = int(item_index)
            if not (0 <= item_index < len(menu.items)):
                return Response({'error': 'Invalid index'}, status=status.HTTP_400_BAD_REQUEST)

            menu.items.pop(item_index)

            if menu.items:
                menu.save()
                return Response({'status': 'Item removed'}, status=status.HTTP_200_OK)
            else:
                menu.delete()
                return Response({'status': 'Menu deleted'}, status=status.HTTP_200_OK)

        except (ValueError, TypeError):
            return Response({'error': 'Invalid item index.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MealSelectionViewSet(viewsets.ModelViewSet):
    queryset = MealSelection.objects.all()
    serializer_class = MealSelectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        meal_time = serializer.validated_data.get("meal_time")

        # Only check for today's meal (can be expanded for date-specific logic)
        today = now().date()
        existing = MealSelection.objects.filter(
            resident=user,
            meal_time=meal_time,
            created_at__date=today
        ).exists()

        if existing:
            raise serializers.ValidationError(
                { "meal_time": f"You have already submitted a {meal_time} selection today." }
            )

        serializer.save(resident=user)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return MealSelection.objects.all()
        return MealSelection.objects.filter(resident=user)

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming(self, request):
        today = now().date()
        user = request.user

        if user.is_staff:
            selections = MealSelection.objects.filter(
                created_at__date__gte=today
            ).order_by('created_at')
        else:
            selections = MealSelection.objects.filter(
                resident=user,
                created_at__date__gte=today
            ).order_by('created_at')

        serializer = self.get_serializer(selections, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if not user.is_staff and instance.resident != user:
            return Response(
                {"error": "You are not authorized to delete this meal selection."},
                status=status.HTTP_403_FORBIDDEN,
            )

        self.perform_destroy(instance)
        return Response({"status": "Selection canceled"}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if not user.is_staff and instance.resident != user:
            return Response(
                {"error": "You are not authorized to update this meal selection."},
                status=status.HTTP_403_FORBIDDEN,
            )

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

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

from .models import UserProfile
from .serializers import UserProfileSerializer

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "profile updated"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

        start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"), local_tz) if start_date_str else datetime.now(local_tz)
        end_date = make_aware(datetime.combine(datetime.strptime(end_date_str, "%Y-%m-%d"), datetime.max.time()), local_tz) if end_date_str else start_date + timedelta(days=30)

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

                if local_current_date.hour == 0 and local_current_date.minute == 0:
                    local_current_date = local_current_date.replace(second=1)

                if start_date <= local_current_date <= end_date:
                    instance, _ = ActivityInstance.objects.get_or_create(
                        activity=activity, occurrence_date=current_date
                    )
                    participants_list = list(instance.participants.values_list('id', flat=True))

                    expanded_activities.append({
                        'id': activity.id,
                        'name': activity.name,
                        'date_time': local_current_date.isoformat(),
                        'location': activity.location,
                        'recurrence': activity.recurrence,
                        'participants': participants_list,
			'capacity': activity.capacity,
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

    def perform_create(self, serializer):
        activity = serializer.save()
        from .models import ActivityInstance
        ActivityInstance.objects.get_or_create(
            activity=activity,
            occurrence_date=activity.date_time
        )

    @action(detail=True, methods=["post"], url_path="signup")
    def signup(self, request, pk=None):
        from django.utils.dateparse import parse_datetime

        occurrence_date = request.data.get("occurrence_date")
        if not occurrence_date:
            return Response({"error": "occurrence_date is required"}, status=400)

        user = request.user
        activity = self.get_object()

        parsed_date = parse_datetime(occurrence_date)
        if not parsed_date:
            return Response({"error": "Invalid date format"}, status=400)

        instance, _ = ActivityInstance.objects.get_or_create(
            activity=activity,
            occurrence_date=parsed_date
        )

        if activity.capacity > 0 and instance.participants.count() >= activity.capacity:
            return Response({"error": "Activity is full"}, status=400)

        instance.participants.add(user)
        instance.save()
        return Response({"status": "signed up"})


    @action(detail=True, methods=["post"], url_path="unregister")
    def unregister(self, request, pk=None):
        from django.utils.dateparse import parse_datetime

        occurrence_date = request.data.get("occurrence_date")
        if not occurrence_date:
            return Response({"error": "occurrence_date is required"}, status=400)

        user = request.user
        activity = self.get_object()

        parsed_date = parse_datetime(occurrence_date)
        if not parsed_date:
            return Response({"error": "Invalid date format"}, status=400)

        try:
            instance = ActivityInstance.objects.get(activity=activity, occurrence_date=parsed_date)
            instance.participants.remove(user)
            return Response({"status": "unregistered"})
        except ActivityInstance.DoesNotExist:
            return Response({"error": "Activity instance not found"}, status=404)