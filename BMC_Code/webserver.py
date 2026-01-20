from flask import Flask, render_template, request, jsonify, send_from_directory
import json
from pathlib import Path
import time
import urllib.request
import urllib.error
import threading
from config import LAUNCHER_URL, LAUNCHER_ENDPOINT

app = Flask(__name__)

# In-memory storage for targets (replace with database if needed)
targets = {}
target_timestamps = {}  # Track last update time for each target
selected_target = None  # Track currently selected target
turret_azimuth = 0  # Track current turret azimuth in degrees
INACTIVE_THRESHOLD = 5.0  # seconds

# ============= Helper Functions =============
updateing_target = False
def notify_launcher(target_id):
    updateing_target = True
    """Notify launcher about the selected target position"""
    if not target_id or target_id not in targets:
        updateing_target = False
        return False
    
    try:
        target_data = targets[target_id]
        position = target_data.get('position', {})
        velocity = target_data.get('velocity', {})
        
        payload = {
            'target_id': 1,
            'position_north': position.get('north', 0),
            'position_east': position.get('east', 0),
            'position_down': position.get('down', 0),
            'velocity_north': velocity.get('vn', 0),
            'velocity_east': velocity.get('ve', 0),
            'velocity_down': velocity.get('vd', 0),
        }
        
        launcher_url = f"{LAUNCHER_URL}{LAUNCHER_ENDPOINT}"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            launcher_url, 
            data=data_bytes, 
            headers={'Content-Type': 'application/json'}, 
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            response_data = resp.read()
        
        print(f"Notified launcher about target {target_id}: {payload}")
        updateing_target = False
        return True
    except Exception as e:
        print(f"Error notifying launcher: {e}")
        updateing_target =False
        return False

def notify_launcher_async(target_id):
    """Send launcher notification asynchronously without blocking"""
    if not updateing_target:
        thread = threading.Thread(target=notify_launcher, args=(target_id,), daemon=True)
        thread.start()

# ============= Helper Functions =============

def get_target_with_status(target_id, target_data):
    """Add active/inactive status based on last update time"""
    last_update = target_timestamps.get(target_id, time.time())
    is_active = (time.time() - last_update) < INACTIVE_THRESHOLD
    
    result = target_data.copy() if isinstance(target_data, dict) else target_data
    if isinstance(result, dict):
        result['_active'] = is_active
        result['_last_update'] = last_update
    return result

def get_all_targets_with_status():
    """Get all targets with active/inactive status"""
    return {target_id: get_target_with_status(target_id, data) 
            for target_id, data in targets.items()}

# ============= REST API Endpoints =============

@app.route('/api/TARGET', methods=['POST'])
def update_target():
    """
    POST endpoint to update target info
    Expects JSON payload with hierarchical structure containing position and velocity
    Can accept either a single target object or an array of targets
    """
    try:
        data = request.get_json()                       

        def handle_target(data):

            # Extract target ID (required)
            target_id = data.get('id')
            
            if not target_id:
                return jsonify({'error': 'Target ID is required'}), 400
            
            # Validate hierarchical structure
            if 'position' not in data:
                return jsonify({'error': 'Position object is required'}), 400
        
            # Store target data and update timestamp
            targets[target_id] = data
            target_timestamps[target_id] = time.time()

        if isinstance(data, list):
            for target in data:
                response = handle_target(target)
        else:
            handle_target(data)

        for tgt_id in targets.keys():
            
            age = time.time() - target_timestamps[tgt_id]
            if age > INACTIVE_THRESHOLD:
                print(f"target_timestamps[{tgt_id}] = {target_timestamps[tgt_id]} ({age:.1f}s old) - removing inactive target")
                del targets[tgt_id]
                del target_timestamps[tgt_id] 

        # If there's a selected target, notify launcher asynchronously
        if selected_target:
            notify_launcher_async(selected_target)

        return jsonify({
            'status': 'success',
            'message': f'Target updated successfully',
            'data': data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/TARGET', methods=['GET'])
def get_targets():
    """GET endpoint to retrieve all targets with active/inactive status"""
    return jsonify(get_all_targets_with_status()), 200


@app.route('/api/TARGET/<target_id>', methods=['GET'])
def get_target(target_id):
    """GET endpoint to retrieve specific target with active/inactive status"""
    if target_id in targets:
        return jsonify(get_target_with_status(target_id, targets[target_id])), 200
    return jsonify({'error': 'Target not found'}), 404


@app.route('/api/TARGET/<target_id>', methods=['DELETE'])
def delete_target(target_id):
    """DELETE endpoint to remove a target"""
    global selected_target
    
    if target_id in targets:
        del targets[target_id]
        if target_id in target_timestamps:
            del target_timestamps[target_id]
        
        # Clear selection if deleted target was selected
        if selected_target == target_id:
            selected_target = None
        
        return jsonify({'status': 'success', 'message': f'Target {target_id} deleted'}), 200
    return jsonify({'error': 'Target not found'}), 404


@app.route('/api/TARGET/<target_id>/select', methods=['POST'])
def select_target(target_id):
    """POST endpoint to select a target and notify launcher asynchronously"""
    global selected_target
    
    if target_id not in targets:
        return jsonify({'error': 'Target not found'}), 404
    
    selected_target = target_id
    
    # Notify launcher asynchronously without blocking
    notify_launcher_async(target_id)
    
    return jsonify({
        'status': 'success',
        'message': f'Target {target_id} selected',
        'selected_target': target_id
    }), 200


@app.route('/api/turret/azimuth_update', methods=['POST'])
def update_turret_azimuth():
    """POST endpoint to update turret azimuth angle"""
    global turret_azimuth
    
    try:
        data = request.get_json()
        
        if not data or 'azimuth' not in data:
            return jsonify({'error': 'Azimuth value is required'}), 400
        
        azimuth = data.get('azimuth')
        
        # Validate that azimuth is a number
        try:
            azimuth = float(azimuth)
        except (TypeError, ValueError):
            return jsonify({'error': 'Azimuth must be a number'}), 400
        
        # Normalize azimuth to 0-360 range
        azimuth = azimuth % 360
        turret_azimuth = azimuth
        
        print(f"Turret azimuth updated: {azimuth}°")
        
        return jsonify({
            'status': 'success',
            'message': f'Turret azimuth updated to {azimuth}°',
            'azimuth': azimuth
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= Web Interface Routes =============

@app.route('/')
def index():
    """Serve the web interface"""
    return render_template('index.html')


@app.route('/operator')
def operator():
    """Serve the operator interface with map view"""
    return render_template('operator.html')


@app.route('/api/status')
def status():
    """API status endpoint"""
    return jsonify({
        'status': 'online',
        'targets_count': len(targets),
        'turret_azimuth': turret_azimuth
    }), 200


# ============= Error Handlers =============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)
    
    # Create default index.html if it doesn't exist
    index_path = Path('templates/index.html')
    
    print("🚀 Starting webserver on http://localhost:5000")
    print("📍 Web Interface: http://localhost:5000")
    print("📍 API Endpoint: http://localhost:5000/api/TARGET")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
