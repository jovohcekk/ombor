from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import UserRole
from apps.inventory.models import MovementType
from apps.inventory.services import apply_stock_movement
from apps.products.models import Category, Product

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo categories, products, stock movements, and users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-password",
            action="store_true",
            help="Reset demo admin password to the documented demo value.",
        )

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "role": UserRole.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created or options["force_password"]:
            admin.set_password("Admin123!")
            admin.role = UserRole.SUPER_ADMIN
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write(self.style.SUCCESS("Demo admin: admin / Admin123!"))
        else:
            self.stdout.write("Admin user already exists (password unchanged)")

        for username, role, email in (
            ("manager", UserRole.MANAGER, "manager@example.com"),
            ("staff", UserRole.STAFF, "staff@example.com"),
        ):
            user, made = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "role": role},
            )
            if made:
                user.set_password("Demo12345!")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created {username} / Demo12345!"))

        categories_data = [
            ("Electronics", "Phones, laptops, accessories"),
            ("Office", "Office supplies"),
            ("Furniture", "Desks and chairs"),
        ]
        categories = {}
        for name, desc in categories_data:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"description": desc})
            categories[name] = cat

        products_data = [
            ("iPhone 15", "IPH15-001", "Electronics", "999", "1199", 25, 5),
            ("MacBook Pro", "MBP-001", "Electronics", "1800", "2199", 10, 3),
            ("Office Chair", "CHR-001", "Furniture", "120", "199", 40, 10),
            ("A4 Paper Pack", "PAP-001", "Office", "5", "8", 200, 50),
            ("USB-C Cable", "CBL-001", "Electronics", "3", "8", 4, 15),
        ]
        for name, sku, cat_name, pp, sp, qty, min_s in products_data:
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": categories[cat_name],
                    "purchase_price": Decimal(pp),
                    "selling_price": Decimal(sp),
                    "minimum_stock": min_s,
                    "quantity": 0,
                },
            )
            if created and qty:
                apply_stock_movement(
                    product=product,
                    movement_type=MovementType.IN,
                    quantity=qty,
                    unit_price=product.purchase_price,
                    note="Seed initial stock",
                    user=admin,
                )

        cable = Product.objects.filter(sku="CBL-001").first()
        if cable and not cable.movements.filter(movement_type=MovementType.OUT).exists():
            apply_stock_movement(
                product=cable,
                movement_type=MovementType.OUT,
                quantity=2,
                unit_price=cable.selling_price,
                note="Seed demo sale",
                user=admin,
            )

        self.stdout.write(self.style.SUCCESS("Seed data completed."))
