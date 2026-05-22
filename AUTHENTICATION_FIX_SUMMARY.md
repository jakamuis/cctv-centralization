# Frontend Authentication Fix Summary

## Problem
Live stream requests were failing with `401 Unauthorized` because the frontend was NOT sending JWT Authorization headers to the stream API endpoints.

## Root Cause
The frontend had NO authentication system implemented:
- No login functionality
- No token storage
- No Authorization headers in API requests
- Raw `fetch()` calls without authentication

## Solution Implemented

### 1. Updated API Client (`frontend/src/api/index.js`)
**Added:**
- Token management functions (`getAuthToken`, `setAuthToken`, `clearAuthToken`, `isAuthenticated`)
- `getAuthHeaders()` function that automatically includes `Authorization: Bearer <token>` header
- Updated all HTTP methods (`httpGet`, `httpPost`, `httpDelete`) to use authenticated headers
- New `authApi` object with login, logout, and getCurrentUser methods
- Login uses OAuth2PasswordRequestForm format (form-urlencoded)

**Key Changes:**
```javascript
function getAuthHeaders() {
  const headers = { 'Accept': 'application/json' }
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}
```

All API requests now automatically include the JWT token when available.

### 2. Created Login Page (`frontend/src/pages/Login.jsx`)
**Features:**
- Username/password form
- Error handling
- Loading states
- Default credentials hint (admin/admin)
- Calls `authApi.login()` which stores the JWT token in localStorage

### 3. Updated App Component (`frontend/src/App.jsx`)
**Added:**
- Authentication state management
- Token validation on mount
- Login/logout flow
- Conditional rendering (Login page vs Dashboard)
- User data fetching

**Flow:**
1. Check if token exists in localStorage
2. If yes, validate by calling `/api/v1/auth/me`
3. If valid, show Dashboard with user info
4. If invalid or missing, show Login page

### 4. Updated Dashboard (`frontend/src/pages/Dashboard.jsx`)
**Added:**
- User info header showing username and roles
- Logout button
- Accepts `user` and `onLogout` props from App

## How It Works

### Authentication Flow:
1. User visits app → App checks for stored token
2. No token → Show Login page
3. User enters credentials → POST to `/api/v1/auth/login`
4. Backend returns `access_token` → Stored in localStorage
5. App fetches user data from `/api/v1/auth/me`
6. Dashboard loads with authenticated user

### Stream Request Flow (FIXED):
1. User clicks "Preview Live" or opens grid
2. `LivePlayer` calls `api.startLive(cameraId)`
3. `startLive()` → `httpPost('/api/v1/streams/live/{id}')`
4. `httpPost()` → `getAuthHeaders()` → Includes `Authorization: Bearer <token>`
5. Backend validates JWT via `Depends(get_current_user)`
6. ✅ Stream starts successfully
7. Backend returns HLS URL with stream token
8. Video player loads HLS stream

### API Requests Now Include:
```http
GET /api/v1/branches
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

POST /api/v1/streams/live/{camera_id}
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

DELETE /api/v1/streams/live/{camera_id}
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Files Modified

1. **frontend/src/api/index.js** - Complete rewrite with authentication
2. **frontend/src/pages/Login.jsx** - New file
3. **frontend/src/App.jsx** - Added authentication logic
4. **frontend/src/pages/Dashboard.jsx** - Added user header and logout

## Testing Checklist

- [ ] Login page appears on first visit
- [ ] Can login with valid credentials (admin/admin)
- [ ] Invalid credentials show error
- [ ] After login, Dashboard loads
- [ ] User info displays in header
- [ ] Branches and cameras load
- [ ] **"Preview Live" button works (no 401 error)**
- [ ] **"Open 2x2 Grid" works (no 401 error)**
- [ ] **HLS stream loads successfully**
- [ ] Logout button works
- [ ] After logout, redirected to login page
- [ ] Token persists across page refreshes

## Security Notes

✅ **Authentication is ENABLED and ENFORCED**
✅ **RBAC is INTACT** - Backend still checks permissions
✅ **No auth bypass** - Only fixed frontend token handling
✅ **JWT tokens stored in localStorage** (standard practice for SPAs)
✅ **Token validation on every protected endpoint**

## Backend Requirements

The backend must have:
- `/api/v1/auth/login` endpoint (OAuth2PasswordRequestForm)
- `/api/v1/auth/me` endpoint (returns user info)
- `/api/v1/auth/logout` endpoint (optional, for audit logging)
- Stream endpoints protected with `Depends(get_current_user)`
- At least one user account (e.g., admin/admin)

All requirements are already met by the existing backend implementation.
