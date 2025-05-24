from django.contrib import admin
from .models import (
    TransportationRequest,
    MaintenanceRequest,
    DailyMenu,
    MealSelection,
    Activity,
    ActivityInstance,
    Alert,
    WellnessReminder,
    BillingStatement,
    UserProfile,
    Feed,
)

admin.site.register(TransportationRequest)
admin.site.register(MaintenanceRequest)
admin.site.register(DailyMenu)
admin.site.register(MealSelection)
admin.site.register(Activity)
admin.site.register(ActivityInstance)
admin.site.register(Alert)
admin.site.register(WellnessReminder)
admin.site.register(BillingStatement)
admin.site.register(UserProfile)
admin.site.register(Feed)