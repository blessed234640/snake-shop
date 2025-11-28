from decimal import Decimal

from coupons.models import Coupon
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Order(models.Model):
    first_name = models.CharField(_("first name"), max_length=50)
    last_name = models.CharField(_("last name"), max_length=50)
    email = models.EmailField(_("e-mail"))
    address = models.CharField(_("address"), max_length=250)
    postal_code = models.CharField(_("postal code"), max_length=20)
    city = models.CharField(_("city"), max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    stripe_id = models.CharField(max_length=250, blank=True)
    coupon = models.ForeignKey(
        Coupon, related_name="orders", null=True, blank=True, on_delete=models.SET_NULL
    )
    discount = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    # ДОБАВИТЬ ЭТИ ПОЛЯ ДЛЯ МУЛЬТИВАЛЮТНОСТИ
    currency = models.CharField(max_length=3, default='USD')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    original_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # В базовой валюте (USD)
    
    # ДОБАВЬТЕ ЭТИ ПОЛЯ ДЛЯ ДОСТАВКИ
    shipping_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name=_("Total weight (g)")
    )
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name=_("Shipping cost")
    )
    shipping_cost_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Shipping cost in base currency (RUB)")
    )
    shipping_method = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Shipping method")
    )

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["-created"]),
        ]

    def __str__(self):
        return f"Order {self.id}"
    
    def calculate_total_weight(self):
        """Рассчитывает общий вес заказа"""
        total_weight = sum(
            item.product.weight * item.quantity for item in self.items.all()
        )
        return total_weight

    def calculate_shipping_cost_base(self):
        """Рассчитывает стоимость доставки в базовой валюте (рублях)"""
        total_weight = self.calculate_total_weight()
        
        # Тарифы доставки в РУБЛЯХ (базовая валюта)
        if total_weight <= 1000:  # до 1 кг
            return Decimal('500.00')  # 500 руб
        elif total_weight <= 5000:  # до 5 кг
            return Decimal('800.00')  # 800 руб
        elif total_weight <= 10000:  # до 10 кг
            return Decimal('1200.00')  # 1200 руб
        else:  # свыше 10 кг
            return Decimal('1200.00') + (total_weight - 10000) / 1000 * Decimal('100.00')

    def get_shipping_cost_in_order_currency(self):
        """Возвращает стоимость доставки в валюте заказа"""
        shipping_base = self.shipping_cost_base
        # Конвертируем из рублей в валюту заказа
        return shipping_base * self.exchange_rate
    
    def get_total_cost_before_discount(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_discount(self):
        total_cost = self.get_total_cost_before_discount()
        if self.discount:
            return total_cost * (self.discount / Decimal(100))
        return Decimal(0)

    def get_total_cost(self):
        """ОБНОВИТЕ ЭТОТ МЕТОД - должен включать доставку!"""
        total_cost = self.get_total_cost_before_discount()
        total_with_discount = total_cost - self.get_discount()
        return total_with_discount + self.shipping_cost
    
    def get_items_total(self):
        """Стоимость только товаров (без доставки)"""
        total_cost = self.get_total_cost_before_discount()
        return total_cost - self.get_discount()
    
    # ДОБАВИТЬ МЕТОДЫ ДЛЯ ВАЛЮТ
    def get_total_in_original_currency(self):
        """Возвращает стоимость в базовой валюте (USD)"""
        return self.original_total
    
    def format_price(self, price):
        """Форматирует цену согласно валюте заказа"""
        if self.currency == 'RUB':
            return f"{price:,.2f} {self.get_currency_symbol()}".replace(',', ' ').replace('.', ',')
        elif self.currency == 'EUR':
            return f"{self.get_currency_symbol()}{price:,.2f}"
        else:  # USD
            return f"{self.get_currency_symbol()}{price:,.2f}"
    
    def get_currency_symbol(self):
        """Возвращает символ валюты"""
        symbols = {'USD': '$', 'EUR': '€', 'RUB': '₽'}
        return symbols.get(self.currency, '$')

    def get_stripe_url(self):
        if not self.stripe_id:
            return ""
        if "_test_" in settings.STRIPE_SECRET_KEY:
            path = "/test/"
        else:
            path = "/"
        return f"https://dashboard.stripe.com{path}payments/{self.stripe_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "shop.Product", related_name="order_items", on_delete=models.CASCADE
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity