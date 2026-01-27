# API Usage Examples

Complete guide to using the AI Product-to-Code System API.

## Authentication

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123"
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "role": "user",
  "created_at": "2024-01-20T10:00:00"
}
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "SecurePass123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save this token for subsequent requests:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Get Current User Info

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

## Project Management

### 1. Create a Project

```bash
curl -X POST "http://localhost:8000/api/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-commerce Platform",
    "description": "Modern e-commerce platform with AI features",
    "product_request": "Build a complete e-commerce platform with:\n- Product catalog with search and filters\n- Shopping cart and checkout\n- Payment processing (Stripe integration)\n- User accounts and order history\n- Admin dashboard for inventory management\n- AI-powered product recommendations\n- Real-time order tracking"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "E-commerce Platform",
  "description": "Modern e-commerce platform with AI features",
  "product_request": "Build a complete e-commerce platform with...",
  "owner_id": 1,
  "created_at": "2024-01-20T10:05:00",
  "updated_at": "2024-01-20T10:05:00"
}
```

### 2. List Your Projects

```bash
curl -X GET "http://localhost:8000/api/projects" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Get Project Details

```bash
curl -X GET "http://localhost:8000/api/projects/1" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Update Project

```bash
curl -X PUT "http://localhost:8000/api/projects/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description"
  }'
```

### 5. Delete Project

```bash
curl -X DELETE "http://localhost:8000/api/projects/1" \
  -H "Authorization: Bearer $TOKEN"
```

## Run Execution

### 1. Create a Run

```bash
curl -X POST "http://localhost:8000/api/runs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1
  }'
```

**Response:**
```json
{
  "id": 1,
  "project_id": 1,
  "status": "pending",
  "current_stage": "initialized",
  "error_message": null,
  "started_at": null,
  "completed_at": null,
  "created_at": "2024-01-20T10:10:00",
  "total_tokens": 0,
  "prompt_tokens": 0,
  "completion_tokens": 0
}
```

### 2. Start Run Execution

```bash
curl -X POST "http://localhost:8000/api/runs/1/start" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "status": "started",
  "run_id": 1
}
```

### 3. Monitor Progress with SSE

Using curl (streaming):
```bash
curl -N "http://localhost:8000/api/runs/1/progress" \
  -H "Authorization: Bearer $TOKEN"
```

**SSE Stream Output:**
```
event: connected
data: {"run_id": 1, "status": "running", "current_stage": "research"}

event: progress
data: {"stage": "research", "message": "Research phase started", "timestamp": "2024-01-20T10:10:05"}

event: progress
data: {"stage": "epics", "message": "Epic generation completed", "timestamp": "2024-01-20T10:12:30"}

event: complete
data: {"run_id": 1, "status": "completed", "message": "Run completed"}
```

Using JavaScript:
```javascript
const evtSource = new EventSource('http://localhost:8000/api/runs/1/progress', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
});

evtSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Stage: ${data.stage}, Message: ${data.message}`);
});

evtSource.addEventListener('complete', (event) => {
  console.log('Run completed!');
  evtSource.close();
});
```

### 4. Get Run Details

```bash
curl -X GET "http://localhost:8000/api/runs/1" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Pause Run

```bash
curl -X POST "http://localhost:8000/api/runs/1/pause" \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Resume Run

```bash
curl -X POST "http://localhost:8000/api/runs/1/start" \
  -H "Authorization: Bearer $TOKEN"
```

## Approvals

### 1. View Pending Approvals

```bash
curl -X GET "http://localhost:8000/api/runs/1/approvals" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
[
  {
    "id": 1,
    "run_id": 1,
    "stage": "epics",
    "approved": null,
    "feedback": null,
    "created_at": "2024-01-20T10:12:30",
    "updated_at": "2024-01-20T10:12:30"
  }
]
```

### 2. Approve Epics

```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/epics" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "feedback": "Epics look good, proceed to stories"
  }'
```

### 3. Reject and Request Changes

```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/epics" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "feedback": "Need more detail on authentication epic"
  }'
```

### 4. Approve Stories

```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/stories" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "feedback": "User stories are comprehensive"
  }'
```

### 5. Approve Specifications

```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/specs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "feedback": "Technical specs approved, proceed to code generation"
  }'
