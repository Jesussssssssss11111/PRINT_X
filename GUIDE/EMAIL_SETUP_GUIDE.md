# Email Configuration Guide

## Current Status
Emails are currently being printed to the **console** (terminal) instead of being sent to users. This is because no email credentials are configured.

## Option 1: Configure Gmail SMTP (Real Emails)

### Step 1: Create Gmail App Password
1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll down to **App passwords**
4. Click **Select app** → Choose "Mail"
5. Click **Select device** → Choose "Other" and name it "Print X"
6. Click **Generate**
7. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 2: Set Environment Variables

**On Windows (Command Prompt):**
```cmd
set EMAIL_HOST_USER=your_email@gmail.com
set EMAIL_HOST_PASSWORD=your_16char_app_password
```

**On Windows (PowerShell):**
```powershell
$env:EMAIL_HOST_USER="your_email@gmail.com"
$env:EMAIL_HOST_PASSWORD="your_16char_app_password"
```

**Permanent (Windows):**
1. Search for "Environment Variables" in Windows
2. Click "Edit the system environment variables"
3. Click "Environment Variables" button
4. Under "User variables", click "New"
5. Add:
   - Variable name: `EMAIL_HOST_USER`
   - Variable value: `your_email@gmail.com`
6. Click "New" again and add:
   - Variable name: `EMAIL_HOST_PASSWORD`
   - Variable value: `your_16char_app_password`
7. Click OK and restart your terminal/IDE

### Step 3: Restart Django Server
After setting environment variables, restart the Django development server:
```bash
cd backend
python manage.py runserver
```

### Step 4: Test Email
The system will now send real emails for:
- Order status updates (processing, shipped, delivered, cancelled)
- Cancellation requests
- Cancellation approvals/rejections
- Custom request status changes

---

## Option 2: Keep Console Output (Development)

If you want to keep emails in the console for testing:
- No changes needed
- Emails will appear in the terminal where Django is running
- Look for email content in the console output

---

## Verify Email Configuration

Run this command to check if emails are configured:
```bash
cd backend
python manage.py shell -c "from django.conf import settings; print('Email Backend:', settings.EMAIL_BACKEND); print('Email User:', settings.EMAIL_HOST_USER or 'Not configured')"
```

**Expected Output:**
- With credentials: `Email Backend: django.core.mail.backends.smtp.EmailBackend`
- Without credentials: `Email Backend: django.core.mail.backends.console.EmailBackend`

---

## Troubleshooting

### Gmail Blocking Sign-in
If Gmail blocks the sign-in attempt:
1. Check if 2-Step Verification is enabled
2. Make sure you're using an **App Password**, not your regular Gmail password
3. Try generating a new App Password

### Emails Not Sending
1. Check environment variables are set correctly
2. Restart Django server after setting variables
3. Check Django console for error messages
4. Verify Gmail credentials are correct

### Testing Email Manually
```bash
cd backend
python manage.py shell
```

Then in the shell:
```python
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'This is a test email from Print X.',
    'noreply@printx.com',
    ['recipient@example.com'],
    fail_silently=False,
)
```

---

## Security Notes

- **Never commit** email credentials to Git
- Use environment variables for sensitive data
- App Passwords are safer than regular passwords
- Revoke App Passwords if compromised
