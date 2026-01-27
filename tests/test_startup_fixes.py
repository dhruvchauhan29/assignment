"""
Test startup and initialization to verify both runtime errors are fixed.
"""
import pytest
from app.auth.utils import get_password_hash, verify_password
from app.auth.schemas import UserCreate
from app.database import User, UserRole


def test_email_validator_works():
    """Test that email-validator is installed and EmailStr validation works."""
    # This will fail if email-validator is not installed
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    
    assert user_data.email == "test@example.com"
    assert user_data.username == "testuser"


def test_invalid_email_rejected():
    """Test that invalid emails are rejected by EmailStr validation."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        UserCreate(
            username="testuser",
            email="not-an-email",
            password="testpass123"
        )


def test_bcrypt_password_hashing():
    """Test that bcrypt password hashing works correctly."""
    password = "admin123"
    
    # Hash the password
    hashed = get_password_hash(password)
    
    # Verify it's a valid bcrypt hash (starts with $2b$ or $2a$)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    
    # Verify the password length is reasonable (bcrypt hashes are 60 bytes)
    assert len(hashed) == 60
    
    # Verify password verification works
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_admin_user_creation(db):
    """Test that admin user can be created with bcrypt password hashing."""
    # Create admin user (mimics init_db.py behavior)
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    # Verify admin was created
    assert admin.id is not None
    assert admin.username == "admin"
    assert admin.email == "admin@example.com"
    assert admin.role == UserRole.ADMIN
    
    # Verify password hash is valid
    assert len(admin.hashed_password) == 60
    assert verify_password("admin123", admin.hashed_password) is True


def test_long_password_rejected():
    """Test that very long passwords are rejected (bcrypt 72 byte limit)."""
    # Create a password longer than 72 bytes
    long_password = "a" * 100
    
    with pytest.raises(ValueError) as exc_info:
        get_password_hash(long_password)
    
    assert "too long" in str(exc_info.value).lower()
    assert "72 bytes" in str(exc_info.value)


def test_multiple_users_with_different_passwords(db):
    """Test creating multiple users with different passwords."""
    users_data = [
        ("user1", "user1@example.com", "password1"),
        ("user2", "user2@example.com", "password2"),
        ("user3", "user3@example.com", "password3"),
    ]
    
    created_users = []
    for username, email, password in users_data:
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.USER
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        created_users.append((user, password))
    
    # Verify each user's password
    for user, password in created_users:
        assert verify_password(password, user.hashed_password) is True
        # Verify wrong password fails
        assert verify_password("wrongpassword", user.hashed_password) is False
