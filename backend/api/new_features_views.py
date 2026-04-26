"""
new_features_views.py — Additional API endpoints for new features
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Category, CustomRequest, Order, Product, UserProfile


# ===========================================================================
# SERIALIZERS
# ===========================================================================

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'product_count', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_product_count(self, obj):
        return obj.products.count()


class ProductWithCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    category_id = serializers.IntegerField(source='category.id', read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'description', 'image', 'stock', 
                  'category', 'category_name', 'category_id', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'phone', 'address', 'profile_picture', 'created_at', 'updated_at')
        read_only_fields = ('id', 'username', 'email', 'created_at', 'updated_at')


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Public order tracking serializer with limited info"""
    items = serializers.SerializerMethodField()
    status_timeline = serializers.SerializerMethodField()
    estimated_delivery_date = serializers.DateField(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'tracking_id', 'status', 'total_price', 'items', 
                  'created_at', 'updated_at', 'status_timeline', 'estimated_delivery_date')
        read_only_fields = ('id', 'tracking_id', 'status', 'total_price', 'items', 
                            'created_at', 'updated_at', 'status_timeline', 'estimated_delivery_date')

    def get_items(self, obj):
        items = obj.get_items()
        # Ensure consistent field names for frontend
        for item in items:
            if 'product_name' in item and 'name' not in item:
                item['name'] = item['product_name']
            if 'price' not in item and 'product_price' in item:
                item['price'] = item['product_price']
        return items

    def get_status_timeline(self, obj):
        """Generate status timeline based on order status"""
        timeline = [
            {'status': 'pending', 'label': 'Order Placed', 'completed': True, 'date': obj.created_at.isoformat()},
            {'status': 'processing', 'label': 'Processing', 'completed': obj.status in ['processing', 'shipped', 'delivered'], 'date': None},
            {'status': 'shipped', 'label': 'Shipped', 'completed': obj.status in ['shipped', 'delivered'], 'date': None},
            {'status': 'delivered', 'label': 'Delivered', 'completed': obj.status == 'delivered', 'date': None},
        ]
        
        if obj.status == 'cancelled':
            timeline = [
                {'status': 'pending', 'label': 'Order Placed', 'completed': True, 'date': obj.created_at.isoformat()},
                {'status': 'cancelled', 'label': 'Cancelled', 'completed': True, 'date': obj.updated_at.isoformat()},
            ]
        elif obj.status == 'cancel_requested':
            timeline = [
                {'status': 'pending', 'label': 'Order Placed', 'completed': True, 'date': obj.created_at.isoformat()},
                {'status': 'cancel_requested', 'label': 'Cancellation Requested', 'completed': True, 'date': obj.updated_at.isoformat()},
            ]
        
        return timeline


# ===========================================================================
# CATEGORY VIEWS
# ===========================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def categories(request):
    """
    GET  /api/categories/ — public, list all categories
    POST /api/categories/ — admin only, create category
    """
    if request.method == 'GET':
        cats = Category.objects.all().order_by('name')
        return Response({'categories': CategorySerializer(cats, many=True).data})

    # POST - admin only
    if not (request.user and request.user.is_authenticated and request.user.is_superuser):
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = CategorySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    category = serializer.save()
    return Response({'message': 'Category created.', 'category': CategorySerializer(category).data},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def products_with_filters(request):
    """
    GET /api/products/filter/
    Query params:
      - category: category ID
      - min_price: minimum price
      - max_price: maximum price
      - search: search term (name or description)
      - in_stock: true/false
    """
    qs = Product.objects.all()

    # Category filter
    category_id = request.query_params.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    # Price range filter
    min_price = request.query_params.get('min_price')
    max_price = request.query_params.get('max_price')
    if min_price:
        try:
            qs = qs.filter(price__gte=Decimal(min_price))
        except:
            pass
    if max_price:
        try:
            qs = qs.filter(price__lte=Decimal(max_price))
        except:
            pass

    # Search filter
    search = request.query_params.get('search', '').strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    # Stock filter
    in_stock = request.query_params.get('in_stock')
    if in_stock and in_stock.lower() == 'true':
        qs = qs.filter(stock__gt=0)

    qs = qs.order_by('-created_at')
    return Response({'products': ProductWithCategorySerializer(qs, many=True).data})


# ===========================================================================
# ORDER TRACKING (PUBLIC)
# ===========================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def track_order(request, tracking_id):
    """
    GET /api/track/<tracking_id>/
    Public endpoint - no auth required
    Track order using unique tracking ID (case-insensitive)
    """
    try:
        # Convert to uppercase for case-insensitive lookup
        tracking_id = tracking_id.upper().strip()
        order = Order.objects.get(tracking_id=tracking_id)
        return Response({'order': OrderTrackingSerializer(order).data})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found. Please check your tracking ID.'},
                        status=status.HTTP_404_NOT_FOUND)


