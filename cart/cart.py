# cart/cart.py
from decimal import Decimal
from coupons.models import Coupon
from django.conf import settings
from django.utils import translation
from shop.models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
        self.coupon_id = self.session.get("coupon_id")

    def get_currency_info(self):
        """Возвращает информацию о валюте для текущего языка"""
        current_language = translation.get_language()
        return settings.CURRENCIES.get(current_language, settings.CURRENCIES['en'])
    
    def convert_price(self, price):
        """Конвертирует цену из РУБЛЕЙ в текущую валюту"""
        currency_info = self.get_currency_info()
        
        # Базовая цена в РУБЛЯХ, конвертируем в целевую валюту
        return round(Decimal(str(price)) * Decimal(str(currency_info['rate'])), 2)

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            # Сохраняем оригинальную цену в рублях
            self.cart[product_id] = {
                "quantity": 0,
                "price": str(product.price),  # Оригинальная цена в рублях
            }
        if override_quantity:
            self.cart[product_id]["quantity"] = quantity
        else:
            self.cart[product_id]["quantity"] += quantity
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()

        for product in products:
            cart[str(product.id)]["product"] = product

        for item in cart.values():
            # Храним оригинальную цену, конвертация будет в шаблоне через фильтр
            original_price = Decimal(item["price"])
            item["price"] = original_price  # Оставляем оригинальную цену
            item["total_price"] = item["price"] * item["quantity"]
            yield item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def get_total_price(self):
        """Общая цена в оригинальной валюте (рублях)"""
        return sum(
            Decimal(item["price"]) * item["quantity"] for item in self.cart.values()
        )

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                pass
        return None

    def get_discount(self):
        if self.coupon:
            # Скидка рассчитывается от оригинальной цены
            original_total = self.get_total_price()
            discount_amount = (self.coupon.discount / Decimal(100)) * original_total
            return discount_amount  # Возвращаем в оригинальной валюте
        return Decimal(0)

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()
    
    def format_price(self, price):
        """Форматирует цену для отображения"""
        currency_info = self.get_currency_info()
        if currency_info['code'] == 'RUB':
            return f"{price:,.2f} {currency_info['symbol']}".replace(',', ' ').replace('.', ',')
        elif currency_info['code'] == 'EUR':
            return f"{currency_info['symbol']}{price:,.2f}"
        else:  # USD
            return f"{currency_info['symbol']}{price:,.2f}"
    
    def get_stripe_total(self):
        """Возвращает сумму для Stripe (в центах/копейках)"""
        currency_info = self.get_currency_info()
        # Конвертируем общую сумму в целевую валюту для Stripe
        total_rub = self.get_total_price_after_discount()
        total_converted = self.convert_price(total_rub)
        
        if currency_info['code'] in ['USD', 'EUR', 'RUB']:
            return int(total_converted * 100)  # центы/копейки
        return int(total_converted * 100)
    
    def get_stripe_currency(self):
        """Возвращает валюту для Stripe"""
        return self.get_currency_info()['stripe_currency']
    
    def get_total_weight(self):
        """Возвращает общий вес корзины в граммах"""
        total_weight = Decimal('0')
        for item in self:
            product = item['product']
            quantity = item['quantity']
            total_weight += product.weight * quantity
        return total_weight

    def calculate_shipping_cost_base(self):
        """Рассчитывает стоимость доставки в базовой валюте (рублях)"""
        total_weight = self.get_total_weight()
        
        # Тарифы доставки в РУБЛЯХ
        if total_weight <= 1000:  # до 1 кг
            return Decimal('500.00')
        elif total_weight <= 5000:  # до 5 кг
            return Decimal('800.00')
        elif total_weight <= 10000:  # до 10 кг
            return Decimal('1200.00')
        else:  # свыше 10 кг
            return Decimal('1200.00') + (total_weight - 10000) / 1000 * Decimal('100.00')