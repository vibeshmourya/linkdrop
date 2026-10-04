"""
LinkDrop - Configuration
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"

# Ensure directories exist
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Security Limits
MAX_DOWNLOAD_SIZE_BYTES = 1024 * 1024 * 1024 * 2  # 2 GB limit per download
ANALYSIS_TIMEOUT_SECONDS = 25
DOWNLOAD_TIMEOUT_SECONDS = 600  # 10 minutes max
FILE_RETENTION_SECONDS = 1800   # 30 minutes before temp cleanup

# Server Settings
HOST = "127.0.0.1"
PORT = 8000
DEBUG = False
