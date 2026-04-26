# Print X - Complete Setup Guide for New Features

## ✅ What Has Been Implemented

All requested features have been successfully implemented:

1. ✅ **Order Tracking System** - Public tracking with unique IDs
2. ✅ **Product Categories & Filtering** - Organize and filter products
3. ✅ **Email Notifications** - Automated emails for orders and custom requests
4. ✅ **User Profile Management** - Update info and change password
5. ✅ **Phone Number Validation** - Philippine format validation
6. ✅ **Order Cancellation** - Cancel pending orders
7. ✅ **Admin Revenue Chart** - Revenue analytics API
8. ✅ **Cart State Management** - Already implemented in database

## 🚀 Quick Start (Step-by-Step)

### Step 1: Fix Python 3.13 Compatibility

```bash
# Upgrade djangorestframework-simplejwt
pip install --upgrade djangorestframework-simplejwt
```

### Step 2: Create Fresh Database

```bash
cd backend

# Delete old database (if exists)
del db.sqlite3

# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Step 3: Create Admin User

```bash
python manage.py createsuperuser
# Enter username, email, and password when prompted
```

### Step 4: Start Server

```bash
python manage.py runserver
```

### Step 5: Test the Features

Open your browser and test:

1. **Main Site**: http://127.0.0.1:8000/docs/customer/index.html
2. **Track Order**: http://127.0.0.1:8000/docs/customer/track.html
3. **User Profile**: http://127.0.0.1:8000/docs/customer/profile.html
4. **Admin Panel**: http://127.0.0.1:8000/admin/

## 📋 Complete Command List

```bash
# 1. Navigate to backend directory
cd c:\Users\User\OneDrive\Desktop\refactored\backend\printxx\backend

# 2. Upgrade dependencies
pip install --upgrade djangorestframework-simplejwt

# 3. Delete old database (fresh start)
del db.sqlite3

# 4. Create migrations
python manage.py makemigrations

# 5. Apply migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Start server
python manage.py runserver
```

## 🎯 Testing Each Feature

### 1. Test Order Tracking

**Steps:**
1. Register a new user at: http://127.0.0.1:8000/docs/customer/login.html#register
2. Login and place an order
3. Note the tracking ID from the order confirmation
4. Go to: http://127.0.0.1:8000/docs/customer/track.html
5. Enter the tracking ID
6. Verify order details and timeline display

**API Test:**
```bash
# Get tracking ID from an order, then:
curl http://127.0.0.1:8000/api/track/YOUR_TRACKING_ID/
```

### 2. Test User Profile

**Steps:**
1. Login as a customer
2. Go to: http://127.0.0.1:8000/docs/customer/profile.html
3. Update your name, email, phone, address
4. Click "Save Changes"
5. Go to "Change Password" tab
6. Change your password
7. Logout and login with new password

**API Test:**
```bash
# Get profile (requires auth token)
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:8000/api/profile/
```

### 3. Test Phone Validation

**Steps:**
1. Go to checkout
2. Try entering invalid phone: "123"
3. Verify error message appears
4. Enter valid phone: "+639123456789" or "09123456789"
5. Complete checkout successfully

### 4. Test Order Cancellation

**Steps:**
1. Place an order
2. Go to: http://127.0.0.1:8000/docs/customer/orders.html
3. Find a pending order
4. Click "Cancel Order"
5. Verify status changes to "Cancelled"
6. Check your email for cancellation notification

**API Test:**
```bash
# Cancel order (requires auth token)
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://127.0.0.1:8000/api/orders/ORDER_ID/cancel/
```

### 5. Test Product Categories

**Admin Steps:**
1. Login to admin: http://127.0.0.1:8000/admin/
2. Go to "Categories"
3. Add new category: "Keychains"
4. Go to "Products"
5. Assign products to categories

**API Test:**
```bash
# Get all categories
curl http://127.0.0.1:8000/api/categories/

# Filter products by category
curl http://127.0.0.1:8000/api/products/filter/?category=1

# Filter by price range
curl http://127.0.0.1:8000/api/products/filter/?min_price=100&max_price=500

# Search products
curl http://127.0.0.1:8000/api/products/filter/?search=keychain

# Filter in-stock only
curl http://127.0.0.1:8000/api/products/filter/?in_stock=true
```

### 6. Test Revenue Chart (Admin)

**API Test:**
```bash
# Get daily revenue for last 30 days (requires admin token)
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  "http://127.0.0.1:8000/api/admin/revenue-chart/?period=daily&days=30"

# Get weekly revenue
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  "http://127.0.0.1:8000/api/admin/revenue-chart/?period=weekly&days=90"

# Get monthly revenue
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  "http://127.0.0.1:8000/api/admin/revenue-chart/?period=monthly&days=365"
```

### 7. Test Email Notifications

**Setup Email (Optional):**

Edit `backend/printx/settings.py`:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use App Password, not regular password
DEFAULT_FROM_EMAIL = 'Print X <your-email@gmail.com>'
```

**For Gmail App Password:**
1. Go to Google Account settings
2. Security → 2-Step Verification
3. App passwords → Generate new app password
4. Use that password in settings

