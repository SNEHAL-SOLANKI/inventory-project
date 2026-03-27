import datetime
from mongoengine import *
from datetime import datetime
from django.db import models
from django.forms import IntegerField
from mongoengine import NULLIFY
from mongoengine import Document,IntField,FloatField, ReferenceField, StringField, ImageField, BooleanField, DateTimeField,ListField,DictField

# Create your models here.
class AdminMaster(Document):
    admName = StringField() 
    admEmail = StringField()
    admPassword = StringField()
    admStatus = StringField()
    
class CategoryMaster(Document):
    catName = StringField()
    catCode = StringField()
    catDescription = StringField()
    catImage = ImageField()
    catstatus = BooleanField(default=True)
    catDate = DateTimeField(auto_now_add=True)
    
class SupplierMaster(Document):
    supName = StringField()
    supCode = StringField()
    supPhone = StringField()
    supEmail = StringField()
    supGST = StringField()
    supCity = StringField()
    supAddress = StringField()
    supStatus = BooleanField(default=True)
    
class CustomerMaster(Document):
    custName = StringField()
    custCode = StringField()
    custEmail = StringField()
    custMobile = StringField()
    custGST = StringField()
    custAddress = StringField()
    custStatus = BooleanField(default=True)
    user = StringField()
    
class InventoryMaster(Document):
    meta = {'strict': False}

    prodName = StringField()
    prodCode = StringField()
    prodCategory = ReferenceField(CategoryMaster)
    
    prodPurchasePrice = FloatField()
    prodSellingPrice = FloatField()
    prodStockQty = StringField()
    
    reorderLevel = IntField(default=5)
    reorderQuantity = IntField(default=10)
    profit = FloatField() 
    
    prodSupplier = ReferenceField(SupplierMaster, null=True)
    prodBarcode = StringField()
    prodLastUpdated = DateTimeField(default=datetime.now)
    prodUnit = StringField()
    prodImage = ImageField()
    prodDescription = StringField()
    prodStatus = BooleanField(default=True)
    
class ManageUser(Document):
    userProfile = ImageField()
    userFname = StringField()
    userUsername = StringField()
    userName = StringField()
    userEmail = StringField()
    userPassword = StringField()
    userRole = StringField()
    userStatus = BooleanField(default=True)
    userLastLogin = DateTimeField(default=datetime.now)
    
class PurchaseMaster(Document):
    purchaseInvoiceNo = StringField()
    purchaseDate = DateTimeField(default=datetime.now)
    purchaseSupplier = ReferenceField(SupplierMaster, null=True)
    purchaseProduct = ReferenceField(InventoryMaster, reverse_delete_rule=NULLIFY, null=True)
    purchaseQuantity = IntField()
    purchasePrice = FloatField()
    purchaseTotalAmount = FloatField()
    purchasePaymentStatus = StringField()
    
class SalesMaster(Document):
    salesInvoiceno = StringField()
    salesDate = DateTimeField()
    salesCustomer = ReferenceField(CustomerMaster)

    salesProducts = ListField(DictField())

    salesTotalQuantity = IntField()
    salesSubTotal = FloatField()
    salesTax = FloatField()
    salesDiscount = FloatField()
    salesGrandTotal = FloatField()

    salesPaymentMode = StringField()
    salesPaidAmount = FloatField()
    



class RoleMaster(Document):
    name = StringField()
    description = StringField()
    permissions = StringField()
    created_date = DateTimeField(default=datetime.now)
    
    



class Customer(models.Model):
    custName = models.CharField(max_length=100)

    def __str__(self):
        return self.custName


class Product(models.Model):
    prodName = models.CharField(max_length=100)
    stock = models.IntegerField(default=0)
    price = models.FloatField(default=0)

    def __str__(self):
        return self.prodName


class Sale(models.Model):
    Customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    Invoiceno = models.CharField(max_length=50)
    Date = models.DateField()
    Subtotal = models.FloatField(default=0)
    Discount = models.FloatField(default=0)
    Tax = models.FloatField(default=0)
    GrandTotal = models.FloatField(default=0)
    PaymentMode = models.CharField(max_length=20, choices=[('Cash','Cash'),('UPI','UPI'),('Card','Card')])
    PaidAmount = models.FloatField(default=0)

    def __str__(self):
        return f"{self.Invoiceno} - {self.Customer}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    Product = models.ForeignKey(Product, on_delete=models.CASCADE)
    Stock = models.IntegerField(default=0)
    Price = models.FloatField(default=0)
    Quantity = models.IntegerField(default=1)
    Total = models.FloatField(default=0)