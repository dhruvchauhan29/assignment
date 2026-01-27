"""
Main FastAPI application.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.auth.routes import router as auth_router
from app.projects.routes import router as projects_router
from app.runs.routes import router as runs_router
from app.admin.routes import router as admin_router
from app.utils.routes import router as export_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_db()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="AI Product-to-Code System",
    description="""
    Backend-only multi-agent AI system that transforms Product Requests into working code.
    
    ## Features
    
    * **Authentication**: JWT-based user authentication with User/Admin roles
    * **Projects**: CRUD operations for managing projects
    * **Runs**: Execute multi-stage workflows with real-time progress
    * **Agents**: Research, Epic, Story, Spec, Code, and Validation agents
    * **SSE**: Real-time progress updates via Server-Sent Events
    * **Approvals**: User approval gates between stages
    * **Artifacts**: Store and retrieve generated artifacts
    * **Observability**: Token tracking and LLM call tracing
    
    ## Workflow
    
    1. **Register/Login** - Create account and authenticate
    2. **Create Project** - Submit product request
    3. **Start Run** - Begin execution
    4. **Monitor Progress** - Watch real-time SSE updates
    5. **Approve Stages** - Review and approve epics, stories, specs
    6. **Get Artifacts** - Download generated code and documentation
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(runs_router)
app.include_router(admin_router)
app.include_router(export_router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Product-to-Code System API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
