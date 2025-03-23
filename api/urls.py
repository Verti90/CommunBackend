from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .auth_views import register_user, login_user
from .views import (
    TransportationRequestViewSet, MealSelectionViewSet, ActivityViewSet,
    MaintenanceRequestViewSet, AlertViewSet, WellnessReminderViewSet, BillingStatementViewSet, UserViewSet, profile_view
)

router = DefaultRouter()
router.register(r'transportation', TransportationRequestViewSet)
router.register(r'meals', MealSelectionViewSet)
router.register(r'activities', ActivityViewSet)
router.register(r'maintenance', MaintenanceRequestViewSet, basename='maintenance')
router.register(r'alerts', AlertViewSet)
router.register(r'wellness', WellnessReminderViewSet)
router.register(r'billing', BillingStatementViewSet)
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path("register/", register_user, name="register"),
    path("login/", login_user, name="login"),
    path("activities/<int:pk>/signup/", ActivityViewSet.as_view({'post': 'signup'}), name="activity-signup"),
    path("activities/<int:pk>/unregister/", ActivityViewSet.as_view({'post': 'unregister'}), name="activity-unregister"),
    path("profile/", profile_view, name="profile"),
]
