from io import BytesIO

import weasyprint
from celery import shared_task
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from orders.models import Order


@shared_task
def payment_completed(order_id):
    """
    Задание по отправке уведомления по электронной
    почте при успешной оплате заказа
    """
    order = Order.objects.get(id=order_id)
    # создаем счет фактуру по емаилу
    subject = f"Магазин Змей - Номер счета-фактуры. {order.id}"
    message = "Пожалуйста, ознакомьтесь с приложенным счетом-фактурой за вашу недавнюю покупку."
    email = EmailMessage(subject, message, "admin@myshop.com", [order.email])
    # сгенерировать PDF
    html = render_to_string("orders/order/pdf.html", {"order": order})
    out = BytesIO()
    stylesheets = [weasyprint.CSS(finders.find("css/pdf.css"))]
    weasyprint.HTML(string=html).write_pdf(out, stylesheets=stylesheets)
    # прикрепить PDF file
    email.attach(f"order_{order.id}.pdf", out.getvalue(), "application/pdf")
    # отправить e-mail
    email.send()
