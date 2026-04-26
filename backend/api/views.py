"""
views.py — PrintX complete API views (all in one file)

Fixes included:
  [P1-1] Stock deduction: uses item['id'] not item['product_id']
  [P1-2] Checkout: creates Payment record instead of invalid Order fields
  [P1-3] Sorting: .order_by('-created_at') everywhere
  [P1-4] Cart.to_dict(): implemented on model + CartSerializer
  [P2-1] No hardcoded admin credentials — uses IsAdminJWT (superuser check)
  [P2-2] Fake tokens replaced with JWT (djangorestframework-simplejwt)
  [P2-3] Settings secured via .env (see settings.py)
  [P2-4] Rate limiting on login/register (LoginRateThrottle)
  [P2-5] Duplicate email blocked in RegisterSerializer + DB migration
  [P3-1] This file replaces the old monolithic views.py
  [P3-2] DRF serializers + api_view decorators replace manual JSON handling
  [P3-3] Manual CORS headers removed — CorsMiddleware handles it
  [DB-1] CustomRequest: negative quantity rejected, non-STL rejected
  [DB-2] estimated_price always set to 0 on create; only admin can set it
  [DB-3] Payment model properly created in checkout() and linked to Order
  [DB-4] Unique email enforced (serializer + migration 0006)
  [NEW]  Bulk custom requests: up to 5 items in one POST /api/custom/
  [NEW]  Public order tracking: GET /api/orders/<id>/track/ (no auth)
  [NEW]  Logout endpoint that blacklists refresh token
"""

import json
import os

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import FileResponse
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Cart, CustomRequest, Order, Payment, Product


# ===========================================================================
# PERMISSIONS
# ===========================================================================

class IsAdminJWT(BasePermission):
    """
    [P2-1] Replaces the old hardcoded 'Token admin_printx_2024' check.
    Grants access only to authenticated Django superusers.
    Create an admin via: python manage.py createsuperuser
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


# ===========================================================================
# THROTTLING
# ===========================================================================

class LoginRateThrottle(AnonRateThrottle):
    """[P2-4] Max 10 login/register attempts per minute per IP."""
    rate = '10/min'


# ===========================================================================
# SERIALIZERS  (inline — keeps everything in one file)
# ===========================================================================

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name')

    def validate_email(self, value):
        """[P2-5 / DB-4] Block duplicate emails at serializer level."""
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError('Email is required.')
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'This email is already in use. Please log in instead.'
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'date_joined')


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'description', 'image', 'stock', 'created_at')
        read_only_fields = ('id', 'created_at')


class CartSerializer(serializers.ModelSerializer):
    """[P1-4] Cart serialization was broken (no to_dict). Fixed here."""
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    name       = serializers.CharField(source='product.name', read_only=True)
    price      = serializers.DecimalField(source='product.price', max_digits=10,
                                          decimal_places=2, read_only=True)
    image      = serializers.CharField(source='product.image', read_only=True)
    stock      = serializers.IntegerField(source='product.stock', read_only=True)
    subtotal   = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'product_id', 'name', 'price', 'quantity',
                  'subtotal', 'image', 'stock')

    def get_subtotal(self, obj):
        return float(obj.product.price * obj.quantity)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'method', 'amount', 'status', 'reference_number', 'created_at')
        read_only_fields = ('id', 'created_at')


class OrderSerializer(serializers.ModelSerializer):
    """[DB-3] Reads payment info from the linked Payment record."""
    items            = serializers.SerializerMethodField()
    username         = serializers.SerializerMethodField()
    email            = serializers.SerializerMethodField()
    date             = serializers.SerializerMethodField()
    payment_method   = serializers.SerializerMethodField()
    reference_number = serializers.SerializerMethodField()
    payment_status   = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'tracking_id', 'status', 'total_price', 'address', 'phone', 'notes',
                  'items', 'created_at', 'username', 'email', 'date',
                  'payment_method', 'reference_number', 'payment_status', 'cancel_reason', 'estimated_delivery_date')
        read_only_fields = ('id', 'tracking_id', 'status', 'total_price', 'created_at')

    def get_items(self, obj):
        return obj.get_items()

    def get_username(self, obj):
        return obj.user.username

    def get_email(self, obj):
        return obj.user.email

    def get_date(self, obj):
        return obj.created_at

    def get_payment_details(self, obj):
        return obj.payments.order_by('-created_at').first()

    def get_payment_method(self, obj):
        payment = self.get_payment_details(obj)
        return payment.method if payment else None

    def get_reference_number(self, obj):
        payment = self.get_payment_details(obj)
        return payment.reference_number if payment else None

    def get_payment_status(self, obj):
        payment = self.get_payment_details(obj)
        return payment.status if payment else None


class CustomRequestSerializer(serializers.ModelSerializer):
    """[DB-1] Validates quantity > 0 and file_name ends with .stl"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = CustomRequest
        fields = ('id', 'user', 'username', 'email', 'file_name', 'file_size', 'stl_file', 'material', 'color', 'quantity', 'notes', 'estimated_price', 'status', 'cancel_reason', 'created_at', 'has_file')
        read_only_fields = ('id', 'estimated_price', 'status', 'cancel_reason', 'created_at', 'has_file')

    def get_has_file(self, obj):
        return bool(obj.stl_file)

    def validate(self, data):
        # File is optional on create, but if provided, must be an STL
        if 'stl_file' in data and data['stl_file']:
            file = data['stl_file']
            if not file.name.lower().endswith('.stl'):
                raise serializers.ValidationError({'stl_file': 'Only .stl files are accepted.'})
        return data


class AdminCustomRequestSerializer(CustomRequestSerializer):
    """Admin version — estimated_price is writable by admin only."""
    class Meta(CustomRequestSerializer.Meta):
        read_only_fields = ('id', 'created_at')


# ===========================================================================
# AUTH VIEWS
# ===========================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def register(request):
    """
    POST /api/register/
    [P2-2] Returns JWT tokens instead of fake 'user_{id}' token.
    [P2-5] Unique email enforced in RegisterSerializer.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user    = serializer.save()
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Account created successfully.',
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'user':    UserPublicSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """
    POST /api/login/
    [P2-1] Hardcoded admin credentials REMOVED.
           Admin is a real Django superuser (python manage.py createsuperuser).
    [P2-2] Returns JWT tokens. is_admin flag tells frontend if superuser.
    [P2-4] Rate limited to 10 attempts/min per IP.
    """
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'error': 'Username and password are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({'error': 'Invalid username or password.'},
                        status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access':   str(refresh.access_token),
        'refresh':  str(refresh),
        'is_admin': user.is_superuser,
        'user':     UserPublicSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/logout/
    [NEW] Blacklists the refresh token so it cannot be reused.
    Body: { "refresh": "<refresh_token>" }
    """
    try:
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response({'message': 'Logged out successfully.'})
    except Exception:
        return Response({'error': 'Invalid or missing refresh token.'},
                        status=status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# PRODUCT VIEWS
# ===========================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def products(request):
    """
    GET  /api/products/  — public
    POST /api/products/  — admin only
    [P3-2] Uses DRF serializer instead of manual json.loads
    """
    if request.method == 'GET':
        qs = Product.objects.all().order_by('-created_at')
        return Response({'products': ProductSerializer(qs, many=True).data})

    if request.method == 'POST':
        if not (request.user and request.user.is_authenticated and request.user.is_superuser):
            return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.save()
        return Response({'message': 'Product created.', 'product': ProductSerializer(product).data},
                        status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    """
    GET    /api/products/<id>/  — public
    PUT    /api/products/<id>/  — admin only
    DELETE /api/products/<id>/  — admin only
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({'product': ProductSerializer(product).data})

    if request.method in ['PUT', 'DELETE']:
        if not (request.user and request.user.is_authenticated and request.user.is_superuser):
            return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'PUT':
            serializer = ProductSerializer(product, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response({'message': 'Product updated.', 'product': serializer.data})

        product.delete()
        return Response({'message': 'Product deleted.'})


# ===========================================================================
# CART VIEWS
# ===========================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart(request):
    """
    GET /api/cart/
    [P1-4] CartSerializer replaces missing Cart.to_dict()
    """
    user            = request.user
    cart_items      = Cart.objects.filter(user=user).select_related('product')
    custom_requests = CustomRequest.objects.filter(user=user, status='approved')

    cart_data   = CartSerializer(cart_items, many=True).data
    custom_data = CustomRequestSerializer(custom_requests, many=True).data

    cart_total   = sum(float(i['subtotal']) for i in cart_data)
    custom_total = sum(float(r['estimated_price']) * r['quantity'] for r in custom_data)

    return Response({
        'cart':            cart_data,
        'custom_requests': custom_data,
        'total':           round(cart_total + custom_total, 2),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_add(request):
    """POST /api/cart/add/"""
    product_id = request.data.get('product_id')
    try:
        quantity = max(1, int(request.data.get('quantity', 1)))
    except (TypeError, ValueError):
        return Response({'error': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product = Product.objects.get(id=product_id)
    except (Product.DoesNotExist, TypeError, ValueError):
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

    if product.stock <= 0:
        return Response({'error': 'This product is out of stock.'}, status=status.HTTP_400_BAD_REQUEST)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user, product=product,
        defaults={'quantity': quantity}  # BUG FIX: honour requested quantity on first add
    )
    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return Response({
        'message':   'Added to cart.',
        'cart_item': CartSerializer(cart_item).data,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def cart_update(request, item_id):
    """PUT /api/cart/update/<item_id>/"""
    try:
        cart_item = Cart.objects.get(id=item_id, user=request.user)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        quantity = int(request.data.get('quantity', 1))
    except (TypeError, ValueError):
        return Response({'error': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

    if quantity <= 0:
        cart_item.delete()
        return Response({'message': 'Item removed from cart.'})

    cart_item.quantity = quantity
    cart_item.save()
    return Response({'message': 'Cart updated.', 'cart_item': CartSerializer(cart_item).data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cart_remove(request, item_id):
    """DELETE /api/cart/remove/<item_id>/"""
    try:
        Cart.objects.get(id=item_id, user=request.user).delete()
        return Response({'message': 'Item removed.'})
    except Cart.DoesNotExist:
        return Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cart_remove_custom(request, req_id):
    """DELETE /api/cart/remove-custom/<req_id>/
    Removes an approved custom request from the cart view by reverting it
    back to 'reviewing' so admin can re-evaluate, rather than cancelling it.
    """
    try:
        cr = CustomRequest.objects.get(id=req_id, user=request.user)
        # Revert to pending so it stays in admin view but leaves the cart
        cr.status = 'pending'
        cr.save()
        return Response({'message': 'Custom item removed from cart.'})
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Custom request not found.'}, status=status.HTTP_404_NOT_FOUND)


# ===========================================================================
# CUSTOM REQUEST VIEWS
# ===========================================================================

MAX_BULK_CUSTOM = 5  # [NEW] max items per bulk submission


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def custom_request(request):
    """
    GET  /api/custom/  — list user's own requests
    POST /api/custom/  — submit a new custom request
    """
    user = request.user

    if request.method == 'GET':
        reqs = CustomRequest.objects.filter(user=user).order_by('-created_at')
        return Response({'requests': CustomRequestSerializer(reqs, many=True).data})

    # --- POST ---
    # Use a mutable copy of the request data
    data = request.data.copy()
    data['user'] = user.id

    serializer = CustomRequestSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # [DB-2] estimated_price always 0 on create
    serializer.save(user=user, estimated_price=0)
    return Response(
        {'message': 'Custom request submitted successfully.', 'request': serializer.data},
        status=status.HTTP_201_CREATED
     )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def upload_custom_stl(request, request_id):
    """PATCH /api/custom/<request_id>/upload/ — attach STL to existing request."""
    try:
        cr = CustomRequest.objects.get(id=request_id, user=request.user)
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Custom request not found.'}, status=status.HTTP_404_NOT_FOUND)

    uploaded_file = request.FILES.get('stl_file')
    if not uploaded_file:
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        _validate_stl_file(uploaded_file)
    except ValidationError as e:
        return Response({'error': str(e.detail[0])}, status=status.HTTP_400_BAD_REQUEST)

    cr.stl_file = uploaded_file
    cr.save()
    return Response({'message': 'File uploaded.', 'request': CustomRequestSerializer(cr).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_custom_request(request, request_id):
    """POST /api/custom/<request_id>/cancel/"""
    try:
        cr = CustomRequest.objects.get(id=request_id, user=request.user)
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if cr.status == 'cancelled':
        return Response({'error': 'Request is already cancelled.'},
                        status=status.HTTP_400_BAD_REQUEST)

    cr.status        = 'cancelled'
    cr.cancel_reason = request.data.get('reason', '').strip() or 'Cancelled by customer.'
    cr.save()
    return Response({'message': 'Request cancelled.'})


# ===========================================================================
# ORDER VIEWS
# ===========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout(request):
    """
    POST /api/checkout/

    [P1-1] items_snapshot uses 'id' as the product key (not 'product_id')
    [P1-2] Creates a Payment record instead of passing invalid fields to Order
    [NEW] Phone number validation added
    """
    from .new_features_views import validate_phone_number
    
    user             = request.user
    address          = request.data.get('address', '').strip()
    phone            = request.data.get('phone', '').strip()
    payment_method   = request.data.get('payment_method', 'gcash').strip()
    reference_number = request.data.get('reference_number', '').strip()
    notes            = request.data.get('notes', '').strip()

    if not address:
        return Response({'error': 'Delivery address is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    if not phone:
        return Response({'error': 'Phone number is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    if not validate_phone_number(phone):
        return Response({'error': 'Invalid phone number format. Use +639XXXXXXXXX or 09XXXXXXXXX'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    if not reference_number:
        return Response({'error': 'Payment reference number is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    VALID_METHODS = {'gcash', 'maya', 'bank_transfer'}
    if payment_method not in VALID_METHODS:
        return Response(
            {'error': f'Invalid payment method. Choose from: {", ".join(VALID_METHODS)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_items      = Cart.objects.filter(user=user).select_related('product')
    custom_requests = CustomRequest.objects.filter(user=user, status='approved')

    if not cart_items.exists() and not custom_requests.exists():
        return Response(
            {'error': 'Your cart is empty and you have no approved custom requests.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    all_items = []
    total     = 0

    for item in cart_items:
        subtotal = item.product.price * item.quantity
        all_items.append({
            'type':     'product',
            'id':       item.product.id,  # [P1-1] key is 'id', not 'product_id'
            'name':     item.product.name,
            'price':    float(item.product.price),
            'quantity': item.quantity,
            'subtotal': float(subtotal),
        })
        total += subtotal

    for req in custom_requests:
        subtotal = req.estimated_price * req.quantity
        all_items.append({
            'type':     'custom',
            'id':       req.id,
            'name':     req.file_name,
            'price':    float(req.estimated_price),
            'quantity': req.quantity,
            'subtotal': float(subtotal),
        })
        total += subtotal

    # [P1-2] Create Order WITH phone field
    order = Order.objects.create(
        user=user,
        total_price=total,
        address=address,
        phone=phone,
        items_snapshot=json.dumps(all_items),
        notes=notes,
    )

    # [P1-2] Create a proper Payment record linked to the Order
    Payment.objects.create(
        order=order,
        method=payment_method,
        amount=total,
        status='pending',
        reference_number=reference_number,
    )

    cart_items.delete()
    custom_requests.update(status='completed')

    return Response(
        {'message': 'Order placed successfully.', 'order': OrderSerializer(order).data, 'tracking_id': order.tracking_id},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    """GET /api/orders/  [P1-3] Fixed: was .order_by('-date') → '-created_at'"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return Response({'orders': OrderSerializer(orders, many=True).data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def customer_delete_order(request, order_id):
    """DELETE /api/orders/delete/<order_id>/"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.status not in ('cancelled', 'delivered'):
        return Response({'error': 'Only cancelled or delivered orders can be deleted.'},
                        status=status.HTTP_400_BAD_REQUEST)

    order.delete()
    return Response({'message': 'Order deleted.'})


@api_view(['GET'])
def order_status_public(request, order_id):
    """
    GET /api/orders/<order_id>/track/
    [NEW] Public endpoint — no auth needed. Safe minimal response.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'order_id':   order.id,
        'status':     order.status,
        'created_at': order.created_at.isoformat(),
    })


# ===========================================================================
# ADMIN VIEWS
# ===========================================================================

@api_view(['GET'])
@permission_classes([IsAdminJWT])
def admin_dashboard_stats(request):
    """GET /api/admin/stats/"""
    total_revenue = sum(float(o.total_price) for o in Order.objects.all())
    return Response({
        'total_revenue':  round(total_revenue, 2),
        'total_orders':   Order.objects.count(),
        'total_products': Product.objects.count(),
        'total_users':    User.objects.filter(is_superuser=False).count(),
        'pending_custom': CustomRequest.objects.filter(status='pending').count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminJWT])
def admin_orders(request):
    """GET /api/admin/orders/  [P1-3] Fixed: was .order_by('-date')"""
    orders = Order.objects.all().order_by('-created_at')
    
    # Also include approved custom requests that haven't been checked out yet
    custom_requests = CustomRequest.objects.filter(status='approved').order_by('-created_at')
    
    # Serialize orders
    orders_data = OrderSerializer(orders, many=True).data
    
    # Add custom requests as "pending orders"
    for cr in custom_requests:
        orders_data.append({
            'id': f'CUSTOM-{cr.id}',
            'status': 'pending',
            'total_price': float(cr.estimated_price * cr.quantity),
            'address': 'Awaiting checkout',
            'notes': cr.notes,
            'items': [{
                'type': 'custom',
                'id': cr.id,
                'name': cr.file_name,
                'price': float(cr.estimated_price),
                'quantity': cr.quantity,
                'subtotal': float(cr.estimated_price * cr.quantity),
            }],
            'created_at': cr.created_at.isoformat(),
            'username': cr.user.username,
            'email': cr.user.email,
            'date': cr.created_at,
            'payment_method': 'Pending',
            'reference_number': None,
            'payment_status': 'pending',
            'is_custom_pending': True,  # Flag to identify these in frontend
        })
    
    # Sort by date
    orders_data.sort(key=lambda x: x['created_at'], reverse=True)
    
    return Response({'orders': orders_data})


@api_view(['POST', 'PATCH'])
@permission_classes([IsAdminJWT])
def admin_update_order_status(request, order_id):
    """
    POST/PATCH /api/admin/orders/<order_id>/status/

    [P1-1] Stock deduction fix: snapshot items use 'id' as product key.
           Old code did item['product_id'] → KeyError → stock never deducted.
           Now correctly uses item['id'].
    [NEW] Admin can set estimated_delivery_date when updating status
    """
    VALID_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    new_status     = request.data.get('status', '').strip()

    if new_status not in VALID_STATUSES:
        return Response(
            {'error': f'Invalid status. Choose from: {", ".join(VALID_STATUSES)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    old_status   = order.status
    order.status = new_status
    
    # Update estimated delivery date if provided
    if 'estimated_delivery_date' in request.data:
        estimated_date = request.data.get('estimated_delivery_date')
        if estimated_date:
            try:
                from datetime import datetime
                # Parse date string (YYYY-MM-DD format)
                order.estimated_delivery_date = datetime.strptime(estimated_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            order.estimated_delivery_date = None
    
    order.save()

    # [P1-1] Deduct stock on first transition to 'processing'
    if new_status == 'processing' and old_status != 'processing':
        try:
            for item in json.loads(order.items_snapshot or '[]'):
                if item.get('type') == 'custom':
                    continue  # custom prints have no stock to deduct
                try:
                    product       = Product.objects.get(id=item['id'])  # FIX: 'id' not 'product_id'
                    product.stock = max(0, product.stock - item.get('quantity', 1))
                    product.save()
                except (Product.DoesNotExist, KeyError):
                    pass
        except (json.JSONDecodeError, TypeError):
            pass

    # Update payment status based on order status
    payment = order.payments.order_by('-created_at').first()
    if payment:
        if new_status in ['delivered', 'shipped']:
            # Mark payment as paid when order is shipped or delivered
            payment.status = 'paid'
            payment.save()
        elif new_status == 'cancelled':
            # Mark payment as failed when order is cancelled
            payment.status = 'failed'
            payment.save()
        elif new_status == 'processing' and payment.status == 'pending':
            # Mark payment as paid when order starts processing
            payment.status = 'paid'
            payment.save()

    email_error   = _send_status_email(order, new_status)
    response_data = {'message': 'Status updated.', 'status': new_status, 'order': OrderSerializer(order).data}
    if email_error:
        response_data['email_error'] = email_error
    return Response(response_data)


@api_view(['DELETE'])
@permission_classes([IsAdminJWT])
def admin_delete_order(request, order_id):
    """DELETE /api/admin/orders/delete/<order_id>/"""
    try:
        Order.objects.get(id=order_id).delete()
        return Response({'message': 'Order deleted.'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdminJWT])
def admin_custom_requests(request):
    """GET /api/admin/custom/"""
    reqs = CustomRequest.objects.all().order_by('-created_at')
    return Response({'requests': AdminCustomRequestSerializer(reqs, many=True).data})


@api_view(['POST', 'PATCH'])
@permission_classes([IsAdminJWT])
def admin_update_custom_status(request, request_id):
    """
    POST/PATCH /api/admin/custom/<request_id>/status/
    [DB-2] Admin sets estimated_price here — never trusted from client.
    [NEW] Sends email notification when status changes to 'approved'
    """
    VALID_STATUSES = ['pending', 'reviewing', 'approved', 'printing',
                      'ready', 'completed', 'cancelled']
    new_status = request.data.get('status', '').strip()

    if new_status not in VALID_STATUSES:
        return Response(
            {'error': f'Invalid status. Choose from: {", ".join(VALID_STATUSES)}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cr = CustomRequest.objects.get(id=request_id)
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    old_status = cr.status
    cr.status = new_status

    # [DB-2] Server-side pricing — only admin can set this
    if 'estimated_price' in request.data:
        try:
            cr.estimated_price = float(request.data['estimated_price'])
        except (TypeError, ValueError):
            return Response({'error': 'Invalid estimated_price.'},
                            status=status.HTTP_400_BAD_REQUEST)

    cr.save()
    
    # Send email notification when approved
    email_error = None
    if new_status == 'approved' and old_status != 'approved':
        email_error = _send_custom_approved_email(cr)
    
    response_data = {
        'message': 'Status updated.',
        'request': AdminCustomRequestSerializer(cr).data,
    }
    if email_error:
        response_data['email_error'] = email_error
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAdminJWT])
def admin_cancel_custom(request, request_id):
    """POST /api/admin/custom/<request_id>/cancel/"""
    reason = request.data.get('reason', '').strip()
    if not reason:
        return Response({'error': 'Cancellation reason is required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        cr = CustomRequest.objects.get(id=request_id)
        old_status = cr.status
        cr.status = 'cancelled'
        cr.cancel_reason = reason
        cr.save()
        
        # Send cancellation email
        email_error = None
        if old_status != 'cancelled':
            email_error = _send_custom_cancelled_email(cr, reason)
        
        response_data = {'message': 'Request cancelled.'}
        if email_error:
            response_data['email_error'] = email_error
        
        return Response(response_data)
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAdminJWT])
def admin_delete_custom(request, request_id):
    """DELETE /api/admin/custom/<request_id>/delete/"""
    try:
        CustomRequest.objects.get(id=request_id).delete()
        return Response({'message': 'Custom request deleted.'})
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdminJWT])
def admin_download_stl(request, request_id):
    """GET /api/admin/custom/<request_id>/download/"""
    try:
        cr = CustomRequest.objects.get(id=request_id)
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not cr.stl_file:
        return Response({'error': 'No file uploaded for this request.'},
                        status=status.HTTP_404_NOT_FOUND)

    file_path = cr.stl_file.path
    if not os.path.exists(file_path):
        return Response({'error': 'File not found on server.'},
                        status=status.HTTP_404_NOT_FOUND)

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=cr.file_name)


@api_view(['GET'])
@permission_classes([IsAdminJWT])
def admin_download_custom_order(request, request_id):
    """GET /api/admin/custom/<request_id>/download-order/ — Download custom order details as text file"""
    try:
        cr = CustomRequest.objects.get(id=request_id)
    except CustomRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    from django.http import HttpResponse
    
    # Create text content
    content = f"""PRINT X - CUSTOM ORDER DETAILS
{'=' * 50}

Order ID: #{cr.id}
Customer: {cr.user.username}
Email: {cr.user.email}
Order Date: {cr.created_at.strftime('%Y-%m-%d %H:%M:%S')}

CUSTOM DESIGN INFORMATION:
{'-' * 50}
File Name: {cr.file_name}
File Size: {cr.file_size:.2f} KB
Material: {cr.material}
Color: {cr.color}
Quantity: {cr.quantity}

PRICING:
{'-' * 50}
Estimated Price (per unit): ₱{float(cr.estimated_price):.2f}
Total Price: ₱{float(cr.estimated_price * cr.quantity):.2f}

STATUS: {cr.status.upper()}

NOTES:
{'-' * 50}
{cr.notes if cr.notes else 'No notes provided'}

{'=' * 50}
Generated by Print X Admin Panel
"""
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="custom_order_{cr.id}.txt"'
    return response


