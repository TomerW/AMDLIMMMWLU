"""
REST API server for Stnr (Starboard).
Receives Fire commands from MMC and returns ACK/NACK responses.
"""

from flask import Flask, request, jsonify
import json
import logging
from . import config
from .fire_command import FireCommandHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
fire_handler = FireCommandHandler()


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "OK",
        "service": "Stnr (Starboard)",
        "state": fire_handler.current_state
    }), 200


@app.route("/fire", methods=["POST"])
def fire_endpoint():
    """
    Main Fire command endpoint.
    
    POST /fire
    Content-Type: application/json
    
    Request:
    {
        "command_id": "FIRE_001",
        "target_id": "T-1",
        "weapon_type": "CANNON",
        "azimuth": 45.0,
        "elevation": 10.0,
        "range_m": 2500.0
    }
    
    Response (ACK):
    {
        "ack_code": 0,
        "command_id": "FIRE_001",
        "state": "ARMED",
        "message": "Fire command FIRE_001 accepted and executing"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ack_code": config.ACK_INVALID_COMMAND, "error": "No JSON payload"}), 400

        logger.info(f"[FIRE CMD] Received: {json.dumps(data)}")

        ack_code, response = fire_handler.process_fire_command(data)

        http_code = 200 if ack_code == config.ACK_SUCCESS else 400
        return jsonify(response), http_code

    except Exception as e:
        logger.error(f"[ERROR] fire_endpoint: {e}")
        return jsonify({
            "ack_code": config.ACK_ERROR,
            "error": str(e)
        }), 500


@app.route("/fire/<command_id>", methods=["GET"])
def fire_status(command_id):
    """Get status of a specific fire command."""
    try:
        status = fire_handler.get_command_status(command_id)
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"[ERROR] fire_status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/status", methods=["GET"])
def status():
    """Get overall Stnr status."""
    return jsonify({
        "service": "Stnr (Starboard)",
        "state": fire_handler.current_state,
        "active_commands": len(fire_handler.commands)
    }), 200


def run_server(host=config.STNR_HOST, port=config.STNR_PORT, debug=config.STNR_DEBUG):
    """Start the Flask REST API server."""
    logger.info(f"Starting Stnr REST API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    run_server()
