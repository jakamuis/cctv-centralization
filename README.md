# CCTV-Centralization Project

## Overview

This project provides a Docker-based skeleton for a CCTV centralization system. It includes backend, frontend, streaming gateway, database, and reverse proxy services orchestrated with Docker Compose.

## Project Structure

- `backend/` - FastAPI backend service with a minimal "Hello World" API.
- `frontend/` - React + Vite frontend application with a minimal UI.
- `nginx/` - Nginx reverse proxy configuration to route requests to backend, frontend, and streaming gateway.
- `go2rtc/` - Streaming gateway service configuration (go2rtc).

## Docker Services

- **postgres**: PostgreSQL database with persistent volume and healthcheck.
- **backend**: FastAPI backend service, waits for postgres readiness.
- **frontend**: React + Vite frontend development server.
- **go2rtc**: Streaming gateway for video streams.
- **nginx**: Reverse proxy routing HTTP traffic to other services.

## Ports

| Service  | Port | Description                  |
|----------|-------|------------------------------|
| frontend | 5173  | React development server     |
| backend  | 8000  | FastAPI backend API          |
| postgres | 5432  | PostgreSQL database          |
| go2rtc   | 1984  | Streaming gateway HTTP port  |
| nginx    | 80    | Reverse proxy HTTP port      |

## Running the Project

1. Copy `.env.example` to `.env` and adjust environment variables as needed.
2. Build and start all services with Docker Compose:

```bash
docker compose up --build
```

3. Access the frontend via `http://localhost`.
4. Backend API is available at `http://localhost/api`.
5. Streaming gateway is accessible at `http://localhost/go2rtc`.

## Startup Flow

- PostgreSQL starts first with a healthcheck to ensure readiness.
- Backend service waits for PostgreSQL to be healthy before starting.
- Frontend and go2rtc services start independently.
- Nginx reverse proxy starts last, routing incoming HTTP requests to the appropriate service based on URL path.
- Frontend serves the React app on `/`.
- Backend API is proxied under `/api/`.
- go2rtc streaming gateway is proxied under `/go2rtc/`.

## Notes

- This is an initial skeleton focusing on project structure and Docker environment.
- Business logic, frontend pages, Hikvision integration, authentication, and playback features are not implemented yet.
- The architecture is kept simple and production-oriented without Kubernetes or microservices.
- Environment variables are used for configuration and can be customized in `.env`.