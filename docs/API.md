# PhishCatcher API Documentation

## Overview

The PhishCatcher API provides RESTful endpoints for email phishing detection, user authentication, Gmail integration, and system administration. The API is built with FastAPI and follows OpenAPI 3.0 specifications.

## Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://api.phishcatcher.com/api/v1`

## Authentication

The API uses JWT (JSON Web Token) authentication with refresh tokens:

```http
Authorization: Bearer <access_token>
```

### Token Types
- **Access Token**: Short-lived (15 minutes) for API access
- **Refresh Token**: Long-lived (7 days) for token renewal

## Authentication Endpoints

### Register User
```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Login
```http
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

### Refresh Token
```http
POST /auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Logout
```http
POST /auth/logout
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

## Email Analysis Endpoints

### Upload Email for Analysis
```http
POST /analysis/upload
```

**Headers:**
```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body:**
```
file: <email_file.eml>
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "message": "Email uploaded successfully for analysis"
}
```

### Get Analysis Results
```http
GET /analysis/{job_id}
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "risk_score": 85,
  "is_phishing": true,
  "confidence": 0.95,
  "analysis_results": {
    "sender_analysis": {
      "sender_email": "suspicious@fake-domain.com",
      "sender_reputation": "low",
      "domain_age_days": 7,
      "spf_record": false,
      "dkim_signature": false,
      "dmarc_policy": "none"
    },
    "content_analysis": {
      "suspicious_keywords": ["urgent", "verify", "suspended"],
      "urgency_indicators": true,
      "grammar_errors": 3,
      "personalization": false
    },
    "url_analysis": {
      "total_urls": 5,
      "suspicious_urls": 3,
      "url_details": [
        {
          "url": "http://bit.ly/suspicious",
          "risk_level": "high",
          "redirects": true,
          "domain_reputation": "low"
        }
      ]
    },
    "findings": [
      {
        "type": "suspicious_sender",
        "severity": "high",
        "description": "Sender domain is newly registered and has poor reputation",
        "recommendation": "Verify sender identity through alternative channels"
      },
      {
        "type": "suspicious_urls",
        "severity": "high",
        "description": "Email contains multiple suspicious URLs",
        "recommendation": "Do not click on any links in this email"
      }
    ]
  },
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:05Z"
}
```

### Get Analysis History
```http
GET /analysis/history
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `status`: Filter by status (`completed`, `processing`, `failed`)

**Response:**
```json
{
  "items": [
    {
      "job_id": "uuid",
      "status": "completed",
      "risk_score": 85,
      "is_phishing": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20,
  "pages": 5
}
```

## Gmail Integration Endpoints

### Get Google OAuth URL
```http
GET /gmail/auth-url
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/oauth/authorize?client_id=...",
  "state": "random_string"
}
```

### Handle OAuth Callback
```http
POST /gmail/callback
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "code": "authorization_code",
  "state": "random_string"
}
```

**Response:**
```json
{
  "message": "Gmail account connected successfully",
  "email": "user@gmail.com"
}
```

### Fetch Gmail Emails
```http
GET /gmail/emails
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `limit`: Number of emails to fetch (default: 50)
- `page`: Page number (default: 1)
- `query`: Gmail search query (optional)

**Response:**
```json
{
  "emails": [
    {
      "id": "gmail_message_id",
      "subject": "Suspicious Email",
      "from": "sender@example.com",
      "date": "2024-01-01T00:00:00Z",
      "snippet": "This is a suspicious email...",
      "is_read": false
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 50
}
```

### Analyze Gmail Emails
```http
POST /gmail/analyze
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "email_ids": ["gmail_message_id_1", "gmail_message_id_2"]
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "emails_queued": 2,
  "message": "Gmail emails queued for analysis"
}
```

## User Management Endpoints

### Get User Profile
```http
GET /users/profile
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_admin": false,
  "gmail_connected": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z"
}
```

### Update User Profile
```http
PUT /users/profile
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "full_name": "John Smith",
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response:**
```json
{
  "message": "Profile updated successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Smith",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

### Delete User Account
```http
DELETE /users/account
```

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Account deleted successfully"
}
```

## Admin Endpoints

### Get System Statistics
```http
GET /admin/stats
```

**Headers:**
```http
Authorization: Bearer <admin_access_token>
```

**Response:**
```json
{
  "users": {
    "total": 1000,
    "active": 850,
    "new_this_month": 50
  },
  "analyses": {
    "total": 10000,
    "this_month": 2000,
    "avg_risk_score": 45.2,
    "phishing_detected": 1500
  },
  "system": {
    "uptime": "99.9%",
    "avg_response_time": "150ms",
    "storage_used": "45GB"
  }
}
```

### Get Users List
```http
GET /admin/users
```

**Headers:**
```http
Authorization: Bearer <admin_access_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50)
- `status`: Filter by status (`active`, `inactive`)

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "John Doe",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1000,
  "page": 1,
  "limit": 50
}
```

## Health Check Endpoints

### System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "postgresql": "healthy",
    "mongodb": "healthy",
    "redis": "healthy"
  }
}
```

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  }
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Invalid input data
- `AUTHENTICATION_ERROR`: Invalid or missing authentication
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable

## Rate Limiting

API requests are rate limited to prevent abuse:
- **Standard Users**: 100 requests per hour
- **Premium Users**: 1000 requests per hour
- **Admin Users**: No rate limiting

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## SDKs and Libraries

Official SDKs are available for:
- **Python**: `pip install phishcatcher-python`
- **JavaScript**: `npm install phishcatcher-js`
- **cURL**: Native support

## Webhooks

PhishCatcher supports webhooks for real-time notifications:

### Configure Webhook
```http
POST /webhooks
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["analysis.completed", "analysis.failed"],
  "secret": "webhook_secret"
}
```

### Webhook Payload
```json
{
  "event": "analysis.completed",
  "data": {
    "job_id": "uuid",
    "status": "completed",
    "risk_score": 85,
    "user_id": "uuid"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- **Development**: `http://localhost:8000/openapi.json`
- **Production**: `https://api.phishcatcher.com/openapi.json`

Interactive API documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
