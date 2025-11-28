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
            
            currency_info = cart.get_currency_info()
            order.currency = currency_info['code']
            order.exchange_rate = Decimal(str(currency_info['rate']))
            
            # ОТЛАДКА
            print(f"🔍 DEBUG: Cart total = {cart.get_total_price_after_discount()}")
            print(f"🔍 DEBUG: Currency = {order.currency}, Rate = {order.exchange_rate}")
            
            # Рассчитываем доставку
            order.shipping_weight = cart.get_total_weight()
            shipping_base = cart.calculate_shipping_cost_base()
            order.shipping_cost_base = shipping_base
            order.shipping_cost = shipping_base * order.exchange_rate

            print(f"🔍 SHIPPING: {shipping_base} RUB * {order.exchange_rate} = {order.shipping_cost} {order.currency}")

            # ВАЖНО: original_total в USD (базовой валюте)
            total_in_rub = Decimal('0')
            for item in cart:
                total_in_rub += item["product"].price * item["quantity"]
            
            if cart.coupon:
                discount_amount = total_in_rub * (cart.coupon.discount / Decimal(100))
                total_in_rub -= discount_amount
            
            # Конвертируем в USD (базовая валюта)
            usd_rate = Decimal('0.012')  # 1 RUB = 0.012 USD
            order.original_total = total_in_rub * usd_rate
            
            order.shipping_method = "standard"

            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.discount
            
            # ДОБАВЬТЕ ОТЛАДКУ ПЕРЕД СОХРАНЕНИЕМ
            print(f"🔍 BEFORE SAVE - shipping_cost: {order.shipping_cost}")
            print(f"🔍 BEFORE SAVE - original_total: {order.original_total}")
            
            order.save()

            # ИСПРАВЛЕНИЕ: Правильная конвертация цен для OrderItem
            for item in cart:
                # Получаем оригинальную цену в рублях
                original_price_rub = item["product"].price
                # Конвертируем в валюту заказа
                price_in_currency = original_price_rub * order.exchange_rate
                
                print(f"🔍 ITEM PRICE: {item['product'].name} - {original_price_rub} RUB -> {price_in_currency} {order.currency}")
                
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    price=price_in_currency,  # Конвертированная цена
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