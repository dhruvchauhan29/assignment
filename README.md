# AI Product-to-Code System

A backend-only multi-agent AI system that transforms high-level Product Requests into Epics → User Stories → Formal Specs → Working Code with automated validation.

## 🎯 Features

### ✨ Milestone-Driven Workflow
- **Foundation (Milestone 1)**: Complete project creation with input validation for text-only Product Requests
- **Research-First (Milestone 2)**: Mandatory evidence-based research before planning
- **Comprehensive Epics (Milestone 3)**: Full epic planning with priorities, dependencies, risks, and Mermaid diagrams
- **Approval Gates**: User approval with regeneration support at every stage
- **Interruptible Execution**: Pause/resume workflow at any point

### 🔧 Core Capabilities
- **Multi-Agent Architecture**: Research, Epic, Story, Spec, Code, and Validation agents powered by LangGraph
- **FastAPI Backend**: RESTful APIs with comprehensive Swagger documentation
- **Real-Time Updates**: Server-Sent Events (SSE) for live progress tracking
- **Enhanced Approval System**: Approve, reject, or regenerate with feedback at each gate
- **JWT Authentication**: User and Admin role-based access control
- **Artifact Storage**: PostgreSQL storage for all generated artifacts with rich metadata
- **Observability**: Langfuse integration for LLM call tracing and token tracking
- **Export Functionality**: Download epics, stories, specs, code, and validation reports

## 🏗 Architecture

```
Product Request → Research (URLs + Analysis) → 
Epics (P0/P1/P2 + Dependencies + Mermaid) → [Approval Gate] → 
Stories (Given/When/Then) → [Approval Gate] → 
Specs (API + Models + Tests) → [Approval Gate] → 
Code → Validation → Artifacts
```

Each stage:
- ✅ Produces persisted artifacts with metadata
- ✅ Requires explicit approval before advancing
- ✅ Supports regeneration with user feedback
- ✅ Can be paused and resumed

### Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── database.py            # SQLAlchemy models and database setup
├── auth/                  # Authentication (JWT, user management)
├── projects/              # Project CRUD operations
├── runs/                  # Run execution and SSE progress
├── agents/                # AI agents (Research, Epic, Story, Spec, Code, Validation)
├── orchestrator/          # LangGraph workflow orchestration
├── observability/         # Langfuse integration
├── admin/                 # Admin-only endpoints
└── utils/                 # Export and utility functions
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/dhruvchauhan29/assignment.git
cd assignment
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `OPENAI_API_KEY`: Your OpenAI API key
- `LANGFUSE_PUBLIC_KEY` (optional): For observability
- `LANGFUSE_SECRET_KEY` (optional): For observability

5. Initialize the database:
```bash
python -c "from app.database import init_db; init_db()"
```

6. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## 📖 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication

### Register a new user

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "securepassword"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john&password=securepassword"
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

Use this token in subsequent requests:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" ...
```

## 📝 Workflow Example

### 1. Create a Project

```bash
curl -X POST "http://localhost:8000/api/projects" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-commerce Platform",
    "description": "Modern e-commerce platform with AI recommendations",
    "product_request": "Build an e-commerce platform with product catalog, shopping cart, checkout, payment processing, and AI-powered product recommendations."
  }'
```

**Validation:**
- Product request cannot be empty (→ 422)

### 2. Create a Run

```bash
curl -X POST "http://localhost:8000/api/runs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1
  }'
```

### 3. Start the Run

```bash
curl -X POST "http://localhost:8000/api/runs/1/start" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Monitor Progress (SSE)

Connect to the SSE endpoint to receive real-time updates:

```bash
curl -N "http://localhost:8000/api/runs/1/progress" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

You'll receive events like:
```
event: connected
data: {"run_id": 1, "status": "running", "current_stage": "research"}

event: progress
data: {"stage": "research", "message": "Research phase started", "timestamp": "2024-01-20T10:30:00"}

event: progress
data: {"stage": "epics", "message": "Epic generation completed", "timestamp": "2024-01-20T10:32:00"}
```

### 5. Approve Stages

After epics are generated, you can approve, reject, or request regeneration:

**Option 1: Approve and Proceed**
```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/epics" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "action": "proceed",
    "feedback": "Looks good, proceed to stories"
  }'
```

**Option 2: Reject and Regenerate with Feedback**
```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/epics" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "action": "regenerate",
    "feedback": "Please add more detail to Epic 2 and include security considerations"
  }'
```

**Option 3: Reject without Regeneration**
```bash
curl -X POST "http://localhost:8000/api/runs/1/approvals/epics" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "action": "reject",
    "feedback": "This approach does not meet our requirements"
  }'
```

Repeat for `stories` and `specs` stages.

### 6. Get Artifacts

```bash
# List all artifacts
curl "http://localhost:8000/api/runs/1/artifacts" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Export as markdown
curl "http://localhost:8000/api/export/1/artifacts.md" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o artifacts.md

# Export code bundle
curl "http://localhost:8000/api/export/1/code.zip" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o code.zip

