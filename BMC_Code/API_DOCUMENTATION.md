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
  "id": "target-001",
  "name": "Tank Alpha",
  "north": 250,
  "east": 350,
  "down": 50,
  "status": "active",
  "value": 100,
  "type": "armored_vehicle"
}
```

**Required Fields:**
- `id` (string): Unique identifier for the target

**Optional Fields:**
- `name` (string): Display name for the target
- `north` (number): North coordinate (vertical axis, increases upward on map)
- `east` (number): East coordinate (horizontal axis, increases rightward on map)
- `down` (number): Down coordinate (altitude/depth, positive values go down)
- `status` (string): Target status (e.g., "active", "inactive", "tracked")
- `value` (number): Priority or value of the target
- `type` (string): Type of target (e.g., "armored_vehicle", "soldier", "installation")
- Additional custom fields can be added as needed

**Coordinate System:**
The system uses NED (North-East-Down) coordinates:
- **North**: Vertical axis on the map (positive = up/north)
- **East**: Horizontal axis on the map (positive = right/east)
- **Down**: Altitude (positive = down/below reference level)

The map automatically scales to display all targets with a 50-pixel margin.

**Response:**
```json
{
  "status": "success",
  "message": "Target target-001 updated successfully",
  "data": {
    "id": "target-001",
    "name": "Tank Alpha",
    "north": 250,
    "east": 350,
    "down": 50,
    "status": "active",
    "value": 100,
    "type": "armored_vehicle"
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
    "id": "target-001",
    "name": "Tank Alpha",
    "north": 250,
    "east": 350,
    "down": 50,
    "status": "active",
    "value": 100,
    "type": "armored_vehicle"
  },
  "target-002": {
    "id": "target-002",
    "name": "Infantry Squad",
    "north": 500,
    "east": 600,
    "down": 0,
    "status": "active",
    "value": 50,
    "type": "soldier"
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
  "id": "target-001",
  "name": "Tank Alpha",
  "north": 250,
  "east": 350,
  "down": 50,
  "status": "active",
  "value": 100,
  "type": "armored_vehicle"
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
    "id": "target-001",
    "name": "Tank Alpha",
    "north": 250,
    "east": 350,
    "down": 50,
    "status": "active",
    "value": 100,
    "type": "armored_vehicle"
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
    "id": "target-001",
    "name": "Tank Alpha",
    "north": 250,
    "east": 350,
    "down": 50,
    "status": "active",
    "value": 100,
    "type": "armored_vehicle"
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
    id: "target-001",
    name: "Tank Alpha",
    north: 250,
    east: 350,
    down: 50,
    status: "active",
    value: 100,
    type: "armored_vehicle"
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
