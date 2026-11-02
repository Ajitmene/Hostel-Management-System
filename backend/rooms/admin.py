from django.contrib import admin

from rooms.models import Room, RoomAllocation


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "block", "floor", "room_type", "capacity", "occupancy_display", "monthly_rate", "is_active")
    list_filter = ("block", "room_type", "is_active")
    search_fields = ("room_number", "block")

    @admin.display(description="Occupancy")
    def occupancy_display(self, obj):
        return f"{obj.occupancy}/{obj.capacity}"


@admin.register(RoomAllocation)
class RoomAllocationAdmin(admin.ModelAdmin):
    """View-only. Allocations and transfers go through the API's transactional
    service so room capacity can never be exceeded."""

    list_display = ("student", "room", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("student__enrollment_no", "student__full_name", "room__room_number")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
