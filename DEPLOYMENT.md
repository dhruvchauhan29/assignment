# Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Database Setup](#database-setup)
7. [Testing](#testing)

## Prerequisites

- Python 3.9 or higher
- PostgreSQL 12 or higher (for production)
- Docker and Docker Compose (optional, for containerized deployment)
- OpenAI API key

## Local Development

### 1. Clone and Setup

```bash
git clone https://github.com/dhruvchauhan29/assignment.git
cd assignment
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and edit with your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/aiproduct
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key  # Optional
LANGFUSE_SECRET_KEY=your-langfuse-secret-key  # Optional
TAVILY_API_KEY=your-tavily-api-key  # Optional
```

### 5. Initialize Database

For development with SQLite (no PostgreSQL required):

```bash
# Update DATABASE_URL in .env to:
# DATABASE_URL=sqlite:///./aiproduct.db

python init_db.py
```

For production with PostgreSQL:

```bash
# Make sure PostgreSQL is running and database is created
createdb aiproduct

python init_db.py
```

### 6. Run Development Server

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker Deployment

### Quick Start with Docker Compose

The easiest way to run the entire stack (app + PostgreSQL):

```bash
# Create .env file with your OpenAI key
echo "OPENAI_API_KEY=your-key-here" > .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

The API will be available at http://localhost:8000

### Custom Docker Build

```bash
# Build image
docker build -t ai-product-system .

# Run container (requires external PostgreSQL)
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e OPENAI_API_KEY=your-key \
  -e SECRET_KEY=your-secret \
  ai-product-system
```

## Production Deployment

### Using Gunicorn

For production, use Gunicorn with Uvicorn workers:

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Systemd Service

Create `/etc/systemd/system/ai-product-system.service`:

```ini
[Unit]
Description=AI Product-to-Code System
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/ai-product-system
Environment="PATH=/opt/ai-product-system/venv/bin"
ExecStart=/opt/ai-product-system/venv/bin/gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable ai-product-system
sudo systemctl start ai-product-system
```

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/ai-product-system`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/ai-product-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Environment Configuration

### Required Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key (generate with: `openssl rand -hex 32`)
- `OPENAI_API_KEY`: Your OpenAI API key

### Optional Variables

- `LANGFUSE_PUBLIC_KEY`: Langfuse public key for observability
- `LANGFUSE_SECRET_KEY`: Langfuse secret key
- `LANGFUSE_HOST`: Langfuse host (default: https://cloud.langfuse.com)
- `TAVILY_API_KEY`: Tavily API key for enhanced research
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT expiration (default: 30)

### Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use strong SECRET_KEY** - Generate cryptographically secure random string
3. **Rotate keys regularly** - Change SECRET_KEY and API keys periodically
4. **Use HTTPS in production** - Always use SSL/TLS
5. **Restrict database access** - Use firewall rules to limit PostgreSQL access
6. **Set up monitoring** - Use Langfuse or similar for observability

## Database Setup

### PostgreSQL Production Setup

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE aiproduct;
CREATE USER aiproduct WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE aiproduct TO aiproduct;
\q
```

### Database Migrations

For schema changes in the future, consider using Alembic:

```bash
pip install alembic
alembic init alembic
```

### Backup and Restore

```bash
# Backup
pg_dump -U aiproduct aiproduct > backup.sql

# Restore
psql -U aiproduct aiproduct < backup.sql
```

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format and lint code
ruff check app/ --fix

# Type checking (optional)
mypy app/
```

## Monitoring and Maintenance

### Health Check

The API provides a health check endpoint:

```bash
curl http://localhost:8000/health
```

### Logs

View application logs:

```bash
# Systemd
sudo journalctl -u ai-product-system -f

# Docker Compose
docker-compose logs -f app
```

### Database Maintenance

```bash
# Vacuum database
psql -U aiproduct -d aiproduct -c "VACUUM ANALYZE;"

# Check database size
psql -U aiproduct -d aiproduct -c "SELECT pg_size_pretty(pg_database_size('aiproduct'));"
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U aiproduct -d aiproduct -h localhost

# Check logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### API Not Starting

```bash
# Check if port is in use
sudo lsof -i :8000

# Check application logs
sudo journalctl -u ai-product-system -n 100

# Verify environment variables
env | grep -E 'DATABASE_URL|OPENAI_API_KEY'
```

### Permission Issues

```bash
# Fix file permissions
sudo chown -R www-data:www-data /opt/ai-product-system
sudo chmod -R 755 /opt/ai-product-system
```

## Scaling

### Horizontal Scaling

1. Use a load balancer (e.g., Nginx, HAProxy)
2. Run multiple instances of the application
3. Use Redis for session storage if needed
4. Ensure database can handle concurrent connections

### Vertical Scaling

1. Increase worker count in Gunicorn
2. Allocate more CPU and memory to PostgreSQL
3. Tune PostgreSQL configuration for performance

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation at `/docs` endpoint
- Review the README.md file
