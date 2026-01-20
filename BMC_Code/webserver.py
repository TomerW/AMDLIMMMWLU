from flask import Flask, render_template, request, jsonify, send_from_directory
import json
from pathlib import Path
import time

app = Flask(__name__)

# In-memory storage for targets (replace with database if needed)
targets = {}
target_timestamps = {}  # Track last update time for each target
INACTIVE_THRESHOLD = 1.0  # seconds

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

        for tgt_id in targets.keys():
            if target_timestamps[tgt_id] > time.time() - INACTIVE_THRESHOLD:
                del targets[tgt_id]
                del target_timestamps[tgt_id] 
                            

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
    if target_id in targets:
        del targets[target_id]
        if target_id in target_timestamps:
            del target_timestamps[target_id]
        return jsonify({'status': 'success', 'message': f'Target {target_id} deleted'}), 200
    return jsonify({'error': 'Target not found'}), 404


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
        'targets_count': len(targets)
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
