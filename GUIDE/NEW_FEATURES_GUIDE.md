# Print X E-Commerce System - New Features Implementation Guide

## Overview
This document describes all the new features added to the Print X system and how to set them up.

## New Features Implemented

### 1. Order Tracking System (Public - No Login Required)
- **Unique Tracking ID**: Each order gets a secure, non-guessable tracking ID (16 characters)
- **Public Tracking Page**: `/docs/customer/track.html`
- **API Endpoint**: `GET /api/track/<tracking_id>/`
- **Features**:
  - Track order status without logging in
  - View order timeline (Pending → Processing → Shipped → Delivered)
  - See order items and total
  - Secure tracking IDs generated using `secrets.token_urlsafe()`

### 2. Product Categories & Filtering
- **Category Model**: New `Category` model for organizing products
- **API Endpoints**:
  - `GET /api/categories/` - List all categories
  - `POST /api/categories/` - Create category (admin only)
  - `GET /api/products/filter/` - Filter products
- **Filter Options**:
  - By category
  - By price range (min_price, max_price)
  - By search term (name/description)
  - By stock availability (in_stock=true)

### 3. User Profile & Account Settings
- **Profile Page**: `/docs/customer/profile.html`
- **UserProfile Model**: Stores phone, address, profile_picture
- **API Endpoints**:
  - `GET /api/profile/` - Get user profile
  - `PATCH /api/profile/` - Update profile
  - `POST /api/profile/change-password/` - Change password
- **Features**:
  - Update personal info (name, email, phone, address)
  - Change password securely
  - Profile picture support

### 4. Phone Number Validation
- **Validation Function**: `validate_phone_number()` in `new_features_views.py`
- **Supported Formats**:
  - +639XXXXXXXXX
  - 09XXXXXXXXX
  - 9XXXXXXXXX
- **Applied At**: Checkout process
- **Error Message**: Shows clear format requirements

### 5. Order Cancellation
- **API Endpoint**: `POST /api/orders/<order_id>/cancel/`
- **Rules**: Only pending or processing orders can be cancelled
- **Email Notification**: Automatic cancellation email sent to customer
- **Frontend**: Cancel button added to orders page

### 6. Admin Revenue Chart
- **API Endpoint**: `GET /api/admin/revenue-chart/`
- **Query Parameters**:
  - `period`: daily, weekly, monthly (default: daily)
  - `days`: number of days to show (default: 30)
- **Returns**:
  - Labels (dates)
  - Revenue data
  - Order counts
  - Total revenue and orders
- **Use Case**: Display charts using Chart.js or similar library

### 7. Email Notifications
- **Order Status Changes**: Emails sent for Processing, Shipped, Delivered, Cancelled
- **Custom Request Updates**: Emails for Approved, Cancelled, Completed status
- **Order Cancellation**: Dedicated cancellation email template
- **HTML Templates**: Professional HTML email templates with Print X branding

### 8. Enhanced Order Model
- **New Fields**:
  - `tracking_id`: Unique tracking identifier (auto-generated)
  - `phone`: Customer phone number
  - `updated_at`: Last update timestamp
- **Auto-generation**: Tracking ID generated on order creation

## Database Migration

Run the following command to apply all new database changes:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

The migration file `0011_new_features.py` includes:
- Category model creation
- Product.category field
- Order.tracking_id field
- Order.phone field
- Order.updated_at field
- UserProfile model creation
- Automatic tracking ID generation for existing orders

## Setup Instructions

### 1. Backend Setup

1. **Install Dependencies** (if not already installed):
```bash
pip install -r requirements.txt
```

2. **Run Migrations**:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Create Superuser** (if not exists):
```bash
python manage.py createsuperuser
```

4. **Start Development Server**:
```bash
python manage.py runserver
```

### 2. Frontend Setup

The following new pages have been created:
- `/docs/customer/track.html` - Public order tracking
- `/docs/customer/profile.html` - User profile management

Update navigation links to include:
- Track Order link in footer
- Profile link in user menu

### 3. Email Configuration

