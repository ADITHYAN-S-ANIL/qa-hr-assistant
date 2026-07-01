import threading
import time
import os
import sys

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_leave_api():
    print("Starting Mock Leave API on port 5001...")
    from mock_leave_api import app as leave_app
    leave_app.run(port=5001, debug=False, use_reloader=False)

def run_main_backend():
    print("Starting Main Backend on port 5000...")
    from app import app as main_app, init_db
    init_db()
    main_app.run(port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start leave API in a background thread
    t = threading.Thread(target=run_leave_api, daemon=True)
    t.start()
    
    # Give it a second to start
    time.sleep(1)
    
    # Run main backend in the foreground
    run_main_backend()
