from django.db import migrations


def seed_promotion_products(apps, schema_editor):
    PromotionProduct = apps.get_model('ads', 'PromotionProduct')
    products = [
        {
            'name': 'Basico',
            'description': 'Publicacion normal sin prioridad especial.',
            'price_tangas': 0,
            'visibility': 'BASIC',
            'priority_weight': 0,
            'duration_days': 30,
            'is_active': True,
        },
        {
            'name': 'Destacado',
            'description': 'Mayor visibilidad que un anuncio basico.',
            'price_tangas': 10,
            'visibility': 'FEATURED',
            'priority_weight': 50,
            'duration_days': 30,
            'is_active': True,
        },
        {
            'name': 'Siempre arriba',
            'description': 'Prioridad maxima en los listados visibles.',
            'price_tangas': 50,
            'visibility': 'TOP',
            'priority_weight': 100,
            'duration_days': 30,
            'is_active': True,
        },
    ]
    for product in products:
        PromotionProduct.objects.get_or_create(name=product['name'], defaults=product)


def unseed_promotion_products(apps, schema_editor):
    PromotionProduct = apps.get_model('ads', 'PromotionProduct')
    PromotionProduct.objects.filter(name__in=['Basico', 'Destacado', 'Siempre arriba']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0006_promotionproduct_ad_promotion_product'),
    ]

    operations = [
        migrations.RunPython(seed_promotion_products, unseed_promotion_products),
    ]
