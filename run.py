import uvicorn
import webbrowser
import threading
import time

def open_browser():
    """Wait for the server to start, then open the frontend in the default browser."""
    time.sleep(1.5)  # Short delay to let Uvicorn initialize
    print("Opening frontend in your web browser...")
    webbrowser.open("http://127.0.0.1:8000/static/index.html")

if __name__ == "__main__":
    # Launch the browser in a separate background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start the FastAPI server (this is a blocking call)
    print("Starting FastAPI backend server...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
