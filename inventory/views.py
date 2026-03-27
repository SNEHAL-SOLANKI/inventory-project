from itertools import product
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from inventory.models import AdminMaster, CategoryMaster, CustomerMaster, InventoryMaster, ManageUser, PurchaseMaster, RoleMaster, SalesMaster, SupplierMaster,SalesMaster
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from mongoengine import DoesNotExist
import random
import time
from datetime import datetime
import json
from functools import wraps
from .utils import permission_required

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.session.get('is_logged_in'):
                return redirect('login')
            user_role = request.session.get('user_role', '')
            if user_role == 'Admin' or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'dashboard.html', {'error': 'You do not have permission to access this page.'})
        return _wrapped_view
    return decorator

# Create your views here.
def dashboard(request):
    if not request.session.get('is_logged_in'):
        return redirect('login')

    # ❌ CUSTOMER KO DASHBOARD NA DIKHE
    if request.session.get('user_role') == "Customer":
        return redirect('sales')

    if not ManageUser.objects(userEmail='admin@example.com').first():
        ManageUser(
            userFname='Admin',
            userUsername='admin',
            userEmail='admin@example.com',
            userPassword='Admin@123',
            userRole='Admin',
            userStatus=True
        ).save()
    if not ManageUser.objects(userEmail='admin@example.com').first():
        ManageUser(userFname='Admin', userUsername='admin', userEmail='admin@example.com', userPassword='Admin@123', userRole='Admin', userStatus=True).save()

    total_products = InventoryMaster.objects.count()
    
    # Calculate Total Stock Quantity
    total_stock = 0
    all_inventory = InventoryMaster.objects.all()
    for item in all_inventory:
        try:
            total_stock += int(item.prodStockQty) if item.prodStockQty else 0
        except ValueError:
            pass
            
    # Calculate Total Purchase Amount
    total_purchase_amount = 0
    all_purchases = PurchaseMaster.objects.all()
    for purchase in all_purchases:
        try:
            total_purchase_amount += float(purchase.purchaseTotalAmount) if purchase.purchaseTotalAmount else 0
        except ValueError:
            pass

    # Calculate Total Sales Amount
    total_sales_amount = 0
    all_sales = SalesMaster.objects.all()
    for sale in all_sales:
        try:
            total_sales_amount += float(sale.salesGrandTotal) if sale.salesGrandTotal else 0
        except ValueError:
            pass

    # Low Stock Items (Quantity <= 15)
    low_stock_items = []
    for item in all_inventory:
        try:
            qty = int(item.prodStockQty) if item.prodStockQty else 0
            if qty <= 15:
                low_stock_items.append({
                    'product': item,
                    'stock': qty,
                    'reorder_qty': item.reorderQuantity # Example Reorder Quantity logic
                })
        except ValueError:
            pass
            
    # Top Customers (For "new" chart)
    # Group sales by customer and sum grand total
    customer_sales = {}
    for sale in all_sales:
        if sale.salesCustomer:
            cust_name = sale.salesCustomer.custName
            try:
                amt = float(sale.salesGrandTotal) if sale.salesGrandTotal else 0
                customer_sales[cust_name] = customer_sales.get(cust_name, 0) + amt
            except ValueError:
                pass
    
    # Sort by amount and take top 7
    top_customers = sorted(customer_sales.items(), key=lambda x: x[1], reverse=True)[:7]
    top_customers_data = [{"label": k, "y": v} for k, v in top_customers]
    
    # Stock by Category (For "chartContainer" pie chart)
    category_stock = {}
    total_stock_qty = 0
    for item in all_inventory:
        cat = str(item.prodCategory).strip() if item.prodCategory else ""

        if not cat or cat.lower() in ["none", "null", "unknown"]:
            continue

        try:
            qty = int(item.prodStockQty) if item.prodStockQty else 0
            category_stock[cat] = category_stock.get(cat, 0) + qty
        except ValueError:
            pass
            
    cat_stock_data = [{"label": k, "y": v} for k, v in category_stock.items()]
    
    # Recently Updated Stock (For "clm" column chart)
    # Assuming prodLastUpdated exists, we can sort by it. Or just take top 10 products by stock
    sorted_inventory = sorted(
        [item for item in all_inventory if item.prodStockQty and item.prodStockQty.isdigit()],
        key=lambda x: int(x.prodStockQty), reverse=True
    )[:10]
    recent_stock_data = [{"label": item.prodName, "y": int(item.prodStockQty)} for item in sorted_inventory]
    
    import json

    context = {
        'total_products': total_products,
        'total_stock': total_stock,
        'total_purchase_amount': total_purchase_amount,
        'total_sales_amount': total_sales_amount,
        'low_stock_items': low_stock_items,
        'top_customers_data': json.dumps(top_customers_data),
        'cat_stock_data': json.dumps(cat_stock_data),
        'recent_stock_data': json.dumps(recent_stock_data),
    }

    return render(request, 'dashboard.html', context)

@permission_required('view_inventory')
def inventory(request):
    invData = InventoryMaster.objects.all()
    
    
    return render(request, 'inventory.html', {'inventory': invData})

