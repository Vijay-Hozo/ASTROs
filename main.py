import sys
import os

# Add the backend directory to sys.path so that all internal imports resolve perfectly
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if os.path.exists(backend_dir):
    sys.path.insert(0, backend_dir)

from backend.main import app
