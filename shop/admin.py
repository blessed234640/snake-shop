from django.contrib import admin
from parler.admin import TranslatableAdmin

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    list_display = ["name", "slug"]

    # def get_prepopulated_fields(self, request, obj=None):
    #     return {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  # Количество пустых форм для добавления новых фото
    fields = ["image", "order", "image_preview"]
    readonly_fields = ["image_preview"]

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 100px;" />'
        return "No image"

    image_preview.allow_tags = True
    image_preview.short_description = "Превью"


@admin.register(Product)
class ProductAdmin(TranslatableAdmin):
    list_display = [
        "name",
        "price",
        "available",
        "created",
        "updated",
        "main_image_preview",
    ]
    list_display_links = ["name"]
    list_filter = ["available", "created", "updated"]  # ← убрали "category"
    list_editable = ["price", "available"]
    inlines = [ProductImageInline]
    readonly_fields = ["main_image_preview"]

    # def get_prepopulated_fields(self, request, obj=None):
    #     return {"slug": ("name",)}

    class Media:
        js = (
            "admin/js/parler_slug_autofill.js",  # наш кастомный скрипт
            "admin/js/parler_slug_autofill.js?v=2",  # ← добавили версию
        )

    def main_image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 100px;" />'
        return "No image"

    main_image_preview.allow_tags = True
    main_image_preview.short_description = "Главное фото"

    # Опционально: можно добавить поля для фильтрации в детальном просмотре
    # fieldsets = (
    #     (None, {"fields": ("category", "price", "available")}),
    #     (
    #         "Описание и изображения",
    #         {"fields": ("image", "main_image_preview")},
    #     ),
    # )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "image_preview", "order", "created"]
    list_filter = ["created", "product__category"]
    list_editable = ["order"]
    list_select_related = ["product"]
    search_fields = ["product__name"]

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 50px; max-width: 50px;" />'
        return "No image"

    image_preview.allow_tags = True
    image_preview.short_description = "Фото"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")
