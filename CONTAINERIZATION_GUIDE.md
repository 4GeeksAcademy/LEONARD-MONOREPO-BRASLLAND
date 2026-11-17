# Company Monorepo Containerization Guide

## Overview

Complete Docker containerization setup for the Brasaland company monorepo with Docker Compose orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Compose Network                     │
│                      (company)                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │   Backend    │    │  PostgreSQL  │  │
│  │  (Next.js)   │───▶│  (FastAPI)   │───▶│ (Supabase)   │  │
│  │  :3000-3001  │    │  :8012       │    │  :5432       │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                               │
│  Volumes:                                                    │
│  • ./uis → /workspace/uis                                   │
│  • ./services → /workspace/services                         │
│  • ./packages → /workspace/packages (read-only)             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Services

### UI Service
- **Image**: Built from `uis/Dockerfile`
- **Ports**: 3000-3001 (Next.js dev server and alternate port)
- **Environment**:
  - `AUTH_API_URL`: Backend authentication endpoint
  - `NEXT_PUBLIC_INVENTORY_API_URL`: Backend API endpoint
  - `NEXT_PUBLIC_TELEMETRY_ENDPOINT`: Telemetry collection
- **Volumes**: 
  - `./uis:/workspace/uis` - Hot reload development
  - `./packages:/workspace/packages:ro` - Shared packages (read-only)
  - `ui-website-node-modules` - Persistent node_modules

### Backend Service
- **Image**: Built from `services/Dockerfile`
- **Port**: 8012
- **Environment**:
  - `DATABASE_URL`: Supabase PostgreSQL connection
  - Other API configuration
- **Volumes**:
  - `./services:/workspace/services` - Hot reload development
  - `./packages:/workspace/packages:ro` - Shared packages

### Database Service
- **Image**: Supabase PostgreSQL (`supabase/postgres:16`)
- **Port**: 5432
- **Environment**: Database credentials and configuration
- **Volumes**: `postgres_data` - Persistent storage

## Quick Start

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- 2GB+ free disk space
- Port availability: 3000-3001, 8012, 5432

### Launch

```bash
# Build and start all services
docker-compose up --build

# Services are ready when:
# • Frontend logs: "Local: http://localhost:3000"
# • Backend logs: "Uvicorn running on http://0.0.0.0:8012"
# • Database logs: "database system is ready to accept connections"
```

### Stop Services

```bash
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Development Workflow

### Code Changes
Since we use volume mounts, code changes are reflected immediately:

1. **Frontend Changes**: Edit files in `uis/` → auto-refresh at http://localhost:3000
2. **Backend Changes**: Edit files in `services/` → Uvicorn hot reload
3. **Database Schema**: Edit migrations → Apply via API

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f ui
docker-compose logs -f postgres
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres

# Or use a GUI client:
# Host: localhost, Port: 5432, User: postgres, Password: postgres
```

### Rebuild Services

```bash
# Rebuild after dependency changes
docker-compose build --no-cache

# Restart with new build
docker-compose up --build
```

## Production Considerations

This setup is optimized for **development**. For production:

1. Use environment-specific configs (`.env.production`)
2. Disable hot-reload volume mounts
3. Add health checks and restart policies
4. Use multi-stage builds to reduce image sizes
5. Implement proper secret management (not in .env)
6. Add monitoring and logging aggregation
7. Use container registries (Docker Hub, ECR, etc.)

## Optimization

### Image Size
- Both `Dockerfile` and `.dockerignore` files are configured to minimize image size
- Node modules are only cached in volumes for development

### Performance
- Named volumes prevent repeated installations
- Read-only `/packages` mount reduces overhead
- Network is isolated with named "company" network

## Troubleshooting

### Services won't start
```bash
# Check Docker daemon
docker ps

# Review detailed logs
docker-compose logs

# Remove and rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Port conflicts
```bash
# Check port usage (Linux/Mac)
lsof -i :3000
lsof -i :8012
lsof -i :5432

# Change ports in docker-compose.yml
# Update PORTS section and environment variables accordingly
```

### Database connection errors
```bash
# Check database service is running
docker-compose logs postgres

# Verify DATABASE_URL in environment
docker-compose logs backend | grep DATABASE_URL

# Manual connection test
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT 1"
```

## Files Reference

```
.
├── docker-compose.yml          # Main orchestration file
├── services/
│   ├── Dockerfile              # Backend (FastAPI) container
│   └── .dockerignore            # Backend build optimization
├── uis/
│   ├── Dockerfile              # Frontend (Next.js) container
│   └── .dockerignore            # Frontend build optimization
└── CONTAINERIZATION_GUIDE.md   # This file
```

## Environment Variables

Default values are set in `docker-compose.yml`. Override with `.env` file:

```env
# Frontend
AUTH_API_URL=http://backend:8012
NEXT_PUBLIC_INVENTORY_API_URL=http://backend:8012
NEXT_PUBLIC_TELEMETRY_ENDPOINT=/telemetry/events

# Backend
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/brasaland

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=brasaland
```

## Commands Cheat Sheet

```bash
# Start
docker-compose up                     # Foreground
docker-compose up -d                  # Background
docker-compose up --build              # Build and start

# Stop
docker-compose down                   # Remove containers, keep volumes
docker-compose down -v                # Remove containers and volumes

# Logs
docker-compose logs -f                # Stream all logs
docker-compose logs -f [service]      # Stream one service

# Execute
docker-compose exec [service] [cmd]   # Run command in container

# Rebuild
docker-compose build                  # Build images
docker-compose build --no-cache        # Force rebuild

# Status
docker-compose ps                     # List running containers
docker-compose images                 # List built images
```

---

**Last Updated**: 2026-11-17
**Status**: Production-ready for development environments
