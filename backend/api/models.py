from django.db import models
from django.contrib.auth.models import User
import json
import uuid
import secrets


# =====================
# PRODUCT CATEGORY
# =====================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


# =====================
# PRODUCT
# =====================
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image = models.CharField(max_length=500, default='')
    stock = models.IntegerField(default=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": float(self.price), # Decimal must be converted to float/string for JSON
            "description": self.description,
            "image": self.image,
            "stock": self.stock,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# =====================
# CART
# =====================
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_cart_item')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x{self.quantity}"


# =====================
# ORDER
# =====================
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('cancel_requested', 'Cancellation Requested'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    tracking_id = models.CharField(max_length=32, unique=True, editable=False)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    address = models.TextField(default='')
    phone = models.CharField(max_length=20, default='')
    items_snapshot = models.TextField(default='')
    notes = models.TextField(blank=True, default='')
    cancel_reason = models.TextField(blank=True, default='')
    estimated_delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = self.generate_tracking_id()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_tracking_id():
        """Generate secure non-guessable tracking ID (16 alphanumeric chars)"""
        # Generate random hex string and take first 16 characters
        return secrets.token_hex(8).upper()  # 8 bytes = 16 hex chars

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.tracking_id}"

    def get_items(self):
        try:
            return json.loads(self.items_snapshot) if self.items_snapshot else []
        except:
            return []


# =====================
# USER PROFILE
# =====================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    profile_picture = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# =====================
# PAYMENT (NEW CLEAN SYSTEM)
# =====================
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('gcash', 'GCash'),
        ('maya', 'Maya'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    reference_number = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.method} - {self.status}"


# =====================
# CUSTOM REQUEST
# =====================
class CustomRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Reviewing'),
        ('approved', 'Approved'),
        ('printing', 'Printing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_requests')
    file_name = models.CharField(max_length=255)
    file_size = models.FloatField(default=0)
    stl_file = models.FileField(upload_to='stl_files/', blank=True, null=True)
    material = models.CharField(max_length=100, default='PLA')
    color = models.CharField(max_length=50, default='White')
    quantity = models.IntegerField(default=1)
    notes = models.TextField(blank=True, default='')
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    cancel_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Custom #{self.id} - {self.file_name}"



# =====================
# PRODUCT REVIEW
# =====================
class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"
