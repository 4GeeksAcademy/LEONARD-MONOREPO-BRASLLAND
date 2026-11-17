# Brasaland Monorepo Structure

## Overview

Complete containerized monorepo for the Brasaland company chain management system.

## Directory Layout

```
.
├── uis/                          # Frontend applications
│   ├── website/                  # Main website (Next.js)
│   ├── backoffice/              # Admin dashboard (Next.js)
│   └── Dockerfile               # Frontend container
│
├── services/                     # Backend services
│   ├── api/                      # FastAPI application
│   │   ├── routers/              # API endpoints
│   │   ├── models/               # Data models
│   │   └── schemas/              # Request/response schemas
│   └── Dockerfile                # Backend container
│
├── packages/                     # Shared code
│   ├── shared/                   # Shared utilities & types
│   └── node_modules/             # Shared dependencies
│
├── docker-compose.yml            # Container orchestration
├── CONTAINERIZATION_GUIDE.md     # Docker setup documentation
├── MONOREPO_STRUCTURE.md        # This file
└── .dockerignore                 # Build optimization
```

## Applications

### Frontend (uis/)

#### Website (`uis/website/`)
- **Purpose**: Public-facing Brasaland website
- **Framework**: Next.js 13+
- **Port**: 3000
- **Features**:
  - Landing page
  - Company information
  - Restaurant locations
  - Menu showcase

#### Backoffice (`uis/backoffice/`)
- **Purpose**: Administrative dashboard
- **Framework**: Next.js 13+
- **Port**: 3001
- **Features**:
  - Incident management
  - Inventory tracking
  - Performance analytics
  - Telemetry dashboard

### Backend (services/)

#### API (`services/api/`)
- **Purpose**: Core business logic
- **Framework**: FastAPI + Uvicorn
- **Port**: 8012
- **Database**: Supabase PostgreSQL

**Main Routers:**
- `/incidents` - Incident management
- `/inventory` - Stock & ingredient tracking
- `/locations` - Restaurant locations
- `/telemetry` - Performance events
- `/auth` - Authentication

### Shared Code (packages/)

- Type definitions
- Utility functions
- Shared schemas
- Constants & enums
- Brasaland business logic

## Development Workflow

### Setup
```bash
docker-compose up --build
```

### Code Changes
- **Frontend**: Edit `uis/` → Auto-refresh at localhost:3000
- **Backend**: Edit `services/` → Uvicorn hot reload at localhost:8012
- **Shared**: Edit `packages/` → Reflected in both frontend & backend

### Database
- **Connection**: localhost:5432
- **Credentials**: postgres:postgres
- **Database**: brasaland

## Key Features

### Authentication
- JWT-based authentication
- Protected API routes
- Session management
- Password recovery flows

### Incident Management
- Create, read, update, delete incidents
- Status tracking (open, in_progress, resolved, discarded)
- Official Brasaland categories
- Location-based filtering

### Inventory Management
- Entry/exit tracking
- Ingredient management
- Consumption vs. waste KPI
- Multi-location support

### Performance Monitoring
- Frontend telemetry
- Event tracking & batching
- Error logging
- Performance metrics
- Core Web Vitals

### Error Handling
- Comprehensive error middleware
- Validation with 422 responses
- Error logging & categorization
- User-friendly error messages

## Configuration

### Environment Variables

**Frontend (.env.local)**
```
AUTH_API_URL=http://localhost:8012
NEXT_PUBLIC_INVENTORY_API_URL=http://localhost:8012
NEXT_PUBLIC_TELEMETRY_ENDPOINT=/telemetry/events
```

**Backend (.env)**
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/brasaland
SECRET_KEY=your-secret-key-here
```

## Testing

### Frontend
```bash
docker-compose exec ui npm test
```

### Backend
```bash
docker-compose exec backend pytest services/api/tests/
```

## Deployment

### Build for Production
```bash
docker-compose build --no-cache
docker-compose up --no-volume
```

### Database Migrations
```bash
docker-compose exec backend alembic upgrade head
```

## Monitoring

### Logs
```bash
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f ui
```

### Database Access
```bash
docker-compose exec postgres psql -U postgres -d brasaland
```

### Telemetry
- Access backoffice at localhost:3001
- View performance metrics dashboard
- Track error patterns
- Monitor user sessions

## Project Status

✅ **Completed Milestones:**
- Authentication & session management
- Incident manager with lifecycle rules
- Inventory backend & interface
- Website foundations
- Containerization with Docker Compose
- Frontend telemetry & performance monitoring
- Error handling audit
- Brasaland compliance (categories, locations, fields)

## Documentation

- [CONTAINERIZATION_GUIDE.md](./CONTAINERIZATION_GUIDE.md) - Docker & Docker Compose setup
- [MONOREPO_STRUCTURE.md](./MONOREPO_STRUCTURE.md) - This file (directory structure & workflow)

---

**Repository**: 4GeeksAcademy/LEONARD-PROJECT-MILESSTONE
**Last Updated**: 2026-11-17
**Status**: Production-ready for development
