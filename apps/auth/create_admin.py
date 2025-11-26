import sys
from getpass import getpass
from core.database import SessionLocal
from apps.auth.models import UserModel, Role
from apps.auth.services import get_password_hash

def create_admin():
    db = SessionLocal()
    # Ensure all roles exist
    roles_to_create = [
        ("admin", "Administrator"),
        ("mechanic", "Mechanic"),
        ("customer", "Customer")
    ]
    
    for role_name, description in roles_to_create:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description=description)
            db.add(role)
            print(f"Created role: {role_name}")
    
    db.commit()
    
    # Create admin user
    email = input("Admin email: ")
    name = input("Admin name: ")
    password = getpass("Admin password: ")
    hashed_password = get_password_hash(password)
    
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    admin = UserModel(name=name, email=email, hashed_password=hashed_password, role=admin_role)
    db.add(admin)
    db.commit()
    print("Admin account created with admin role.")
    print("All roles (admin, mechanic, customer) have been initialized.")

if __name__ == "__main__":
    create_admin()