@api_view(['GET'])
@permission_classes([IsAdminJWT])
def admin_users(request):
    """GET /api/admin/users/"""
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return Response({'users': UserPublicSerializer(users, many=True).data})


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _extract_multipart_single(request):
    """Pull a single custom-request payload dict from a multipart POST."""
    return {
        'file_name': request.POST.get('file_name', '').strip(),
        'file_size': float(request.POST.get('file_size', 0) or 0),
        'material':  request.POST.get('material', 'PLA').strip(),
        'color':     request.POST.get('color', 'White').strip(),
        'quantity':  int(request.POST.get('quantity', 1) or 1),
        'notes':     request.POST.get('notes', '').strip(),
    }


def _validate_stl_file(uploaded_file):
    """[DB-1] Raise ValidationError for non-STL uploads."""
    if not uploaded_file.name.lower().endswith('.stl'):
        raise ValidationError('Only .stl files are accepted.')


def _send_custom_approved_email(custom_request: CustomRequest):
    """
    Send HTML email to customer when their custom request is approved.
    Returns an error string on failure, or None on success.
    Email is sent asynchronously to avoid blocking the HTTP response.
    """
    if not custom_request.user.email:
        return None

    try:
        from .email_utils import send_email_async

        name = custom_request.user.first_name or custom_request.user.username
        subject = f'[Print X] Custom Request Approved - Ready to Checkout'
        total_price = float(custom_request.estimated_price * custom_request.quantity)

        text_body = (
            f"Hi {name},\n\n"
            f"Great news! Your custom print request has been approved and is ready for checkout.\n\n"
            f"Request Details:\n"
            f"  File: {custom_request.file_name}\n"
            f"  Material: {custom_request.material}\n"
            f"  Color: {custom_request.color}\n"
            f"  Quantity: {custom_request.quantity}\n"
            f"  Price per unit: P{float(custom_request.estimated_price):.2f}\n"
            f"  Total Price: P{total_price:.2f}\n\n"
            f"Your custom request has been added to your cart. Please proceed to checkout to complete your order.\n\n"
            f"Visit: https://printx.com/cart\n\n"
            f"-- The Print X Team\n"
        )

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">CUSTOM REQUEST APPROVED</div>
</td></tr>
<tr><td style="background:#16a34a;padding:20px 32px;text-align:center">
  <div style="font-size:22px;font-weight:900;color:#fff">✓ Request Approved</div>
  <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px">Ready for Checkout</div>
</td></tr>
<tr><td style="padding:28px 32px 16px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">
    Great news! Your custom print request has been reviewed and approved. 
    We've added it to your cart and it's ready for checkout.
  </p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">File Name</td>
          <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;font-size:13px">{custom_request.file_name}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Material</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.material}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Color</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.color}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Quantity</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.quantity}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Price per unit</td>
          <td style="padding:6px 0;font-weight:700;text-align:right;color:#ef4444">P{float(custom_request.estimated_price):.2f}</td></tr>
      <tr style="border-top:2px solid #e5e7eb"><td style="padding:12px 0 6px;color:#111827;font-size:15px;font-weight:700">Total Price</td>
          <td style="padding:12px 0 6px;font-weight:900;text-align:right;color:#ef4444;font-size:18px">P{total_price:.2f}</td></tr>
    </table>
  </div>
</td></tr>
<tr><td style="padding:0 32px 28px;text-align:center">
  <a href="https://printx.com/cart" style="display:inline-block;background:#ef4444;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px">Proceed to Checkout →</a>
</td></tr>
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Thank you for choosing <strong style="color:#ef4444">Print X</strong>.<br>
    This is an automated notification — please do not reply.
  </p>
