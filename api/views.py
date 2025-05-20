import pytz
from pytz import utc
from datetime import datetime, timedelta

from django.db import models
from django.shortcuts import render
from django.utils.timezone import make_aware, is_naive, now
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date

from rest_framework import viewsets, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action, api_view, permission_classes

from .models import (
    TransportationRequest, MealSelection, Activity, MaintenanceRequest,
    Alert, WellnessReminder, BillingStatement, ActivityInstance, Feed,
    DailyMenu, UserProfile
)

from .serializers import (
    TransportationRequestSerializer, MealSelectionSerializer, ActivitySerializer,
    MaintenanceRequestSerializer, AlertSerializer, WellnessReminderSerializer,
    BillingStatementSerializer, UserSerializer, FeedSerializer,
    DailyMenuSerializer, UserProfileSerializer,
    MealReportSerializer, ActivityReportSerializer
)

def backend_home(request):
    return render(request, 'backend_home.html')

from datetime import datetime

class TransportationRequestViewSet(viewsets.ModelViewSet):
    queryset = TransportationRequest.objects.all()
    serializer_class = TransportationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data
        time_str = data.get('pickup_time') or data.get('appointment_time')
        if not time_str:
            return Response({'error': 'Time is required.'}, status=400)

        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            return Response({'error': 'Invalid time format.'}, status=400)

        block_start = dt.replace(hour=(dt.hour // 2) * 2, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        block_end = block_start + timedelta(hours=2)

        same_block = TransportationRequest.objects.filter(
            ~models.Q(status='Cancelled'),
        ).filter(
            models.Q(appointment_time__startswith=dt.date().isoformat()) |
            models.Q(pickup_time__startswith=dt.date().isoformat())
        )

        # In-memory filtering because appointment_time/pickup_time are CharFields
        count = 0
        for req in same_block:
            t = req.pickup_time or req.appointment_time
            if not t:
                continue
            try:
                rdt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                if block_start <= rdt < block_end:
                    count += 1
            except Exception:
                continue

        if count >= 2:
            return Response(
                {'error': f'Time block {block_start.strftime("%I:%M %p")} – {block_end.strftime("%I:%M %p")} is full.'},
                status=400
            )

        return super().create(request, *args, **kwargs)

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
        submitted_date = self.request.data.get("date")

        try:
            submitted_date = parse_date(submitted_date)
        except Exception:
            submitted_date = now().date()

        if not submitted_date:
            submitted_date = now().date()

        existing = MealSelection.objects.filter(
            resident=user,
            meal_time=meal_time,
            date=submitted_date
        ).exists()

        if existing:
            raise serializers.ValidationError(
                { "meal_time": f"You have already submitted a {meal_time} selection for {submitted_date}." }
            )

        serializer.save(resident=user, date=submitted_date)

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
                date__gte=today
            ).order_by('date')
        else:
            selections = MealSelection.objects.filter(
                resident=user,
                date__gte=today
            ).order_by('date')

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

    def update(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response(
                {"error": "Only staff can update maintenance requests."},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

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

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'user created'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        user = request.user

        email = request.data.get('email')
        if email:
            user.email = email
            user.save()

        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "profile updated"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import UserProfile
        from .serializers import UserProfileSerializer

        user_data = UserSerializer(request.user).data
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_data = UserProfileSerializer(profile).data

        return Response({**user_data, **profile_data}, status=status.HTTP_200_OK)

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
        
class FeedViewSet(viewsets.ModelViewSet):
    queryset = Feed.objects.all().order_by('-created_at')
    serializer_class = FeedSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise serializers.ValidationError("Only staff can post announcements.")
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({"error": "Only staff can delete announcements."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def meal_report_view(request):
    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'error': 'Missing date'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)

    selections = MealSelection.objects.filter(date=selected_date)
    data = MealReportSerializer(selections, many=True).data
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_report_view(request):
    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'error': 'Missing date'}, status=400)

    try:
        local_tz = pytz.timezone('America/Chicago')
        selected_date = make_aware(datetime.strptime(date_str, '%Y-%m-%d'), local_tz)
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)

    start = selected_date.replace(hour=0, minute=0, second=0)
    end = selected_date.replace(hour=23, minute=59, second=59)

    instances = ActivityInstance.objects.select_related('activity').filter(
        occurrence_date__range=(start, end)
    )

    report_data = [{
        'name': inst.activity.name,
        'date_time': inst.occurrence_date,
        'location': inst.activity.location,
        'instance': inst
    } for inst in instances]

    serialized = ActivityReportSerializer(report_data, many=True).data
    return Response(serialized)