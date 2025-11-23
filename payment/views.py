import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION


def payment_process(request):
    order_id = request.session.get("order_id")
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        # Используем build_absolute_uri вместо build_absolute_url
        success_url = request.build_absolute_uri(reverse("payment:completed"))
        cancel_url = request.build_absolute_uri(reverse("payment:canceled"))

        # Получаем текущий язык для локализации Stripe
        current_language = translation.get_language()

        # Маппинг языков для Stripe (Stripe поддерживает не все языки Django)
        language_map = {
            "ru": "ru",  # Русский
            "es": "es",  # Испанский
            "en": "en",  # Английский
            "fr": "fr",  # Французский
            "de": "de",  # Немецкий
            "it": "it",  # Итальянский
        }
        stripe_locale = language_map.get(current_language, "auto")

        # Базовые данные сессии
        session_data = {
            "mode": "payment",
            "client_reference_id": order.id,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "customer_email": order.email,  # Предзаполнение email
            "locale": stripe_locale,  # Язык интерфейса Stripe
            "submit_type": "pay",  # Текст на кнопке ("Оплатить")
            "line_items": [],
        }

        # Добавляем товары заказа
        for item in order.items.all():
            session_data["line_items"].append(
                {
                    "price_data": {
                        "unit_amount": int(item.price * 100),  # Цена в центах
                        "currency": "usd",
                        "product_data": {
                            "name": item.product.name,
                            # Можно добавить изображение товара
                            # "images": [item.product.image.url] if item.product.image else [],
                        },
                    },
                    "quantity": item.quantity,
                }
            )

        # Обработка купонов для Stripe
        if order.coupon:
            try:
                # Создаем купон в Stripe
                stripe_coupon = stripe.Coupon.create(
                    name=order.coupon.code,
                    percent_off=order.discount,
                    duration="once",
                    currency="usd",  # Указываем валюту для купона
                )
                session_data["discounts"] = [{"coupon": stripe_coupon.id}]
            except stripe.error.StripeError as e:
                # Логируем ошибку, но продолжаем без купона
                print(f"Stripe coupon error: {e}")
                # Можно добавить сообщение для пользователя

        # Настройки адреса доставки (если нужно)
        session_data["shipping_address_collection"] = {
            "allowed_countries": ["US", "CA", "GB", "RU", "KZ", "UA", "DE", "FR", "ES"]
        }

        # Настройки сбора billing адреса
        session_data["billing_address_collection"] = "required"

        # Кастомные тексты (опционально)
        session_data["custom_text"] = {
            "submit": {
                "message": "Платеж защищен Stripe",  # Будет переведено автоматически
            }
        }

        # Настройки налогов (если применимо)
        session_data["automatic_tax"] = {"enabled": False}

        try:
            # Создаем сессию Stripe
            session = stripe.checkout.Session.create(**session_data)

            # Сохраняем ID сессии в заказе для отслеживания
            order.stripe_checkout_session_id = session.id
            order.save()

            # Перенаправляем на Stripe Checkout
            return redirect(session.url, code=303)

        except stripe.error.StripeError as e:
            # Обработка ошибок Stripe
            print(f"Stripe error: {e}")
            # Можно вернуть пользователя с сообщением об ошибке
            return render(
                request, "payment/error.html", {"order": order, "error": str(e)}
            )

    # GET запрос - отображаем страницу процесса оплаты
    return render(request, "payment/process.html", {"order": order})


def payment_completed(request):
    # Очищаем сессию корзины после успешной оплаты
    if "cart" in request.session:
        del request.session["cart"]
    if "order_id" in request.session:
        del request.session["order_id"]

    return render(request, "payment/completed.html")


def payment_canceled(request):
    return render(request, "payment/canceled.html")
