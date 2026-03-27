from django.core.management.base import BaseCommand
from inventory.models import ManageUser, RoleMaster
from datetime import datetime

class Command(BaseCommand):
    help = 'Create default roles and admin user'

    def handle(self, *args, **options):
        # 1. Create Default Roles
        roles = [
            {'name': 'Admin', 'description': 'Full system access'},
            {'name': 'Manager', 'description': 'Access to inventory, masters, and transactions'},
            {'name': 'Staff', 'description': 'Access to inventory and categories'},
            {'name': 'Sales Executive', 'description': 'Access to customers and sales'},
        ]

        for role_data in roles:
            if not RoleMaster.objects(name=role_data['name']).first():
                RoleMaster(**role_data).save()
                self.stdout.write(self.style.SUCCESS(f"Created role: {role_data['name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Role already exists: {role_data['name']}"))

        # 2. Create Default Admin in ManageUser
        if not ManageUser.objects(userEmail='admin@example.com').first():
            ManageUser(
                userFname='Admin',
                userUsername='admin',
                userEmail='admin@example.com',
                userPassword='Admin@123',
                userRole='Admin',
                userStatus=True
            ).save()
            self.stdout.write(self.style.SUCCESS("Created default admin in ManageUser: admin@example.com / Admin@123"))
        else:
            self.stdout.write(self.style.WARNING("Default admin in ManageUser already exists"))

        self.stdout.write(self.style.SUCCESS("Database initialization complete."))
