from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TransportationRequestViewSet, MealSelectionViewSet, ActivityViewSet,
    MaintenanceRequestViewSet, AlertViewSet, WellnessReminderViewSet,
    BillingStatementViewSet, UserViewSet, RegisterView, ProfileView, UserProfileView, DailyMenuViewSet,FeedViewSet
)
from .auth_views import login_view  # ✅ Fixed import

router = DefaultRouter()
router.register(r'transportation', TransportationRequestViewSet)
router.register(r'daily-menus', DailyMenuViewSet, basename='daily-menus')
router.register(r'meals', MealSelectionViewSet)
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'maintenance', MaintenanceRequestViewSet)
router.register(r'alerts', AlertViewSet)
router.register(r'wellness', WellnessReminderViewSet)
router.register(r'billing', BillingStatementViewSet)
router.register(r'users', UserViewSet)
router.register(r'feed', FeedViewSet, basename='feed')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', login_view, name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/preferences/', UserProfileView.as_view(), name='user-profile-preferences'),
]