Ensure your `settings.py` has email configuration:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'Print X <your-email@gmail.com>'
```

For Gmail, use an App Password (not your regular password).

## API Endpoints Summary

### New Endpoints

#### Categories
- `GET /api/categories/` - List categories
- `POST /api/categories/` - Create category (admin)

#### Products
- `GET /api/products/filter/?category=1&min_price=100&max_price=500&search=keychain&in_stock=true`

#### Order Tracking
- `GET /api/track/<tracking_id>/` - Public tracking (no auth)

#### Profile
- `GET /api/profile/` - Get profile
- `PATCH /api/profile/` - Update profile
- `POST /api/profile/change-password/` - Change password

#### Orders
- `POST /api/orders/<order_id>/cancel/` - Cancel order

#### Admin
- `GET /api/admin/revenue-chart/?period=daily&days=30` - Revenue data

## Testing the Features

### 1. Test Order Tracking
1. Place an order (you'll receive a tracking ID in the response)
2. Go to `/docs/customer/track.html`
3. Enter the tracking ID
4. Verify order details and timeline display

### 2. Test Profile Management
1. Login as a customer
2. Go to `/docs/customer/profile.html`
3. Update personal information
4. Change password
5. Verify changes are saved

### 3. Test Phone Validation
1. Go to checkout
2. Try invalid phone numbers (e.g., "123")
3. Verify error message appears
4. Try valid format (+639123456789)
5. Verify order is placed successfully

### 4. Test Order Cancellation
1. Place an order
2. Go to orders page
3. Click "Cancel Order" on a pending order
4. Verify status changes to "Cancelled"
5. Check email for cancellation notification

### 5. Test Product Filtering
1. Create categories in admin panel
2. Assign products to categories
3. Use filter API: `/api/products/filter/?category=1`
4. Test price range filtering
5. Test search functionality

### 6. Test Revenue Chart
1. Login as admin
2. Call `/api/admin/revenue-chart/?period=daily&days=7`
3. Verify JSON response with labels and revenue data
4. Integrate with Chart.js for visualization

## Security Features

1. **Secure Tracking IDs**: Generated using `secrets.token_urlsafe()` - cryptographically secure
2. **Phone Validation**: Regex-based validation prevents invalid data
3. **Password Change**: Requires current password verification
4. **Email Validation**: Prevents duplicate emails
5. **Order Cancellation**: Only order owner can cancel their orders
6. **Profile Updates**: Users can only update their own profile

## Frontend Integration Examples

### Track Order from Orders Page
Add this to orders page to show tracking ID:

```javascript
// In orders.html
function showTrackingId(trackingId) {
  const trackUrl = `track.html?id=${trackingId}`;
  window.open(trackUrl, '_blank');
}
```

### Display Revenue Chart (Admin)
```javascript
// In admin dashboard
async function loadRevenueChart() {
  const res = await apiFetch('/admin/revenue-chart/?period=daily&days=30');
  if (res.ok) {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: res.data.labels,
        datasets: [{
          label: 'Revenue',
          data: res.data.revenues,
          borderColor: '#e8000d',
          backgroundColor: 'rgba(232, 0, 13, 0.1)'
        }]
      }
    });
  }
}
```

### Product Filtering
```javascript
// In product.html
async function filterProducts() {
  const category = document.getElementById('categoryFilter').value;
  const minPrice = document.getElementById('minPrice').value;
  const maxPrice = document.getElementById('maxPrice').value;
  const search = document.getElementById('searchInput').value;
  
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (minPrice) params.append('min_price', minPrice);
  if (maxPrice) params.append('max_price', maxPrice);
  if (search) params.append('search', search);
  
  const res = await apiFetch(`/products/filter/?${params.toString()}`);
  if (res.ok) {
    renderProducts(res.data.products);
  }
}
```

## Troubleshooting

### Issue: Tracking ID not generated
**Solution**: Run migrations to add the tracking_id field and auto-generation logic

### Issue: Email not sending
**Solution**: Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py. For Gmail, use App Password.

### Issue: Phone validation failing
**Solution**: Ensure phone number matches one of these formats: +639XXXXXXXXX, 09XXXXXXXXX, or 9XXXXXXXXX

### Issue: Profile not loading
**Solution**: UserProfile is auto-created on first access. Ensure migrations are run.

### Issue: Revenue chart showing no data
**Solution**: Ensure there are orders with status 'processing', 'shipped', or 'delivered'

## Next Steps

1. **Add Chart.js** to admin dashboard for revenue visualization
2. **Implement product category filter** in product.html UI
3. **Add tracking ID display** in order confirmation email
4. **Create admin interface** for managing categories
5. **Add profile picture upload** functionality
6. **Implement order status notifications** via SMS (optional)

## Support

For issues or questions:
- Email: 3dprintxcontact@gmail.com
- Check Django logs: `python manage.py runserver` output
- Check browser console for frontend errors

## License

© 2024 Print X. All rights reserved.