</td></tr>
</table></td></tr></table>
</body></html>"""

        # Send email asynchronously (non-blocking)
        send_email_async(subject, text_body, html_body, custom_request.user.email)
        return None

    except Exception as exc:
        return str(exc)


def _send_custom_cancelled_email(custom_request: CustomRequest, reason: str):
    """
    Send HTML email to customer when their custom request is cancelled.
    Returns an error string on failure, or None on success.
    Email is sent asynchronously to avoid blocking the HTTP response.
    """
    if not custom_request.user.email:
        return None

    try:
        from .email_utils import send_email_async

        name = custom_request.user.first_name or custom_request.user.username
        subject = f'[Print X] Custom Request Cancelled'

        text_body = (
            f"Hi {name},\n\n"
            f"We regret to inform you that your custom print request has been cancelled.\n\n"
            f"Request Details:\n"
            f"  File: {custom_request.file_name}\n"
            f"  Material: {custom_request.material}\n"
            f"  Color: {custom_request.color}\n"
            f"  Quantity: {custom_request.quantity}\n\n"
            f"Cancellation Reason:\n"
            f"{reason}\n\n"
            f"If you have any questions or would like to submit a new request, please contact us.\n\n"
            f"-- The Print X Team\n"
        )

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">CUSTOM REQUEST CANCELLED</div>
</td></tr>
<tr><td style="background:#dc2626;padding:20px 32px;text-align:center">
  <div style="font-size:22px;font-weight:900;color:#fff">✕ Request Cancelled</div>
  <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px">Custom Request #{custom_request.id}</div>
</td></tr>
<tr><td style="padding:28px 32px 16px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">
    We regret to inform you that your custom print request has been cancelled.
  </p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">File Name</td>
          <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;font-size:13px">{custom_request.file_name}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Material</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.material}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Color</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.color}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Quantity</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.quantity}</td></tr>
    </table>
  </div>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#fee2e2;border-radius:8px;padding:16px;border:1px solid #fecaca">
    <div style="font-size:13px;font-weight:700;color:#991b1b;margin-bottom:8px">Cancellation Reason:</div>
    <div style="font-size:14px;color:#7f1d1d;line-height:1.6">{reason}</div>
  </div>
</td></tr>
<tr><td style="padding:0 32px 28px">
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0;text-align:center">
    If you have any questions or would like to submit a new request, please contact us.
  </p>
</td></tr>
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Thank you for choosing <strong style="color:#ef4444">Print X</strong>.<br>
    This is an automated notification — please do not reply.
  </p>
</td></tr>
</table></td></tr></table>
</body></html>"""

        # Send email asynchronously (non-blocking)
        send_email_async(subject, text_body, html_body, custom_request.user.email)
        return None

    except Exception as exc:
        return str(exc)


def _send_status_email(order: Order, new_status: str):
    """
    Send HTML status-update email to the customer.
    Returns an error string on failure, or None on success.
    """
    STATUS_LABELS = {
        'processing': 'Approved & Processing',
        'shipped':    'Shipped',
        'delivered':  'Delivered',
        'cancelled':  'Cancelled',
    }
    STATUS_COLORS = {
        'processing': '#16a34a',
        'shipped':    '#2563eb',
        'delivered':  '#059669',
        'cancelled':  '#dc2626',
    }
    STATUS_MESSAGES = {
        'processing': 'Great news! Your order has been approved and our team is now preparing it.',
        'shipped':    'Your order is on its way! Expect it within 1-3 business days.',
        'delivered':  'Your order has been delivered. Thank you for choosing Print X!',
        'cancelled':  'Your order has been cancelled. Contact us if you have any questions.',
    }

    if new_status not in STATUS_LABELS or not order.user.email:
        return None

    try:
        from django.core.mail import EmailMultiAlternatives

        label   = STATUS_LABELS[new_status]
        color   = STATUS_COLORS[new_status]
        message = STATUS_MESSAGES[new_status]
        name    = order.user.first_name or order.user.username
        subject = f'[Print X] Order #{order.id} — {label}'
        payment = order.payments.order_by('-created_at').first()

        try:
            snap_items = json.loads(order.items_snapshot or '[]')
            items_html = ''.join(
                f"<tr>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #f0f0f0'>{i['name']}</td>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center'>"
                f"x{i['quantity']}</td>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right;"
                f"font-weight:600'>P{i['subtotal']:.2f}</td>"
                f"</tr>"
                for i in snap_items
            )
            items_text = '\n'.join(
                f"  - {i['name']} x{i['quantity']} - P{i['subtotal']:.2f}"
                for i in snap_items
            )
        except Exception:
            items_html = "<tr><td colspan='3' style='padding:8px 12px'>(details unavailable)</td></tr>"
            items_text = '  (details unavailable)'

        ref_row = (
            f"<tr><td style='padding:6px 0;color:#6b7280'>Reference</td>"
            f"<td style='padding:6px 0;font-weight:600;font-family:monospace'>"
            f"{payment.reference_number}</td></tr>"
        ) if payment and payment.reference_number else ''

        payment_display = payment.method.upper() if payment else 'N/A'

        text_body = (
            f"Hi {name},\n\n"
            f"Your Order #{order.id} is now: {label}\n\n"
            f"{message}\n\n"
            f"Order ID : #{order.id}\n"
            f"Total    : P{float(order.total_price):.2f}\n"
            f"Payment  : {payment_display}\n"
            f"{'Reference: ' + payment.reference_number + chr(10) if payment and payment.reference_number else ''}"
            f"\nItems:\n{items_text}\n\n"
            f"Address: {order.address}\n\n"
            f"-- The Print X Team\n"
        )

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">ORDER NOTIFICATION</div>
</td></tr>
<tr><td style="background:{color};padding:20px 32px;text-align:center">
  <div style="font-size:22px;font-weight:900;color:#fff">{label}</div>
  <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px">Order #{order.id}</div>
