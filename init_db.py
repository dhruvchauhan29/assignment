"""
Initialize the database with tables.
"""
from app.database import init_db, engine, Base, SessionLocal, User, UserRole
from app.auth.utils import get_password_hash


def create_admin_user():
    """Create a default admin user if none exists."""
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN
            )
            db.add(admin)
            db.commit()
            print("✅ Created default admin user (username: admin, password: admin123)")
        else:
            print("ℹ️  Admin user already exists")
    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database tables created")
    
    print("\n🔧 Creating default admin user...")
    create_admin_user()
    
    print("\n✅ Database initialization complete!")
    print("\nYou can now start the server with:")
    print("  uvicorn app.main:app --reload")
