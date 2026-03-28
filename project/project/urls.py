from django.contrib import admin
from django.urls import path
from apple import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.hello, name='hello'),
    path('logout/', views.logout_view, name='logout'),
    path('products/', views.product_list, name='products'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),

    path('customer/', views.customer_details, name='customer_details'),
    path('cart/', views.view_cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('success/', views.success, name='success'),

    path('increase/<int:item_id>/', views.increase_quantity, name='increase_qty'),
    path('decrease/<int:item_id>/', views.decrease_quantity, name='decrease_qty'),
    path('remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('saved/', views.saved_Details, name='saved'),
    path('profile/', views.profile, name='profile'),
    path('account/', views.account, name='account'),
    path('nav_address/', views.nav_address, name='nav_address'),
    
    path('contactus/', views.contacts, name="contactus"),
    path('prime/', views.prime, name="prime"),
    path('payments/', views.payment, name="payments"),

    path('orders/', views.orders, name='orders'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('rating/', views.rating, name="rating"),

    path('edit-address/', views.edit_address, name='edit_address'),
    path('remove-address/', views.remove_address, name='remove_address'),
    path('razorpay-create/', views.create_razorpay_order, name='create_razorpay_order'),
    
    path('edit-name/', views.edit_name, name='edit_name'),
    path('edit-email/', views.edit_email, name='edit_email'),
    path('edit-number/', views.edit_number, name='edit_number'),
    path("cancel-order/<int:order_id>/", views.cancel_order, name="cancel_order"),
    


]




if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATICFILES_DIRS[0]
    )
