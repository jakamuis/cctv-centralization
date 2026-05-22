# Async SQLAlchemy Authentication Fix

## Summary
Fixed async SQLAlchemy usage in authentication/login endpoints to resolve `AttributeError: 'AsyncSession' object has no attribute 'query'` error.

## Changes Made

### 1. `/backend/app/api/v1/api.py`
**Fixed endpoints:**
- `POST /auth/login` - Login endpoint
- `POST /auth/logout` - Logout endpoint  
- `GET /users` - List users
- `POST /users` - Create user
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user
- `GET /roles` - List roles
- `GET /permissions` - List permissions

**Changes:**
- Changed `Session` to `AsyncSession` imports and type hints
- Added `from sqlalchemy import select` import
- Converted all `db.query(Model).filter(...).first()` to:
  ```python
  result = await db.execute(select(Model).where(...))
  model = result.scalar_one_or_none()
  ```
- Converted `db.query(Model).all()` to:
  ```python
  result = await db.execute(select(Model))
  models = result.scalars().all()
  ```
- Added `await` to all `db.commit()` and `db.refresh()` calls
- Made all affected functions `async`

### 2. `/backend/app/api/v1/dependencies.py`
**Fixed functions:**
- `get_current_user()` - JWT token validation and user lookup
- `require_branch_access()` - Branch access validation

**Changes:**
- Changed `Session` to `AsyncSession` imports
- Added `from sqlalchemy import select` import
- Added `from app.models.branch import Branch` import
- Converted `get_current_user()` to async with proper SQLAlchemy 2.x patterns
- Fixed `require_branch_access()` to use async patterns and accept `db` parameter
- Removed problematic `next(get_db())` pattern that doesn't work with async

### 3. `/backend/app/api/v1/routers/streams.py`
**Fixed endpoints:**
- `POST /streams/live/{camera_id}` - Start stream
- `DELETE /streams/live/{camera_id}` - Stop stream
- `GET /streams/hls/{camera_id}/index.m3u8` - HLS master playlist
- `GET /streams/hls/{camera_id}/{rest:path}` - HLS segments

**Changes:**
- Changed `Session` to `AsyncSession` imports
- Added `db: AsyncSession = Depends(get_db)` to HLS endpoints
- Added `await` to all `CameraRepository(db).get_by_id()` calls
- Removed `next(get_db())` anti-pattern

## Pattern Changes

### Before (Synchronous - BROKEN):
```python
from sqlalchemy.orm import Session

def login(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    db.commit()
```

### After (Async - FIXED):
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def login(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    await db.commit()
```

## Files Modified
1. `backend/app/api/v1/api.py` - Auth and user management endpoints
2. `backend/app/api/v1/dependencies.py` - Auth dependencies
3. `backend/app/api/v1/routers/streams.py` - Stream endpoints with auth

## Testing Checklist
- [ ] Login works (`POST /auth/login`)
- [ ] JWT issued correctly
- [ ] Frontend auth succeeds
- [ ] Current user lookup works (`GET /auth/me`)
- [ ] Protected endpoints work with JWT
- [ ] Stream authorization works
- [ ] Preview Live works
- [ ] User management endpoints work (SUPER_ADMIN only)

## Notes
- The seed file (`backend/app/seeds/seed_roles_permissions.py`) still uses synchronous patterns but is only run during initial setup, not during runtime API calls
- All runtime authentication and authorization now uses proper async SQLAlchemy 2.x patterns
- CameraRepository was already async-compatible, no changes needed
