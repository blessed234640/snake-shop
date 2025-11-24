# shop/templatetags/currency_tags.py
from decimal import Decimal
from django import template
from django.conf import settings
from django.utils import translation

# ДОБАВЬТЕ ЭТУ СТРОКУ
register = template.Library()

@register.filter
def currency(value):
    """Фильтр для конвертации и форматирования цены"""
    if value is None:
        return ""
    
    try:
        current_language = translation.get_language()
        currency_info = settings.CURRENCIES.get(current_language, settings.CURRENCIES['en'])
        
        print(f"🔴 CURRENCY FILTER: value={value}, language={current_language}, rate={currency_info['rate']}")
        
        # Конвертируем из рублей в целевую валюту
        decimal_value = Decimal(str(value))
        decimal_rate = Decimal(str(currency_info['rate']))
        
        converted_price = decimal_value * decimal_rate
        formatted_price = round(converted_price, 2)
        
        if currency_info['code'] == 'RUB':
            result = f"{formatted_price:,.2f} {currency_info['symbol']}".replace(',', ' ').replace('.', ',')
        elif currency_info['code'] == 'EUR':
            result = f"{currency_info['symbol']}{formatted_price:,.2f}"
        else:  # USD
            result = f"{currency_info['symbol']}{formatted_price:,.2f}"
            
        print(f"🔴 CURRENCY RESULT: {result}")
        return result
            
    except (ValueError, TypeError, KeyError) as e:
        print(f"🔴 CURRENCY ERROR: {e}")
        return f"${value}"