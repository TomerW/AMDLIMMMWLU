"""
MCU launcher - run server or UI.
"""
import sys
import os

try:
    from . import config
    from .api_server import run_server
    from .ui import McuNetworkUI
except Exception:
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
    from MCU import config
    from MCU.api_server import run_server
    from MCU.ui import McuNetworkUI


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['server','ui'], default='server')
    parser.add_argument('--host', default=config.MCU_HOST)
    parser.add_argument('--port', type=int, default=config.MCU_PORT)
    args = parser.parse_args()

    if args.mode == 'server':
        run_server(host=args.host, port=args.port)
    else:
        display_host = 'localhost' if args.host in ('0.0.0.0','::','') else args.host
        url = f"http://{display_host}:{args.port}"
        ui = McuNetworkUI(mcu_url=url)
        ui.run()


if __name__ == '__main__':
    main()
