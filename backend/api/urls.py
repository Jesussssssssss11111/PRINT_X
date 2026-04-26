from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from . import views
from . import new_features_views as nf_views

urlpatterns = [
    # Auth
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/',           views.logout_view,    name='logout'),
    path('token/refresh/',    TokenRefreshView.as_view(), name='token_refresh'),

    # Categories
    path('categories/', nf_views.categories, name='categories'),

    # Products
    path('products/', views.products, name='products'),
    path('products/filter/', nf_views.products_with_filters, name='products_filter'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # Product Reviews
    path('products/<int:product_id>/reviews/', views.product_reviews, name='product_reviews'),
    path('products/<int:product_id>/reviews/add/', views.add_review, name='add_review'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),

    # Cart
    path('cart/', views.cart, name='cart'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('cart/remove-custom/<int:req_id>/', views.cart_remove_custom, name='cart_remove_custom'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),

    # Checkout & Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<int:order_id>/track/', views.order_status_public, name='order_track'),
    path('orders/<int:order_id>/cancel/', nf_views.cancel_order, name='cancel_order'),
    path('orders/delete/<int:order_id>/', views.customer_delete_order, name='customer_delete_order'),

    # Order Tracking (Public)
    path('track/<str:tracking_id>/', nf_views.track_order, name='track_order'),

    # User Profile
    path('profile/', nf_views.user_profile, name='user_profile'),
    path('profile/change-password/', nf_views.change_password, name='change_password'),

    # Custom Requests
    path('custom/', views.custom_request, name='custom_request'),
    path('custom/<int:request_id>/upload/', views.upload_custom_stl, name='custom_upload'),
    path('custom/cancel/<int:request_id>/', views.cancel_custom_request, name='cancel_custom'),

    # Admin
    path('admin/stats/', views.admin_dashboard_stats, name='admin_stats'),
    path('admin/revenue-chart/', nf_views.admin_revenue_chart, name='admin_revenue_chart'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/orders/delete/<int:order_id>/', views.admin_delete_order, name='admin_delete_order'),
    path('admin/orders/<int:order_id>/status/', views.admin_update_order_status, name='admin_status'),
    path('admin/orders/<int:order_id>/approve-cancel/', nf_views.approve_cancel_order, name='approve_cancel'),
    path('admin/orders/<int:order_id>/reject-cancel/', nf_views.reject_cancel_order, name='reject_cancel'),
    path('admin/custom/', views.admin_custom_requests, name='admin_custom'),
    path('admin/custom/<int:request_id>/status/', views.admin_update_custom_status, name='admin_update_custom_status'),

    path('admin/custom/cancel/<int:request_id>/', views.admin_cancel_custom, name='admin_cancel_custom'),
    path('admin/custom/delete/<int:request_id>/', views.admin_delete_custom, name='admin_delete_custom'),
    path('admin/users/', views.admin_users, name='admin_users'),

    path('admin/custom/<int:request_id>/download/', views.admin_download_stl, name='admin_download_stl'),
    path('admin/custom/<int:request_id>/download-order/', views.admin_download_custom_order, name='admin_download_custom_order'),
]
