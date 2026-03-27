from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inventory', views.inventory, name='inventory'),
    path('add_inventory', views.add_inventory, name='add_inventory'),
    path('edit_inventory/<str:inventory_id>/', views.edit_inventory, name='edit_inventory'),
    path('delete_inventory/<str:inventory_id>/', views.delete_inventory, name='delete)_inventory'),
    
    path('categories', views.categories, name='categories'),
    path('add_category', views.add_category, name='add_category'),
    path('delete_category/<str:category_id>/', views.delete_category, name='delete_category'),
    path('edit_category/<str:category_id>/', views.edit_category, name='edit_category'),
    
    path('suppliers', views.suppliers, name='suppliers'),
    path('add_supplier', views.add_supplier, name='add_supplier'),
    path('edit_supplier/<str:supplier_id>/', views.edit_supplier, name='edit_supplier'),
    path('delete_supplier/<str:supplier_id>/', views.delete_supplier, name='delete_supplier'),
    
    path('customers', views.customers, name='customers'),
    path('add_customer', views.add_customer, name='add_customer'),
    path('edit_customer/<str:customer_id>/', views.edit_customer, name='edit_customer'),
    path('delete_customer/<str:customer_id>/', views.delete_customer, name='delete_customer'),
    
    path('purchases', views.purchases, name='purchases'),
    path('add_purchase', views.add_purchase, name='add_purchase'),
    path('edit_purchase/<str:purchase_id>/', views.edit_purchase, name='edit_purchase'),
    path('delete_purchase/<str:purchase_id>/', views.delete_purchase, name='delete_purchase'),
    
    path('sales', views.sales, name='sales'),
    path('add_sale', views.add_sale, name='add_sale'),
    path('edit_sale/<str:sale_id>/', views.edit_sale, name='edit_sale'),
    #path('sales/', views.sales_list, name='sales'),  # your sales list page
    path('delete_sale/<str:sale_id>/', views.delete_sale, name='delete_sale'),
    path('reports', views.reports, name='reports'),
   
    
    path('manage_users', views.manage_users, name='manage_users'),
    path('add_user', views.add_user, name='add_user'),
    path('edit_user/<str:user_id>/', views.edit_user, name='edit_user'),
    path('delete_user/<str:user_id>/', views.delete_user, name='delete_user'),
    
    path('roles', views.roles, name='roles'),
    path('add_role', views.add_role, name='add_role'),
    path('edit_role/<str:role_id>/', views.edit_role, name='edit_role'),
    path('delete_role/<str:role_id>/', views.delete_role, name='delete_role'),
    
    path('login', views.login, name='login'),
    path('send_otp', views.send_otp, name='send_otp'),
    path('verify_otp', views.verify_otp, name='verify_otp'),
    path('profile', views.profile, name='profile'),
    path('logout', views.logout, name='logout'),
    
    
    path('inventory/image/<str:id>/', views.get_inventory_image, name='get_inventory_image'),
    path('image/<str:id>/', views.get_category_image, name='get_category_image'),
    path('image/<str:id>/', views.get_user_profile, name='get_user_profile'),
   ]

    