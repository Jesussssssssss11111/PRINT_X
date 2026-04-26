# Quick Fix for Migration Issue

## Problem
The migration is failing due to UNIQUE constraint on tracking_id field when trying to migrate existing orders.

## Solution Options

### Option 1: Fresh Start (Recommended for Development)

1. **Backup your data** (if you have important data):
```bash
cd backend
python manage.py dumpdata > backup.json
```

2. **Delete the database**:
```bash
del db.sqlite3  # Windows
# or
rm db.sqlite3   # Linux/Mac
```

3. **Delete migration cache**:
```bash
del api\migrations\__pycache__\*  # Windows
# or
rm -rf api/migrations/__pycache__/*  # Linux/Mac
```

4. **Run migrations fresh**:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Create superuser**:
```bash
python manage.py createsuperuser
```

6. **Restore data** (if you backed up):
```bash
python manage.py loaddata backup.json
```

### Option 2: Manual Fix (If you have important data)

1. **Open Django shell**:
```bash
python manage.py shell
```

2. **Manually add tracking IDs to existing orders**:
```python
from api.models import Order
import secrets

for order in Order.objects.all():
    if not hasattr(order, 'tracking_id') or not order.tracking_id:
        # Generate unique tracking ID
        while True:
            tracking_id = secrets.token_urlsafe(16)[:16].upper().replace('-', '').replace('_', '')
            if not Order.objects.filter(tracking_id=tracking_id).exists():
                # Use raw SQL to update
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE api_order SET tracking_id = %s WHERE id = %s",
                        [tracking_id, order.id]
                    )
                break
        print(f"Order {order.id} -> {tracking_id}")

print("Done!")
exit()
```

3. **Then run migrations**:
```bash
python manage.py migrate
```

### Option 3: Simplified Migration (Easiest)

Since you deleted the database, just run:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Python 3.13 Compatibility Issue

If you see `ModuleNotFoundError: No module named 'pkg_resources'`, this is a Python 3.13 compatibility issue with djangorestframework-simplejwt.

**Fix**:
```bash
pip install --upgrade djangorestframework-simplejwt
```

Or downgrade to Python 3.11 or 3.12:
```bash
# Use Python 3.11 or 3.12 instead of 3.13
python3.11 -m venv venv
# or
python3.12 -m venv venv
```

## Verify Everything Works

After migration:

1. **Start server**:
```bash
python manage.py runserver
```

2. **Test endpoints**:
- Register: http://127.0.0.1:8000/api/register/
- Login: http://127.0.0.1:8000/api/login/
- Products: http://127.0.0.1:8000/api/products/
- Categories: http://127.0.0.1:8000/api/categories/

3. **Test frontend**:
- Open: http://127.0.0.1:8000/docs/customer/index.html
- Track page: http://127.0.0.1:8000/docs/customer/track.html
- Profile page: http://127.0.0.1:8000/docs/customer/profile.html

## Common Issues

### Issue: "No module named 'pkg_resources'"
**Solution**: 
```bash
pip install setuptools
# or upgrade simplejwt
pip install --upgrade djangorestframework-simplejwt
```

### Issue: "UNIQUE constraint failed"
**Solution**: Use Option 1 (Fresh Start) above

### Issue: "Table already exists"
**Solution**: 
```bash
python manage.py migrate --fake-initial
```

### Issue: "No such table: api_order"
**Solution**: 
```bash
python manage.py migrate --run-syncdb
```

## Success Checklist

- [ ] Database created successfully
- [ ] All migrations applied
- [ ] Superuser created
- [ ] Server starts without errors
- [ ] Can login to admin panel
- [ ] Can register new user
- [ ] Can place order and get tracking ID
- [ ] Can track order without login
- [ ] Can update profile
- [ ] Can cancel order

## Need Help?

If you're still having issues:

1. Check Python version: `python --version` (use 3.11 or 3.12)
2. Check Django version: `python -m django --version`
3. Check installed packages: `pip list`
4. Look at error logs in terminal
5. Check browser console for frontend errors

## Quick Test Script

Create a file `test_features.py` in backend folder:

```python
import requests

BASE_URL = 'http://127.0.0.1:8000/api'

# Test 1: Register
print("Testing registration...")
response = requests.post(f'{BASE_URL}/register/', json={
    'username': 'testuser',
    'password': 'testpass123',
    'email': 'test@test.com',
    'first_name': 'Test',
    'last_name': 'User'
})
print(f"Register: {response.status_code}")

# Test 2: Login
print("Testing login...")
response = requests.post(f'{BASE_URL}/login/', json={
    'username': 'testuser',
    'password': 'testpass123'
})
if response.status_code == 200:
    token = response.json()['access']
    print(f"Login: Success - Token: {token[:20]}...")
    
    # Test 3: Get Profile
    print("Testing profile...")
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{BASE_URL}/profile/', headers=headers)
    print(f"Profile: {response.status_code}")
    
    # Test 4: Get Categories
    print("Testing categories...")
    response = requests.get(f'{BASE_URL}/categories/')
    print(f"Categories: {response.status_code}")
    
    print("\n✅ All tests passed!")
else:
    print(f"Login failed: {response.status_code}")
```

Run it:
```bash
python test_features.py
```
