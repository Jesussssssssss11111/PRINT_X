# Order Cancellation with Admin Approval Guide

## Overview
Order cancellation now requires a reason from the customer and approval from the admin before the order is actually cancelled.

## Features Implemented

### 1. Customer Side
- **Cancellation Request**: When customers click "Cancel" on pending/processing orders, they must provide a reason
- **Status Tracking**: Orders with cancellation requests show "Cancel Requested" status with "Pending Approval" badge
- **Reason Display**: Customers can see their cancellation reason in the order details modal
- **No Direct Cancellation**: Orders are not immediately cancelled - they enter "cancel_requested" status

### 2. Admin Side
- **Cancellation Queue**: Orders with status "cancel_requested" appear in the admin orders panel
- **Reason Visibility**: Admin can see the customer's cancellation reason directly in the table
- **Approve/Reject Actions**: 
  - **Approve**: Changes order status to "cancelled" and sends cancellation email to customer
  - **Reject**: Changes order status back to "processing" and sends rejection email to customer
- **Email Notifications**: Automatic emails sent for:
  - Cancellation request submitted (to customer)
  - Cancellation approved (to customer)
  - Cancellation rejected (to customer)

## Database Changes

### New Fields in Order Model
```python
cancel_reason = models.TextField(blank=True, default='')
```

### New Status
```python
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('cancel_requested', 'Cancellation Requested'),  # NEW
]
```

## API Endpoints

### Customer Endpoints

#### Request Cancellation
```
POST /api/orders/<order_id>/cancel/
Body: { "reason": "Customer's cancellation reason" }
Response: { "message": "Cancellation request submitted. Waiting for admin approval." }
```

### Admin Endpoints

#### Approve Cancellation
```
POST /api/admin/orders/<order_id>/approve-cancel/
Response: { "message": "Cancellation approved." }
```

#### Reject Cancellation
```
POST /api/admin/orders/<order_id>/reject-cancel/
Response: { "message": "Cancellation request rejected." }
```

## User Flow

### Customer Cancellation Flow
1. Customer navigates to Orders page
2. Clicks "Cancel" button on pending/processing order
3. Prompted to enter cancellation reason (required)
4. Submits cancellation request
5. Order status changes to "Cancel Requested"
6. Customer receives email confirmation that request was submitted
7. Customer waits for admin approval
8. Customer receives email when admin approves or rejects

### Admin Approval Flow
1. Admin logs into admin panel
2. Navigates to "All Orders" section
3. Sees orders with "Cancel Requested" status badge (yellow/warning)
4. Reviews cancellation reason displayed in the table
5. Clicks "Approve" to cancel the order OR "Reject" to continue processing
6. System sends appropriate email to customer
7. Order status updates accordingly

## Email Templates

### 1. Cancellation Request Submitted
- **Subject**: [Print X] Cancellation Request for Order #[ID]
- **Content**: Confirms request submitted, shows reason, mentions admin review

### 2. Cancellation Approved
- **Subject**: [Print X] Order #[ID] Cancelled
- **Content**: Confirms order cancelled, shows order details

### 3. Cancellation Rejected
- **Subject**: [Print X] Cancellation Request Rejected - Order #[ID]
- **Content**: Informs customer request was rejected, order continues processing

## UI Changes

### Customer Orders Page
- **Cancel Button**: Shows for pending/processing orders
- **Pending Approval Badge**: Shows for cancel_requested orders instead of cancel button
- **Reason Display**: Shows cancellation reason in order detail modal
- **Status Badge**: "Cancel Requested" badge with warning color

### Admin Orders Panel
- **Status Column**: Shows "Cancel Requested" badge with reason below
- **Actions Column**: Shows "Approve" and "Reject" buttons for cancel_requested orders
- **Status Dropdown**: Excludes "cancel_requested" from manual selection (only set via API)

## Migration

Run the migration to add the new fields:
```bash
cd backend
python manage.py migrate
```

Migration file: `0012_add_cancel_reason_and_status.py`

## Testing

### Test Customer Cancellation Request
1. Login as customer
2. Place an order
3. Go to Orders page
4. Click "Cancel" on the order
5. Enter reason: "Changed my mind"
6. Verify order status shows "Cancel Requested"
7. Check email for confirmation

### Test Admin Approval
1. Login as admin
2. Go to All Orders
3. Find order with "Cancel Requested" status
4. Click "Approve"
5. Verify order status changes to "Cancelled"
6. Check customer receives cancellation email

### Test Admin Rejection
1. Login as admin
2. Go to All Orders
3. Find order with "Cancel Requested" status
4. Click "Reject"
5. Verify order status changes to "Processing"
6. Check customer receives rejection email

## Key Benefits

1. **Better Control**: Admin has final say on cancellations
2. **Audit Trail**: Cancellation reasons are recorded
3. **Customer Communication**: Automatic emails keep customers informed
4. **Flexibility**: Admin can reject cancellations if order is already being processed
5. **Transparency**: Both customer and admin can see cancellation status and reason

## Notes

- Orders can only be cancelled if status is "pending" or "processing"
- Cancellation reason is required (cannot be empty)
- Admin cannot manually set status to "cancel_requested" via dropdown
- Once approved, cancellation cannot be undone
- Rejected cancellations return order to "processing" status
