from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.store.models import Category, Product


class Command(BaseCommand):
    """Fill the store with test categories and products."""

    help = "Create test categories and products for the store."

    CATALOG: dict[str, list[tuple[str, str, str]]] = {
        "Drinks": [
            ("Coca-Cola 0.5 L", "DRK-COLA-05", "400.00"),
            ("Fanta 0.5 L", "DRK-FANTA-05", "400.00"),
            ("Water 0.5 L", "DRK-WATER-05", "250.00"),
            ("Red Bull 0.25 L", "DRK-REDBULL-025", "900.00"),
        ],
        "Snacks": [
            ("Lays Classic", "SNK-LAYS-01", "600.00"),
            ("Pringles Original", "SNK-PRINGLES-01", "1200.00"),
            ("Snickers", "SNK-SNICKERS-01", "450.00"),
        ],
        "Accessories": [
            ("DualSense Controller", "ACC-DUALSENSE", "35000.00"),
            ("Controller Charging Station", "ACC-CHARGER", "15000.00"),
        ],
    }

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--stock",
            type=int,
            default=20,
            help="Starting stock for every new product (default: 20)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Command entry point."""
        stock: int = options["stock"]
        if stock < 0:
            raise CommandError("--stock can't be negative")

        categories: dict[str, Category] = self.__get_categories()
        products: list[Product] = self.__create_products(categories, stock)

        if products:
            self.stdout.write(self.style.SUCCESS(f"Created {len(products)} products."))
        else:
            self.stdout.write(self.style.WARNING("Nothing new to create."))

    def __get_categories(self) -> dict[str, Category]:
        """Return categories by name, creating the missing ones."""
        categories: dict[str, Category] = {}
        for category in Category.objects.filter(deleted_at__isnull=True):
            categories[category.name] = category

        new_categories: list[Category] = []
        for name in self.CATALOG:
            if name not in categories:
                new_categories.append(Category(name=name))

        Category.objects.bulk_create(new_categories)
        for category in new_categories:
            categories[category.name] = category
        return categories

    def __create_products(
        self,
        categories: dict[str, Category],
        stock: int,
    ) -> list[Product]:
        """Create products that don't exist yet. Skip known SKUs."""
        used_skus: set[str] = set(
            Product.objects.filter(deleted_at__isnull=True).values_list("sku", flat=True)
        )

        new_products: list[Product] = []
        for category_name, items in self.CATALOG.items():
            for name, sku, price in items:
                if sku in used_skus:
                    continue
                used_skus.add(sku)
                new_products.append(
                    Product(
                        category=categories[category_name],
                        name=name,
                        sku=sku,
                        price=Decimal(price),
                        stock=stock,
                    )
                )

        Product.objects.bulk_create(new_products)
        return new_products