# CertiMAP AI

CertiMAP AI is a local full-stack certificate verification and MAP point calculation web app. It includes:

- Role-based login for student, faculty, and admin users.
- Batch certificate upload for PDF, JPG, JPEG, PNG, and TXT files.
- Local AI-style keyword classification for category, event level, confidence, and MAP point calculation.
- SQLite database connectivity with editable MAP rules.
- Certificate file storage in `uploads/`.
- Faculty approval/rejection workflow, audit logging, notifications, dashboards, charts, and CSV report export.

## Run

```powershell
python server.py
```

Open http://127.0.0.1:8765

## Demo Logins

- Student: `student@certimap.local` / `student123`
- Faculty: `faculty@certimap.local` / `faculty123`
- Admin: `admin@certimap.local` / `admin123`

## OAuth Login

Google and LinkedIn buttons are available on the login page. To enable them, set these environment variables before starting the server:

- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`

## Storage

- Database: `data/certimap.db`
- Certificate files: `uploads/`

## Notes

This build uses only Python standard-library modules so it can run without installing packages. The AI pipeline is implemented as a local heuristic classifier. For production OCR and transformer classification, connect PaddleOCR, PyMuPDF, OpenCV, and sentence-transformers inside the upload pipeline in `server.py`.
# MAP_Counter
