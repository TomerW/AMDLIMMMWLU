"""
Stnr (Starboard) Configuration
Handles Fire commands from MMC via REST API and returns acknowledgments.
"""

# Server settings
STNR_HOST = "0.0.0.0"
STNR_PORT = 8001
STNR_DEBUG = True

# Fire command defaults
DEFAULT_FIRE_TIMEOUT = 5.0  # seconds to wait for fire command execution

# Network simulator settings (for testing with MMC)
SIM_ENABLED = True
SIM_HOST = "localhost"
SIM_PORT = 8002

# Fire command states
FIRE_STATE_IDLE = "IDLE"
FIRE_STATE_ARMED = "ARMED"
FIRE_STATE_FIRING = "FIRING"
FIRE_STATE_COMPLETED = "COMPLETED"
FIRE_STATE_ERROR = "ERROR"

# ACK/NACK codes
ACK_SUCCESS = 0
ACK_INVALID_COMMAND = 1
ACK_BUSY = 2
ACK_ERROR = 3
