"""Run the complete demo"""

import subprocess
import time
import webbrowser
import sys
from pathlib import Path

def main():
    """Run the complete demo"""
    
    print("🚀 Dubai ETA Prediction System - Demo Runner")
    print("=" * 50)
    
    # Check if models exist
    if not Path("data/models").exists():
        print("⚠️  Models not found. Training models first...")
        subprocess.run([sys.executable, "scripts/train_model.py"])
        print("✅ Models trained successfully!")
    
    # Start API server
    print("\n📡 Starting API server...")
    api_process = subprocess.Popen(
        ["uvicorn", "api.main:app", "--reload", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    # Open browser
    print("🌐 Opening browser...")
    webbrowser.open("http://localhost:8000")
    webbrowser.open("file://" + str(Path("frontend/index.html").absolute()))
    
    print("\n✅ Demo is running!")
    print("📍 API: http://localhost:8000")
    print("📍 Frontend: Open frontend/index.html in your browser")
    print("\nPress Ctrl+C to stop the demo...")
    
    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
        api_process.terminate()
        print("✅ Demo stopped.")

if __name__ == "__main__":
    main()