@permission_required('add_inventory')
def add_inventory(request):

    cat = CategoryMaster.objects.all()
    suppliers = SupplierMaster.objects.all()

    if request.method == 'POST':

        name = request.POST.get('Name')

        category_id = request.POST.get('Category')
        supplier_id = request.POST.get("Supplier")

        # ✅ correct FK fetch
        category = CategoryMaster.objects(id=category_id).first() if category_id else None
        if supplier_id:
            supplier = SupplierMaster.objects(id=supplier_id).first() if supplier_id else None
        else:
            supplier = None

        purchase_price = float(request.POST.get('PurchasePrice') or 0)
        selling_price = float(request.POST.get('SellingPrice') or 0)
        stock_qty = request.POST.get('StockQuantity') or "0"

        reorderLevel = int(request.POST.get("ReorderLevel") or 0)
        reorderQuantity = int(request.POST.get("ReorderQuantity") or 0)

        profit = selling_price - purchase_price

        unit = request.POST.get('Unit')
        description = request.POST.get('Description')
        image = request.FILES.get('Image')

        barcode_value = str(random.randint(1000000000,9999999999))

        product = InventoryMaster(
            prodName=name,
            prodCode=barcode_value,
            prodCategory=category,   # ✅ FIXED
            prodPurchasePrice=purchase_price,
            prodSellingPrice=selling_price,
            prodStockQty=stock_qty,
            reorderLevel=reorderLevel,
            reorderQuantity=reorderQuantity,
            profit=profit,
            prodUnit=unit,
            prodSupplier=supplier,
            prodBarcode=barcode_value,
            prodDescription=description
        )

        if image:
            product.prodImage.put(image, content_type=image.content_type)

        product.save()

        return redirect('inventory')

    return render(request, 'add_inventory.html', {
        'categories': cat,
        'suppliers': suppliers
    })
def get_inventory_image(request, id):

    prod = InventoryMaster.objects.get(id=id)

    if prod.prodImage:
        image_data = prod.prodImage.read()
        return HttpResponse(image_data, content_type=prod.prodImage.content_type)
    else:
        return HttpResponse(status=404)

@permission_required('edit_inventory')
def edit_inventory(request, inventory_id):

    inventory = InventoryMaster.objects.get(id=inventory_id)

    categories = CategoryMaster.objects.all()
    suppliers = SupplierMaster.objects.all()

    if request.method == 'POST':

        name = request.POST.get('Name')
        code = request.POST.get('Code')

        category_id = request.POST.get('Category')
        supplier_id = request.POST.get('Supplier')

        category = CategoryMaster.objects(id=category_id).first()
        if supplier_id:
            supplier = SupplierMaster.objects(id=supplier_id).first()
        else:
            supplier = None

        if not category:
            return HttpResponse("Invalid Category")

        

        purchase_price = float(request.POST.get('PurchasePrice') or 0)
        selling_price = float(request.POST.get('SellingPrice') or 0)
        stock_qty = request.POST.get('StockQuantity') or "0"

        unit = request.POST.get('Unit')
        description = request.POST.get('Description')
        image = request.FILES.get('Image')

        barcode = request.POST.get('Barcode')

        reorderLevel = int(request.POST.get("ReorderLevel") or 0)
        reorderQuantity = int(request.POST.get("ReorderQuantity") or 0)

        inventory.prodName = name
        inventory.prodCode = code
        inventory.prodCategory = category   
        inventory.prodSupplier = supplier   
        inventory.prodPurchasePrice = purchase_price
        inventory.prodSellingPrice = selling_price
        inventory.prodStockQty = stock_qty
        inventory.prodUnit = unit
        inventory.prodBarcode = barcode
        inventory.prodDescription = description
        inventory.reorderLevel = reorderLevel
        inventory.reorderQuantity = reorderQuantity

        if image:
            inventory.prodImage.replace(image, content_type=image.content_type)

        inventory.save()

        return redirect('inventory')

    return render(request, 'edit_inventory.html', {
        'inventory': inventory,
        'categories': categories,
        'suppliers': suppliers
    })
@permission_required('delete_inventory')
def delete_inventory(request, inventory_id):
    inventory = InventoryMaster.objects.get(id=inventory_id)
    inventory.delete()
    return redirect('inventory')


def get_category_image(request, id):
    cat = CategoryMaster.objects.get(id=id)
    if cat.catImage:
        image_data = cat.catImage.read()
        return HttpResponse(image_data, content_type=cat.catImage.content_type)
    else:
        return HttpResponse(status=404)
@permission_required('view_categories')
def categories(request):
    catData = CategoryMaster.objects.all()
    
    return render(request, 'categories.html', {'categories': catData,})
@permission_required('add_category')
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('Name')
        code = request.POST.get('Code')
        image = request.FILES.get('Image')
        desc = request.POST.get('Description')
        

        # Create and save the category
        category = CategoryMaster(
            catName=name,
            catCode=code,
            catDescription=desc,
             
        )
        if image:
            category.catImage.put(image,content_type=image.content_type) 
        category.save()
        return redirect('categories')
    return render(request, 'add_category.html')

