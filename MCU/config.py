"""
MCU configuration
"""

# Server settings
MCU_HOST = "0.0.0.0"
MCU_PORT = 8003
MCU_DEBUG = True

# Callback to MMC (if you run a mock MMC to receive notifications)
SIM_HOST = "localhost"
SIM_PORT = 8004
MMC_CALLBACK_URL = f"http://{SIM_HOST}:{SIM_PORT}/callback"

# Fire states
FIRE_STATE_IDLE = "IDLE"
FIRE_STATE_LOCKED = "LOCKED"
FIRE_STATE_FIRING = "FIRING"
FIRE_STATE_COMPLETED = "COMPLETED"
FIRE_STATE_ERROR = "ERROR"

# ACK codes
ACK_SUCCESS = 0
ACK_INVALID_COMMAND = 1
ACK_BUSY = 2
ACK_ERROR = 3
