import random
import string
from django.shortcuts import render, redirect, get_object_or_404
from .models import Customer, Product, Cart, CartItem, Order, OrderItem
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.conf import settings

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def generate_captcha(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))



def get_customer(request):
    customer_id = request.session.get('customer_id')
    if not customer_id:
        return None
    return Customer.objects.filter(id=customer_id).first()



def hello(request):
    ip_address = get_client_ip(request)

    # 🔥 AUTO LOGIN ONLY IF NOT FORCED LOGOUT
    if not request.session.get('force_login'):
        customer = Customer.objects.filter(ip_address=ip_address).first()

        if customer:
            request.session['customer_id'] = customer.id
            request.session['display_name'] = customer.name
            request.session['details_filled'] = bool(
                customer.address and customer.city and customer.pincode
            )
            return redirect('products')

    # 🔴 CLEAR FORCE LOGIN FLAG
    request.session.pop('force_login', None)

    # ❌ SHOW LOGIN PAGE
    if request.method == "GET":
        return render(request, "index.html", {
            "captcha": generate_captcha()
        })

    # CAPTCHA CHECK
    if request.POST.get("captcha") != request.POST.get("real_captcha"):
        return render(request, "index.html", {
            "captcha": generate_captcha(),
            "error": "Captcha incorrect"
        })

    # CREATE NEW CUSTOMER
    customer = Customer.objects.create(
        name=request.POST.get("name"),
        ip_address=ip_address
    )

    request.session['customer_id'] = customer.id
    request.session['display_name'] = customer.name
    request.session['details_filled'] = False

    return redirect('products')


def logout_view(request):
    request.session.flush()
    request.session['force_login'] = True
    return redirect('hello')


def cart_count(request):
    customer = get_customer(request)
    if not customer:
        return 0
    cart = Cart.objects.filter(customer=customer).first()
    return cart.items.count() if cart else 0


def product_list(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    products = Product.objects.filter(is_active=True).order_by('-id')

    return render(request, 'product.html', {
        'products': products,
        'cart_count': cart_count(request)
    })




from django.http import JsonResponse

def add_to_cart(request, product_id):
    customer = get_customer(request)
    if not customer:
        return JsonResponse({"error": "Login required"}, status=401)

    qty = int(request.POST.get('quantity', 1))
    product = get_object_or_404(Product, id=product_id)

    cart, _ = Cart.objects.get_or_create(customer=customer)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    item.quantity = item.quantity + qty if not created else qty
    item.save()

    # ✅ CALCULATE CART COUNT (IMPORTANT)
    cart_count = cart.items.count()

    # ✅ IF AJAX → RETURN JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "cart_count": cart_count
        })

    # 🔴 NORMAL FLOW (fallback)
    return redirect('products')


def buy_now(request, product_id):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    product = get_object_or_404(Product, id=product_id)

    request.session['buy_now'] = {
        'product_id': product.id,
        'quantity': 1
    }

    return render(request, 'buy_now.html', {
        'product': product,
        'quantity': 1,
        'total': product.price
    })