# Export validation report
curl "http://localhost:8000/api/export/1/validation.md" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o validation.md
```

## 🎭 Multi-Agent System

### Research Agent (Milestone 2: Evidence Before Planning)
- **Mandatory first step** - no planning without research
- Performs comprehensive domain research
- **Output includes:**
  - URLs consulted with relevance scores (citations)
  - Key findings summary in structured sections
  - Technology stack recommendations with rationale
  - Architecture approach suggestions
  - Implementation considerations and risks
  - Influence on downstream planning (epics, stories, specs)
- Grounds all planning in real-world evidence

### Epic Agent (Milestone 3: Comprehensive Epic Planning)
- Generates 3-5 comprehensive epics from research
- **Each epic includes:**
  - **Goal**: Clear, action-oriented objective
  - **Priority**: P0 (Critical) / P1 (High) / P2 (Medium) with reasoning
  - **In-Scope**: Explicit deliverables included
  - **Out-of-Scope**: Explicit items NOT included
  - **Dependencies**: Epic and external dependencies
  - **Risks & Assumptions**: With mitigation strategies
  - **Success Metrics**: Quantifiable measures
- **Generates Mermaid dependency diagram** with color-coded priorities
- **Supports regeneration** with user feedback incorporation

### Story Agent
- Generates user stories for each epic
- Uses Given/When/Then acceptance criteria
- Includes edge cases and NFRs

### Spec Agent
- Creates formal technical specifications
- Defines API contracts and data models
- Specifies security and validation requirements

### Code Agent
- Generates production-ready code
- Creates comprehensive tests
- Follows best practices and patterns

### Validation Agent
- Validates generated code
- Checks for syntax, security, performance issues
- Provides fix recommendations

## 🔄 Pause/Resume

Pause a running execution:
```bash
curl -X POST "http://localhost:8000/api/runs/1/pause" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Resume execution:
```bash
curl -X POST "http://localhost:8000/api/runs/1/start" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🎯 Milestone System Features

### Milestone 1: Foundation - User Can Start
- ✅ JWT-based authentication with User/Admin roles
- ✅ Project creation with input validation
  - Empty product request → 400 Bad Request
  - Files > 20MB → 413 Request Entity Too Large
  - Unsupported file types → 415 Unsupported Media Type
- ✅ Document upload support (PDF, TXT, MD, DOC, DOCX)
- ✅ Run lifecycle management (pending → running → paused → completed/failed)

### Milestone 2: Research - Evidence Before Planning
- ✅ **Mandatory research** before any planning
- ✅ Research artifacts include:
  - URLs consulted with titles, summaries, and relevance scores
  - Key findings organized in sections
  - Technology recommendations with rationale
  - Architecture approach explanation
  - Planning influence documentation
- ✅ Research stored as first-class artifact with rich metadata

### Milestone 3: Epic Generation with Approval Gates
- ✅ Comprehensive epic structure with all required fields
- ✅ Priority system (P0/P1/P2) with business reasoning
- ✅ Explicit in-scope and out-of-scope definitions
- ✅ Dependency tracking (epic + external)
- ✅ Risk assessment with mitigation strategies
- ✅ Success metrics for each epic
- ✅ **Mermaid dependency diagram** with color-coded priorities
- ✅ **Approval gate with actions:**
  - Approve → Continue to stories
  - Regenerate → Incorporate feedback and regenerate
  - Reject → Stop without regeneration
- ✅ **No stories generated until epics approved**

### Milestone 4: User Story & Spec Generation
- ✅ Stories generated only from approved epics
- ✅ Given/When/Then acceptance criteria
- ✅ Edge cases and NFRs included
- ✅ Specs with API contracts, data models, test cases
- ✅ Approval gates at stories and specs stages
- ✅ Regeneration support with feedback incorporation

## 👨‍💼 Admin Features

Admin users can manage all users and projects:

```bash
# List all users
curl "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Delete a user
curl -X DELETE "http://localhost:8000/api/admin/users/2" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# List all projects
curl "http://localhost:8000/api/admin/projects" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Delete a project
curl -X DELETE "http://localhost:8000/api/admin/projects/3" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## 📊 Observability

If Langfuse is configured, all LLM calls are traced:

1. Set up Langfuse credentials in `.env`
2. View traces at https://cloud.langfuse.com (or your self-hosted instance)
3. Track token usage per run in the database

## 🧪 Testing

Run tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## 🔧 Development

Format code:
```bash
ruff check app/ --fix
```

Type checking (if using mypy):
```bash
mypy app/
```

## 📦 Deployment

### Using Docker (recommended)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t ai-product-system .
docker run -p 8000:8000 --env-file .env ai-product-system
```

### Using Gunicorn (production)

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🛠 Tech Stack

- **FastAPI**: Modern Python web framework
- **LangGraph**: Multi-agent orchestration
- **LangChain**: LLM framework
- **OpenAI GPT-4**: Language model
- **PostgreSQL**: Primary database
- **SQLAlchemy**: ORM
- **JWT**: Authentication
- **SSE**: Real-time updates
- **Langfuse**: Observability
- **pytest**: Testing

## 📄 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or support, please open an issue on GitHub.