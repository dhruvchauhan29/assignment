"""
Tests for Milestone 1: Foundation - User Can Start
Tests input validation for project creation.
"""
import pytest
from io import BytesIO


def test_create_project_empty_product_request(client, auth_token):
    """Test that empty product request returns 400."""
    response = client.post(
        "/api/projects",
        data={
            "name": "Test Project",
            "product_request": "   ",  # Empty/whitespace only
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_create_project_valid_request(client, auth_token):
    """Test that valid project request succeeds."""
    response = client.post(
        "/api/projects",
        data={
            "name": "Valid Project",
            "product_request": "Build a web application",
            "description": "Test description"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Valid Project"
    assert data["product_request"] == "Build a web application"


def test_create_project_with_file_too_large(client, auth_token):
    """Test that files over 20MB return 413."""
    # Create a file larger than 20MB
    large_content = b"x" * (21 * 1024 * 1024)  # 21 MB
    
    response = client.post(
        "/api/projects",
        data={
            "name": "Test Project",
            "product_request": "Build something",
        },
        files={"files": ("large_file.txt", BytesIO(large_content), "text/plain")},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 413
    assert "20MB" in response.json()["detail"]


def test_create_project_with_unsupported_file_type(client, auth_token):
    """Test that unsupported file types return 415."""
    # Create an executable file (unsupported)
    file_content = b"#!/bin/bash\necho 'test'"
    
    response = client.post(
        "/api/projects",
        data={
            "name": "Test Project",
            "product_request": "Build something",
        },
        files={"files": ("script.sh", BytesIO(file_content), "application/x-sh")},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 415
    assert "not supported" in response.json()["detail"]


def test_create_project_with_valid_pdf(client, auth_token):
    """Test that valid PDF upload succeeds."""
    # Create a minimal PDF-like content
    pdf_content = b"%PDF-1.4\nTest content"
    
    response = client.post(
        "/api/projects",
        data={
            "name": "Test Project",
            "product_request": "Build something",
        },
        files={"files": ("doc.pdf", BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["documents"] is not None
    assert len(data["documents"]) == 1
    assert data["documents"][0]["filename"] == "doc.pdf"


def test_create_project_with_multiple_valid_files(client, auth_token):
    """Test that multiple valid files succeed."""
    files = [
        ("files", ("doc1.txt", BytesIO(b"content1"), "text/plain")),
        ("files", ("doc2.md", BytesIO(b"content2"), "text/markdown")),
    ]
    
    response = client.post(
        "/api/projects",
        data={
            "name": "Test Project",
            "product_request": "Build something",
        },
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["documents"]) == 2


def test_create_project_without_auth(client):
    """Test that creating project without auth returns 401."""
    response = client.post(
        "/api/projects",
        data={
            "name": "Test Project",
            "product_request": "Build something",
        }
    )
    assert response.status_code == 401
