from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('taskForce.accounts.urls')),
    path('', include('taskForce.common.urls')),
    path('comms/', include('taskForce.comms.urls')),
    path('units/', include('taskForce.units.urls')),
    path('zones/', include('taskForce.zones.urls')),
    path('tasks/', include('taskForce.tasks.urls')),
]
