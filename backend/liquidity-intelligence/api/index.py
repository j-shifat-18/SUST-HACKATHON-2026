"""
Vercel serverless entrypoint.
Exposes the FastAPI app as a Vercel-compatible handler.
"""
import sys
import os

# Ensure the app directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Vercel expects an `app` variable or a handler.
# The @vercel/python builder automatically detects FastAPI/ASGI apps.
