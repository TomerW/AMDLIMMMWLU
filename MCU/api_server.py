"""
MCU REST API server.
"""

from flask import Flask, request, jsonify
import logging
import threading
from . import config
from .fire_command import FireCommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_EVENTS = []
_EVENTS_LOCK = threading.Lock()
_MAX_EVENTS = 200


def _push_event(e):
    with _EVENTS_LOCK:
        _EVENTS.append(e)
        if len(_EVENTS) > _MAX_EVENTS:
            del _EVENTS[0: len(_EVENTS)-_MAX_EVENTS]


handler = FireCommandHandler(event_callback=_push_event)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status":"OK","service":"MCU"}), 200


@app.route('/fire', methods=['POST'])
def fire():
    data = request.get_json()
    if not data:
        return jsonify({"ack_code": config.ACK_INVALID_COMMAND, "error":"no json"}), 400
    logger.info(f"[FIRE REQ] {data}")
    ack, resp = handler.process_fire_command(data)
    code = 200 if ack == config.ACK_SUCCESS else 400
    return jsonify(resp), code


@app.route('/fire/<cmd_id>', methods=['GET'])
def status(cmd_id):
    try:
        return jsonify(handler.get_command_status(cmd_id)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/events', methods=['GET'])
def events():
    with _EVENTS_LOCK:
        return jsonify({"events": list(_EVENTS)}), 200


@app.route('/ui', methods=['GET'])
def ui_page():
        # Simple single-file web UI that polls /events and renders them
        html = '''
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <title>MCU Network Monitor</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 12px }
                #log { width: 100%; height: 80vh; border: 1px solid #ccc; padding: 8px; overflow: auto; background:#f7f7f7 }
                .evt { margin: 4px 0; padding: 6px; border-radius:4px; background: #fff; box-shadow: 0 1px 1px rgba(0,0,0,0.03) }
            </style>
        </head>
        <body>
            <h3>MCU Network Monitor</h3>
            <div id="log"></div>
            <script>
                let lastTs = 0;
                async function poll(){
                    try{
                        const r = await fetch('/events');
                        const j = await r.json();
                        const log = document.getElementById('log');
                        (j.events || []).forEach(e=>{
                            if((e.timestamp||0) > lastTs){
                                const d = new Date((e.timestamp||0)*1000);
                                const div = document.createElement('div');
                                div.className='evt';
                                div.textContent = `[${d.toISOString()}] ${e.type.toUpperCase()} ${e.command_id || ''} ${JSON.stringify(e.payload||{})}`;
                                log.appendChild(div);
                                lastTs = Math.max(lastTs, e.timestamp||lastTs);
                            }
                        });
                        log.scrollTop = log.scrollHeight;
                    }catch(err){
                        console.error('poll err', err);
                    }
                }
                setInterval(poll, 1000);
                poll();
            </script>
        </body>
        </html>
        '''
        return html, 200, {'Content-Type': 'text/html'}


@app.route('/status', methods=['GET'])
def status_root():
    return jsonify({"service":"MCU","active_commands": len(handler.commands)}), 200


def run_server(host=config.MCU_HOST, port=config.MCU_PORT, debug=config.MCU_DEBUG):
    logger.info(f"Starting MCU on {host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    run_server()
