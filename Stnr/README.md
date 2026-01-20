# Stnr (Starboard) - Fire Control System

## Overview

Stnr is a Fire Control System that receives **Fire commands from MMC** (via REST API), processes them, and returns **ACK/NACK responses** immediately. It includes a network simulator for testing communication with MMC.

## Architecture

### Components

1. **config.py** - Configuration and constants
2. **fire_command.py** - FireCommand model and handler (processes commands, manages state)
3. **api_server.py** - Flask REST API server (receives commands, returns ACKs)
4. **network_simulator.py** - Test simulator for MMC↔Stnr communication
5. **run.py** - Launcher script

## Requirements

### 1. Fire Command Reception (REST API)
- **Endpoint:** `POST /fire`
- **Input:** Fire command JSON with target, weapon, azimuth, elevation, range
- **Output:** ACK with command_id and state
- **Response time:** Immediate (< 100ms)

### 2. Fire Command Execution
- Fire commands execute asynchronously in background threads
- State transitions: IDLE → ARMED → FIRING → COMPLETED (or ERROR)
- Acknowledgment sent immediately (does not wait for firing to complete)

### 3. Network Simulator
- Simulates MMC sending Fire commands to Stnr
- Tests various scenarios: single, sequence, continuous
- Tracks success/failure rates
- Interactive menu for manual testing

## Running Stnr

### Start REST API Server

```bash
# Terminal 1: Start Stnr server
python -m Stnr.run --mode server --host 0.0.0.0 --port 8001
```

### Test with Network Simulator

```bash
# Terminal 2: Start simulator (interactive)
python -m Stnr.run --mode simulator --port 8001
```

Or programmatically:

```python
from Stnr.network_simulator import NetworkSimulator

sim = NetworkSimulator("http://localhost:8001")
sim.send_fire_command(target_id="T-1", weapon_type="CANNON", azimuth=45.0, elevation=10.0, range_m=2500.0)
sim.run_test_sequence(num_commands=10, delay_between=2.0)
sim.print_results()
```

## REST API Endpoints

### 1. POST /fire - Submit Fire Command

**Request:**
```json
{
  "command_id": "FIRE_001",
  "target_id": "T-1",
  "weapon_type": "CANNON",
  "azimuth": 45.0,
  "elevation": 10.0,
  "range_m": 2500.0
}
```

**Response (ACK):**
```json
{
  "ack_code": 0,
  "command_id": "FIRE_001",
  "state": "ARMED",
  "message": "Fire command FIRE_001 accepted and executing"
}
```

### 2. GET /fire/<command_id> - Get Command Status

**Response:**
```json
{
  "command_id": "FIRE_001",
  "state": "COMPLETED",
  "data": {
    "command_id": "FIRE_001",
    "target_id": "T-1",
    "weapon_type": "CANNON",
    "azimuth": 45.0,
    "elevation": 10.0,
    "range_m": 2500.0,
    "state": "COMPLETED",
    "created_time": 1234567890.123,
    "started_time": 1234567890.234,
    "completed_time": 1234567890.484,
    "error_msg": null
  }
}
```

### 3. GET /status - Get Stnr Status

**Response:**
```json
{
  "service": "Stnr (Starboard)",
  "state": "IDLE",
  "active_commands": 0
}
```

### 4. GET /health - Health Check

**Response:**
```json
{
  "status": "OK",
  "service": "Stnr (Starboard)",
  "state": "IDLE"
}
```

## Command Flow

```
MMC                          Stnr
 |                           |
 |--- POST /fire (cmd) ----> |
 |                           | Fire command accepted
 |                           | Return ACK immediately
 | <--- ACK (code=0) --------|
 |                           | Command executes asynchronously
 |                           | State: ARMED → FIRING → COMPLETED
 |                           |
 | (optional)                |
 |--- GET /fire/<cmd_id> --> |
 | <--- Status (COMPLETED) --|
```

## ACK Codes

- `0` (ACK_SUCCESS) - Command accepted and executing
- `1` (ACK_INVALID_COMMAND) - Missing required fields
- `2` (ACK_BUSY) - System busy or command already processing
- `3` (ACK_ERROR) - Internal error

## Fire Command States

- `IDLE` - Awaiting command
- `ARMED` - Command received and validated
- `FIRING` - Weapon firing in progress
- `COMPLETED` - Fire sequence complete
- `ERROR` - Command failed

## Testing Scenarios

### Scenario 1: Single Fire Command
```python
sim = NetworkSimulator()
success, ack = sim.send_fire_command("T-1", weapon_type="CANNON")
```

### Scenario 2: Sequential Firing (5 commands, 2s apart)
```python
sim = NetworkSimulator()
sim.run_test_sequence(num_commands=5, delay_between=2.0)
sim.print_results()
```

### Scenario 3: Rapid Fire (continuous)
```python
sim = NetworkSimulator()
sim.run_continuous(interval=0.5)  # 1 command every 500ms
```

## Dependencies

- `flask` - REST API server
- `requests` - HTTP client for simulator
- `threading` - Background command execution
- Standard library: `json`, `time`, `random`, `logging`

Install with:
```bash
pip install flask requests
```

## Notes

- Fire commands execute asynchronously to avoid blocking the REST API
- ACK is returned immediately (command_state = ARMED), actual firing happens in background
- Network simulator can test at various intervals and detect failures
- All fire commands are logged for auditing
