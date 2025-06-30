import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import the app
try:
    from app.main import app
except ImportError as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    print(f"Starting LustBot on {host}:{port}")
    uvicorn.run(app, host=host, port=port, debug=debug)
