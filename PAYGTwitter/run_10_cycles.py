#!/usr/bin/env python3
"""
Wrapper to run TwitterAutoReply.py 10 times with 30-second delays
For testing API reliability
"""

import time
import subprocess
import sys
from datetime import datetime

CYCLES = 200
DELAY_SECONDS = 10

def run_cycle(cycle_number):
    """Run a single cycle of TwitterAutoReply.py"""
    print("=" * 80)
    print(f"CYCLE {cycle_number}/{CYCLES} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    try:
        # Run TwitterAutoReply.py as a subprocess
        result = subprocess.run(
            [sys.executable, "TwitterAutoReply.py"],
            capture_output=False,  # Show output in real-time
            text=True
        )

        print(f"\nCycle {cycle_number} completed with return code: {result.returncode}")

    except Exception as e:
        print(f"\nError in cycle {cycle_number}: {e}")

    return True

def main():
    """Run 10 cycles with delays"""
    print("\n" + "=" * 80)
    print(f"STARTING {CYCLES} CYCLES WITH {DELAY_SECONDS}-SECOND DELAYS")
    print("=" * 80 + "\n")

    for i in range(1, CYCLES + 1):
        run_cycle(i)

        # Delay between cycles (except after the last one)
        if i < CYCLES:
            print(f"\n⏳ Waiting {DELAY_SECONDS} seconds before next cycle...\n")
            time.sleep(DELAY_SECONDS)

    print("\n" + "=" * 80)
    print(f"ALL {CYCLES} CYCLES COMPLETED!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Stopping cycles.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
