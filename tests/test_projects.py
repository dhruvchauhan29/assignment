"""
Tests for project endpoints.
"""
from app.database import Project


def test_create_project(client, auth_token):
    """Test creating a project."""
    response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Project",
            "description": "A test project",
            "product_request": "Build a simple todo app"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert data["product_request"] == "Build a simple todo app"


def test_create_project_no_auth(client):
    """Test creating a project without authentication."""
    response = client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "product_request": "Build something"
        }
    )
    assert response.status_code == 401


def test_list_projects(client, auth_token, db, test_user):
    """Test listing projects."""
    # Create a project
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()

    response = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Project"


def test_get_project(client, auth_token, db, test_user):
    """Test getting a specific project."""
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.get(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project.id
    assert data["name"] == "Test Project"


def test_update_project(client, auth_token, db, test_user):
    """Test updating a project."""
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.put(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"name": "Updated Project"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Project"


def test_delete_project(client, auth_token, db, test_user):
    """Test deleting a project."""
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.delete(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 204

    # Verify deletion
    response = client.get(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404


def test_create_project_empty_product_request(client, auth_token):
    """Test creating a project with empty product request."""
    response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Project",
            "description": "A test project",
            "product_request": ""
        }
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Product Request cannot be empty" in str(error) for error in data["detail"])


def test_create_project_whitespace_only_product_request(client, auth_token):
    """Test creating a project with whitespace-only product request."""
    response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Project",
            "description": "A test project",
            "product_request": "   \n\t   "
        }
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Product Request cannot be empty" in str(error) for error in data["detail"])


def test_create_project_trims_whitespace(client, auth_token):
    """Test that product request whitespace is trimmed."""
    response = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Project",
            "description": "A test project",
            "product_request": "  Build a simple todo app  "
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["product_request"] == "Build a simple todo app"


def test_update_project_empty_product_request(client, auth_token, db, test_user):
    """Test updating a project with empty product request."""
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.put(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"product_request": ""}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Product Request cannot be empty" in str(error) for error in data["detail"])


def test_update_project_whitespace_only_product_request(client, auth_token, db, test_user):
    """Test updating a project with whitespace-only product request."""
    project = Project(
        name="Test Project",
        product_request="Build something",
        owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.put(
        f"/api/projects/{project.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"product_request": "   \n\t   "}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Product Request cannot be empty" in str(error) for error in data["detail"])
