# Universal Media Downloader

A clean, modern, and high-performance **Universal Media Downloader** built from scratch with Python (FastAPI), `yt-dlp`, `FFmpeg`, and lightweight Vanilla HTML/CSS/JavaScript.

Designed with a single universal workflow: paste a URL, analyze available streams, choose format/quality, and download directly without complicated accounts, history bloat, or enterprise dashboards.

---

## Architecture & Workflow

```text
PASTE PUBLIC URL
      ↓
POST /api/analyze (SSRF & Security Validation)
      ↓
SOURCE DETECTION & MEDIA EXTRACTION
      ↓
DISPLAY METADATA & AVAILABLE FORMATS
      ↓
SELECT FORMAT / QUALITY (Video / Audio / Image / Gallery)
      ↓
POST /api/download (Asynchronous Thread Pool)
      ↓
STREAM PROCESSING & FFMPEG REMUXING
      ↓
DIRECT FILE DELIVERY & AUTOMATIC CLEANUP
```

---

## Key Features

- **Single Universal Input**: Automatically identifies YouTube, Instagram, Facebook, TikTok, X (Twitter), WhatsApp status links, and direct media files.
- **Clean Format & Quality Options**:
  - **Video**: 4K, 2K, 1080p, 720p, 480p, 360p with estimated sizes and automatic audio remuxing to MP4.
  - **Audio**: High-Quality MP3 (320kbps), M4A (AAC), or lossless WAV extraction powered by FFmpeg.
  - **Images & Galleries**: High-resolution thumbnails, post images, and multi-item gallery downloads packaged cleanly into `.zip` archives.
- **Enterprise-Grade Security Without Bloat**:
  - Strict SSRF (Server-Side Request Forgery) protection rejecting private IPs, loopback, multicast, and cloud metadata endpoints (`169.254.169.254`).
  - Path traversal and filename sanitization.
  - Safe subprocess argument arrays without raw shell execution.
  - Transient in-memory job coordination with automatic temporary file cleanup.
  - Zero databases, zero user logins, zero tracking.
- **Human-Friendly Error Messages**: Clear explanations for private content, login requirements, DRM locks, or expired links.

---

## Project Structure

```text
universal-media-downloader/
│
├── backend/
│   ├── app.py                      # FastAPI application & REST endpoints
│   │
│   ├── core/
│   │   ├── config.py               # Paths, limits, and runtime configuration
│   │   ├── security.py             # SSRF protection, IP verification, filename sanitizer
│   │   └── validators.py           # URL validation & length checks
│   │
│   ├── services/
│   │   ├── source_detector.py      # Platform & direct media detector
│   │   ├── media_analyzer.py       # Metadata extraction and format grouping
│   │   ├── downloader.py           # Asynchronous job coordinator & progress tracker
│   │   ├── video_downloader.py     # yt-dlp video downloader with FFmpeg MP4 merge
│   │   ├── audio_downloader.py     # Audio extraction to MP3/M4A/WAV
│   │   ├── image_downloader.py     # Image downloader with Pillow conversion
│   │   └── gallery_downloader.py   # Multi-item carousel/gallery downloader & ZIP bundler
│   │
│   └── utils/
│       ├── filenames.py            # Path containment & collision-free naming
│       └── cleanup.py              # Automatic expiration cleanup of temp files
│
├── frontend/
│   ├── index.html                  # Accessible, human-crafted downloader UI
│   ├── style.css                   # Clean, restrained modern styling
│   └── app.js                      # Reactive analysis, format switching, progress polling
│
├── tests/
│   ├── test_core.py                # Security, SSRF, detector, and analyzer tests
│   └── test_download.py            # Real audio extraction and image download tests
│
├── downloads/                      # Isolated destination for completed downloads
├── temp/                           # Transient scratch workspace for remuxing
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Installation & Prerequisites

### 1. Requirements
- **Python 3.11+**
- **FFmpeg** (installed and accessible in PATH)

Verify FFmpeg:
```bash
ffmpeg -version
```

### 2. Setup Virtual Environment
```bash
cd universal-media-downloader
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Application

Start the server:
```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
```text
http://127.0.0.1:8000
```

---

## Running Tests

Run the core unit and integration test suite:
```bash
python tests/test_core.py
```

Run the download and extraction pipeline test:
```bash
python tests/test_download.py
```

---

## Supported Sources & Media Types

| Platform | Supported Media Types | Quality / Formats |
| :--- | :--- | :--- |
| **YouTube** | Videos, Shorts, Audio | 1080p, 720p, 480p, 360p (MP4) / MP3, M4A, WAV |
| **Instagram** | Public Reels, Videos, Posts, Images | MP4 Video / High-Res JPG / Multi-item ZIP |
| **Facebook** | Public Videos, Reels | High / Standard Quality MP4 |
| **TikTok** | Public Videos | Original MP4 |
| **X (Twitter)**| Public Videos, Images | MP4 / JPG |
| **Direct Media**| `.mp4`, `.webm`, `.mp3`, `.wav`, `.jpg`, `.png`, `.webp` | Native or converted |

*Note: Respects access restrictions and platform policies. Private, DRM-protected, or login-required media are safely rejected with clear notifications.*
