from django.contrib import admin
from django.urls import path

admin.site.site_header = "Hostel Management Administration"
admin.site.site_title = "Hostel Admin"
admin.site.index_title = "Management"

urlpatterns = [
    path("admin/", admin.site.urls),
]