@permission_required('edit_category')
def edit_category(request, category_id):
    cat = CategoryMaster.objects.get(id=category_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        #code = request.POST.get('code')
        image = request.FILES.get('Image')
        desc = request.POST.get('description')
        status = request.POST.get('status') == 'on' # Checkbox value

        cat.catName = name
        #cat.catCode = code
        cat.catDescription = desc
        cat.catStatus = status
        
        
        if image:
            cat.catImage.replace(image, content_type=image.content_type)
        
        cat.save()
        return redirect('categories')
    return render(request, 'edit_category.html', {'category_id': category_id,'category': cat})
@permission_required('delete_category')
def delete_category(request, category_id):
    cat = CategoryMaster.objects.get(id=category_id)
    cat.delete()
    return redirect('categories')

@permission_required('view_suppliers')
def suppliers(request):
    supData = SupplierMaster.objects.all()
    return render(request, 'suppliers.html', {'suppliers': supData})

@permission_required('add_supplier')
def add_supplier(request):
    if request.method == 'POST':
        name = request.POST.get('Name')
        code = request.POST.get('Code')
        phone = request.POST.get('Phone')
        email = request.POST.get('Email')
        gst = request.POST.get('GST')
        city = request.POST.get('City')
        address = request.POST.get('Address')
        
        # Create and save the supplier
        supplier = SupplierMaster(
            supName=name,
            supCode=code,
            supPhone=phone,
            supEmail=email,
            supGST=gst,
            supCity=city,
            supAddress=address
        )
        supplier.save()
    return render(request, 'add_supplier.html')
@permission_required('edit_supplier')
def edit_supplier(request, supplier_id):
    sup = SupplierMaster.objects.get(id=supplier_id)
    if request.method == 'POST':
        name = request.POST.get('Name')
        code = request.POST.get('Code')
        phone = request.POST.get('Phone')
        email = request.POST.get('Email')
        gst = request.POST.get('GST')
        city = request.POST.get('City')
        address = request.POST.get('Address')
        sup.supStatus = 'Status' in request.POST

        sup.supName = name
        sup.supCode = code
        sup.supPhone = phone
        sup.supEmail = email
        sup.supGST = gst
        sup.supCity = city
        sup.supAddress = address
          
        sup.save()
        return redirect('suppliers')
    return render(request, 'edit_supplier.html', {'supplier_id': supplier_id,'supplier': sup})
@permission_required('delete_supplier')
def delete_supplier(request, supplier_id):
    sup = SupplierMaster.objects.get(id=supplier_id)
    sup.delete()
    return redirect('suppliers')

@permission_required('view_customers')
def customers(request):
    cusData = CustomerMaster.objects.all()
    return render(request, 'customers.html', {'customers': cusData})

@permission_required('add_customer')
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('Name')
        code = request.POST.get('Code')
        email = request.POST.get('Email')
        mobile = request.POST.get('Mobile')
        gst = request.POST.get('GST')
        address = request.POST.get('Address')
        
        # Create and save the customer
        customer = CustomerMaster(
            custName=name,
            custCode=code,
            custEmail=email,
            custMobile=mobile,
            custGST=gst,
            custAddress=address,
            user=request.session.get('user_id')
        )
        customer.save()
    return render(request, 'add_customer.html')
@permission_required('edit_customer')
def edit_customer(request, customer_id):
    customer = CustomerMaster.objects.get(id=customer_id)
    if request.method == 'POST':
        name = request.POST.get('Name')
        code = request.POST.get('Code')
        email = request.POST.get('Email')
        mobile = request.POST.get('Mobile')
        gst = request.POST.get('GST')
        address = request.POST.get('Address')
        customer.custStatus = 'Status' in request.POST

        customer.custName = name
        customer.custCode = code
        customer.custEmail = email
        customer.custMobile = mobile
        customer.custGST = gst
        customer.custAddress = address
           
        customer.save()
        return redirect('customers')
    return render(request, 'edit_customer.html', {'customer_id': customer_id,'customer': customer})
@permission_required('delete_customer')
def delete_customer(request, customer_id):
    customer = CustomerMaster.objects.get(id=customer_id)
    customer.delete()
    return redirect('customers')

@permission_required('view_purchases')
def purchases(request):
    purchaseData = PurchaseMaster.objects.all()

    safe_data = []

    for item in purchaseData:
        try:
            _ = item.purchaseProduct
            safe_data.append(item)
        except DoesNotExist:
            pass

    return render(request, 'purchases.html', {'purchases': safe_data})

def generate_invoice():
    last_purchase = PurchaseMaster.objects.order_by('-purchaseInvoiceNo').first()
    if last_purchase and last_purchase.purchaseInvoiceNo:
        try:
            number = int(last_purchase.purchaseInvoiceNo.split('-')[1])
            return f"INV-{number+1}"
        except:
            return "INV-1001"
    return "INV-1001"

def generate_sales_invoice():
    last_sale = SalesMaster.objects.order_by('-salesInvoiceno').first()
    if last_sale and last_sale.salesInvoiceno:
        try:
            # Assuming format SALE-1001
            parts = last_sale.salesInvoiceno.split('-')
            if len(parts) > 1:
                number = int(parts[1])
                return f"SALE-{number+1}"
            else:
                return "SALE-1001"
        except:
            return "SALE-1001"
    return "SALE-1001"

@permission_required('add_purchase')
def add_purchase(request):

    suppliers = SupplierMaster.objects.all()
    products = InventoryMaster.objects.all()

    invoice_no = generate_invoice()

    if request.method == 'POST':

        purchase_date = request.POST.get('PurchaseDate')
        supplier_id = request.POST.get('Supplier')
        product_id = request.POST.get('Product')

        # Validate Supplier
        supplier_obj = SupplierMaster.objects(id=supplier_id).first() if supplier_id else None
        if not supplier_obj:
            messages.error(request, "Please select a valid supplier.")
            return redirect('add_purchase')

        # Validate Product
        product_obj = InventoryMaster.objects(id=product_id).first() if product_id else None
        if not product_obj:
            messages.error(request, "Please select a valid product.")
            return redirect('add_purchase')

        quantity = int(request.POST.get('Quantity', 0))
        purchase_price = float(request.POST.get('PurchasePrice', 0))
        total_amount = float(request.POST.get('TotalAmount', 0))
        payment_status = request.POST.get('PaymentStatus')

        # Update inventory stock
        invData = product_obj
        if invData:
            current_stock = int(invData.prodStockQty)
            new_stock = current_stock + quantity
            invData.prodStockQty = str(new_stock)
            invData.save()

        # Save purchase
        purchase = PurchaseMaster(
            purchaseInvoiceNo=invoice_no,
            purchaseDate=datetime.strptime(purchase_date, "%Y-%m-%d") if purchase_date else datetime.now(),
            purchaseSupplier=supplier_obj,
            purchaseProduct=product_obj,
            purchaseQuantity=quantity,
            purchasePrice=purchase_price,
            purchaseTotalAmount=total_amount,
            purchasePaymentStatus=payment_status
        )
        purchase.save()

        return redirect('purchases')

    return render(request, 'add_purchase.html', {
        "suppliers": suppliers,
        "products": products,
        "invoice_no": invoice_no
    })
    
@permission_required('edit_purchase')
def edit_purchase(request, purchase_id):

    purchase = PurchaseMaster.objects(id=purchase_id).first()
    suppliers = SupplierMaster.objects.all()
    products = InventoryMaster.objects.all()

    if request.method == 'POST':

        purchase_date = request.POST.get('PurchaseDate')
        supplier_id = request.POST.get('purchaseSupplier')
        product_id = request.POST.get('Product')

        # Validate supplier
        supplier_obj = SupplierMaster.objects(id=supplier_id).first() if supplier_id else None
        if not supplier_obj:
            messages.error(request, "Please select a valid supplier.")
            return redirect('edit_purchase', purchase_id=purchase_id)

        # Validate product
        product_obj = InventoryMaster.objects(id=product_id).first() if product_id else None
        if not product_obj:
            messages.error(request, "Please select a valid product.")
            return redirect('edit_purchase', purchase_id=purchase_id)

        quantity = int(request.POST.get('Quantity', 0))
        purchase_price = float(request.POST.get('PurchasePrice', 0))
        total_amount = float(request.POST.get('TotalAmount', 0))
        payment_status = request.POST.get('PaymentStatus')

        purchase.purchaseDate = datetime.strptime(purchase_date, "%Y-%m-%d") if purchase_date else datetime.now()
        purchase.purchaseSupplier = supplier_obj
        purchase.purchaseProduct = product_obj
        purchase.purchaseQuantity = quantity
        purchase.purchasePrice = purchase_price
        purchase.purchaseTotalAmount = total_amount
        purchase.purchasePaymentStatus = payment_status

        purchase.save()

        return redirect('purchases')

    return render(request,'edit_purchase.html',{
        "purchase": purchase,
        "suppliers": suppliers,
        "products": products
    })
@permission_required('delete_purchase')
def delete_purchase(request, purchase_id):
    purchase = PurchaseMaster.objects.get(id=purchase_id)
    purchase.delete()
    return redirect('purchases')


@permission_required('view_sales')
def sales(request):

    user_role = request.session.get('user_role')

    # 🔐 CUSTOMER → only own data
    if user_role == "Customer":
        email = request.session.get('customer_email')

        # ✅ STEP 1: Get customer object
        customer = CustomerMaster.objects(custEmail=email).first()

        if not customer:
            return redirect('login')

        # ✅ STEP 2: Use object (NOT __ join)
        salesData = SalesMaster.objects(salesCustomer=customer)

    else:
        # ADMIN / STAFF / MANAGER
        salesData = SalesMaster.objects.all()

    # ✅ Process Products List
    for sale in salesData:
        try:
            if isinstance(sale.salesProducts, str):
                sale.products_list = json.loads(sale.salesProducts)
            else:
                sale.products_list = sale.salesProducts if sale.salesProducts else []

            for item in sale.products_list:
                product_id = item.get('product_id')

                if product_id:
                    product = InventoryMaster.objects(id=product_id).first()
                    item['product_name'] = product.prodName if product else 'Unknown Product'

        except:
            sale.products_list = []

    return render(request, 'sales.html', {'sales': salesData})
# def add_sale(request):
#     customers = CustomerMaster.objects.all()
#     products = InventoryMaster.objects.all()
#     if request.method == 'POST':
#         invoice_no = request.POST.get('Invoiceno')
#         sales_date = request.POST.get('Date')
#         sales_customer = request.POST.get('Customer')
        
#         product_ids = request.POST.getlist('Product[]')
#         prices = request.POST.getlist('Price[]')
#         quantities = request.POST.getlist('Quantity[]')
#         totals = request.POST.getlist('Total[]')
        
#         products_list = []
#         total_quantity = 0
#         for i in range(len(product_ids)):
#             if product_ids[i]:
#                 products_list.append({
#                     'product_id': product_ids[i],
#                     'price': prices[i],
#                     'quantity': quantities[i],
#                     'total': totals[i]
#                 })
#                 total_quantity += int(quantities[i] if quantities[i] else 0)

#         subtotal = request.POST.get('Subtotal')
#         discount = request.POST.get('Discount')
#         tax = request.POST.get('Tax')
#         grand_total = request.POST.get('GrandTotal')
#         payment_mode = request.POST.get('PaymentMode')
#         paid_amount = request.POST.get('PaidAmount')
        
#         parsed_date = datetime.now()
#         if sales_date:
#             try:
#                 parsed_date = datetime.strptime(sales_date, "%Y-%m-%d")
#             except:
#                 pass

#         # Create and save the sale
#         sale = SalesMaster(     
#             salesInvoiceno=invoice_no,
#             salesDate=parsed_date,
#             salesCustomer=sales_customer,
#             salesProducts=json.dumps(products_list),
#             salesTotalQuantity=str(total_quantity),
#             salesTax=tax,
#             salesSubTotal=subtotal,
#             salesDiscount=discount,
#             salesGrandTotal=grand_total,
#             salesPaymentMode=payment_mode,
#             salesPaidAmount=paid_amount
#         )
#         sale.save()
#         return redirect('sales')
#     return render(request, 'add_sale.html', {'customers': customers, 'products': products})
@permission_required('add_sale')
def add_sale(request):
    customers = CustomerMaster.objects.all()
    products = InventoryMaster.objects.all()

    # Auto generate invoice
    invoice_no = generate_sales_invoice()

    if request.method == 'POST':

        sales_date = request.POST.get('Date')
        sales_customer_id = request.POST.get('Customer')
        customer_obj = CustomerMaster.objects(id=sales_customer_id).first()

        product_ids = request.POST.getlist('Product[]')
        prices = request.POST.getlist('Price[]')
        quantities = request.POST.getlist('Quantity[]')
        totals = request.POST.getlist('Total[]')

        products_list = []
        total_quantity = 0

        for i in range(len(product_ids)):

            if product_ids[i]:
                product = InventoryMaster.objects(id=product_ids[i]).first()
                
                if product:
                    try:
                        current_stock = int(product.prodStockQty) if product.prodStockQty else 0
                        new_stock = current_stock - int(quantities[i])
                        product.prodStockQty = str(new_stock)
                        product.save()
                    except ValueError:
                        pass
                
                products_list.append({
                    "product_id": product_ids[i],
                    "product_name": product.prodName if product else "Unknown",
                    "price": float(prices[i]),
                    "quantity": int(quantities[i]),
                    "total": float(totals[i])
                })

                total_quantity += int(quantities[i])

        subtotal = float(request.POST.get('Subtotal') or 0)
        discount = float(request.POST.get('Discount') or 0)
        tax = float(request.POST.get('Tax') or 0)
        grand_total = float(request.POST.get('GrandTotal') or 0)
        payment_mode = request.POST.get('PaymentMode')
        paid_amount = float(request.POST.get('PaidAmount') or 0)

        parsed_date = datetime.now()

        if sales_date:
            try:
                parsed_date = datetime.strptime(sales_date, "%Y-%m-%d")
            except:
                pass

        sale = SalesMaster(

            salesInvoiceno=invoice_no,
            salesDate=parsed_date,
            salesCustomer=customer_obj,

            salesProducts=products_list,   # ✅ LIST (not json)

            salesTotalQuantity=total_quantity,
            salesSubTotal=subtotal,
            salesTax=tax,
            salesDiscount=discount,
            salesGrandTotal=grand_total,

            salesPaymentMode=payment_mode,
            salesPaidAmount=paid_amount
        )

        sale.save()

        return redirect('sales')

    return render(request, 'add_sale.html', {
        'customers': customers,
        'products': products,
        'invoice_no': invoice_no
    })

@permission_required('delete_sale')
def delete_sale(request, sale_id):
    sale = SalesMaster.objects.get(id=sale_id)
    sale.delete()
    return redirect('sales')
@permission_required('edit_sale')
def edit_sale(request, sale_id):
    customers = CustomerMaster.objects.all()
    products = InventoryMaster.objects.all()
    
    sale = SalesMaster.objects.get(id=sale_id)
    
    # Pre-parse products if it's stored as JSON (for compatibility with old records)
    old_products = []
    if getattr(sale, 'salesProducts', None):
        if isinstance(sale.salesProducts, str):
            try:
                old_products = json.loads(sale.salesProducts)
            except:
                old_products = []
        else:
            old_products = sale.salesProducts

    if request.method == "POST":
        # 1. Revert Old Stock
        for item in old_products:
            prod_id = item.get('product_id')
            qty = int(item.get('quantity', 0))
            if prod_id:
                product = InventoryMaster.objects(id=prod_id).first()
                if product:
                    try:
                        current_stock = int(product.prodStockQty) if product.prodStockQty else 0
                        product.prodStockQty = str(current_stock + qty)
                        product.save()
                    except:
                        pass

        # 2. Update with New Data
        sale.salesInvoiceno = request.POST.get("Invoiceno")
        sales_date = request.POST.get("Date")
        sales_customer_id = request.POST.get("Customer")
        sale.salesCustomer = CustomerMaster.objects(id=sales_customer_id).first()
        
        product_ids = request.POST.getlist('Product[]')
        prices = request.POST.getlist('Price[]')
        quantities = request.POST.getlist('Quantity[]')
        totals = request.POST.getlist('Total[]')
        
        products_list = []
        total_quantity = 0
        for i in range(len(product_ids)):
            if product_ids[i]:
                # Update Stock for New Quantities
                product = InventoryMaster.objects(id=product_ids[i]).first()
                qty_val = int(quantities[i]) if quantities[i] else 0
                if product:
                    try:
                        current_stock = int(product.prodStockQty) if product.prodStockQty else 0
                        product.prodStockQty = str(current_stock - qty_val)
                        product.save()
                    except:
                        pass

                products_list.append({
                    'product_id': product_ids[i],
                    'product_name': product.prodName if product else "Unknown",
                    'price': float(prices[i]) if prices[i] else 0,
                    'quantity': qty_val,
                    'total': float(totals[i]) if totals[i] else 0
                })
                total_quantity += qty_val

        sale.salesProducts = products_list
        sale.salesTotalQuantity = total_quantity
        sale.salesSubTotal = float(request.POST.get("Subtotal") or 0)
        sale.salesDiscount = float(request.POST.get("Discount") or 0)
        sale.salesTax = float(request.POST.get("Tax") or 0)
        sale.salesGrandTotal = float(request.POST.get("GrandTotal") or 0)
        sale.salesPaymentMode = request.POST.get("PaymentMode")
        sale.salesPaidAmount = float(request.POST.get("PaidAmount") or 0)

        if sales_date:
            try:
                sale.salesDate = datetime.strptime(sales_date, "%Y-%m-%d")
            except:
                pass

        sale.save()
        return redirect('sales')

    context = {
        "sale": sale,
        "sale_products": old_products,
        "customers": customers,
        "products": products
    }

    return render(request, "edit_sale.html", context)
@permission_required('view_reports')
def reports(request):
    import json
    from datetime import datetime
    
    report_type = request.GET.get('report_type', 'all')
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')
    
    from_date = None
    to_date = None

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # =========================
    # FETCH DATA
    # =========================
    all_purchases = list(PurchaseMaster.objects.all())
    all_sales = list(SalesMaster.objects.all())

    # =========================
    # FILTER PURCHASES
    # =========================
    if from_date or to_date:
        filtered_purchases = []
        for p in all_purchases:
            p_date = getattr(p, 'purchaseDate', None)
            if p_date:
                pd = p_date.date() if hasattr(p_date, 'date') else p_date
                if from_date and pd < from_date:
                    continue
                if to_date and pd > to_date:
                    continue
                filtered_purchases.append(p)
        all_purchases = filtered_purchases

    # =========================
    # FILTER SALES
    # =========================
    if from_date or to_date:
        filtered_sales = []
        for s in all_sales:
            s_date = getattr(s, 'salesDate', None)
            if s_date:
                sd = s_date.date() if hasattr(s_date, 'date') else s_date
                if from_date and sd < from_date:
                    continue
                if to_date and sd > to_date:
                    continue
                filtered_sales.append(s)
        all_sales = filtered_sales

    # =========================
    # TOTAL PURCHASE
    # =========================
    total_purchase = 0
    for purchase in all_purchases:
        try:
            total_purchase += float(purchase.purchaseTotalAmount or 0)
        except ValueError:
            pass

    # =========================
    # TOTAL SALES
    # =========================
    total_sales = 0
    total_orders = len(all_sales)
    report_details = []

    # =========================
    # SALES DATA
    # =========================
    if report_type in ('all', 'sales'):
        for sale in all_sales:
            try:
                gt = float(sale.salesGrandTotal or 0)
                total_sales += gt

                cust_name = "Unknown Customer"
                if getattr(sale, 'salesCustomer', None) and hasattr(sale.salesCustomer, 'custName'):
                    cust_name = sale.salesCustomer.custName

                s_date = getattr(sale, 'salesDate', None)

                report_details.append({
                    'invoice': getattr(sale, 'salesInvoiceno', 'N/A'),
                    'date': s_date.strftime('%d-%m-%Y') if s_date else 'N/A',
                    'raw_date': s_date or datetime.min,
                    'party': cust_name,
                    'amount': gt,
                    'type': 'Sale'
                })
            except:
                pass
    else:
        for sale in all_sales:
            try:
                total_sales += float(sale.salesGrandTotal or 0)
            except:
                pass

    # =========================
    # PURCHASE DATA
    # =========================
    if report_type in ('all', 'purchase'):
        for purchase in all_purchases:
            try:
                amt = float(purchase.purchaseTotalAmount or 0)
                party = getattr(purchase, 'purchaseSupplier', "Unknown Supplier")
                p_date = getattr(purchase, 'purchaseDate', None)

                report_details.append({
                    'invoice': getattr(purchase, 'purchaseInvoiceNo', 'N/A'),
                    'date': p_date.strftime('%d-%m-%Y') if p_date else 'N/A',
                    'raw_date': p_date or datetime.min,
                    'party': party,
                    'amount': amt,
                    'type': 'Purchase'
                })
            except:
                pass

    # =========================
    # SORT
    # =========================
    report_details.sort(key=lambda x: x['raw_date'], reverse=True)

    net_profit = total_sales - total_purchase

    # =========================
    # PERFORMANCE CHART
    # =========================
    all_inventory = InventoryMaster.objects.all()

    sorted_inventory = sorted(
        [item for item in all_inventory if item.prodStockQty and str(item.prodStockQty).isdigit()],
        key=lambda x: int(x.prodStockQty),
        reverse=True
    )[:10]

    performance_data = [
        {"label": item.prodName, "y": int(item.prodStockQty)}
        for item in sorted_inventory
    ]

    # =========================
    # PIE CHART (FINAL FIX)
    # =========================
    category_stock = {}
    total_stock_qty = 0

    for item in all_inventory:
        cat = str(item.prodCategory).strip() if item.prodCategory else ""
        if not cat or cat.lower() in ["none", "null", "unknown"]:
          continue
        try:
            qty = int(item.prodStockQty) if item.prodStockQty and str(item.prodStockQty).isdigit() else 0
            category_stock[cat] = category_stock.get(cat, 0) + qty
            total_stock_qty += qty
        except:
            pass

    distribution_data = []

    # ✅ FINAL SAFE LOGIC
    if total_stock_qty == 0:
        distribution_data = [{"label": "No Data", "y": 100}]
    else:
        for cat, qty in category_stock.items():
            percentage = (qty / total_stock_qty) * 100

            distribution_data.append({
                "label": cat if cat else "Unknown",
                "y": round(percentage, 2)
            })

    # =========================
    # CONTEXT
    # =========================
    context = {
        'total_sales': total_sales,
        'total_purchase': total_purchase,
        'net_profit': net_profit,
        'total_orders': total_orders,
        'report_details': report_details,
        'performance_data': json.dumps(performance_data),
        'distribution_data': json.dumps(distribution_data),
        'report_type': report_type,
        'from_date': from_date_str,
        'to_date': to_date_str,
    }

    return render(request, 'reports.html', context)
@permission_required('view_users')
def manage_users(request):
    userData = ManageUser.objects.all()
    
    return render(request, 'manageUsers.html', {'users': userData})
@permission_required('add_user')
def add_user(request): 
    if request.method == 'POST':
        profileImage = request.FILES.get('ProfileImage')
        name = request.POST.get('Fname')
        username = request.POST.get('Username')
        password = request.POST.get('Password')
        email = request.POST.get('Email')
        lastlogin = request.POST.get('LastLogin')
        role = request.POST.get('Role')
        status = request.POST.get('Status') == True  # Checkbox value

        user = ManageUser(
            userProfile=profileImage,
            userFname=name,
            userUsername=username,
            userEmail=email,
            userLastLogin=lastlogin,
            userPassword=password,
            userRole=role,
            userStatus=True
        )
        user.save()
        return redirect('manage_users') 
    
    roles = RoleMaster.objects.all()
    return render(request, 'add_user.html', {'roles': roles})
@permission_required('edit_user')
def edit_user(request, user_id):
    user = ManageUser.objects.get(id=user_id)
    if request.method == 'POST':
        profileImage = request.FILES.get('ProfileImage')
        name = request.POST.get('Fname')
        username = request.POST.get('Username')
        password = request.POST.get('Password')
        email = request.POST.get('Email')
        lastlogin = request.POST.get('LastLogin')
        role = request.POST.get('Role')
        user.userStatus = 'Status' in request.POST

        user.userFname = name
        user.userUsername = username
        user.username = username
        user.userEmail = email
        user.userLastLogin = lastlogin # Keep existing value if not provided
        user.userPassword = password
        user.userRole = role
        
        if profileImage:
            user.userProfile.replace(profileImage, content_type=profileImage.content_type)
        
        user.save()
        return redirect('manage_users') 
    
    roles = RoleMaster.objects.all()
    return render(request, 'edit_user.html', {'user_id': user_id,'user': user, 'roles': roles})
@permission_required('delete_user')
def delete_user(request, user_id):
    user = ManageUser.objects.get(id=user_id)
    user.delete()
    return redirect('manage_users')

def get_user_profile(request, id):
    user = ManageUser.objects.get(id=id)
    if user.userProfile:
        image_data = user.userProfile.read()
        return HttpResponse(image_data, content_type=user.userProfile.content_type)
    else:
        return HttpResponse(status=404)
    
@permission_required('view_roles')
def roles(request):
    roles = RoleMaster.objects.all()
    return render(request, 'roles.html', {'roles': roles})
@permission_required('add_role')
def add_role(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        permissions = request.POST.getlist('permissions[]')

        role = RoleMaster(
            name=name,
            description=description,
            permissions=', '.join(permissions)
        )
        role.save()
        return redirect('roles')
    return render(request, 'add_role.html') 
@permission_required('edit_role')
def edit_role(request, role_id):
    role = RoleMaster.objects.get(id=role_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        permissions = request.POST.getlist('permissions[]')

        role.name = name
        role.description = description
        role.permissions = ', '.join(permissions)
        
        role.save()
        return redirect('roles')
    return render(request, 'edit_role.html', {'role_id': role_id,'role': role})
@permission_required('delete_role')
def delete_role(request, role_id):
    role = RoleMaster.objects.get(id=role_id)
    role.delete()
    return redirect('roles')



def login(request):
    # ✅ Default Admin create
    if not ManageUser.objects(userEmail='admin@example.com').first():
        ManageUser(
            userFname='Admin',
            userUsername='admin',
            userEmail='admin@example.com',
            userPassword='Admin@123',
            userRole='Admin',
            userStatus=True
        ).save()

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # 🔐 1. CHECK ManageUser (Admin, Staff, etc.)
        user = ManageUser.objects(userEmail=email, userPassword=password).first()

        if user:
            if not user.userStatus:
                return render(request, 'login.html', {'error': 'Your account is deactivated.'})
            
            # ✅ SESSION STORE
            request.session['is_logged_in'] = True
            request.session['user_id'] = str(user.id)
            request.session['user_role'] = user.userRole
            request.session['user_name'] = user.userFname
            
            # ✅ PERMISSIONS
            user_permissions = []
            if user.userRole != 'Admin':
                role_obj = RoleMaster.objects(name=user.userRole).first()
                if role_obj and role_obj.permissions:
                    user_permissions = [p.strip() for p in role_obj.permissions.split(',') if p.strip()]
            
            request.session['user_permissions'] = user_permissions
            
            user.userLastLogin = datetime.now()
            user.save()

            # ✅ ROLE BASED REDIRECT
            if user.userRole in ['Admin', 'Staff', 'Manager']:
                return redirect('dashboard')
            elif user.userRole in ['Sales Executive', 'Customer']:
                return redirect('sales')
            else:
                return redirect('dashboard')

        # 🔥 2. CHECK CustomerMaster (IMPORTANT FIX)
        customer = CustomerMaster.objects(custEmail=email).first()

        if customer and password == "123456":   # default password
            request.session['is_logged_in'] = True
            request.session['customer_email'] = customer.custEmail
            request.session['user_role'] = "Customer"
            request.session['user_name'] = customer.custName

            # ✅ 🔥 VERY IMPORTANT FIX (UI + PERMISSION ISSUE SOLVED)
            request.session['user_permissions'] = ['view_sales']
            request.session['user_id'] = str(customer.id)

            return redirect('sales')

        return render(request, 'login.html', {'error': 'Invalid email or password.'})
        
    return render(request, 'login.html')

def send_otp(request):
    if request.method == "POST":
        email = request.POST.get('email')

        otp = random.randint(100000,999999)

        request.session['otp'] = otp
        request.session['email'] = email

        send_mail(
            'Your Login OTP',
            f'Your OTP is {otp}',
            'yourgmail@gmail.com',
            [email],
            fail_silently=False
        )

        return redirect('verify_otp')

    return redirect('login')
def verify_otp(request):
    if request.method == "POST":
        user_otp = request.POST.get('otp')
        otp = request.session.get('otp')

        if otp and str(otp) == user_otp:
            request.session['is_logged_in'] = True
            return redirect('dashboard')

        else:
            return render(request,'verify_otp.html',{'error':'Invalid OTP'})

    return render(request,'verify_otp.html')

    
@role_required(['Admin','Staff','Manager','Customer','Sales Executive']) # Example: User and Manager can view their profile
def profile(request):
    user_id = request.session.get('user_id')

    user = ManageUser.objects(id=user_id).first()

    return render(request, 'profile.html', {'user': user})

def logout(request):
    request.session.flush()
    return redirect('login')
