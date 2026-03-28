from django.contrib import admin
from .models import Customer, Product, Cart, CartItem, Order, OrderItem

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)

