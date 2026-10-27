from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext as _
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "category"
            slug = base
            n = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def product_count(self):
        return self.products.count()


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    description = models.TextField(blank=True)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    quantity = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=5)
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.name is not None and not str(self.name).strip():
            raise ValidationError({"name": _("Product name cannot be empty.")})
        if self.quantity is not None and self.quantity < 0:
            raise ValidationError({"quantity": _("Quantity cannot be negative.")})

    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock

    @property
    def stock_status(self):
        if self.quantity <= 0:
            return "out"
        if self.is_low_stock:
            return "low"
        return "ok"

    @property
    def stock_value(self):
        return self.quantity * self.purchase_price
