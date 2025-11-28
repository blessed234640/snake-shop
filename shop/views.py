from cart.forms import CartAddProductForm
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product
from .recommender import Recommender


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        language = request.LANGUAGE_CODE
        category = get_object_or_404(
            Category,
            translations__language_code=language,
            translations__slug=category_slug,
        )
        products = products.filter(category=category)

    return render(
        request,
        "shop/product/list.html",
        {
            "category": category,
            "categories": categories,
            "products": products,
        },
    )


def product_detail(request, id, slug):
    language = request.LANGUAGE_CODE
    product = get_object_or_404(
        Product,
        id=id,
        translations__language_code=language,
        translations__slug=slug,
        available=True,
    )

    # Получаем все дополнительные изображения товара
    additional_images = product.images.all()

    cart_product_form = CartAddProductForm()
    r = Recommender()
    recommended_products = r.suggest_products_for([product], 4)

    return render(
        request,
        "shop/product/detail.html",
        {
            "product": product,
            "additional_images": additional_images,
            "cart_product_form": cart_product_form,
            "recommended_products": recommended_products,
        },
    )


def product_search(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.filter(available=True)
    
    if query:
        # Ищем в нескольких вариантах
        query_variants = [
            query,           # оригинальный запрос
            query.lower(),   # нижний регистр
            query.upper(),   # верхний регистр
            query.capitalize(), # с заглавной буквы
        ]
        
        # Создаем Q объекты для всех вариантов
        q_objects = Q()
        for variant in set(query_variants):  # set для удаления дубликатов
            q_objects |= Q(translations__name__icontains=variant)
            q_objects |= Q(translations__description__icontains=variant)
        
        products = products.filter(q_objects).distinct()
    
    return render(request, 'shop/product/search.html', {
        'products': products,
        'query': query
    })