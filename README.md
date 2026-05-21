# CCTV Centralization Platform - Backend

## Overview

This backend service provides a centralized CCTV monitoring platform with features including JWT authentication, RBAC, secure user management, audit logging, and more. It is built with FastAPI, PostgreSQL, Redis, and Docker.

## Features Implemented in Phase 4

- JWT Authentication (access and refresh tokens)
- Role-Based Access Control (RBAC) foundation
- Secure user management endpoints
- Permission system
- Audit logging foundation
- Secure admin structure
- Google Sheets sync endpoint (to be implemented)
- Docker Compose setup with hot reload, PostgreSQL persistence, and Redis connectivity

## Project Structure

```
app/
  api/
    v1/
      api.py                # Main API routes
      dependencies.py       # Security and RBAC dependencies
      example_protected.py  # Example protected endpoints
  core/
    config.py               # Configuration and environment variables
  models/
    user.py                 # User model and user_roles association
    role.py                 # Role and Permission models
    branch.py               # Branch and Region models
    audit_log.py            # Audit log model
  security/
    jwt.py                  # JWT token creation and verification, password hashing
  seeds/
    seed_roles_permissions.py # Seed script for roles and permissions
  db/
    base.py                 # Base model
    session.py              # Database session management
alembic/
  versions/
    2b3f4c5d6e7f_add_auth_and_rbac_models.py  # Alembic migration for auth and RBAC models
docker-compose.yml          # Docker Compose configuration
.env                        # Environment variables
README.md                   # This file
```

## Setup and Running

1. **Environment Variables**

   Copy `.env` file and adjust as needed:

   ```
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cctv_db
   REDIS_URL=redis://localhost:6379/0

   JWT_SECRET=supersecretkey
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=7
   ```

2. **Docker Compose**

   Build and start containers:

   ```bash
   docker-compose up --build
   ```

3. **Database Migration**

   Inside the backend container, run:

   ```bash
   alembic upgrade head
   ```

4. **Seeding Roles and Permissions**

   Run the seed script to populate roles and permissions:

   ```bash
   python -m app.seeds.seed_roles_permissions
   ```

5. **API Endpoints**

   - `POST /auth/login` - Login and receive JWT tokens
   - `POST /auth/logout` - Logout (audit logged)
   - `POST /auth/refresh` - Refresh access token
   - `GET /auth/me` - Get current user info
   - `GET /users` - List users (SUPER_ADMIN only)
   - `POST /users` - Create user (SUPER_ADMIN only)
   - `PUT /users/{id}` - Update user (SUPER_ADMIN only)
   - `DELETE /users/{id}` - Delete user (SUPER_ADMIN only)
   - `GET /roles` - List roles
   - `GET /permissions` - List permissions

6. **Security**

   - Passwords hashed with bcrypt
   - JWT tokens with access and refresh tokens
   - RBAC enforced via dependencies
   - Audit logging for key actions

## Next Steps

- Implement Google Sheets sync endpoint with audit logging
- Expand user-branch-region relationships and access control
- Add more detailed schemas and input validation
- Implement frontend integration and testing

## Contact

For questions or contributions, please contact the development team.