**Test:**
1. Place an order
2. Admin changes order status to "Processing"
3. Check customer email for notification
4. Admin changes status to "Delivered"
5. Check email again

## 🗂️ New Files Created

### Backend Files:
- `backend/api/new_features_views.py` - New API endpoints
- `backend/api/migrations/0011_new_features.py` - Database migration (auto-generated)
- Updated: `models.py`, `views.py`, `urls.py`, `admin.py`

### Frontend Files:
- `docs/customer/track.html` - Public order tracking page
- `docs/customer/profile.html` - User profile management page

### Documentation:
- `NEW_FEATURES_GUIDE.md` - Detailed feature documentation
- `MIGRATION_FIX_GUIDE.md` - Troubleshooting guide
- `SETUP_GUIDE.md` - This file

## 🔧 Troubleshooting

### Issue: "No module named 'pkg_resources'"
```bash
pip install --upgrade djangorestframework-simplejwt
```

### Issue: "UNIQUE constraint failed: tracking_id"
```bash
# Delete database and start fresh
del db.sqlite3
python manage.py makemigrations
python manage.py migrate
```

### Issue: "Table already exists"
```bash
python manage.py migrate --fake-initial
```

### Issue: Email not sending
1. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py
2. For Gmail, use App Password (not regular password)
3. Enable "Less secure app access" or use App Password
4. Check spam folder

### Issue: Can't access admin panel
```bash
# Create superuser
python manage.py createsuperuser
```

## 📊 Database Schema Changes

### New Models:
- **Category** - Product categories
- **UserProfile** - Extended user information

### Updated Models:
- **Order** - Added: tracking_id, phone, updated_at
- **Product** - Added: category (ForeignKey)

## 🎨 Frontend Integration Examples

### Show Tracking ID in Order Confirmation

```javascript
// In checkout success screen
function showSuccessScreen(order) {
  const trackingUrl = `track.html?id=${order.tracking_id}`;
  content.innerHTML = `
    <div class="success-box">
      <h2>Order Placed Successfully!</h2>
      <p>Tracking ID: <strong>${order.tracking_id}</strong></p>
      <a href="${trackingUrl}" class="btn btn-primary">Track Order</a>
    </div>
  `;
}
```

### Add Category Filter to Products Page

```javascript
// In product.html
async function loadCategories() {
  const res = await apiFetch('/categories/');
  if (res.ok) {
    const select = document.getElementById('categoryFilter');
    select.innerHTML = '<option value="">All Categories</option>' +
      res.data.categories.map(cat => 
        `<option value="${cat.id}">${cat.name}</option>`
      ).join('');
  }
}

async function filterByCategory() {
  const categoryId = document.getElementById('categoryFilter').value;
  const url = categoryId 
    ? `/products/filter/?category=${categoryId}`
    : '/products/';
  const res = await apiFetch(url);
  if (res.ok) {
    renderProducts(res.data.products);
  }
}
```

### Display Revenue Chart (Admin Dashboard)

```html
<!-- Add Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<canvas id="revenueChart"></canvas>

<script>
async function loadRevenueChart() {
  const res = await apiFetch('/admin/revenue-chart/?period=daily&days=30');
  if (res.ok) {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: res.data.labels,
        datasets: [{
          label: 'Revenue (₱)',
          data: res.data.revenues,
          borderColor: '#e8000d',
          backgroundColor: 'rgba(232, 0, 13, 0.1)',
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: 'Revenue Over Time'
          }
        }
      }
    });
  }
}
</script>
```

## ✅ Success Checklist

- [ ] Python 3.13 compatibility fixed
- [ ] Database created successfully
- [ ] All migrations applied
- [ ] Superuser created
- [ ] Server starts without errors
- [ ] Can access admin panel
- [ ] Can register new user
- [ ] Can login as customer
- [ ] Can place order and receive tracking ID
- [ ] Can track order without login
- [ ] Can update profile
- [ ] Can change password
- [ ] Can cancel pending order
- [ ] Phone validation works at checkout
- [ ] Categories API works
- [ ] Product filtering works
- [ ] Revenue chart API returns data
- [ ] Email notifications work (if configured)

## 🎉 You're All Set!

Your Print X e-commerce system now has all the requested features:

1. ✅ Secure order tracking system
2. ✅ Product categories and filtering
3. ✅ Email notifications
4. ✅ User profile management
5. ✅ Phone validation
6. ✅ Order cancellation
7. ✅ Revenue analytics
8. ✅ Enhanced security

## 📞 Support

If you encounter any issues:
1. Check the error message in terminal
2. Check browser console (F12)
3. Review the MIGRATION_FIX_GUIDE.md
4. Review the NEW_FEATURES_GUIDE.md

## 🚀 Next Steps

1. Configure email settings for notifications
2. Add Chart.js to admin dashboard
3. Create category management UI
4. Add product images
5. Implement SMS notifications (optional)
6. Add more payment methods
7. Create mobile app (optional)

Happy coding! 🎨🖨️
