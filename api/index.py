import sys
import os

# Add src/backend to Python path so fastapi_app is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "backend"))

from fastapi_app import app  # noqa: F401  (Vercel ASGI entrypoint)
