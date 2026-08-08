from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import csv
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import shutil
import sqlite3
import sys
import time


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "certimap.db"
MAX_UPLOAD_BYTES = 30 * 1024 * 1024

LEVELS = ["college", "taluka", "district", "university", "state", "national", "international"]

DEFAULT_RULES = [
    ("Paper Presentation", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Project Competition", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Hackathon", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Poster Competition", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Competitive Programming", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Workshop", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Industrial Training", "Certificate / report", None, None, None, None, None, None, None, 5, None),
    ("Internship", "Certificate / offer letter / report", None, None, None, None, None, None, None, 5, None),
    ("MOOC", "Certificate with final assessment", None, None, None, None, None, None, None, 5, None),
    ("Language Proficiency", "Certificate", None, None, None, None, None, None, None, 5, "Mandatory points - 5"),
    ("Sports", "Certificate", 3, 5, 8, 12, 15, 15, 20, None, None),
    ("Cultural", "Certificate", 3, 5, 8, 12, 15, 15, 20, None, None),
    ("Community Service - Two Day", "Certificate", None, None, None, None, None, None, None, 3, None),
    ("Community Service - Up To One Week", "Certificate", None, None, None, None, None, None, None, 6, None),
    ("Community Service - Recognition", "Recognition letter / document", None, None, None, None, None, None, None, 9, None),
    ("Community Service - One Semester", "Certificate / report", None, None, None, None, None, None, None, 12, None),
    ("Entrepreneurship Workshop", "Certificate", None, None, None, None, None, None, None, 5, None),
    ("MSME Programme", "Certificate", None, None, None, None, None, None, None, 5, None),
    ("Awards For Products", "Award / recognition proof", None, None, None, None, None, None, None, 10, None),
    ("Completed Prototype Development", "Recognition letter / document", None, None, None, None, None, None, None, 15, None),
    ("Filed Patent", "Letter / legal proof", None, None, None, None, None, None, None, 5, None),
    ("Published Patent", "Patent publication proof", None, None, None, None, None, None, None, 10, None),
    ("Patent Granted", "Patent grant proof", None, None, None, None, None, None, None, 15, None),
    ("International Conference", "Certificate / paper proof", None, None, None, None, None, None, None, 10, None),
    ("Startup Registration", "Certificate / registration proof", None, None, None, None, None, None, None, 10, None),
    ("Generated Significant Revenue", "Revenue proof", None, None, None, None, None, None, None, 15, None),
    ("External Funding", "Funding proof", None, None, None, None, None, None, None, 15, None),
    ("User / Industry Impact", "Impact proof", None, None, None, None, None, None, None, 15, None),
    ("Significant Value Creation", "Validation proof", None, None, None, None, None, None, None, 10, None),
    ("Business Hackathon", "Certificate", None, None, None, None, None, None, None, 10, None),
    ("Social Enterprise", "Proof", None, None, None, None, None, None, None, 10, None),
    ("High Customer Satisfaction", "Proof", None, None, None, None, None, None, None, 10, None),
    ("Developed Social Innovation", "Proof", None, None, None, None, None, None, None, 10, None),
    ("Club Activity - Participation", "Recognition letter / certificate", None, None, None, None, None, None, None, 3, "For department level"),
    ("Club Activity - Association", "Phone / email / placement proof", None, None, None, None, None, None, None, 3, "For department level"),
    ("Professional Society", "Membership / participation proof", None, None, None, None, None, None, None, 5, None),
    ("Special Initiative", "Certificate / approval proof", None, None, None, None, None, None, None, 5, None),
    ("Seminar", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Webinar", "Certificate", 3, 6, 9, 12, 15, 15, 20, None, None),
    ("Certification Course", "Certificate", None, None, None, None, None, None, None, 5, None),
    ("Other", "Faculty review required", None, None, None, None, None, None, None, 0, "Manual MAP review"),
]

CATEGORY_KEYWORDS = {
    "Hackathon": ["hackathon", "hack", "ideathon", "codeathon"],
    "Project Competition": ["project competition", "project expo", "project exhibition", "project contest"],
    "Paper Presentation": ["paper presentation", "research paper", "paper presented"],
    "Poster Competition": ["poster", "poster presentation"],
    "Competitive Programming": ["competitive programming", "leetcode", "coding contest", "codechef", "hackerrank"],
    "Workshop": ["workshop", "hands-on", "bootcamp"],
    "Industrial Training": ["industrial training", "training program", "industrial visit"],
    "Internship": ["internship", "intern", "trainee"],
    "MOOC": ["mooc", "coursera", "nptel", "edx", "udemy", "swayam"],
    "Language Proficiency": ["language proficiency", "ielts", "toefl", "german", "japanese", "french"],
    "Sports": ["sports", "cricket", "football", "basketball", "athletics", "kabaddi", "volleyball"],
    "Cultural": ["cultural", "dance", "music", "drama", "fine arts", "singing"],
    "Community Service - Two Day": ["two day", "2 day", "community service", "nss"],
    "Community Service - Up To One Week": ["one week", "week long", "up to one week"],
    "Community Service - Recognition": ["recognition", "appreciation", "community service"],
    "Community Service - One Semester": ["one semester", "semester activity"],
    "Entrepreneurship Workshop": ["entrepreneurship workshop", "e-cell workshop"],
    "MSME Programme": ["msme"],
    "Awards For Products": ["award", "product award"],
    "Completed Prototype Development": ["prototype", "mvp"],
    "Filed Patent": ["filed patent", "patent filed"],
    "Published Patent": ["published patent", "patent published"],
    "Patent Granted": ["patent granted", "grant of patent"],
    "International Conference": ["international conference", "conference"],
    "Startup Registration": ["startup registration", "registered startup", "dpiit"],
    "Generated Significant Revenue": ["revenue", "sales generated"],
    "External Funding": ["funding", "investment", "grant"],
    "User / Industry Impact": ["industry impact", "users", "customer adoption"],
    "Business Hackathon": ["business hackathon", "case competition"],
    "Social Enterprise": ["social enterprise"],
    "Club Activity - Participation": ["club activity", "club participation"],
    "Professional Society": ["ieee", "csi", "professional society", "acm"],
    "Special Initiative": ["special initiative", "university initiative"],
    "Seminar": ["seminar"],
    "Webinar": ["webinar"],
    "Certification Course": ["certification course", "certified", "course completion"],
}



class UploadedFile:
    def __init__(self, name, filename, content_type, content):
        self.name = name
        self.filename = filename
        self.type = content_type
        self.file = io.BytesIO(content)


class MultipartForm:
    def __init__(self):
        self.values = {}

    def add(self, name, value):
        self.values.setdefault(name, []).append(value)

    def getfirst(self, name):
        items = self.values.get(name, [])
        if not items:
            return None
        value = items[0]
        if isinstance(value, UploadedFile):
            return None
        return value

    def __contains__(self, name):
        return name in self.values

    def __getitem__(self, name):
        items = self.values[name]
        return items if len(items) > 1 else items[0]


def parse_multipart(handler):
    content_type = handler.headers.get("Content-Type", "")
    boundary_match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
    if not boundary_match:
        raise ValueError("Missing multipart boundary.")
    boundary = (boundary_match.group(1) or boundary_match.group(2)).encode("utf-8")
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length > MAX_UPLOAD_BYTES:
        raise ValueError("Upload is too large. Limit is 30 MB per request.")
    body = handler.rfile.read(length)
    form = MultipartForm()
    delimiter = b"--" + boundary
    for raw_part in body.split(delimiter):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        header_blob = part[:header_end].decode("utf-8", errors="replace")
        content = part[header_end + 4:]
        headers = {}
        for line in header_blob.split("\r\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.lower().strip()] = value.strip()
        disposition = headers.get("content-disposition", "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match and filename_match.group(1):
            form.add(name, UploadedFile(name, filename_match.group(1), headers.get("content-type", ""), content))
        else:
            form.add(name, content.decode("utf-8", errors="replace"))
    return form

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def json_response(handler, payload, status=200):
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler, body, status=200, content_type="text/plain; charset=utf-8"):
    data = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def password_hash(password):
    salt = "certimap-local-demo"
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    with get_db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                semester TEXT DEFAULT '',
                academic_year TEXT DEFAULT '',
                email TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student','faculty','admin')),
                student_id INTEGER REFERENCES students(id),
                notify_dashboard INTEGER NOT NULL DEFAULT 1,
                notify_email INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS map_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                document_required TEXT DEFAULT '',
                college INTEGER,
                taluka INTEGER,
                district INTEGER,
                university INTEGER,
                state INTEGER,
                national INTEGER,
                international INTEGER,
                fixed_points INTEGER,
                note TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id),
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT DEFAULT '',
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                extracted_text TEXT DEFAULT '',
                certificate_number TEXT DEFAULT '',
                event_name TEXT DEFAULT '',
                organizer TEXT DEFAULT '',
                event_date TEXT DEFAULT '',
                achievement_type TEXT DEFAULT '',
                verification_url TEXT DEFAULT '',
                qr_value TEXT DEFAULT '',
                category TEXT NOT NULL,
                event_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                map_points INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                duplicate_of INTEGER REFERENCES certificates(id),
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','changes_requested')),
                faculty_note TEXT DEFAULT '',
                uploaded_at TEXT NOT NULL,
                reviewed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        ensure_columns(con)
        seed_defaults(con)
        con.execute("UPDATE certificates SET duplicate_of = NULL")


def ensure_columns(con):
    user_cols = {row["name"] for row in con.execute("PRAGMA table_info(users)").fetchall()}
    if "notify_dashboard" not in user_cols:
        con.execute("ALTER TABLE users ADD COLUMN notify_dashboard INTEGER NOT NULL DEFAULT 1")
    if "notify_email" not in user_cols:
        con.execute("ALTER TABLE users ADD COLUMN notify_email INTEGER NOT NULL DEFAULT 0")


def seed_defaults(con):
    con.execute(
        """
        INSERT OR IGNORE INTO students
        (id, name, roll_number, department, semester, academic_year, email, created_at)
        VALUES (1, 'Aditya Wale', '2125UMLM2025', 'Computer Engineering', 'Semester 5', '2025-26', 'student@certimap.local', ?)
        """,
        (now_iso(),),
    )
    users = [
        ("Aditya Wale", "student@certimap", "student123", "student", 1),
        ("Faculty Verifier", "faculty@certimap", "faculty123", "faculty", None),
        ("MAP Administrator", "admin@certimap", "admin123", "admin", None),
    ]
    for name, username, password, role, student_id in users:
        con.execute(
            """
            INSERT OR IGNORE INTO users
            (name, username, password_hash, role, student_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, username, password_hash(password), role, student_id, now_iso()),
        )
    for rule in DEFAULT_RULES:
        con.execute(
            """
            INSERT OR IGNORE INTO map_rules
            (category, document_required, college, taluka, district, university, state, national, international,
             fixed_points, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*rule, now_iso()),
        )


def row_to_dict(row):
    return dict(row) if row else None


def certificate_payload(row):
    item = row_to_dict(row)
    if not item:
        return None
    ext = Path(item["stored_filename"]).suffix.lower()
    mime = item.get("mime_type") or mimetypes.guess_type(item["stored_filename"])[0] or ""
    if mime.startswith("image/") or ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        preview_kind = "image"
    elif mime == "application/pdf" or ext == ".pdf":
        preview_kind = "pdf"
    else:
        preview_kind = "text"
    item["preview_kind"] = preview_kind
    item["file_url"] = f"/uploads/{item['stored_filename']}"
    return item


def parse_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length > MAX_UPLOAD_BYTES:
        raise ValueError("Upload is too large. Limit is 30 MB per request.")
    raw = handler.rfile.read(length)
    if "application/json" in handler.headers.get("Content-Type", ""):
        return json.loads(raw.decode("utf-8") or "{}")
    return parse_qs(raw.decode("utf-8"))


def get_current_user(handler):
    auth = handler.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "", 1).strip() if auth.startswith("Bearer ") else ""
    if not token:
        token = handler.headers.get("X-Session-Token", "").strip()
    if not token:
        token = parse_qs(urlparse(handler.path).query).get("token", [""])[0].strip()
    if not token:
        return None
    with get_db() as con:
        row = con.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    return row_to_dict(row)


