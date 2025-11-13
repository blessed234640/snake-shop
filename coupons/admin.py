from django.contrib import admin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "valid_form", "valid_to", "discount", "active"]
    list_filter = ["active", "valid_form", "valid_to"]
    search_fields = ["code"]
