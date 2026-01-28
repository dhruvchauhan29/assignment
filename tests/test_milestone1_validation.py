"""
Tests for Milestone 1: Foundation - User Can Start
Tests input validation for project creation.
"""
import pytest


def test_create_project_empty_product_request(client, auth_token):
    """Test that empty product request returns 400."""
    response = client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "product_request": "   ",  # Empty/whitespace only
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422  # Pydantic validation error
    assert "product_request" in str(response.json()).lower()


def test_create_project_valid_request(client, auth_token):
    """Test that valid project request succeeds."""
    response = client.post(
        "/api/projects",
        json={
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


def test_create_project_without_auth(client):
    """Test that creating project without auth returns 401."""
    response = client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "product_request": "Build something",
        }
    )
    assert response.status_code == 401
