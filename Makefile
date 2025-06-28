# LustBot Makefile

.PHONY: help install run-dev run-prod lint test clean build

# Default target
help:
	@echo "🔥 LustBot - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install      - Install dependencies"
	@echo "  run-dev      - Run development server (http://localhost:8001)"
	@echo "  run-prod     - Run production server"
	@echo ""
	@echo "Quality:"
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code with black"
	@echo "  test         - Run tests"
	@echo ""
	@echo "Utilities:"
	@echo "  clean        - Clean temporary files"
	@echo "  load-data    - Load product data into vector store"
	@echo "  reset-agent  - Reset agent memory"

# Installation
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Development
run-dev:
	@echo "🚀 Starting LustBot development server..."
	uvicorn app.main:app --reload --port 8001 --host 0.0.0.0

run-prod:
	@echo "🌐 Starting LustBot production server..."
	gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001

# Code quality
lint:
	@echo "🔍 Running linting..."
	ruff check app/
	black --check app/

format:
	@echo "✨ Formatting code..."
	black app/
	ruff check app/ --fix

test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

# Utilities
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

load-data:
	@echo "📊 Loading product data..."
	curl -X POST http://localhost:8001/admin/load-products

reset-agent:
	@echo "🤖 Resetting agent memory..."
	curl -X GET http://localhost:8001/admin/agent-reset

# Docker commands (optional)
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t lustbot .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -p 8001:8001 --env-file .env lustbot
