"""
services/playback

Phase 9 — Playback System service layer.

Modules:
  hikvision_playback  — ISAPI recording search + RTSP URL generation
  playback_session    — session CRUD helpers (DB + Redis)
  playback_manager    — orchestrates session lifecycle
  timeline_parser     — converts raw ISAPI segments to timeline blocks
  playback_cleanup    — background worker that expires stale sessions
  download_service    — recording clip export / proxy download
"""
