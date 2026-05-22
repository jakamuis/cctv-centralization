# MASTER_SPEC.md

# Centralized Multi-Branch CCTV Platform
## Docker-Based Lightweight Enterprise VMS
## Hikvision-Focused Architecture

---

# 1. PROJECT OVERVIEW

This project aims to build a modern centralized CCTV operations platform for multi-branch monitoring using Hikvision NVRs connected through VPN/L2TP infrastructure.

The platform will provide:
- Live View
- Playback
- Download Clip
- User Management
- Audit Logging
- Branch-Based Access Control
- On-Demand Streaming
- Modern Web Dashboard

Initial deployment target:
- 2 branches (proof of concept)

Future scalability target:
- 113+ branches
- Hundreds of cameras

Development environment:
- MacBook Air (local development)

Deployment model:
- Fully Docker-based architecture

---

# 2. CORE OBJECTIVES

The system must:

1. Centralize CCTV access for all branches
2. Minimize bandwidth usage
3. Support scalable architecture
4. Provide secure multi-user access
5. Avoid unnecessary permanent streams
6. Support future AI analytics integration
7. Remain lightweight and operationally stable

---

# 3. CORE DESIGN PRINCIPLES

## 3.1 ON-DEMAND STREAMING ONLY

Streaming must:
- Start only when requested
- Stop automatically when viewer closes
- Stop automatically after timeout
- Never autoplay
- Never preload all cameras

Purpose:
- Reduce bandwidth
- Reduce NVR load
- Improve scalability

---

## 3.2 PLAYBACK DIRECTLY FROM NVR

Playback must:
- Use recordings stored on Hikvision NVR
- Avoid central recording initially
- Stream dynamically from NVR

Purpose:
- Simplify infrastructure
- Reduce storage requirements
- Improve scalability

---

## 3.3 SUBSTREAM VS MAINSTREAM STRATEGY

### Substream
Use for:
- Dashboard preview
- Multi-camera grid

### Mainstream
Use for:
- Fullscreen live view
- Playback
- Download clip

Example Hikvision channels:
- 101 = Mainstream
- 102 = Substream

---

## 3.4 LIGHTWEIGHT ARCHITECTURE

Requirements:
- Docker Compose only
- No Kubernetes
- No microservices initially
- Monolith backend approach

Purpose:
- Faster development
- Easier debugging
- Lower operational complexity

---

## 3.5 ENTERPRISE-READY FOUNDATION

The architecture must support:
- RBAC
- JWT authentication
- Audit logging
- Branch-based permissions
- Session management
- Future scalability

---

# 4. TECHNOLOGY STACK

## Frontend
- React
- Vite

## Backend
- FastAPI (Python)

## Database
- PostgreSQL

## Streaming Gateway
- go2rtc

## Cache / Session Layer
- Redis

## Reverse Proxy
- Nginx

## Containerization
- Docker
- Docker Compose

## Future Optional Services
- AI/OpenCV services
- Telegram alerting
- WhatsApp alerting

---

# 5. HIGH LEVEL ARCHITECTURE

```text
Browser User
      |
    Nginx
      |
 ┌─────────────┐
 |  Frontend   |
 |   React     |
 └─────────────┘
      |
 ┌─────────────┐
 |   Backend   |
 |   FastAPI   |
 └─────────────┘
      |
 ┌──────────────────────┐
 | PostgreSQL           |
 | Redis                |
 | go2rtc               |
 └──────────────────────┘
      |
 Hikvision NVR
      |
 Cameras
```

---

# 6. CURRENT IMPLEMENTATION STATUS

## Completed
- JWT Authentication
- Basic RBAC Foundation
- Dockerized Backend
- PostgreSQL Integration
- Hikvision Integration
- Device Management
- Camera Management
- go2rtc Integration
- Redis-backed StreamManager
- Shared Stream Sessions
- Active Stream Registry
- HLS Live Streaming
- On-Demand Stream Lifecycle
- Idle Stream Cleanup
- Viewer Count Tracking
- Multi-camera Live View
- Dockerized Streaming Layer

## In Progress
- Stream Authorization Layer
- Signed Stream URLs
- Branch Scope Validation
- Camera Scope Validation
- Stream Audit Logging

