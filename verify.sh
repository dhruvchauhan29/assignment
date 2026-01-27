#!/bin/bash

# Verification script for AI Product-to-Code System

echo "=========================================="
echo "AI Product-to-Code System Verification"
echo "=========================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python --version 2>&1)
echo "  $python_version"
echo ""

# Check required files
echo "✓ Checking project structure..."
required_files=(
    "app/main.py"
    "app/config.py"
    "app/database.py"
    "requirements.txt"
    "Dockerfile"
    "docker-compose.yml"
    "init_db.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
    fi
done
echo ""

# Check module structure
echo "✓ Checking module structure..."
modules=(
    "app/auth"
    "app/projects"
    "app/runs"
    "app/agents"
    "app/orchestrator"
    "app/observability"
    "app/admin"
    "app/utils"
    "tests"
)

for module in "${modules[@]}"; do
    if [ -d "$module" ]; then
        echo "  ✓ $module/"
    else
        echo "  ✗ $module/ (MISSING)"
    fi
done
echo ""

# Check agent files
echo "✓ Checking agent implementations..."
agents=(
    "app/agents/base.py"
    "app/agents/research_agent.py"
    "app/agents/epic_agent.py"
    "app/agents/story_agent.py"
    "app/agents/spec_agent.py"
    "app/agents/code_agent.py"
    "app/agents/validation_agent.py"
)

for agent in "${agents[@]}"; do
    if [ -f "$agent" ]; then
        echo "  ✓ $agent"
    else
        echo "  ✗ $agent (MISSING)"
    fi
done
echo ""

# Check test files
echo "✓ Checking test suite..."
tests=(
    "tests/conftest.py"
    "tests/test_auth.py"
    "tests/test_projects.py"
    "tests/test_runs.py"
)

for test in "${tests[@]}"; do
    if [ -f "$test" ]; then
        echo "  ✓ $test"
    else
        echo "  ✗ $test (MISSING)"
    fi
done
echo ""

# Check documentation
echo "✓ Checking documentation..."
docs=(
    "README.md"
    "DEPLOYMENT.md"
    "API_EXAMPLES.md"
    "FEATURES.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo "  ✓ $doc"
    else
        echo "  ✗ $doc (MISSING)"
    fi
done
echo ""

# Count lines of code
echo "✓ Code statistics..."
if command -v wc &> /dev/null; then
    py_files=$(find app -name "*.py" | wc -l)
    py_lines=$(find app -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
    test_files=$(find tests -name "*.py" | wc -l)
    test_lines=$(find tests -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
    
    echo "  Python files: $py_files"
    echo "  Lines of code: $py_lines"
    echo "  Test files: $test_files"
    echo "  Test lines: $test_lines"
fi
echo ""

# Check syntax
echo "✓ Checking Python syntax..."
syntax_errors=0
for file in $(find app -name "*.py"); do
    if ! python -m py_compile "$file" 2>/dev/null; then
        echo "  ✗ Syntax error in $file"
        syntax_errors=$((syntax_errors + 1))
    fi
done

if [ $syntax_errors -eq 0 ]; then
    echo "  ✓ All Python files have valid syntax"
else
    echo "  ✗ Found $syntax_errors files with syntax errors"
fi
echo ""

echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo ""
echo "To get started:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Configure .env file with your API keys"
echo "3. Initialize database: python init_db.py"
echo "4. Run server: uvicorn app.main:app --reload"
echo "5. Visit http://localhost:8000/docs"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
