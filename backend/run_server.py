"""
Embodier Trader Backend — Entry point for PyInstaller bundle.
Starts the FastAPI server via uvicorn.
"""
import os
import sys

# When running as PyInstaller bundle, set the working directory
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
    # Ensure the app package is importable
    sys.path.insert(0, os.path.dirname(sys.executable))

from dotenv import load_dotenv
load_dotenv()

import uvicorn


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