## Planned
- Playback Timeline UI
- Clip Download
- WebRTC
- AI Analytics
- Telegram Alerts
- WhatsApp Alerts
- Mobile Optimization
- Multi-grid Dashboard
- PTZ Controls

---

# 7. BRANCH ARCHITECTURE

Each branch contains:
- Hikvision NVR
- Local camera recording
- VPN/L2TP connection

The central platform acts only as:
- Access layer
- Authorization layer
- Stream orchestration layer
- Monitoring dashboard

IMPORTANT:
Recording remains local at each branch NVR.

The central platform does NOT initially:
- Store recordings permanently
- Re-record all streams
- Maintain permanent live streams

Purpose:
- Reduce bandwidth usage
- Improve operational stability
- Reduce infrastructure complexity
- Improve scalability

---

# 8. STREAM LIFECYCLE

## Live Stream Flow

1. User requests live stream
2. Backend validates authentication
3. Backend validates permissions
4. StreamManager checks existing stream session
5. Existing session reused if already active
6. go2rtc starts/reuses RTSP pull from NVR
7. HLS stream delivered to frontend
8. Viewer count tracked in Redis
9. Viewer disconnect decreases counter
10. Idle streams automatically terminate

---

## Stream Optimization Principles

Requirements:
- One RTSP pull per camera
- Shared live sessions
- Automatic idle cleanup
- Minimal bandwidth usage
- Minimal NVR load

---

# 9. SECURITY PRINCIPLES

## Authentication
- JWT-based authentication
- Secure password hashing
- Protected API endpoints

---

## Authorization
- RBAC-based permissions
- Branch-scoped access
- Camera-scoped access
- Future signed stream tokens

---

## Streaming Security
- No raw RTSP exposure to frontend
- No permanent public HLS URLs
- No direct NVR exposure
- Stream access validated server-side

---

## Auditability
Future audit logging includes:
- User login activity
- Stream access history
- Playback access history
- Download activity
- Failed access attempts

---

# 10. RBAC MODEL

## Roles
- super_admin
- admin
- operator
- viewer
- auditor
- vendor

---

## Permissions
- stream.live
- playback.view
- playback.download
- ptz.control
- camera.view
- device.manage
- user.manage
- branch.manage

---

## Scope Model

Permissions may be scoped by:
- Global
- Branch
- Camera

Examples:
- Branch operator only accesses assigned branch
- Central admin accesses all branches

---

# 11. STREAMING STRATEGY

## Live View
- HLS delivery via go2rtc
- Future WebRTC-ready architecture
- On-demand streaming only

---

## Grid View
- Substream preferred
- Lower bitrate
- Lower CPU usage

---

## Fullscreen View
- Mainstream preferred
- Higher quality
- Full resolution

---

# 12. DOCKER ARCHITECTURE

Services currently include:
- frontend
- backend
- postgres
- redis
- go2rtc
- nginx

Architecture goals:
- Easy local development
- Simple deployment
- Minimal operational overhead
- Easy future scaling

---

# 13. FUTURE ROADMAP

## Phase 7A
- Stream Infrastructure
- Stream Authorization
- Signed Stream Access

---

## Phase 7B
- Playback UX
- Timeline Playback
- Download Clip

---

## Phase 8
- Multi-grid Dashboard
- Multi-branch Scaling
- Improved Monitoring UX

---

## Future Optional Features
- AI Detection
- Motion Analytics
- Telegram Notifications
- WhatsApp Notifications
- License Plate Recognition
- Face Recognition
- Edge AI Processing

---

# 14. NON-GOALS (INITIAL PHASE)

The initial platform will NOT:
- Centralize all recordings
- Use Kubernetes
- Use microservices
- Permanently stream all cameras
- Perform AI processing on all streams
- Replace branch NVR functionality

Purpose:
Maintain lean and operationally efficient architecture.

---

# 15. DEVELOPMENT PHILOSOPHY

Primary priorities:
1. Stability
2. Simplicity
3. Low operational complexity
4. Scalability
5. Security
6. Bandwidth efficiency

The system should remain:
- Lean
- Maintainable
- Cost-efficient
- Easy to debug
- Easy to scale incrementally