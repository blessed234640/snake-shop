import weasyprint
from cart.cart import Cart
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from decimal import Decimal

from .forms import OrderCreateForm
from .models import Order, OrderItem
from .tasks import order_created


def order_create(request):
    cart = Cart(request)
    if request.method == "POST":
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            
            # ДОБАВЬТЕ ЭТОТ КОД - сохраняем валюту заказа
            currency_info = cart.get_currency_info()
            order.currency = currency_info['code']
            order.exchange_rate = Decimal(str(currency_info['rate']))
            
            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.discount
            order.save()

            # ОБНОВИТЕ ЭТОТ КОД - конвертируем цены при создании OrderItem
            for item in cart:
                # Конвертируем цену из рублей в валюту заказа
                original_price_rub = Decimal(item["price"])
                price_in_order_currency = cart.convert_price(original_price_rub)
                
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    price=price_in_order_currency,  # Сохраняем конвертированную цену
                    quantity=item["quantity"],
                )

            # ДОБАВЬТЕ ЭТОТ КОД - запись рекомендаций
            if len(cart) > 1:  # Если в корзине больше 1 товара
                from shop.recommender import Recommender

                r = Recommender()
                cart_products = [item["product"] for item in cart]
                print(
                    f"✅ Записываем рекомендации для товаров: {[p.id for p in cart_products]}"
                )
                r.products_bought(cart_products)

            # Очистить корзину
            cart.clear()

            # Загружать асинхронные задания
            order_created.delay(order.id)

            # задать заказ в сеансе
            request.session["order_id"] = order.id

            # перенаправлять к платежу
            return redirect(reverse("payment:process"))
    else:
        form = OrderCreateForm()
    return render(request, "orders/order/create.html", {"cart": cart, "form": form})


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "admin/orders/order/detail.html", {"order": order})


@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string("orders/order/pdf.html", {"order": order})
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"filename=order_{order.id}.pdf"
    weasyprint.HTML(string=html).write_pdf(
        response, stylesheets=[weasyprint.CSS(finders.find("shop/css/pdf.css"))]
    )
    return response