def require_user(handler, roles=None):
    user = get_current_user(handler)
    if not user:
        json_response(handler, {"error": "Authentication required."}, 401)
        return None
    if roles and user["role"] not in roles:
        json_response(handler, {"error": "You do not have permission for this action."}, 403)
        return None
    return user


def create_session(con, user_id):
    token = secrets.token_urlsafe(32)
    con.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, user_id, now_iso()))
    return token


def register_student(payload):
    required = ["name", "username", "password", "roll_number", "department"]
    missing = [key for key in required if not str(payload.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Missing required field: {', '.join(missing)}")
    password = str(payload["password"])
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    with get_db() as con:
        if con.execute("SELECT id FROM users WHERE username = ?", (payload["username"].strip(),)).fetchone():
            raise ValueError("Username is already registered.")
        if con.execute("SELECT id FROM students WHERE roll_number = ?", (payload["roll_number"].strip(),)).fetchone():
            raise ValueError("Roll number is already registered.")
        cur = con.execute(
            """
            INSERT INTO students (name, roll_number, department, semester, academic_year, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"].strip(),
                payload["roll_number"].strip(),
                payload["department"].strip(),
                payload.get("semester", "").strip(),
                payload.get("academic_year", "").strip(),
                payload.get("email", "").strip(),
                now_iso(),
            ),
        )
        student_id = cur.lastrowid
        user_cur = con.execute(
            """
            INSERT INTO users (name, username, password_hash, role, student_id, created_at)
            VALUES (?, ?, ?, 'student', ?, ?)
            """,
            (payload["name"].strip(), payload["username"].strip(), password_hash(password), student_id, now_iso()),
        )
        user_id = user_cur.lastrowid
        token = create_session(con, user_id)
        log_action(con, user_id, "register", "student", student_id, "")
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return token, row_to_dict(row)


def log_action(con, user_id, action, entity, entity_id=None, details=""):
    con.execute(
        "INSERT INTO audit_log (user_id, action, entity, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, action, entity, entity_id, details, now_iso()),
    )


def guess_level(text):
    source = text.lower()
    checks = [
        ("international", ["international", "global", "world"]),
        ("national", ["national", "india level", "all india"]),
        ("state", ["state", "maharashtra", "karnataka", "gujarat"]),
        ("university", ["university", "inter-university", "inter university"]),
        ("district", ["district", "zonal"]),
        ("taluka", ["taluka", "tehsil"]),
        ("college", ["college", "institute", "department", "campus"]),
    ]
    for level, keys in checks:
        if any(key in source for key in keys):
            return level
    return "college"


def guess_category(text):
    source = text.lower()
    scores = []
    for category, keys in CATEGORY_KEYWORDS.items():
        score = sum(1 for key in keys if key in source)
        if score:
            scores.append((score, category))
    if not scores:
        return "Other", 0.42
    scores.sort(reverse=True)
    top_score, category = scores[0]
    confidence = min(0.98, 0.58 + (top_score * 0.16))
    return category, round(confidence, 3)


def extract_fields(text):
    compact = " ".join(text.split())
    cert_number = ""
    for pattern in [r"(certificate\s*(no|number|id)[:\s#-]*)([A-Z0-9/-]{4,})", r"\b(cert[-\s]?[A-Z0-9/-]{4,})\b"]:
        match = re.search(pattern, compact, re.I)
        if match:
            cert_number = match.group(match.lastindex)
            break
    url_match = re.search(r"https?://[^\s)]+", compact, re.I)
    date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", compact)
    event_match = re.search(r"(?:for|in|at)\s+([A-Z][A-Za-z0-9 &:/-]{4,70})", compact)
    organizer_match = re.search(r"(?:organized by|organised by|by)\s+([A-Z][A-Za-z0-9 &.,'-]{4,80})", compact, re.I)
    achievement = "Participant"
    lowered = compact.lower()
    if "winner" in lowered or "first prize" in lowered:
        achievement = "Winner"
    elif "runner" in lowered or "second prize" in lowered:
        achievement = "Runner-up"
    elif "completed" in lowered:
        achievement = "Completed"
    return {
        "certificate_number": cert_number,
        "verification_url": url_match.group(0) if url_match else "",
        "event_date": date_match.group(1) if date_match else "",
        "event_name": event_match.group(1).strip(" .,-") if event_match else "",
        "organizer": organizer_match.group(1).strip(" .,-") if organizer_match else "",
        "achievement_type": achievement,
    }


def extract_text_from_upload(filename, file_bytes, manual_text):
    texts = [manual_text.strip(), Path(filename).stem.replace("_", " ").replace("-", " ")]
    try:
        decoded = file_bytes[:200000].decode("utf-8", errors="ignore")
        readable = "".join(ch if ch.isprintable() or ch.isspace() else " " for ch in decoded)
        if len(readable.strip()) > 20:
            texts.append(readable)
    except Exception:
        pass
    return "\n".join(item for item in texts if item).strip()


def calculate_points(con, category, level, count):
    rule = con.execute("SELECT * FROM map_rules WHERE category = ? AND active = 1", (category,)).fetchone()
    if not rule:
        return 0
    if rule["fixed_points"] is not None:
        return int(rule["fixed_points"]) * count
    level_value = rule[level] if level in LEVELS else None
    return int(level_value or 0) * count


def save_upload(field, manual_text, form, user):
    if not field.filename:
        return None
    file_bytes = field.file.read()
    digest = hashlib.sha256(file_bytes).hexdigest()
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(field.filename).name)
    stored_name = f"{int(time.time())}_{digest[:12]}_{safe_name}"
    target = UPLOAD_DIR / stored_name
    target.write_bytes(file_bytes)

    extracted_text = extract_text_from_upload(field.filename, file_bytes, manual_text)
    category, confidence = guess_category(extracted_text)
    level = guess_level(extracted_text)
    fields = extract_fields(extracted_text)

    student_id = form_value(form, "student_id")
    with get_db() as con:
        if user["role"] == "student":
            student_id = user["student_id"]
        if not student_id:
            student_id = ensure_student(con, form)
        count = int(form_value(form, "count") or "1")
        points = calculate_points(con, category, level, count)
        cur = con.execute(
            """
            INSERT INTO certificates
            (student_id, original_filename, stored_filename, file_path, mime_type, file_size, file_hash, extracted_text,
             certificate_number, event_name, organizer, event_date, achievement_type, verification_url, qr_value,
             category, event_level, confidence, map_points, count, duplicate_of, status, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                student_id,
                field.filename,
                stored_name,
                str(target),
                field.type or mimetypes.guess_type(field.filename)[0] or "",
                len(file_bytes),
                digest,
                extracted_text,
                fields["certificate_number"],
                fields["event_name"],
                fields["organizer"],
                fields["event_date"],
                fields["achievement_type"],
                fields["verification_url"],
                "",
                category,
                level,
                confidence,
                points,
                count,
                None,
                now_iso(),
            ),
        )
        certificate_id = cur.lastrowid
        log_action(con, user["id"], "upload", "certificate", certificate_id, f"Predicted {category} / {level}")
        owner = con.execute("SELECT users.id FROM users WHERE student_id = ?", (student_id,)).fetchone()
        if owner:
            con.execute(
                "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
                (owner["id"], f"Certificate uploaded: {field.filename}", now_iso()),
            )
        con.commit()
        return certificate_id


def ensure_student(con, form):
    roll_number = form_value(form, "roll_number") or f"TEMP-{secrets.token_hex(3).upper()}"
    existing = con.execute("SELECT id FROM students WHERE roll_number = ?", (roll_number,)).fetchone()
    if existing:
        return existing["id"]
    cur = con.execute(
        """
        INSERT INTO students (name, roll_number, department, semester, academic_year, email, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            form_value(form, "student_name") or "New Student",
            roll_number,
            form_value(form, "department") or "General",
            form_value(form, "semester") or "",
            form_value(form, "academic_year") or "",
            form_value(form, "email") or "",
            now_iso(),
        ),
    )
    return cur.lastrowid


def form_value(form, key):
    item = form.getfirst(key) if hasattr(form, "getfirst") else None
    return str(item).strip() if item is not None else ""


def list_certificates(query, user):
    clauses = []
    params = []
    if user["role"] == "student":
        clauses.append("certificates.student_id = ?")
        params.append(user["student_id"])
    for field in ["status", "category", "event_level"]:
        value = query.get(field, [""])[0].strip()
        if value:
            clauses.append(f"certificates.{field} = ?")
            params.append(value)
    search = query.get("q", [""])[0].strip()
    if search:
        clauses.append(
            """
            (students.name LIKE ? OR students.roll_number LIKE ? OR certificates.original_filename LIKE ?
             OR certificates.event_name LIKE ? OR certificates.organizer LIKE ?)
            """
        )
        params.extend([f"%{search}%"] * 5)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db() as con:
        rows = con.execute(
            f"""
            SELECT certificates.*, students.name AS student_name, students.roll_number, students.department,
                   students.semester, students.academic_year
            FROM certificates
            JOIN students ON students.id = certificates.student_id
            {where}
            ORDER BY certificates.uploaded_at DESC, certificates.id DESC
            """,
            params,
        ).fetchall()
    return [certificate_payload(row) for row in rows]


def dashboard_payload(user):
    with get_db() as con:
        certs = list_certificates({}, user)
        rule_rows = con.execute("SELECT * FROM map_rules WHERE active = 1 ORDER BY category").fetchall()
        students = con.execute("SELECT * FROM students ORDER BY name").fetchall()
        student_profile = None
        if user["student_id"]:
            student_profile = con.execute("SELECT * FROM students WHERE id = ?", (user["student_id"],)).fetchone()
        notifications = con.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 8",
            (user["id"],),
        ).fetchall()
    approved_points = sum(item["map_points"] for item in certs if item["status"] == "approved")
    pending_points = sum(item["map_points"] for item in certs if item["status"] == "pending")
    by_category = {}
    by_month = {}
    by_department = {}
    for item in certs:
        by_category[item["category"]] = by_category.get(item["category"], 0) + item["map_points"]
        by_department[item["department"]] = by_department.get(item["department"], 0) + item["map_points"]
        month = item["uploaded_at"][:7]
        by_month[month] = by_month.get(month, 0) + 1
    leaderboard = {}
    for item in certs:
        if item["status"] == "approved":
            key = f"{item['student_name']} ({item['roll_number']})"
            leaderboard[key] = leaderboard.get(key, 0) + item["map_points"]
    student_points = {}
    for item in certs:
        sid = item["student_id"]
        student_points.setdefault(sid, {"total": 0, "approved": 0, "pending": 0, "certificates": 0})
        student_points[sid]["total"] += item["map_points"]
        student_points[sid]["certificates"] += 1
        if item["status"] == "approved":
            student_points[sid]["approved"] += item["map_points"]
        if item["status"] == "pending":
            student_points[sid]["pending"] += item["map_points"]
    student_summaries = []
    for student in students:
        sdict = row_to_dict(student)
        totals = student_points.get(student["id"], {"total": 0, "approved": 0, "pending": 0, "certificates": 0})
        sdict.update(totals)
        student_summaries.append(sdict)
    return {
        "user": {
            key: user[key]
            for key in ["id", "name", "username", "role", "student_id", "notify_dashboard", "notify_email"]
        },
        "studentProfile": row_to_dict(student_profile),
        "stats": {
            "totalCertificates": len(certs),
            "approved": sum(1 for item in certs if item["status"] == "approved"),
            "pending": sum(1 for item in certs if item["status"] == "pending"),
            "rejected": sum(1 for item in certs if item["status"] == "rejected"),
            "approvedPoints": approved_points,
            "pendingPoints": pending_points,
            "calculatedPoints": sum(item["map_points"] for item in certs),
        },
        "certificates": certs,
        "rules": [row_to_dict(row) for row in rule_rows],
        "students": student_summaries,
        "charts": {
            "byCategory": by_category,
            "byMonth": by_month,
            "byDepartment": by_department,
        },
        "notifications": [row_to_dict(row) for row in notifications],
    }


def update_certificate(certificate_id, payload, user):
    allowed = ["category", "event_level", "map_points", "status", "faculty_note", "event_name", "organizer", "achievement_type", "certificate_number"]
    updates = []
    params = []
    with get_db() as con:
        row = con.execute("SELECT * FROM certificates WHERE id = ?", (certificate_id,)).fetchone()
        if not row:
            return None
        if "recalculate" in payload and payload["recalculate"]:
            category = payload.get("category") or row["category"]
            level = payload.get("event_level") or row["event_level"]
            count = int(payload.get("count") or row["count"])
            payload["map_points"] = calculate_points(con, category, level, count)
            payload["count"] = count
            allowed.append("count")
        for key in allowed:
            if key in payload:
                updates.append(f"{key} = ?")
                params.append(payload[key])
        if "status" in payload:
            updates.append("reviewed_at = ?")
            params.append(now_iso())
        if not updates:
            return row_to_dict(row)
        params.append(certificate_id)
        con.execute(f"UPDATE certificates SET {', '.join(updates)} WHERE id = ?", params)
        log_action(con, user["id"], "update", "certificate", certificate_id, json.dumps(payload))
        owner = con.execute(
            """
            SELECT users.id FROM users
            JOIN certificates ON certificates.student_id = users.student_id
            WHERE certificates.id = ?
            """,
            (certificate_id,),
        ).fetchone()
        if owner and "status" in payload:
            con.execute(
                "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
                (owner["id"], f"Certificate #{certificate_id} marked {payload['status']}.", now_iso()),
            )
        con.commit()
        return certificate_payload(con.execute("SELECT * FROM certificates WHERE id = ?", (certificate_id,)).fetchone())


def can_delete_certificate(row, user):
    if user["role"] in ("faculty", "admin"):
        return True
    return user["role"] == "student" and row["student_id"] == user["student_id"] and row["status"] != "approved"


def delete_certificate(certificate_id, user):
    with get_db() as con:
        row = con.execute("SELECT * FROM certificates WHERE id = ?", (certificate_id,)).fetchone()
        if not row:
            return False, "Certificate not found."
        if not can_delete_certificate(row, user):
            return False, "You can delete only your own unapproved certificates."
        stored_filename = row["stored_filename"]
        con.execute("UPDATE certificates SET duplicate_of = NULL WHERE duplicate_of = ?", (certificate_id,))
        con.execute("DELETE FROM certificates WHERE id = ?", (certificate_id,))
        log_action(con, user["id"], "delete", "certificate", certificate_id, row["original_filename"])
        still_used = con.execute("SELECT id FROM certificates WHERE stored_filename = ? LIMIT 1", (stored_filename,)).fetchone()
        con.commit()
    if not still_used:
        target = UPLOAD_DIR / stored_filename
        if target.exists() and target.is_file():
            target.unlink()
    return True, "Certificate deleted."


def reset_certificate_points(certificate_id, user):
    if user["role"] not in ("faculty", "admin"):
        return None, "Only faculty or admin can reset points."
    with get_db() as con:
        row = con.execute("SELECT * FROM certificates WHERE id = ?", (certificate_id,)).fetchone()
        if not row:
            return None, "Certificate not found."
        con.execute(
            """
            UPDATE certificates
            SET map_points = 0, faculty_note = ?, reviewed_at = ?
            WHERE id = ?
            """,
            ("MAP points reset for manual review.", now_iso(), certificate_id),
        )
        log_action(con, user["id"], "reset_points", "certificate", certificate_id, "")
        con.commit()
        updated = con.execute("SELECT * FROM certificates WHERE id = ?", (certificate_id,)).fetchone()
        return certificate_payload(updated), ""


def update_profile(payload, user):
    notify_dashboard = 1 if payload.get("notify_dashboard") in (True, "true", "1", "on", 1) else 0
    notify_email = 1 if payload.get("notify_email") in (True, "true", "1", "on", 1) else 0
    with get_db() as con:
        con.execute(
            "UPDATE users SET notify_dashboard = ?, notify_email = ? WHERE id = ?",
            (notify_dashboard, notify_email, user["id"]),
        )
        if user["role"] == "student" and user["student_id"]:
            values = {
                "name": payload.get("name", user["name"]).strip() or user["name"],
                "roll_number": payload.get("roll_number", "").strip(),
                "department": payload.get("department", "").strip(),
                "semester": payload.get("semester", "").strip(),
                "academic_year": payload.get("academic_year", "").strip(),
                "email": payload.get("email", "").strip(),
                "id": user["student_id"],
            }
            existing = con.execute(
                "SELECT id FROM students WHERE roll_number = ? AND id != ?",
                (values["roll_number"], user["student_id"]),
            ).fetchone()
            if existing:
                raise ValueError("Roll number is already used by another student.")
            con.execute(
                """
                UPDATE students
                SET name = :name, roll_number = :roll_number, department = :department,
                    semester = :semester, academic_year = :academic_year, email = :email
                WHERE id = :id
                """,
                values,
            )
            con.execute("UPDATE users SET name = ? WHERE id = ?", (values["name"], user["id"]))
        log_action(con, user["id"], "update", "profile", user["id"], "")
        con.commit()
        updated_user = con.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        profile = None
        if updated_user["student_id"]:
            profile = con.execute("SELECT * FROM students WHERE id = ?", (updated_user["student_id"],)).fetchone()
        return row_to_dict(updated_user), row_to_dict(profile)


def cleanup_pending_duplicates(user):
    if user["role"] not in ("faculty", "admin"):
        raise PermissionError("Only faculty or admin can remove pending duplicates.")
    deleted = []
    with get_db() as con:
        rows = con.execute(
            """
            SELECT * FROM certificates
            WHERE status = 'pending' AND duplicate_of IS NOT NULL
            ORDER BY id
            """
        ).fetchall()
        for row in rows:
            certificate_id = row["id"]
            stored_filename = row["stored_filename"]
            con.execute("UPDATE certificates SET duplicate_of = NULL WHERE duplicate_of = ?", (certificate_id,))
            con.execute("DELETE FROM certificates WHERE id = ?", (certificate_id,))
            deleted.append({"id": certificate_id, "stored_filename": stored_filename})
            log_action(con, user["id"], "cleanup_duplicate", "certificate", certificate_id, row["original_filename"])
        con.commit()
        for item in deleted:
            still_used = con.execute("SELECT id FROM certificates WHERE stored_filename = ? LIMIT 1", (item["stored_filename"],)).fetchone()
            if not still_used:
                target = UPLOAD_DIR / item["stored_filename"]
                if target.exists() and target.is_file():
                    target.unlink()
    return len(deleted)


def upsert_rule(payload, user):
    with get_db() as con:
        values = {
            "category": payload.get("category", "").strip(),
            "document_required": payload.get("document_required", "").strip(),
            "college": nullable_int(payload.get("college")),
            "taluka": nullable_int(payload.get("taluka")),
            "district": nullable_int(payload.get("district")),
            "university": nullable_int(payload.get("university")),
            "state": nullable_int(payload.get("state")),
            "national": nullable_int(payload.get("national")),
            "international": nullable_int(payload.get("international")),
            "fixed_points": nullable_int(payload.get("fixed_points")),
            "note": payload.get("note", "").strip(),
            "updated_at": now_iso(),
        }
        if not values["category"]:
            raise ValueError("Category is required.")
        con.execute(
            """
            INSERT INTO map_rules
            (category, document_required, college, taluka, district, university, state, national, international,
             fixed_points, note, updated_at)
            VALUES (:category, :document_required, :college, :taluka, :district, :university, :state, :national,
                    :international, :fixed_points, :note, :updated_at)
            ON CONFLICT(category) DO UPDATE SET
                document_required = excluded.document_required,
                college = excluded.college,
                taluka = excluded.taluka,
                district = excluded.district,
                university = excluded.university,
                state = excluded.state,
                national = excluded.national,
                international = excluded.international,
                fixed_points = excluded.fixed_points,
                note = excluded.note,
                updated_at = excluded.updated_at,
                active = 1
            """,
            values,
        )
        row = con.execute("SELECT id FROM map_rules WHERE category = ?", (values["category"],)).fetchone()
        log_action(con, user["id"], "upsert", "map_rule", row["id"], values["category"])
        con.commit()
        return row_to_dict(con.execute("SELECT * FROM map_rules WHERE category = ?", (values["category"],)).fetchone())


def nullable_int(value):
    if value in (None, ""):
        return None
    return int(value)


def build_csv_report(user, query):
    rows = list_certificates(query, user)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student", "Roll Number", "Department", "Certificate", "Category", "Level", "Points", "Status", "Uploaded"])
    for row in rows:
        writer.writerow([
            row["student_name"],
            row["roll_number"],
            row["department"],
            row["original_filename"],
            row["category"],
            row["event_level"],
            row["map_points"],
            row["status"],
            row["uploaded_at"],
        ])
    return output.getvalue()


class CertiMapHandler(BaseHTTPRequestHandler):
    server_version = "CertiMAPAI/1.0"

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path in ("", "/"):
                self.serve_file(STATIC_DIR / "index.html")
            elif parsed.path.startswith("/static/"):
                self.serve_file(STATIC_DIR / parsed.path.removeprefix("/static/"))
            elif parsed.path.startswith("/uploads/"):
                user = require_user(self)
                if user:
                    self.serve_file(UPLOAD_DIR / parsed.path.removeprefix("/uploads/"), as_attachment=False)
            elif parsed.path == "/api/bootstrap":
                user = require_user(self)
                if user:
                    json_response(self, dashboard_payload(user))
            elif parsed.path == "/api/certificates":
                user = require_user(self)
                if user:
                    json_response(self, {"certificates": list_certificates(parse_qs(parsed.query), user)})
            elif parsed.path == "/api/report.csv":
                user = require_user(self)
                if user:
                    csv_text = build_csv_report(user, parse_qs(parsed.query))
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", "attachment; filename=certimap-report.csv")
                    self.end_headers()
                    self.wfile.write(csv_text.encode("utf-8"))
            elif parsed.path == "/api/health":
                json_response(self, {"ok": True, "database": str(DB_PATH), "uploads": str(UPLOAD_DIR)})
            else:
                text_response(self, "Not found", 404)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, 500)

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/login":
                payload = parse_body(self)
                username = payload.get("username", "")
                password = payload.get("password", "")
                with get_db() as con:
                    row = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                    if not row or not hmac.compare_digest(row["password_hash"], password_hash(password)):
                        json_response(self, {"error": "Invalid username or password."}, 401)
                        return
                    token = create_session(con, row["id"])
                    log_action(con, row["id"], "login", "session", None, "")
                    con.commit()
                    json_response(self, {"token": token, "user": row_to_dict(row)})
            elif parsed.path == "/api/register":
                payload = parse_body(self)
                token, user = register_student(payload)
                json_response(self, {"token": token, "user": user}, 201)
            elif parsed.path == "/api/upload":
                user = require_user(self, ["student", "faculty", "admin"])
                if not user:
                    return
                form = parse_multipart(self)
                manual_text = form_value(form, "certificate_text")
                files = form["certificates"] if "certificates" in form else []
                if not isinstance(files, list):
                    files = [files]
                ids = [save_upload(file_field, manual_text, form, user) for file_field in files if getattr(file_field, "filename", None)]
                json_response(self, {"uploaded": [item for item in ids if item]})
            elif parsed.path == "/api/rules":
                user = require_user(self, ["admin"])
                if user:
                    payload = parse_body(self)
                    json_response(self, {"rule": upsert_rule(payload, user)})
            elif parsed.path == "/api/profile":
                user = require_user(self)
                if user:
                    payload = parse_body(self)
                    updated_user, profile = update_profile(payload, user)
                    json_response(self, {"user": updated_user, "studentProfile": profile})
            elif parsed.path == "/api/cleanup-duplicates":
                user = require_user(self, ["faculty", "admin"])
                if user:
                    deleted = cleanup_pending_duplicates(user)
                    json_response(self, {"deleted": deleted})
            else:
                reset_match = re.match(r"^/api/certificates/(\d+)/reset-points$", parsed.path)
                if reset_match:
                    user = require_user(self, ["faculty", "admin"])
                    if not user:
                        return
                    row, error = reset_certificate_points(int(reset_match.group(1)), user)
                    if error:
                        json_response(self, {"error": error}, 404)
                    else:
                        json_response(self, {"certificate": row})
                    return
                text_response(self, "Not found", 404)
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, 400)
        except PermissionError as exc:
            json_response(self, {"error": str(exc)}, 403)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, 500)

    def do_PATCH(self):
        try:
            parsed = urlparse(self.path)
            match = re.match(r"^/api/certificates/(\d+)$", parsed.path)
            if not match:
                text_response(self, "Not found", 404)
                return
            user = require_user(self, ["faculty", "admin"])
            if not user:
                return
            payload = parse_body(self)
            row = update_certificate(int(match.group(1)), payload, user)
            if not row:
                json_response(self, {"error": "Certificate not found."}, 404)
            else:
                json_response(self, {"certificate": row})
        except Exception as exc:
            json_response(self, {"error": str(exc)}, 500)

    def do_DELETE(self):
        try:
            parsed = urlparse(self.path)
            match = re.match(r"^/api/certificates/(\d+)$", parsed.path)
            if not match:
                text_response(self, "Not found", 404)
                return
            user = require_user(self)
            if not user:
                return
            ok, message = delete_certificate(int(match.group(1)), user)
            json_response(self, {"ok": ok, "message": message}, 200 if ok else 403)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, 500)

    def serve_file(self, path, as_attachment=False):
        resolved = path.resolve()
        allowed = [STATIC_DIR.resolve(), UPLOAD_DIR.resolve()]
        if not any(str(resolved).startswith(str(root)) for root in allowed) or not resolved.exists() or not resolved.is_file():
            text_response(self, "Not found", 404)
            return
        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if as_attachment:
            self.send_header("Content-Disposition", f"attachment; filename={resolved.name}")
        self.send_header("Content-Length", str(resolved.stat().st_size))
        self.end_headers()
        with resolved.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    init_db()
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), CertiMapHandler)
    print(f"CertiMAP AI running at http://127.0.0.1:{port}")
    print(f"Database: {DB_PATH}")
    print(f"Certificate uploads: {UPLOAD_DIR}")
    server.serve_forever()


if __name__ == "__main__":
    main()

