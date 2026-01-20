# Target Management API Documentation

## Overview
The Target Management System provides a REST API for managing targets. Targets can be created, updated, retrieved, and deleted through HTTP endpoints.

## Base URL
```
http://localhost:5000/api
```

## Endpoints

### 1. Update/Create Target
**Endpoint:** `POST /api/TARGET`

**Description:** Creates a new target or updates an existing one with the provided information.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "id": "T-123",
  "timestamp": 1342.44,
  "position": {
    "north": 1.53,
    "east": -43.22,
    "down": -600.5
  },
  "velocity": {
    "vn": 0.1,
    "ve": -2.5,
    "vd": -0.8
  }
}
```

**Required Fields:**
- `id` (string): Unique identifier for the target (also used as display name)
- `position` (object): Target position in NED coordinates
  - `north` (number): North coordinate (vertical axis)
  - `east` (number): East coordinate (horizontal axis)
  - `down` (number): Down coordinate (altitude/depth)

**Optional Fields:**
- `timestamp` (number): Time of the measurement/update
- `velocity` (object): Target velocity in NED frame
  - `vn` (number): Velocity North component
  - `ve` (number): Velocity East component
  - `vd` (number): Velocity Down component
- Additional custom fields can be added as needed

**Coordinate System:**
The system uses NED (North-East-Down) coordinates:
- **North**: Vertical axis on the map (positive = up/north)
- **East**: Horizontal axis on the map (positive = right/east)
- **Down**: Altitude (positive = down/below reference level)

The map automatically scales to display all targets with a 50-pixel margin, centered on the operator position at (0, 0, 0).

**Response:**
```json
{
  "status": "success",
  "message": "Target T-123 updated successfully",
  "data": {
    "id": "T-123",
    "timestamp": 1342.44,
    "position": {
      "north": 1.53,
      "east": -43.22,
      "down": -600.5
    },
    "velocity": {
      "vn": 0.1,
      "ve": -2.5,
      "vd": -0.8
    }
  }
}
```

**Status Code:** 200 OK

**Error Response (Missing ID):**
```json
{
  "error": "Target ID is required"
}
```
**Status Code:** 400 Bad Request

---

### 2. Get All Targets
**Endpoint:** `GET /api/TARGET`

**Description:** Retrieves all targets currently stored in the system.

**Request Headers:** None required

**Response:**
```json
{
  "target-001": {
    "id": "T-123",
    "timestamp": 1342.44,
    "position": {
      "north": 1.53,
      "east": -43.22,
      "down": -600.5
    },
    "velocity": {
      "vn": 0.1,
      "ve": -2.5,
      "vd": -0.8
    }
  },
  "target-002": {
    "id": "T-124",
    "timestamp": 1343.50,
    "position": {
      "north": 50.0,
      "east": 60.0,
      "down": -100.0
    },
    "velocity": {
      "vn": 0.5,
      "ve": -1.0,
      "vd": 0.0
    }
  }
}
```

**Status Code:** 200 OK

---

### 3. Get Specific Target
**Endpoint:** `GET /api/TARGET/<target_id>`

**Description:** Retrieves information for a specific target by ID.

**Path Parameters:**
- `target_id` (string): The ID of the target to retrieve

**Response (Success):**
```json
{
  "id": "T-123",
  "timestamp": 1342.44,
  "position": {
    "north": 1.53,
    "east": -43.22,
    "down": -600.5
  },
  "velocity": {
    "vn": 0.1,
    "ve": -2.5,
    "vd": -0.8
  }
}
```

**Status Code:** 200 OK

**Response (Not Found):**
```json
{
  "error": "Target not found"
}
```

**Status Code:** 404 Not Found

---

### 4. Delete Target
**Endpoint:** `DELETE /api/TARGET/<target_id>`

**Description:** Removes a target from the system.

**Path Parameters:**
- `target_id` (string): The ID of the target to delete

**Response (Success):**
```json
{
  "status": "success",
  "message": "Target target-001 deleted"
}
```

**Status Code:** 200 OK

**Response (Not Found):**
```json
{
  "error": "Target not found"
}
```

**Status Code:** 404 Not Found

---

### 5. System Status
**Endpoint:** `GET /api/status`

**Description:** Gets the current system status and statistics.

**Response:**
```json
{
  "status": "online",
  "targets_count": 5
}
```

**Status Code:** 200 OK

---

## Example Usage

### Using cURL

**Create/Update a target:**
```bash
curl -X POST http://localhost:5000/api/TARGET \
  -H "Content-Type: application/json" \
  -d '{
    "id": "T-123",
    "timestamp": 1342.44,
    "position": {
      "north": 250.0,
      "east": 350.0,
      "down": -50.0
    },
    "velocity": {
      "vn": 0.1,
      "ve": -2.5,
      "vd": -0.8
    }
  }'
```

**Get all targets:**
```bash
curl http://localhost:5000/api/TARGET
```

**Get a specific target:**
```bash
curl http://localhost:5000/api/TARGET/target-001
```

**Delete a target:**
```bash
curl -X DELETE http://localhost:5000/api/TARGET/target-001
```

**Check system status:**
```bash
curl http://localhost:5000/api/status
```

### Using Python

```python
import requests
import json

BASE_URL = "http://localhost:5000/api"

# Create/Update a target
target_data = {
    "id": "T-123",
    "timestamp": 1342.44,
    "position": {
        "north": 250.0,
        "east": 350.0,
        "down": -50.0
    },
    "velocity": {
        "vn": 0.1,
        "ve": -2.5,
        "vd": -0.8
    }
}

response = requests.post(
    f"{BASE_URL}/TARGET",
    json=target_data,
    headers={"Content-Type": "application/json"}
)
print(response.json())

# Get all targets
response = requests.get(f"{BASE_URL}/TARGET")
print(response.json())

# Get specific target
response = requests.get(f"{BASE_URL}/TARGET/target-001")
print(response.json())

# Delete target
response = requests.delete(f"{BASE_URL}/TARGET/target-001")
print(response.json())
```

### Using JavaScript

```javascript
// Create/Update a target
const targetData = {
    id: "T-123",
    timestamp: 1342.44,
    position: {
        north: 250.0,
        east: 350.0,
        down: -50.0
    },
    velocity: {
        vn: 0.1,
        ve: -2.5,
        vd: -0.8
    }
};

fetch('http://localhost:5000/api/TARGET', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(targetData)
})
.then(response => response.json())
.then(data => console.log(data));

// Get all targets
fetch('http://localhost:5000/api/TARGET')
    .then(response => response.json())
    .then(data => console.log(data));

// Delete target
fetch('http://localhost:5000/api/TARGET/target-001', {
    method: 'DELETE'
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "error": "No JSON data provided"
}
```

**404 Not Found:**
```json
{
  "error": "Endpoint not found"
}
```

**405 Method Not Allowed:**
```json
{
  "error": "Method not allowed"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error details"
}
```

---

## Data Storage

The system currently stores targets in memory. This means:
- Data persists during the current server session
- All data is lost when the server restarts
- Multiple instances will not share data

For production use, consider integrating a database (SQLite, PostgreSQL, MongoDB, etc.).

---

## Web Interfaces

### Management Interface
- **URL:** `http://localhost:5000`
- **Purpose:** Create, update, delete, and manage targets
- **Features:** Form-based target management, real-time updates

### Operator Interface
- **URL:** `http://localhost:5000/operator`
- **Purpose:** Visual map display of targets
- **Features:** Real-time target visualization, grid-based coordinates, target tracking
