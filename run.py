#!/usr/bin/env python3
"""
PubLog Application Runner
Starts both Streamlit UI and FastAPI server
"""
import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# Change to app directory
os.chdir(Path(__file__).parent)

def run_streamlit():
    """Run Streamlit server"""
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", "8501",
         "--server.address", "localhost",
         "--browser.gatherUsageStats", "false",
         "--server.headless", "true"],
    )

def run_api():
    """Run FastAPI server"""
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app",
         "--host", "localhost",
         "--port", "8000"],
    )

def main():
    print("=" * 60)
    print("PubLog Application")
    print("=" * 60)
    print()
    print("Starting services...")
    print()

    # Start both servers
    api_process = run_api()
    time.sleep(2)  # Give API time to start
    streamlit_process = run_streamlit()

    time.sleep(3)  # Give Streamlit time to start

    print("Services started:")
    print(f"  📊 Streamlit UI:  http://localhost:8501")
    print(f"  🌐 REST API:      http://localhost:8000")
    print(f"  📖 API Docs:      http://localhost:8000/api/docs")
    print()
    print("Press Ctrl+C to stop all services")
    print("=" * 60)

    def signal_handler(sig, frame):
        print("\nShutting down...")
        api_process.terminate()
        streamlit_process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Wait for processes
    try:
        while True:
            # Check if processes are still running
            if api_process.poll() is not None:
                print("API server stopped unexpectedly")
                break
            if streamlit_process.poll() is not None:
                print("Streamlit server stopped unexpectedly")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        api_process.terminate()
        streamlit_process.terminate()

if __name__ == "__main__":
    main()
