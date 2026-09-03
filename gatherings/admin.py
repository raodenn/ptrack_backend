from django.contrib import admin
from .models import Venue,UserLocation,Session,Attendance
# Register your models here.

admin.site.register(Venue)
admin.site.register(UserLocation)
admin.site.register(Session)
admin.site.register(Attendance)