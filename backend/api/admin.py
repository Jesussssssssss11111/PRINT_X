from django.contrib import admin
from .models import Product, Cart, Order, Payment, CustomRequest, Category, UserProfile

admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(Payment)
admin.site.register(CustomRequest)
admin.site.register(Category)
admin.site.register(UserProfile)