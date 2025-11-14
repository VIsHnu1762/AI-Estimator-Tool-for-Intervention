# Road Safety Intervention Intelligence System

A production-grade platform for Government of India engineers to ingest road-safety intervention dossiers, extract interventions via hybrid NLP + transformer models, map them to IRC standards through RAG, pull authoritative CPWD/GEM material prices, compute quantities, and publish clean audit-ready PDF reports.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Redis + PostgreSQL. Handles uploads, document processing, AI pipelines, pricing, and PDF generation.
- **AI Pipeline**: spaCy NER + SentenceTransformers embeddings + OCR fallbacks for scanned documents, backed by a Chroma vector store for IRC standards.
- **Pricing**: CPWD SOR/AOR + GeM integrations with Redis/database caching and authoritative metadata.
- **Frontend**: React + Vite single-page UI with government styling, secure upload flow, live status, and report previews.
- **Reports**: Jinja2 + WeasyPrint templates styled after India.gov aesthetics with citations, quantities, formulas, and timestamps.
- **Deployment**: Dockerized microservices behind Nginx reverse proxy with HTTPS termination.

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (only if running the frontend locally outside Docker)
- Python 3.11 (if running backend without containers)

## Quick Start (Docker Compose)

```bash
cd "AI for road safety/APP"
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- API Gateway (Nginx): http://localhost
- FastAPI backend: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

Create a `.env` file from `.env.example` and supply real secrets (DB credentials, OpenAI, GeM token, etc.).

## Local Development

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

For local development outside Docker, you can override where `/api` requests proxy by creating `frontend/.env` with:

```
VITE_API_PROXY_TARGET=http://localhost:8000
```

When running inside Docker Compose, this isn't required because the frontend talks to the backend through Nginx.

### Database
Use the default PostgreSQL from Docker Compose or point `DATABASE_URL` to an existing instance. Run Alembic migrations (to be added) or let SQLAlchemy create tables automatically on startup for development.

## Key Directories

- `app/` – FastAPI application modules
- `app/services/` – document extraction, AI, pricing, RAG, reporting
- `templates/reports/` – Jinja HTML template rendered to PDF
- `static/assets/` – branding assets
- `frontend/` – Vite React SPA
- `nginx/` – reverse proxy configuration

## Testing & Quality Gates

- Backend: `pytest` (tests to be expanded with fixture data)
- Frontend: `npm run build` ensures type-safe compilation
- Linting: rely on TypeScript + mypy/ruff (additions welcome)

## Security & Compliance

- File uploads sanitized, size-limited, and hashed (SHA-256 helper ready)
- Trusted-host/CORS hardening and gzip compression
- Redis-backed caching for pricing and request throttling support via Nginx `limit_req`
- Report lineage includes pricing timestamps + IRC clauses for audit traceability

## Future Enhancements

- Production deployment pipeline (CI/CD)
- Additional tests + Alembic migrations
- Advanced monitoring dashboards (Prometheus/Grafana)
- Real CPWD/GEM API adapters once credentials available

---
Crafted for the Ministry of Road Transport & Highways to keep every rupee transparent, verifiable, and auditor-ready.
