# Makefile for ActuallyOpenSnow

.PHONY: help build up down logs dev prod clean status migrate seed

help:
	@echo "ActuallyOpenSnow Docker Commands"
	@echo "================================="
	@echo ""
	@echo "Production (Coolify-compatible, no port bindings):"
	@echo "  make build    - Build production images"
	@echo "  make up       - Start production containers"
	@echo "  make down     - Stop all containers"
	@echo "  make logs     - View container logs"
	@echo ""
	@echo "Development (local with port bindings):"
	@echo "  make dev      - Start development environment"
	@echo "  make dev-down - Stop development containers"
	@echo ""
	@echo "Database:"
	@echo "  make migrate  - Run Alembic migrations"
	@echo "  make seed     - Seed resorts into database"
	@echo ""
	@echo "Utility:"
	@echo "  make clean    - Remove containers, images, and volumes"
	@echo "  make status   - Show container status"
	@echo ""

# Production (Coolify-compatible)
prod: build up

build:
	docker-compose -f docker-compose.yaml build

up:
	docker-compose -f docker-compose.yaml up -d

down:
	docker-compose -f docker-compose.yaml down

logs:
	docker-compose -f docker-compose.yaml logs -f

logs-backend:
	docker-compose -f docker-compose.yaml logs -f backend

logs-frontend:
	docker-compose -f docker-compose.yaml logs -f frontend

logs-engine:
	docker-compose -f docker-compose.yaml logs -f engine

logs-engine-backend:
	docker-compose -f docker-compose.yaml logs -f engine-backend

# Development (with port bindings for local use)
dev:
	docker-compose -f docker-compose.dev.yaml up --build

dev-d:
	docker-compose -f docker-compose.dev.yaml up --build -d

dev-down:
	docker-compose -f docker-compose.dev.yaml down

# Database management
migrate:
	cd db && alembic upgrade head

seed:
	python db/seed.py

# Cleanup
clean:
	docker-compose -f docker-compose.yaml down -v --rmi all --remove-orphans 2>/dev/null || true
	docker-compose -f docker-compose.dev.yaml down -v --rmi all --remove-orphans 2>/dev/null || true

# Individual services
backend:
	docker-compose -f docker-compose.yaml up -d backend

frontend:
	docker-compose -f docker-compose.yaml up -d frontend

engine:
	docker-compose -f docker-compose.yaml up -d engine

engine-backend:
	docker-compose -f docker-compose.yaml up -d engine-backend

# Rebuild specific service
rebuild-backend:
	docker-compose -f docker-compose.yaml build backend
	docker-compose -f docker-compose.yaml up -d backend

rebuild-frontend:
	docker-compose -f docker-compose.yaml build frontend
	docker-compose -f docker-compose.yaml up -d frontend

rebuild-engine:
	docker-compose -f docker-compose.yaml build engine
	docker-compose -f docker-compose.yaml up -d engine

# Status
status:
	docker-compose -f docker-compose.yaml ps