# ===========================================================================
# USER PROFILE VIEWS
# ===========================================================================

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    GET   /api/profile/ — get user profile
    PATCH /api/profile/ — update user profile
    """
    user = request.user
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'GET':
        return Response({'profile': UserProfileSerializer(profile).data})

    # PATCH - update profile
    data = request.data

    # Update User model fields
    if 'username' in data:
        username = data['username'].strip()
        if username != user.username:
            if User.objects.filter(username__iexact=username).exclude(id=user.id).exists():
                return Response({'error': 'This username is already taken.'},
                                status=status.HTTP_400_BAD_REQUEST)
            user.username = username
    if 'first_name' in data:
        user.first_name = data['first_name'].strip()
    if 'last_name' in data:
        user.last_name = data['last_name'].strip()
    if 'email' in data:
        email = data['email'].strip().lower()
        if email != user.email:
            # Check if email already exists
            if User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                return Response({'error': 'This email is already in use.'},
                                status=status.HTTP_400_BAD_REQUEST)
            user.email = email

    user.save()

    # Update UserProfile fields
    if 'phone' in data:
        profile.phone = data['phone'].strip()
    if 'address' in data:
        profile.address = data['address'].strip()
    if 'profile_picture' in data:
        profile.profile_picture = data['profile_picture'].strip()

    profile.save()

    return Response({
        'message': 'Profile updated successfully.',
        'profile': UserProfileSerializer(profile).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    POST /api/profile/change-password/
    Body: { "current_password": "...", "new_password": "..." }
    """
    user = request.user
    current_password = request.data.get('current_password', '').strip()
    new_password = request.data.get('new_password', '').strip()

    if not current_password or not new_password:
        return Response({'error': 'Both current and new passwords are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not user.check_password(current_password):
        return Response({'error': 'Current password is incorrect.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if len(new_password) < 8:
        return Response({'error': 'New password must be at least 8 characters.'},
                        status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    update_session_auth_hash(request, user)  # Keep user logged in

    return Response({'message': 'Password changed successfully.'})


# ===========================================================================
# ORDER CANCELLATION
# ===========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """
    POST /api/orders/<order_id>/cancel/
    Request cancellation with reason - requires admin approval
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.status not in ['pending', 'processing']:
        return Response({'error': 'Only pending or processing orders can be cancelled.'},
                        status=status.HTTP_400_BAD_REQUEST)

    cancel_reason = request.data.get('reason', '').strip()
    if not cancel_reason:
        return Response({'error': 'Cancellation reason is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    order.status = 'cancel_requested'
    order.cancel_reason = cancel_reason
    order.save()

    _send_cancel_request_email(order)

    return Response({'message': 'Cancellation request submitted. Waiting for admin approval.'})


# ===========================================================================
# ADMIN APPROVE/REJECT CANCELLATION
# ===========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_cancel_order(request, order_id):
    """
    POST /api/admin/orders/<order_id>/approve-cancel/
    Admin approves cancellation request
    """
    if not request.user.is_superuser:
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.status != 'cancel_requested':
        return Response({'error': 'No pending cancellation request for this order.'},
                        status=status.HTTP_400_BAD_REQUEST)

    order.status = 'cancelled'
    order.save()

    _send_cancellation_email(order)

    return Response({'message': 'Cancellation approved.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_cancel_order(request, order_id):
    """
    POST /api/admin/orders/<order_id>/reject-cancel/
    Admin rejects cancellation request
    """
    if not request.user.is_superuser:
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.status != 'cancel_requested':
        return Response({'error': 'No pending cancellation request for this order.'},
                        status=status.HTTP_400_BAD_REQUEST)

    order.status = 'processing'
    order.save()

    _send_cancel_rejection_email(order)

    return Response({'message': 'Cancellation request rejected.'})


# ===========================================================================
# ADMIN REVENUE CHART
# ===========================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_revenue_chart(request):
    """
    GET /api/admin/revenue-chart/
    Query params:
      - period: 'daily', 'weekly', 'monthly' (default: 'daily')
      - days: number of days to show (default: 30)
    """
    if not request.user.is_superuser:
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    period = request.query_params.get('period', 'daily')
    try:
        days = int(request.query_params.get('days', 30))
    except:
        days = 30

    # Get orders from last N days
    from django.utils import timezone
    start_date = timezone.now() - timedelta(days=days)
    orders = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['processing', 'shipped', 'delivered']  # Only count completed orders
    )

    if period == 'daily':
        # Group by day
        chart_data = orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total_price'),
            count=Count('id')
        ).order_by('date')

        labels = [item['date'].strftime('%Y-%m-%d') for item in chart_data]
        revenues = [float(item['revenue']) for item in chart_data]
        counts = [item['count'] for item in chart_data]

    elif period == 'weekly':
        # Group by week
        weekly_data = {}
        for order in orders:
            week_start = order.created_at.date() - timedelta(days=order.created_at.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            if week_key not in weekly_data:
                weekly_data[week_key] = {'revenue': 0, 'count': 0}
            weekly_data[week_key]['revenue'] += float(order.total_price)
            weekly_data[week_key]['count'] += 1

        labels = sorted(weekly_data.keys())
        revenues = [weekly_data[label]['revenue'] for label in labels]
        counts = [weekly_data[label]['count'] for label in labels]

    elif period == 'monthly':
        # Group by month
        monthly_data = {}
        for order in orders:
            month_key = order.created_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'revenue': 0, 'count': 0}
            monthly_data[month_key]['revenue'] += float(order.total_price)
            monthly_data[month_key]['count'] += 1

        labels = sorted(monthly_data.keys())
        revenues = [monthly_data[label]['revenue'] for label in labels]
        counts = [monthly_data[label]['count'] for label in labels]

    else:
        return Response({'error': 'Invalid period. Use daily, weekly, or monthly.'},
                        status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'labels': labels,
        'revenues': revenues,
        'order_counts': counts,
        'total_revenue': sum(revenues),
        'total_orders': sum(counts),
        'period': period
    })


# ===========================================================================
# PHONE VALIDATION HELPER
# ===========================================================================

def validate_phone_number(phone):
    """
    Validate Philippine phone number format
    Accepts: +639XXXXXXXXX, 09XXXXXXXXX, 9XXXXXXXXX
    """
    phone = phone.strip().replace(' ', '').replace('-', '')
    
    # Pattern for Philippine numbers
    patterns = [
        r'^\+639\d{9}$',      # +639XXXXXXXXX
        r'^09\d{9}$',         # 09XXXXXXXXX
        r'^9\d{9}$',          # 9XXXXXXXXX
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone):
            return True
    
    return False


# ===========================================================================
# EMAIL HELPERS
# ===========================================================================

def _send_cancel_request_email(order):
    """Send email notification when cancellation is requested"""
    if not order.user.email:
        return

    try:
        name = order.user.first_name or order.user.username
        subject = f'[Print X] Cancellation Request for Order #{order.id}'

        text_body = f"""Hi {name},

Your cancellation request for order #{order.id} has been submitted.

Reason: {order.cancel_reason}

Our team will review your request and notify you once it's processed.

Order Details:
- Order ID: #{order.id}
- Tracking ID: {order.tracking_id}
- Total: ₱{float(order.total_price):.2f}

-- The Print X Team
"""

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">CANCELLATION REQUEST</div>
</td></tr>
<tr><td style="background:#f59e0b;padding:20px 32px;text-align:center">
  <div style="font-size:22px;font-weight:900;color:#fff">Request Submitted</div>
  <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px">Order #{order.id}</div>
</td></tr>
<tr><td style="padding:28px 32px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">
    Your cancellation request has been submitted. Our team will review it and notify you once processed.
  </p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Order ID</td>
          <td style="padding:6px 0;font-weight:700;text-align:right">#{order.id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Tracking ID</td>
          <td style="padding:6px 0;font-weight:600;font-family:monospace;text-align:right">{order.tracking_id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Reason</td>
          <td style="padding:6px 0;text-align:right">{order.cancel_reason}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Total</td>
          <td style="padding:6px 0;font-weight:700;color:#ef4444;text-align:right">₱{float(order.total_price):.2f}</td></tr>
    </table>
  </div>
</td></tr>
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Questions? Contact us at <strong style="color:#ef4444">3dprintxcontact@gmail.com</strong>
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
        msg.send(fail_silently=True)

    except Exception as e:
        print(f"Failed to send cancel request email: {e}")


def _send_cancel_rejection_email(order):
    """Send email notification when cancellation is rejected"""
    if not order.user.email:
        return

    try:
        name = order.user.first_name or order.user.username
        subject = f'[Print X] Cancellation Request Rejected - Order #{order.id}'

        text_body = f"""Hi {name},

Your cancellation request for order #{order.id} has been reviewed and rejected.

Your order is being processed and will be shipped soon.

Order Details:
- Order ID: #{order.id}
- Tracking ID: {order.tracking_id}
- Total: ₱{float(order.total_price):.2f}

If you have concerns, please contact us.

-- The Print X Team
"""

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">CANCELLATION REJECTED</div>
</td></tr>
<tr><td style="background:#3b82f6;padding:20px 32px;text-align:center">
  <div style="font-size:22px;font-weight:900;color:#fff">Request Rejected</div>
  <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px">Order #{order.id}</div>
</td></tr>
<tr><td style="padding:28px 32px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">
    Your cancellation request has been reviewed and rejected. Your order is being processed and will be shipped soon.
  </p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Order ID</td>
          <td style="padding:6px 0;font-weight:700;text-align:right">#{order.id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Tracking ID</td>
          <td style="padding:6px 0;font-weight:600;font-family:monospace;text-align:right">{order.tracking_id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Total</td>
          <td style="padding:6px 0;font-weight:700;color:#ef4444;text-align:right">₱{float(order.total_price):.2f}</td></tr>
    </table>
  </div>
</td></tr>
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Questions? Contact us at <strong style="color:#ef4444">3dprintxcontact@gmail.com</strong>
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
        msg.send(fail_silently=True)

    except Exception as e:
        print(f"Failed to send cancel rejection email: {e}")


def _send_cancellation_email(order):
    """Send email notification when order is cancelled (async)"""
    if not order.user.email:
        return

    try:
        from .email_utils import send_email_async

        name = order.user.first_name or order.user.username
        subject = f'[Print X] Order #{order.id} Cancelled'

        text_body = f"""Hi {name},

Your order #{order.id} has been cancelled.

Reason: {order.cancel_reason or 'No reason provided'}

If you did not request this cancellation, please contact us immediately.

Order Details:
- Order ID: #{order.id}
- Tracking ID: {order.tracking_id}
- Total: ₱{float(order.total_price):.2f}

-- The Print X Team
"""

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">ORDER CANCELLATION</div>
</td></tr>
<tr><td style="background:#dc2626;padding:20px 32px;text-align:center">
  <div style="font-size:22px;font-weight:900;color:#fff">✕ Order Cancelled</div>
  <div style="font-size:13px;color:rgba(255,255,255,.85);margin-top:6px">Order #{order.id}</div>
</td></tr>
<tr><td style="padding:28px 32px 16px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">
    Your order has been cancelled. If you did not request this, please contact us immediately.
  </p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Order ID</td>
          <td style="padding:6px 0;font-weight:700;text-align:right">#{order.id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Tracking ID</td>
          <td style="padding:6px 0;font-weight:600;font-family:monospace;text-align:right">{order.tracking_id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Total</td>
          <td style="padding:6px 0;font-weight:700;color:#dc2626;text-align:right">₱{float(order.total_price):.2f}</td></tr>
    </table>
  </div>
</td></tr>
{'<tr><td style="padding:0 32px 20px"><div style="background:#fee2e2;border-radius:8px;padding:16px;border:1px solid #fecaca"><div style="font-size:13px;font-weight:700;color:#991b1b;margin-bottom:8px">Cancellation Reason:</div><div style="font-size:14px;color:#7f1d1d;line-height:1.6">' + (order.cancel_reason or 'No reason provided') + '</div></div></td></tr>' if order.cancel_reason else ''}
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Questions? Contact us at <strong style="color:#ef4444">3dprintxcontact@gmail.com</strong>
  </p>
</td></tr>
</table></td></tr></table>
</body></html>"""

        # Send email asynchronously (non-blocking)
        send_email_async(subject, text_body, html_body, order.user.email)

    except Exception as e:
        print(f"Failed to send cancellation email: {e}")


def send_custom_request_email(custom_request, status_change):
    """Send email notification for custom request status changes"""
    if not custom_request.user.email:
        return

    STATUS_MESSAGES = {
        'approved': 'Great news! Your custom request has been approved.',
        'cancelled': 'Your custom request has been cancelled.',
        'completed': 'Your custom order has been completed!',
    }

    if status_change not in STATUS_MESSAGES:
        return

    try:
        name = custom_request.user.first_name or custom_request.user.username
        subject = f'[Print X] Custom Request #{custom_request.id} - {status_change.title()}'
        message = STATUS_MESSAGES[status_change]

        text_body = f"""Hi {name},

{message}

Custom Request Details:
- Request ID: #{custom_request.id}
- File: {custom_request.file_name}
- Status: {custom_request.status.upper()}
- Estimated Price: ₱{float(custom_request.estimated_price):.2f}

-- The Print X Team
"""

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:12px;overflow:hidden">
<tr><td style="background:#111827;padding:28px 32px;text-align:center">
  <div style="font-size:22px;color:#fff;letter-spacing:2px;font-weight:900">PRINT X</div>
  <div style="font-size:12px;color:rgba(255,255,255,.5);margin-top:4px">CUSTOM REQUEST UPDATE</div>
</td></tr>
<tr><td style="padding:28px 32px">
  <p style="font-size:16px;color:#111827;margin:0 0 10px">Hi <strong>{name}</strong>,</p>
  <p style="font-size:14px;color:#4b5563;line-height:1.7;margin:0">{message}</p>
</td></tr>
<tr><td style="padding:0 32px 20px">
  <div style="background:#f9fafb;border-radius:8px;padding:20px;border:1px solid #e5e7eb">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Request ID</td>
          <td style="padding:6px 0;font-weight:700;text-align:right">#{custom_request.id}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">File</td>
          <td style="padding:6px 0;font-weight:600;text-align:right">{custom_request.file_name}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Status</td>
          <td style="padding:6px 0;font-weight:700;text-align:right">{custom_request.status.upper()}</td></tr>
      <tr><td style="padding:6px 0;color:#6b7280;font-size:14px">Estimated Price</td>
          <td style="padding:6px 0;font-weight:700;color:#ef4444;text-align:right">₱{float(custom_request.estimated_price):.2f}</td></tr>
    </table>
  </div>
</td></tr>
<tr><td style="background:#111827;padding:24px 32px;text-align:center">
  <p style="color:rgba(255,255,255,.5);font-size:12px;margin:0">
    Thank you for choosing <strong style="color:#ef4444">Print X</strong>
  </p>
</td></tr>
</table></td></tr></table>
</body></html>"""

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[custom_request.user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)

    except Exception as e:
        print(f"Failed to send custom request email: {e}")