```

## Artifacts

### 1. List All Artifacts

```bash
curl -X GET "http://localhost:8000/api/runs/1/artifacts" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
[
  {
    "id": 1,
    "run_id": 1,
    "artifact_type": "research",
    "name": "research.md",
    "content": "# Research Findings\n\n...",
    "metadata": {"urls": [...], "total_urls": 5},
    "created_at": "2024-01-20T10:11:00"
  },
  {
    "id": 2,
    "run_id": 1,
    "artifact_type": "epics",
    "name": "epics.md",
    "content": "# Project Epics\n\n...",
    "metadata": {"epic_count": 5, "has_mermaid": true},
    "created_at": "2024-01-20T10:12:30"
  }
]
```

## Export

### 1. Export All Artifacts as Markdown

```bash
curl -X GET "http://localhost:8000/api/export/1/artifacts.md" \
  -H "Authorization: Bearer $TOKEN" \
  -o project_artifacts.md
```

### 2. Export Code Bundle as ZIP

```bash
curl -X GET "http://localhost:8000/api/export/1/code.zip" \
  -H "Authorization: Bearer $TOKEN" \
  -o code_bundle.zip
```

### 3. Export Validation Report

```bash
curl -X GET "http://localhost:8000/api/export/1/validation.md" \
  -H "Authorization: Bearer $TOKEN" \
  -o validation_report.md
```

## Admin Endpoints

*Note: These require admin role*

### 1. List All Users

```bash
curl -X GET "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 2. Delete User

```bash
curl -X DELETE "http://localhost:8000/api/admin/users/2" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 3. List All Projects

```bash
curl -X GET "http://localhost:8000/api/admin/projects" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 4. Delete Project

```bash
curl -X DELETE "http://localhost:8000/api/admin/projects/1" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Python Client Example

```python
import requests
import json

class AIProductClient:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def register(self, username, email, password):
        response = requests.post(
            f"{self.base_url}/api/auth/register",
            json={"username": username, "email": email, "password": password}
        )
        return response.json()
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        data = response.json()
        self.token = data["access_token"]
        self.headers["Authorization"] = f"Bearer {self.token}"
        return data
    
    def create_project(self, name, product_request, description=None):
        response = requests.post(
            f"{self.base_url}/api/projects",
            headers=self.headers,
            json={
                "name": name,
                "product_request": product_request,
                "description": description
            }
        )
        return response.json()
    
    def create_run(self, project_id):
        response = requests.post(
            f"{self.base_url}/api/runs",
            headers=self.headers,
            json={"project_id": project_id}
        )
        return response.json()
    
    def start_run(self, run_id):
        response = requests.post(
            f"{self.base_url}/api/runs/{run_id}/start",
            headers=self.headers
        )
        return response.json()
    
    def approve(self, run_id, stage, approved, feedback=None):
        response = requests.post(
            f"{self.base_url}/api/runs/{run_id}/approvals/{stage}",
            headers=self.headers,
            json={"approved": approved, "feedback": feedback}
        )
        return response.json()
    
    def get_artifacts(self, run_id):
        response = requests.get(
            f"{self.base_url}/api/runs/{run_id}/artifacts",
            headers=self.headers
        )
        return response.json()

# Usage
client = AIProductClient()

# Login
client.login("johndoe", "SecurePass123")

# Create project
project = client.create_project(
    name="My App",
    product_request="Build a simple todo application"
)

# Start run
run = client.create_run(project["id"])
client.start_run(run["id"])

# Later: Approve stages
client.approve(run["id"], "epics", approved=True, feedback="Looks good!")
client.approve(run["id"], "stories", approved=True)
client.approve(run["id"], "specs", approved=True)

# Get results
artifacts = client.get_artifacts(run["id"])
for artifact in artifacts:
    print(f"{artifact['artifact_type']}: {artifact['name']}")
```

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `204`: No Content (successful deletion)
- `400`: Bad Request (validation error)
- `401`: Unauthorized (missing or invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

*Note: Rate limiting not implemented yet but recommended for production*

Recommended limits:
- Authentication endpoints: 5 requests per minute
- API endpoints: 100 requests per minute
- SSE connections: 5 concurrent connections per user

## Webhooks

*Note: Webhooks not implemented yet but could be added for:*
- Run completion notifications
- Stage approval requests
- Error notifications
