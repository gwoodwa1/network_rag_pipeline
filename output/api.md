---
title: "REST API Documentation"
description: "Complete API reference for client integration"
author: "API Team"
date: "2024-01-20"
id: "api-documentation"
category: "api"
---

# REST API Documentation

This document provides comprehensive documentation for our REST API endpoints.

## Authentication

All API endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## User Endpoints

### POST /api/users/register

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "name": "John Doe",
  "createdAt": "2024-01-20T10:00:00Z"
}
```

### POST /api/users/login

Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresIn": 3600,
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

## Data Endpoints

### GET /api/data/items

Retrieve paginated list of items.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `sort`: Sort field (id, name, createdAt)
- `order`: Sort order (asc, desc)

**Response:**
```json
{
  "items": [
    {
      "id": "item_1",
      "name": "Sample Item",
      "description": "A sample item",
      "createdAt": "2024-01-20T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

### POST /api/data/items

Create a new item.

**Request Body:**
```json
{
  "name": "New Item",
  "description": "Description of the new item",
  "category": "electronics"
}
```

## Error Handling

The API uses standard HTTP status codes and returns error details in JSON format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

## Rate Limiting

API requests are limited to 1000 requests per hour per user. Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```