from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import UserRole
from apps.products.models import Category, Product

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Username or Email"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Username or email"),
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Password"),
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label=_("Remember me"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class RegistrationForm(UserCreationForm):
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "username",
                    "autofocus": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username", "autofocus": True}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "new-password"}
        )
        self.fields["password2"].label = _("Confirm password")
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "new-password"}
        )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("This username is already registered."))
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This email address is already registered."))
        return email


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        labels = {
            "name": _("Name"),
            "description": _("Description"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError(_("Category name cannot be empty."))
        return name


class ProductForm(forms.ModelForm):
    initial_quantity = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        help_text=_("Only used when creating a new product."),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "category",
            "description",
            "purchase_price",
            "selling_price",
            "minimum_stock",
            "image",
            "is_active",
        ]
        labels = {
            "name": _("Name"),
            "sku": _("SKU"),
            "category": _("Category"),
            "description": _("Description"),
            "purchase_price": _("Purchase price"),
            "selling_price": _("Selling price"),
            "minimum_stock": _("Minimum stock"),
            "image": _("Image"),
            "is_active": _("Active"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "sku": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "category": forms.Select(attrs={"class": "form-select", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "purchase_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "selling_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/png,image/jpeg,image/webp"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError(_("Product name cannot be empty."))
        return name

    def clean_sku(self):
        return self.cleaned_data["sku"].strip()

    def clean_purchase_price(self):
        value = self.cleaned_data["purchase_price"]
        if value < 0:
            raise forms.ValidationError(_("Price cannot be negative."))
        return value

    def clean_selling_price(self):
        value = self.cleaned_data["selling_price"]
        if value < 0:
            raise forms.ValidationError(_("Price cannot be negative."))
        return value


class StockMovementForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).select_related("category"),
        label=_("Product"),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_product"}),
    )
    quantity = forms.IntegerField(
        label=_("Quantity"),
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
    )
    unit_price = forms.DecimalField(
        label=_("Unit price"),
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
    )
    note = forms.CharField(
        label=_("Note"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text=_("Leave blank to keep current password."),
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role", "is_active"]
        labels = {
            "username": _("Username"),
            "email": _("Email"),
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "role": _("Role"),
            "is_active": _("Active"),
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserCreateForm(UserForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = UserRole.choices
        self.fields["password"].required = True
