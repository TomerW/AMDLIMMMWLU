"""
Network simulator for testing Stnr (Starboard) with MMC.
Simulates MMC sending Fire commands to Stnr and receiving ACKs.
"""

import requests
import json
import time
import threading
import random
from . import config


class NetworkSimulator:
    """Simulates MMC-Stnr network communication for testing."""

    def __init__(self, stnr_url="http://localhost:8001"):
        self.stnr_url = stnr_url
        self.mmc_url = "http://localhost:8000"  # assumed MMC location
        self.running = False
        self.command_counter = 0
        self.results = []

    def send_fire_command(self, target_id, weapon_type="CANNON", azimuth=None, elevation=None, range_m=None):
        """
        Send a Fire command to Stnr and receive ACK.
        
        Returns: (success: bool, ack_response: dict)
        """
        try:
            self.command_counter += 1
            command_id = f"FIRE_{self.command_counter:03d}"

            # Generate random fire parameters if not specified
            if azimuth is None:
                azimuth = random.uniform(0, 360)
            if elevation is None:
                elevation = random.uniform(0, 45)
            if range_m is None:
                range_m = random.uniform(1000, 5000)

            payload = {
                "command_id": command_id,
                "target_id": target_id,
                "weapon_type": weapon_type,
                "azimuth": azimuth,
                "elevation": elevation,
                "range_m": range_m
            }

            print(f"[SIM] Sending Fire command {command_id} to {self.stnr_url}/fire")
            print(f"      Target: {target_id}, Weapon: {weapon_type}, Az: {azimuth:.1f}°, El: {elevation:.1f}°, Range: {range_m:.1f}m")

            response = requests.post(
                f"{self.stnr_url}/fire",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )

            ack = response.json()
            ack_code = ack.get("ack_code", -1)
            success = response.status_code == 200 and ack_code == config.ACK_SUCCESS

            print(f"      ACK Code: {ack_code}, State: {ack.get('state', 'UNKNOWN')}")
            print(f"      Message: {ack.get('message', 'N/A')}")

            result = {
                "command_id": command_id,
                "target_id": target_id,
                "success": success,
                "ack_code": ack_code,
                "ack_response": ack,
                "timestamp": time.time()
            }
            self.results.append(result)

            return success, ack

        except Exception as e:
            print(f"[SIM ERROR] send_fire_command: {e}")
            return False, {"error": str(e)}

    def check_command_status(self, command_id):
        """Check status of a previously sent command."""
        try:
            response = requests.get(
                f"{self.stnr_url}/fire/{command_id}",
                timeout=5.0
            )
            status = response.json()
            print(f"[SIM] Status of {command_id}: {status.get('data', {}).get('state', 'UNKNOWN')}")
            return status
        except Exception as e:
            print(f"[SIM ERROR] check_command_status: {e}")
            return {"error": str(e)}

    def run_test_sequence(self, num_commands=5, delay_between=2.0):
        """Run a sequence of Fire commands for testing."""
        print(f"\n[SIM] Starting test sequence ({num_commands} commands, {delay_between}s between)")
        self.running = True
        target_ids = [f"T-{i+1}" for i in range(3)]

        for i in range(num_commands):
            if not self.running:
                break

            target_id = random.choice(target_ids)
            self.send_fire_command(target_id)

            if i < num_commands - 1:
                time.sleep(delay_between)

        print(f"[SIM] Test sequence completed. Sent {len(self.results)} commands.\n")
        self.print_results()

    def run_continuous(self, interval=3.0):
        """Run continuous Fire command generation."""
        print(f"\n[SIM] Starting continuous mode (1 command every {interval}s)")
        self.running = True
        target_ids = [f"T-{i+1}" for i in range(3)]

        try:
            while self.running:
                target_id = random.choice(target_ids)
                self.send_fire_command(target_id)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[SIM] Continuous mode stopped by user.")

    def print_results(self):
        """Print summary of all commands sent."""
        if not self.results:
            print("[SIM] No commands sent yet.")
            return

        successful = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - successful

        print(f"\n[SIM RESULTS]")
        print(f"  Total commands: {len(self.results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Success rate: {successful / len(self.results) * 100:.1f}%")

    def stop(self):
        """Stop continuous simulation."""
        self.running = False
        print("[SIM] Stopping simulator.")


def run_simulator_interactive():
    """Interactive simulator for manual testing."""
    sim = NetworkSimulator()

    while True:
        print("\n[SIM] Network Simulator - Menu:")
        print("  1. Send single Fire command")
        print("  2. Run test sequence (5 commands)")
        print("  3. Run continuous mode")
        print("  4. Check command status")
        print("  5. Print results")
        print("  6. Exit")

        choice = input("Select option (1-6): ").strip()

        if choice == "1":
            target_id = input("Target ID (default T-1): ").strip() or "T-1"
            sim.send_fire_command(target_id)

        elif choice == "2":
            sim.run_test_sequence(num_commands=5, delay_between=1.0)

        elif choice == "3":
            interval = float(input("Interval between commands (s, default 3.0): ") or "3.0")
            thread = threading.Thread(target=sim.run_continuous, args=(interval,), daemon=True)
            thread.start()
            try:
                thread.join()
            except KeyboardInterrupt:
                sim.stop()

        elif choice == "4":
            cmd_id = input("Command ID: ").strip()
            sim.check_command_status(cmd_id)

        elif choice == "5":
            sim.print_results()

        elif choice == "6":
            print("[SIM] Exiting.")
            break

        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    run_simulator_interactive()
