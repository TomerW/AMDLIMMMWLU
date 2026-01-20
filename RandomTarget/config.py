import threading
import os

# --- Configuration ---
JSON_FILENAME = "live_targets.json"
# Secondary test output directory/filename (will be created when used)
RANDOM_TEST_DIR = "Random_test"
TEST_JSON_FILENAME = os.path.join(RANDOM_TEST_DIR, "live_targets.json")
TARGET_UPDATE_RATE = 0.05       # target internal update rate (s)
JSON_WRITE_RATE = 0.1           # default JSON flush interval (s)
TARGET_LIFETIME = 300.0         # seconds a target remains active (5 minutes)

# Endpoint / sending control (can be updated from UI)
SEND_TO_ENDPOINT = False
ENDPOINT_URL = "http://172.20.10.3:5000/api/TARGET"   # default local test endpoint

# ENDPOINT_URL = "http://localhost:8000/upload"   # default local test endpoint
ENDPOINT_API_KEY = ""

# --- Shared Resources (Protected by Lock) ---
active_targets = []             # list of Target instances
targets_lock = threading.Lock()
target_threads = []             # references to per-target threads
stop_threads_event = threading.Event()