def customer_details(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.session.get('details_filled'):
        return redirect('checkout')

    if request.method == "POST":
        mobile = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')

        customer.phone = mobile
        customer.address = address
        customer.city = city
        customer.pincode = pincode
        customer.save()

        request.session['details_filled'] = True
        return redirect('checkout')   # ✅ ONLY CHANGE



    return render(request, 'customer.html', {
        'customer': customer
    })

def orders(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    orders = Order.objects.filter(customer=customer).order_by('-created_at')

    return render(request, 'orders.html', {
        'orders': orders
    })

def view_cart(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    cart = Cart.objects.filter(customer=customer).first()
    items = cart.items.all() if cart else []
    total = sum(i.subtotal() for i in items)

    return render(request, 'cart.html', {
        'items': items,
        'total': total
    })


def increase_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.quantity += 1
    item.save()
    return redirect('cart')


def decrease_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
    return redirect('cart')


def remove_from_cart(request, product_id):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    cart = Cart.objects.filter(customer=customer).first()
    if cart:
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()

    return redirect('cart')


def checkout(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if not request.session.get('details_filled'):
        return redirect('customer_details')

    # 🔥 BUY NOW FLOW
    if request.session.get('buy_now'):
        data = request.session['buy_now']
        product = get_object_or_404(Product, id=data['product_id'])
        quantity = data['quantity']
        total = product.price * quantity

        return render(request, 'checkout.html', {
            'customer': customer,
            'single_item': {
                'name': product.name,
                'quantity': quantity,
                'subtotal': total
            },
            'total': total,
            'is_buy_now': True
        })

    # 🛒 CART FLOW
    cart = Cart.objects.filter(customer=customer).first()
    if not cart or not cart.items.exists():
        return redirect('products')

    items = cart.items.all()
    total = sum(i.subtotal() for i in items)

    return render(request, 'checkout.html', {
        'items': items,
        'total': total,
        'customer': customer,
        'is_buy_now': False
    })


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Product, Cart, Order, OrderItem
def place_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    customer = get_customer(request)
    if not customer:
        return JsonResponse({"error": "Login required"}, status=401)

    # 🔒 DELIVERY SNAPSHOT (THIS IS THE FIX)
    delivery_name = request.POST.get("delivery_name")
    delivery_phone = request.POST.get("delivery_phone")
    delivery_address = request.POST.get("delivery_address")
    delivery_city = request.POST.get("delivery_city")
    delivery_pincode = request.POST.get("delivery_pincode")

    # 🔥 BUY NOW FLOW
    if request.session.get("buy_now"):
        data = request.session.get("buy_now")
        product = get_object_or_404(Product, id=data["product_id"])
        quantity = data["quantity"]

        total = product.price * quantity

        order = Order.objects.create(
            customer=customer,
            delivery_name=delivery_name,
            delivery_phone=delivery_phone,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_pincode=delivery_pincode,
            total_amount=total,
            payment_status="Paid",
            order_status="Placed"
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price
        )

        del request.session["buy_now"]
        return JsonResponse({"success": True})

    # 🛒 CART FLOW
    cart = Cart.objects.filter(customer=customer).first()
    if not cart or not cart.items.exists():
        return JsonResponse({"error": "Cart empty"}, status=400)

    total = sum(i.subtotal() for i in cart.items.all())

    order = Order.objects.create(
        customer=customer,
        delivery_name=delivery_name,
        delivery_phone=delivery_phone,
        delivery_address=delivery_address,
        delivery_city=delivery_city,
        delivery_pincode=delivery_pincode,
        total_amount=total,
        payment_status="Paid",
        order_status="Placed"
    )

    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

    cart.items.all().delete()
    return JsonResponse({"success": True})




def success(request):
    return render(request, "success.html")



def profile(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.method == "POST":
        customer.city = request.POST.get('city')
        customer.pincode = request.POST.get('pincode')
        customer.save()
        return redirect('profile')

    return render(request, 'nav_pro.html', {
        'customer': customer
    })


def account(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.method == "POST":
        name = request.POST.get('name')

        request.session['display_name'] = name
        customer.name = name          # ✅ NAME DB SAVE
        customer.phone = request.POST.get('phone')
        customer.city = request.POST.get('city')
        customer.pincode = request.POST.get('pincode')
        customer.save()

        return redirect('nav_address')

    # ✅ THIS LINE WAS MISSING
    return render(request, 'profile.html', {
        'customer': customer
    })



def nav_address(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    return render(request, 'address.html', {
        'customer': customer
    })


def saved_Details(request):
    return render(request, 'rating.html')

def contacts(request):
    return render(request, 'contactus.html')

def prime(request):
    return render(request, 'prime.html')

def payment(request):
    return render(request, 'payment.html')

def rating(request):
    return render(request, 'rating.html')

def edit_name(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.method == "POST":
        name = request.POST.get('name')

        if name:
            customer.name = name
            customer.save()
            request.session['display_name'] = name

        return redirect('profile')

    return render(request, 'edit-name.html', {
        'customer': customer
    })

from django.shortcuts import render, redirect
from django.contrib import messages

def edit_email(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.method == "POST":
        email = request.POST.get('email')  # ✅ CORRECT KEY

        if not email:
            messages.error(request, "Email cannot be empty")
            return redirect('edit_email')

        # ✅ SAVE TO DB
        customer.email = email
        customer.save()

        # ✅ SAVE TO SESSION (optional)
        request.session['display_email'] = email

        return redirect('profile')



    return render(request, 'edit-email.html', {
        'customer': customer
    })

def edit_number(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.method == "POST":
        phone = request.POST.get('phone')

        if phone:
            customer.phone = phone
            customer.save()

        return redirect('profile')

    return render(request, 'edit-number.html', {
        'customer': customer
    })

def login_security(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    return render(request, 'login-security.html', {
        'customer': customer
    })

def edit_address(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    if request.method == "POST":
        # ❌ DO NOT TOUCH NAME / PHONE
        customer.address = request.POST.get('address')
        customer.city = request.POST.get('city')
        customer.pincode = request.POST.get('pincode')
        customer.save()

        next_page = request.GET.get('next')
        if next_page == 'checkout':
            return redirect('checkout')

        return redirect('nav_address')

    return render(request, 'edit_address.html', {
        'customer': customer
    })

def remove_address(request):
    customer = get_customer(request)
    if not customer:
        return redirect('hello')

    # Clear address details
    customer.address = ""
    customer.city = ""
    customer.pincode = ""
    customer.phone = ""
    customer.save()

    return redirect('nav_address')

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@csrf_exempt
def create_razorpay_order(request):
    amount = int(request.POST.get("amount"))

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })

    return JsonResponse({
        "key": settings.RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": order["amount"]
    })

@csrf_exempt
def payment_success(request):
    return JsonResponse({"status": "Payment Successful"})

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Order

@require_POST
def cancel_order(request, order_id):
    customer = get_customer(request)
    if not customer:
        return JsonResponse({"error": "Login required"}, status=401)

    order = get_object_or_404(Order, id=order_id, customer=customer)

    if order.order_status in ["Shipped", "Delivered"]:
        return JsonResponse({
            "error": "Order cannot be cancelled now"
        }, status=400)

    order.order_status = "Cancelled"
    order.save()

    return JsonResponse({
        "success": True,
        "status": "Cancelled"
    })
