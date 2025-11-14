import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


def payment_process(request):
    order_id = request.session.get("order_id")
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        # Используем build_absolute_uri вместо build_absolute_url
        success_url = request.build_absolute_uri(reverse("payment:completed"))
        cancel_url = request.build_absolute_uri(reverse("payment:canceled"))

        # Создаем сессию Stripe Checkout
        session_data = {
            "mode": "payment",
            "client_reference_id": order.id,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items": [],
        }

        # Добавляем товары заказа
        for item in order.items.all():
            session_data["line_items"].append(
                {
                    "price_data": {
                        "unit_amount": int(item.price * 100),
                        "currency": "usd",
                        "product_data": {
                            "name": item.product.name,
                        },
                    },
                    "quantity": item.quantity,
                }
            )
        # Купоны для Stripe
        if order.coupon:
            stripe_coupon = stripe.Coupon.create(
                name=order.coupon.code, percent_off=order.discount, duration="once"
            )
            session_data["discounts"] = [{"coupon": stripe_coupon.id}]

        # Создаем сессию Stripe
        session = stripe.checkout.Session.create(**session_data)

        # Перенаправляем на Stripe Checkout
        return redirect(session.url, code=303)

    # GET запрос
    return render(request, "payment/process.html", {"order": order})


def payment_completed(request):
    return render(request, "payment/completed.html")


def payment_canceled(request):
    return render(request, "payment/canceled.html")
