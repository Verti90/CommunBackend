from django.contrib import admin
from django.urls import path, include
from api.views import backend_home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', backend_home, name='home'),
]
