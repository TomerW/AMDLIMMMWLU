from flask import Flask, render_template, request, jsonify, send_from_directory
import json
from pathlib import Path

app = Flask(__name__)

# In-memory storage for targets (replace with database if needed)
targets = {}

# ============= REST API Endpoints =============

@app.route('/api/TARGET', methods=['POST'])
def update_target():
    """
    POST endpoint to update target info
    Expects JSON payload with target data
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Extract target ID (required)
        target_id = data.get('id')
        if not target_id:
            return jsonify({'error': 'Target ID is required'}), 400
        
        # Store target data
        targets[target_id] = data
        
        return jsonify({
            'status': 'success',
            'message': f'Target {target_id} updated successfully',
            'data': data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/TARGET', methods=['GET'])
def get_targets():
    """GET endpoint to retrieve all targets"""
    return jsonify(targets), 200


@app.route('/api/TARGET/<target_id>', methods=['GET'])
def get_target(target_id):
    """GET endpoint to retrieve specific target"""
    if target_id in targets:
        return jsonify(targets[target_id]), 200
    return jsonify({'error': 'Target not found'}), 404


@app.route('/api/TARGET/<target_id>', methods=['DELETE'])
def delete_target(target_id):
    """DELETE endpoint to remove a target"""
    if target_id in targets:
        del targets[target_id]
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
    if not index_path.exists():
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Target Management System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background-color: #333; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        h1 { margin-bottom: 10px; }
        .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section h2 { color: #333; margin-bottom: 15px; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        input, textarea, button { padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; }
        input, textarea { width: 100%; }
        button { background-color: #007bff; color: white; cursor: pointer; width: auto; }
        button:hover { background-color: #0056b3; }
        button.delete { background-color: #dc3545; }
        button.delete:hover { background-color: #c82333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        .response { background-color: #f8f9fa; padding: 10px; border-left: 4px solid #007bff; margin-top: 10px; border-radius: 4px; word-break: break-all; }
        .error { border-left-color: #dc3545; color: #dc3545; }
        .success { border-left-color: #28a745; color: #28a745; }
        .targets-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .target-card { background-color: #f8f9fa; padding: 15px; border-radius: 4px; border: 1px solid #ddd; }
        .target-card h3 { color: #007bff; margin-bottom: 10px; }
        .target-card p { font-size: 0.9em; color: #666; margin-bottom: 10px; }
        pre { background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Target Management System</h1>
            <p>REST API Server - Manage targets via Web Interface or API</p>
        </header>

        <div class="section">
            <h2>📊 System Status</h2>
            <button onclick="checkStatus()">Check Status</button>
            <div id="statusResponse" class="response" style="display:none;"></div>
        </div>

        <div class="section">
            <h2>➕ Create/Update Target</h2>
            <div class="form-group">
                <label for="targetId">Target ID:</label>
                <input type="text" id="targetId" placeholder="e.g., target-001" required>
            </div>
            <div class="form-group">
                <label for="targetData">Target Data (JSON):</label>
                <textarea id="targetData" rows="6" placeholder='{"name": "Target 1", "value": 100, "status": "active"}' required></textarea>
            </div>
            <button onclick="updateTarget()">Update Target</button>
            <div id="updateResponse" class="response" style="display:none;"></div>
        </div>

        <div class="section">
            <h2>📋 All Targets</h2>
            <button onclick="getAllTargets()">Load All Targets</button>
            <div id="targetsList" class="targets-list" style="margin-top: 15px;"></div>
        </div>

        <div class="section">
            <h2>🔍 Get Specific Target</h2>
            <div class="form-group">
                <label for="searchId">Target ID:</label>
                <input type="text" id="searchId" placeholder="e.g., target-001">
            </div>
            <button onclick="getTarget()">Search</button>
            <div id="getResponse" class="response" style="display:none;"></div>
        </div>

        <div class="section">
            <h2>🗑️ Delete Target</h2>
            <div class="form-group">
                <label for="deleteId">Target ID:</label>
                <input type="text" id="deleteId" placeholder="e.g., target-001">
            </div>
            <button class="delete" onclick="deleteTarget()">Delete Target</button>
            <div id="deleteResponse" class="response" style="display:none;"></div>
        </div>
    </div>

    <script>
        function showResponse(elementId, data, isError = false) {
            const element = document.getElementById(elementId);
            element.textContent = JSON.stringify(data, null, 2);
            element.classList.toggle('error', isError);
            element.classList.toggle('success', !isError);
            element.style.display = 'block';
        }

        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                showResponse('statusResponse', data, !response.ok);
            } catch (error) {
                showResponse('statusResponse', { error: error.message }, true);
            }
        }

        async function updateTarget() {
            const id = document.getElementById('targetId').value;
            const dataStr = document.getElementById('targetData').value;

            if (!id || !dataStr) {
                showResponse('updateResponse', { error: 'ID and Data are required' }, true);
                return;
            }

            try {
                const payload = JSON.parse(dataStr);
                payload.id = id;

                const response = await fetch('/api/TARGET', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                showResponse('updateResponse', data, !response.ok);
            } catch (error) {
                showResponse('updateResponse', { error: error.message }, true);
            }
        }

        async function getAllTargets() {
            try {
                const response = await fetch('/api/TARGET');
                const targets = await response.json();

                const container = document.getElementById('targetsList');
                container.innerHTML = '';

                if (Object.keys(targets).length === 0) {
                    container.innerHTML = '<p>No targets found</p>';
                    return;
                }

                Object.entries(targets).forEach(([id, data]) => {
                    const card = document.createElement('div');
                    card.className = 'target-card';
                    card.innerHTML = `
                        <h3>${id}</h3>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                        <button class="delete" onclick="deleteTarget('${id}')">Delete</button>
                    `;
                    container.appendChild(card);
                });
            } catch (error) {
                alert('Error loading targets: ' + error.message);
            }
        }

        async function getTarget() {
            const id = document.getElementById('searchId').value;
            if (!id) {
                showResponse('getResponse', { error: 'ID is required' }, true);
                return;
            }

            try {
                const response = await fetch(`/api/TARGET/${id}`);
                const data = await response.json();
                showResponse('getResponse', data, !response.ok);
            } catch (error) {
                showResponse('getResponse', { error: error.message }, true);
            }
        }

        async function deleteTarget(id = null) {
            id = id || document.getElementById('deleteId').value;
            if (!id) {
                showResponse('deleteResponse', { error: 'ID is required' }, true);
                return;
            }

            if (!confirm(`Are you sure you want to delete target "${id}"?`)) return;

            try {
                const response = await fetch(`/api/TARGET/${id}`, { method: 'DELETE' });
                const data = await response.json();
                showResponse('deleteResponse', data, !response.ok);
                getAllTargets();
            } catch (error) {
                showResponse('deleteResponse', { error: error.message }, true);
            }
        }

        // Load targets on page load
        window.onload = () => getAllTargets();
    </script>
</body>
</html>''')
    
    print("🚀 Starting webserver on http://localhost:5000")
    print("📍 Web Interface: http://localhost:5000")
    print("📍 API Endpoint: http://localhost:5000/api/TARGET")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