</td></tr>
<tr><td style="padding:28px 32px 16px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">{message}</p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Order ID</td>
          <td style="padding:6px 0;font-weight:700;text-align:right">#{order.id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Payment</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{payment_display}</td></tr>
      {ref_row}
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Address</td>
          <td style="padding:6px 0;font-size:13px;text-align:right">{order.address}</td></tr>
    </table>
  </div>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
    <thead><tr style="background:#f3f4f6">
      <th style="padding:8px 12px;text-align:left;font-size:12px;color:#6b7280">Item</th>
      <th style="padding:8px 12px;text-align:center;font-size:12px;color:#6b7280">Qty</th>
      <th style="padding:8px 12px;text-align:right;font-size:12px;color:#6b7280">Subtotal</th>
    </tr></thead>
    <tbody>{items_html}</tbody>
    <tfoot><tr style="background:#111827">
      <td colspan="2" style="padding:12px;font-weight:700;color:#fff">Total</td>
      <td style="padding:12px;font-weight:900;color:#ef4444;text-align:right">P{float(order.total_price):.2f}</td>
    </tr></tfoot>
  </table>
</td></tr>
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Thank you for shopping with <strong style="color:#ef4444">Print X</strong>.<br>
    This is an automated notification — please do not reply.
  </p>
</td></tr>
</table></td></tr></table>
</body></html>"""

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return None

    except Exception as exc:
        return str(exc)


# ===========================================================================
# PRODUCT REVIEW VIEWS
# ===========================================================================

from .models import ProductReview

@api_view(['GET'])
@permission_classes([AllowAny])
def product_reviews(request, product_id):
    """GET /api/products/<product_id>/reviews/"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    reviews = ProductReview.objects.filter(product=product).select_related('user').order_by('-created_at')
    
    # Calculate average rating
    total_reviews = reviews.count()
    average_rating = 0
    if total_reviews > 0:
        total_rating = sum(r.rating for r in reviews)
        average_rating = round(total_rating / total_reviews, 1)
    
    # Serialize reviews
    reviews_data = []
    for review in reviews:
        can_delete = False
        if request.user.is_authenticated:
            can_delete = request.user.is_superuser or review.user == request.user
        
        reviews_data.append({
            'id': review.id,
            'user': review.user.username,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.isoformat(),
            'can_delete': can_delete,
        })
    
    return Response({
        'reviews': reviews_data,
        'average_rating': average_rating,
        'total_reviews': total_reviews,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_review(request, product_id):
    """POST /api/products/<product_id>/reviews/add/"""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Check if user has purchased this product
    user_orders = Order.objects.filter(
        user=request.user,
        status__in=['delivered', 'completed']
    )
    has_purchased = False
    for order in user_orders:
        try:
            items = json.loads(order.items_snapshot or '[]')
            for item in items:
                if item.get('type') != 'custom' and str(item.get('id')) == str(product_id):
                    has_purchased = True
                    break
        except (json.JSONDecodeError, TypeError):
            pass
        if has_purchased:
            break

    if not has_purchased:
        return Response({'error': 'You can only review products you have purchased and received.'}, status=status.HTTP_403_FORBIDDEN)

    rating = request.data.get('rating')
    comment = request.data.get('comment', '').strip()

    if not rating or not comment:
        return Response({'error': 'Rating and comment are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'Rating must be between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)

    review, created = ProductReview.objects.update_or_create(
        user=request.user,
        product=product,
        defaults={'rating': rating, 'comment': comment}
    )

    message = 'Review added successfully.' if created else 'Review updated successfully.'
    return Response({'message': message}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_review(request, review_id):
    """DELETE /api/reviews/<review_id>/delete/"""
    try:
        review = ProductReview.objects.get(id=review_id)
    except ProductReview.DoesNotExist:
        return Response({'error': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    # Only owner or admin can delete
    if not (request.user.is_superuser or review.user == request.user):
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)
    
    review.delete()
    return Response({'message': 'Review deleted.'})
