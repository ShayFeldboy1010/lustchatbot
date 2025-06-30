"""
LustBot - AI Shopping Assistant
FastAPI + Agno Agent
"""

__version__ = "1.0.0"

# Import the FastAPI app and make it available at module level for gunicorn
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .main import app

# Make the app available at module level for gunicorn
__all__ = ['app']
