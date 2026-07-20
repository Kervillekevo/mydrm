# UHONDO - Video DRM Platform

A secure video streaming platform with HLS encryption, adaptive bitrate streaming, and token-based access control.

## Features

- **AES-128 Encrypted HLS Streaming** — videos are encrypted and served via signed token URLs
- **Adaptive Bitrate** — automatic quality switching between 240p, 360p, 480p, and 720p
- **Parallel Video Processing** — FFmate encodes all renditions simultaneously for faster processing
- **Token-based Security** — short-lived signed tokens for playlist, key, and segment access
- **User Authentication** — register, login, logout, password reset via email
- **User Profiles** — bio, phone, profile photo
- **Django Admin** — manage videos and users from admin panel
- **Redis Cache** — persistent segment alias cache across server restarts
- **PostgreSQL** — production-ready database

## Tech Stack

### Backend
- **Django 4.2** + Django REST Framework
- **Gunicorn** — WSGI server
- **Django Q** — async task queue for video processing
- **FFmate** — parallel ffmpeg encoding manager
- **FFmpeg** — video encoding (HLS + AES-128)
- **PostgreSQL** — production database
- **Redis** — caching (segment aliases, tokens, rate limiting)
- **Whitenoise** — static file serving

### Frontend
- **React** — SPA frontend
- **Video.js** — HLS video player with quality selector
- **React Router** — client-side routing

## Architecture

```
User Upload → Django → Django Q → FFmate → FFmpeg (4 parallel renditions)
                                         ↓
                              Webhook → Django → Video marked Ready
                                         ↓
                              React → Stream Token → HLS Manifest → Encrypted Segments
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- FFmpeg installed
- FFmate binary
- Redis (Memurai on Windows)
- PostgreSQL

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key
DEBUG=True
SITE_BASE_URL=http://localhost:3000
BACKEND_BASE_URL=http://127.0.0.1:8000
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
FFMATE_URL=http://localhost:8001
REDIS_URL=redis://127.0.0.1:6379/1
ALLOWED_HOSTS=
CORS_ALLOWED_ORIGINS=
CSRF_TRUSTED_ORIGINS=
ALLOWED_EMBED_ORIGINS=
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Start Django Q worker (separate terminal):

```bash
python manage.py qcluster
```

### FFmate Setup

Download FFmate from https://github.com/welovemedia/ffmate/releases and run:

```bash
./ffmate server --port 8001
```

### Frontend Setup

```bash
cd frontend
npm install
```

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
```

Start the frontend:

```bash
npm start
```

## Video Processing Flow

1. Admin uploads video via Django admin panel
2. Django Q queues the processing task
3. `process_video` generates AES-128 encryption key and keyinfo file
4. FFmate receives 4 parallel encoding jobs (240p, 360p, 480p, 720p)
5. Each job encodes to HLS with AES-128 encryption
6. FFmate sends webhook to Django when each rendition finishes
7. After all 4 renditions complete, video is marked as **Ready**

## Security

- All HLS segments served via one-time alias URLs (expire in 600 seconds)
- AES-128 encryption on all video segments
- Token validation on playlist requests (HMAC-SHA256 signed)
- Rate limiting on key and segment requests
- IP + User-Agent fingerprinting on tokens
- Context menu disabled on video player

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | required |
| `DEBUG` | Debug mode | `True` |
| `DATABASE_URL` | PostgreSQL connection URL | SQLite fallback |
| `SITE_BASE_URL` | Frontend URL (for password reset emails) | `http://localhost:3000` |
| `BACKEND_BASE_URL` | Backend URL (for embed codes) | `http://127.0.0.1:8000` |
| `FFMATE_URL` | FFmate server URL | `http://localhost:8001` |
| `REDIS_URL` | Redis connection URL | `redis://127.0.0.1:6379/1` |
| `EMAIL_HOST_USER` | Gmail address for sending emails | required |
| `EMAIL_HOST_PASSWORD` | Gmail app password | required |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | localhost only |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | localhost:3000 only |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins | empty |

## License

MIT