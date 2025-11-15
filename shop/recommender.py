import redis
from django.conf import settings

from .models import Product

# Подключаемся к Redis
r = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)


class Recommender:
    def get_product_key(self, id):
        return f"product:{id}:purchased_with"

    def products_bought(self, products):
        product_ids = [p.id for p in products]
        print(f"🔄 Обновление рекомендаций для товаров: {product_ids}")

        for product_id in product_ids:
            for with_id in product_ids:
                if product_id != with_id:
                    # увеличьте балл за продукт, приобретенный вместе
                    key = self.get_product_key(product_id)
                    r.zincrby(key, 1, with_id)
                    print(f"   📈 Увеличена связь: {product_id} -> {with_id}")

        print("✅ Рекомендации обновлены!")

    def suggest_products_for(self, products, max_results=6):
        product_ids = [p.id for p in products]
        print(f"🔍 Поиск рекомендаций для товаров: {product_ids}")

        if len(products) == 1:
            # Только 1 товар
            key = self.get_product_key(product_ids[0])
            suggestions = r.zrange(key, 0, -1, desc=True)[:max_results]
            print(f"   Найдено рекомендаций для {product_ids[0]}: {suggestions}")
        else:
            # сгенерировать временный ключ
            flat_ids = "".join([str(id) for id in product_ids])
            tmp_key = f"tmp_{flat_ids}"

            # если несколько товаров объединить баллы всех товаров
            keys = [self.get_product_key(id) for id in product_ids]
            r.zunionstore(tmp_key, keys)

            # удалить идентификаторы товаров для которых дается рекомендация
            r.zrem(tmp_key, *product_ids)

            # получить предлагаемые товары и отсортировать их по порядку появления
            suggestions = r.zrange(tmp_key, 0, -1, desc=True)[:max_results]
            print(f"   Найдено рекомендаций для нескольких товаров: {suggestions}")

            # Удалить временный ключ
            r.delete(tmp_key)

        suggested_product_ids = [int(id) for id in suggestions]

        # Получить предлагаемые товары и отсортировать их по порядку появления
        suggested_products = list(Product.objects.filter(id__in=suggested_product_ids))
        suggested_products.sort(key=lambda x: suggested_product_ids.index(x.id))

        return suggested_products

    def clear_puchases(self):
        for id in Product.objects.values_list("id", flat=True):
            r.delete(self.get_product_key(id))
