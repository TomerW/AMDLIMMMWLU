#!/usr/bin/env python
"""
Stnr (Starboard) launcher.
Starts the REST API server to receive Fire commands from MMC.
"""

import sys
import os

# Support running the file both as a module (python -m Stnr.run)
# and directly as a script (python Stnr/run.py). Relative imports
# fail when the file is executed as a script, so try the package
# relative imports first and fall back to inserting the package
# parent directory on sys.path and importing the package absolutely.
try:
    from . import config
    from .api_server import run_server
    from .network_simulator import NetworkSimulator
except Exception:
    # We're probably running the script directly. Ensure the parent
    # directory (workspace root) is on sys.path so `Stnr` is importable.
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
    # Import using the package name
    from Stnr import config
    from Stnr.api_server import run_server
    from Stnr.network_simulator import NetworkSimulator


def main():
    """Main entry point for Stnr."""
    import argparse

    parser = argparse.ArgumentParser(description="Stnr (Starboard) Fire Control System")
    parser.add_argument("--mode", choices=["server", "simulator"], default="server",
                        help="Run mode: server (REST API) or simulator (test)")
    parser.add_argument("--host", default=config.STNR_HOST, help=f"Server host (default {config.STNR_HOST})")
    parser.add_argument("--port", type=int, default=config.STNR_PORT, help=f"Server port (default {config.STNR_PORT})")
    parser.add_argument("--debug", action="store_true", default=config.STNR_DEBUG, help="Enable debug mode")

    args = parser.parse_args()

    if args.mode == "server":
        print(f"\n[STNR] Starting REST API server...")
        print(f"       Host: {args.host}")
        print(f"       Port: {args.port}")
        print(f"       Endpoints:")
        print(f"         POST   /fire              - Submit Fire command")
        print(f"         GET    /fire/<cmd_id>    - Get Fire command status")
        print(f"         GET    /status            - Get Stnr status")
        print(f"         GET    /health            - Health check\n")

        try:
            run_server(host=args.host, port=args.port, debug=args.debug)
        except KeyboardInterrupt:
            print("\n[STNR] Server stopped.")
            sys.exit(0)

    elif args.mode == "simulator":
        print(f"\n[STNR] Starting Network Simulator...")
        print(f"       Target Stnr URL: http://{args.host}:{args.port}\n")

        from .network_simulator import run_simulator_interactive
        run_simulator_interactive()


if __name__ == "__main__":
    main()
