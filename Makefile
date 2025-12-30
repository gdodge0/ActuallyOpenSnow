# Makefile for ActuallyOpenSnow

.PHONY: help build up down logs dev prod clean

help:
	@echo "ActuallyOpenSnow Docker Commands"
	@echo "================================="
	@echo ""
	@echo "  make dev      - Start development environment (hot reload)"
	@echo "  make prod     - Start production environment"
	@echo "  make build    - Build production images"
	@echo "  make up       - Start production containers"
	@echo "  make down     - Stop all containers"
	@echo "  make logs     - View container logs"
	@echo "  make clean    - Remove containers, images, and volumes"
	@echo ""

# Development
dev:
	docker-compose -f docker-compose.dev.yml up --build

dev-d:
	docker-compose -f docker-compose.dev.yml up --build -d

dev-down:
	docker-compose -f docker-compose.dev.yml down

# Production
prod: build up

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

# Cleanup
clean:
	docker-compose down -v --rmi all --remove-orphans
	docker-compose -f docker-compose.dev.yml down -v --rmi all --remove-orphans

# Individual services
backend:
	docker-compose up -d backend

frontend:
	docker-compose up -d frontend

# Rebuild specific service
rebuild-backend:
	docker-compose build backend
	docker-compose up -d backend

rebuild-frontend:
	docker-compose build frontend
	docker-compose up -d frontend

# Shell access
shell-backend:
	docker-compose exec backend /bin/sh

shell-frontend:
	docker-compose exec frontend /bin/sh

# Status
status:
	docker-compose ps

