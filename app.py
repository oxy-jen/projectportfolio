import json
import hmac
import os
import secrets
import shutil
import sqlite3
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)
DB_PATH = os.environ.get("DB_PATH", os.path.join(app.root_path, "oxyjen.db"))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(app.root_path, "static", "uploads"))
GITHUB_USER = "oxy-jen"
CACHE = {"profile": None, "repos": None, "events": None, "languages": None, "time": 0}
CACHE_TTL = int(os.environ.get("GITHUB_CACHE_TTL", "300"))


REAL_PROFILE_FALLBACK = {
    "login": "oxy-jen",
    "name": "oxy-jen.com",
    "html_url": "https://github.com/oxy-jen",
    "avatar_url": "https://avatars.githubusercontent.com/u/212161806?v=4",
    "bio": "Software Developer | Building practical web solutions\nFocused on clean code, problem-solving, and continuous learning.",
    "public_repos": 6,
    "followers": 1,
    "following": 1,
    "hireable": True,
    "created_at": "2025-05-17T19:20:03Z",
}

REAL_REPO_FALLBACK = [
    {"name": "uiBattle", "html_url": "https://github.com/oxy-jen/uiBattle", "description": None, "language": "HTML", "pushed_at": "2026-05-25T08:07:41Z", "stargazers_count": 0, "fork": False, "has_pages": False},
    {"name": "UI-Battle-Arena", "html_url": "https://github.com/oxy-jen/UI-Battle-Arena", "description": "This is for developers by Developers to compete", "language": None, "pushed_at": "2026-05-21T09:22:00Z", "stargazers_count": 0, "fork": False, "has_pages": False},
    {"name": "secondHubWeb", "html_url": "https://github.com/oxy-jen/secondHubWeb", "description": None, "language": "HTML", "pushed_at": "2026-02-12T13:55:12Z", "stargazers_count": 0, "fork": False, "has_pages": False},
    {"name": "projectHub", "html_url": "https://github.com/oxy-jen/projectHub", "description": None, "language": "HTML", "pushed_at": "2026-02-05T13:48:52Z", "stargazers_count": 0, "fork": False, "has_pages": True},
    {"name": "fronted.web", "html_url": "https://github.com/oxy-jen/fronted.web", "description": "just for frontend learning only", "language": "HTML", "pushed_at": "2026-02-02T09:59:58Z", "stargazers_count": 0, "fork": False, "has_pages": True},
    {"name": "Manu-XMD", "html_url": "https://github.com/oxy-jen/Manu-XMD", "description": "Forked bot project", "language": None, "pushed_at": "2025-05-17T17:16:51Z", "stargazers_count": 0, "fork": True, "has_pages": False},
]


def init_db():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    bundled_db = os.path.join(app.root_path, "oxyjen.db")
    if DB_PATH != bundled_db and not os.path.exists(DB_PATH) and os.path.exists(bundled_db):
        shutil.copyfile(bundled_db, DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                approved INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS testimonials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                quote TEXT NOT NULL,
                rating INTEGER DEFAULT 5,
                approved INTEGER DEFAULT 0,
                recommended INTEGER DEFAULT 0,
                flagged INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                status TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                flagged INTEGER DEFAULT 0,
                reply TEXT,
                replied_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                url TEXT NOT NULL,
                note TEXT,
                visible INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        ensure_column(conn, "testimonials", "recommended", "INTEGER DEFAULT 0")
        ensure_column(conn, "testimonials", "flagged", "INTEGER DEFAULT 0")
        ensure_column(conn, "testimonials", "country_code", "TEXT")
        ensure_column(conn, "testimonials", "country_name", "TEXT")
        ensure_column(conn, "comments", "email", "TEXT")
        ensure_column(conn, "comments", "flagged", "INTEGER DEFAULT 0")
        ensure_column(conn, "comments", "country_code", "TEXT")
        ensure_column(conn, "comments", "country_name", "TEXT")
        ensure_column(conn, "messages", "country_code", "TEXT")
        ensure_column(conn, "messages", "country_name", "TEXT")
        ensure_column(conn, "messages", "reply_sent", "INTEGER DEFAULT 0")
        ensure_column(conn, "content_items", "page", "TEXT DEFAULT 'home'")
        ensure_column(conn, "content_items", "slot", "TEXT DEFAULT 'main'")
        ensure_column(conn, "content_items", "layout", "TEXT DEFAULT 'card'")
        ensure_column(conn, "content_items", "media_behavior", "TEXT DEFAULT 'scroll'")
        ensure_column(conn, "content_items", "button_label", "TEXT")
        ensure_column(conn, "content_items", "button_url", "TEXT")
        ensure_column(conn, "content_items", "starts_at", "TEXT")
        ensure_column(conn, "content_items", "ends_at", "TEXT")
        ensure_column(conn, "content_items", "visible", "INTEGER DEFAULT 1")
        ensure_column(conn, "content_items", "sort_order", "INTEGER DEFAULT 0")
        ensure_column(conn, "content_items", "assets", "TEXT")
        ensure_column(conn, "content_items", "subtitle", "TEXT")
        ensure_column(conn, "content_items", "text_effect", "TEXT DEFAULT 'normal'")
        ensure_column(conn, "content_items", "font_family", "TEXT DEFAULT 'default'")
        ensure_column(conn, "content_items", "text_align", "TEXT DEFAULT 'left'")
        ensure_column(conn, "content_items", "text_color", "TEXT")
        ensure_column(conn, "content_items", "background_url", "TEXT")
        ensure_column(conn, "content_items", "transparent_bg", "INTEGER DEFAULT 0")
        ensure_column(conn, "content_items", "html_content", "TEXT")
        ensure_column(conn, "content_items", "display_seconds", "INTEGER")
        ensure_column(conn, "content_items", "pause_seconds", "INTEGER")
        ensure_column(conn, "content_items", "carousel_direction", "TEXT DEFAULT 'left'")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        seed_default_contacts(conn)
        seed_default_page_blocks(conn)


def ensure_column(conn, table, column, definition):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def seed_default_contacts(conn):
    count = conn.execute("SELECT COUNT(*) FROM contact_links").fetchone()[0]
    if count:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT INTO contact_links (label, url, note, visible, sort_order, created_at) VALUES (?, ?, ?, 1, ?, ?)",
        [
            ("WhatsApp", "https://wa.me/254791305329", "Chat on WhatsApp", 1, now),
            ("Email", "mailto:oxygenvessel@gmail.com", "oxygenvessel@gmail.com", 2, now),
        ],
    )


def seed_default_page_blocks(conn):
    defaults = [
        ("home", "hero", "hero_banner", "Open to work", "Oxy-Jen Tech", "Software Developer | Building practical web solutions. Focused on clean code, problem-solving, and continuous learning.", "View Projects", "/projects", 10),
        ("home", "about_intro", "text_block", "About Oxy-Jen Tech", "Focused web products with a clean engineering hand.", "Oxy-Jen Tech brings together interface design, Flask systems, GitHub-driven project work, and a growing community layer for challenges, feedback, and collaboration.", "", "", 20),
        ("home", "terminal_intro", "text_block", "Live Code Typing", "A small look at the backend powering the site.", "This block controls the text above the live code area.", "", "", 30),
        ("home", "github_intro", "text_block", "Featured GitHub Projects", "Real public repositories from github.com/oxy-jen.", "This section is fed by GitHub data, and this heading is editable from admin.", "", "", 40),
        ("home", "github_data_intro", "text_block", "GitHub Integration", "Live profile, repos, events, and language distribution.", "Admin can change this copy or hide it without touching code.", "", "", 50),
        ("home", "testimonials_intro", "text_block", "Testimonials", "Notes from people who have worked with the brand.", "Selected feedback and recommendations from the Oxy-Jen Tech network.", "", "", 60),
        ("home", "contact_intro", "text_block", "Contact", "Start a practical web solution with Oxy-Jen Tech.", "Use the dedicated contact page to send a message or open one of the official contact links.", "Open Contact Page", "/contact", 70),
        ("about", "hero", "hero_banner", "About Oxy-Jen Tech", "Focused web products with a clean engineering hand.", "Oxy-Jen Tech brings together interface design, Flask systems, GitHub-driven project work, and a growing community layer for challenges, feedback, and collaboration.", "", "", 10),
        ("about", "github_intro", "text_block", "Live GitHub Profile", "Real activity and profile data from github.com/oxy-jen.", "The numbers beside this block are live GitHub data.", "", "", 20),
        ("about", "milestones_intro", "text_block", "Milestones", "Uploaded images and achievements can be managed from admin.", "Add achievements and photos as editable content blocks whenever you want.", "", "", 30),
        ("projects", "hero", "hero_banner", "Projects", "Selected builds, experiments, and public repositories.", "UI Battle Arena lives here with the rest of the project work.", "", "", 10),
        ("projects", "featured_intro", "text_block", "Featured Work", "Highlighted pieces from the Oxy-Jen workspace.", "Project cards and media can be added, timed, hidden, and reordered from admin.", "", "", 20),
        ("projects", "github_intro", "text_block", "Public Repository Feed", "Live projects from GitHub.", "This widget keeps using real repository data while the surrounding text stays editable.", "", "", 30),
        ("ecosystem", "hero", "hero_banner", "Tech Ecosystem", "Showcase, activity, challenges, and now-building systems.", "A home for project media, active challenges, and the next pieces moving through the Oxy-Jen pipeline.", "", "", 10),
        ("ecosystem", "showcase_intro", "text_block", "Showcase", "Project clips and visual updates.", "Add videos, images, and carousel blocks from admin.", "", "", 20),
        ("ecosystem", "challenges_intro", "text_block", "Challenges", "Frontend prompts and community submissions.", "Challenge text is editable when you add challenge blocks from the dashboard.", "", "", 30),
        ("ecosystem", "roadmap_intro", "text_block", "Now Building", "Active development roadmap.", "Use admin blocks to replace or add to this roadmap area.", "", "", 40),
        ("community", "hero", "hero_banner", "Community", "Open notes, ideas, and project conversations.", "Post publicly for everyone to see, or send a private note directly to Oxy-Jen Tech.", "", "", 10),
        ("community", "form_intro", "text_block", "Leave a note", "Join the public conversation.", "Use the form to send public notes, testimonials, or private messages.", "", "", 20),
        ("community", "testimonials_intro", "text_block", "Testimonials", "Community feedback with country flags.", "Approved testimonials appear below.", "", "", 30),
        ("contact", "hero", "hero_banner", "Contact Oxy-Jen Tech", "Send a message or use an official contact link.", "Share project details, collaboration ideas, or support requests. Replies come back through the contact method you provide.", "", "", 10),
        ("contact", "form_intro", "text_block", "Leave a message", "Send a direct message.", "Admin can change this text, hide it, or schedule a replacement.", "", "", 20),
        ("contact", "direct_intro", "text_block", "Reach me directly", "Official contact links.", "Manage these links and location details from admin.", "", "", 30),
    ]
    now = datetime.now(timezone.utc).isoformat()
    for page, slot, layout, status, title, description, button_label, button_url, sort_order in defaults:
        exists = conn.execute(
            "SELECT 1 FROM content_items WHERE kind = 'system_block' AND page = ? AND slot = ? LIMIT 1",
            (page, slot),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO content_items
            (kind, title, description, status, page, slot, layout, media_behavior, button_label, button_url, visible, sort_order, text_effect, font_family, text_align, created_at)
            VALUES ('system_block', ?, ?, ?, ?, ?, ?, 'scroll', ?, ?, 1, ?, 'normal', 'default', 'left', ?)
            """,
            (title, description, status, page, slot, layout, button_label, button_url, sort_order, now),
        )


def github_get(path, fallback):
    try:
      req = Request(
          f"https://api.github.com{path}",
          headers={"User-Agent": "Oxy-Jen-Tech-Portfolio", "Accept": "application/vnd.github+json"},
      )
      with urlopen(req, timeout=8) as response:
          return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
      return fallback


def get_setting(key, default=""):
    found = row("SELECT value FROM site_settings WHERE key = ?", (key,))
    return found["value"] if found and found["value"] is not None else default


def get_site_settings():
    return {
        "brand_name": get_setting("brand_name", "Oxy-Jen Tech"),
        "footer_bio": get_setting("footer_bio", "Software Developer | Building practical web solutions. Focused on clean code, problem-solving, and continuous learning."),
        "nav_home": get_setting("nav_home", "Home"),
        "nav_about": get_setting("nav_about", "About"),
        "nav_projects": get_setting("nav_projects", "Projects"),
        "nav_ecosystem": get_setting("nav_ecosystem", "Ecosystem"),
        "nav_community": get_setting("nav_community", "Community"),
        "nav_contact": get_setting("nav_contact", "Contact"),
        "nav_github": get_setting("nav_github", "GitHub"),
        "location_name": get_setting("location_name", "Kenya"),
        "country_name": get_setting("country_name", "Kenya"),
        "country_code": get_setting("country_code", "KE"),
        "collaboration_note": get_setting("collaboration_note", "Available for web projects, UI builds, collaborations, and practical software work."),
        "about_heading": get_setting("about_heading", "Focused web products with a clean engineering hand."),
        "about_story": get_setting("about_story", "Oxy-Jen Tech brings together interface design, Flask systems, GitHub-driven project work, and a growing community layer for challenges, feedback, and collaboration."),
        "smtp_host": get_setting("smtp_host", os.environ.get("SMTP_HOST", "")),
        "smtp_port": get_setting("smtp_port", os.environ.get("SMTP_PORT", "587")),
        "smtp_username": get_setting("smtp_username", os.environ.get("SMTP_USERNAME", "")),
        "smtp_from": get_setting("smtp_from", os.environ.get("SMTP_FROM", os.environ.get("SMTP_USERNAME", ""))),
        "smtp_admin_email": get_setting("smtp_admin_email", os.environ.get("ADMIN_EMAIL", "")),
        "smtp_use_tls": get_setting("smtp_use_tls", os.environ.get("SMTP_USE_TLS", "1")),
    }


def save_setting(conn, key, value):
    conn.execute(
        "INSERT INTO site_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value.strip()),
    )


def get_secret_setting(key, env_key=""):
    env_value = os.environ.get(env_key or key.upper(), "").strip()
    if env_value:
        return env_value
    return get_setting(key, "")


def get_smtp_config():
    settings = get_site_settings()
    return {
        "host": settings["smtp_host"].strip(),
        "port": int((settings["smtp_port"] or "587").strip() or 587),
        "username": settings["smtp_username"].strip(),
        "password": get_secret_setting("smtp_password", "SMTP_PASSWORD"),
        "from": settings["smtp_from"].strip() or settings["smtp_username"].strip(),
        "admin_email": settings["smtp_admin_email"].strip(),
        "use_tls": settings["smtp_use_tls"] != "0",
    }


def admin_password_hash():
    saved = get_setting("admin_password_hash", "")
    if saved:
        return saved
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    return generate_password_hash(password)


def verify_admin_password(password):
    return check_password_hash(admin_password_hash(), password or "")


def country_flag(code):
    clean = "".join(ch for ch in (code or "").upper() if "A" <= ch <= "Z")[:2]
    if len(clean) != 2:
        return ""
    return chr(0x1F1E6 + ord(clean[0]) - ord("A")) + chr(0x1F1E6 + ord(clean[1]) - ord("A"))


def send_email_reply(to_email, subject, body):
    smtp = get_smtp_config()
    if not smtp["host"] or not smtp["from"] or not to_email:
        return False, "Email saved. Add SMTP settings in Admin Security & Email to send mail."

    msg = EmailMessage()
    msg["Subject"] = subject or "Reply from Oxy-Jen Tech"
    msg["From"] = smtp["from"]
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(smtp["host"], smtp["port"], timeout=15) as server:
            if smtp["use_tls"]:
                server.starttls()
            if smtp["username"] and smtp["password"]:
                server.login(smtp["username"], smtp["password"])
            server.send_message(msg)
        return True, "Reply sent to the sender."
    except OSError as exc:
        return False, f"Email saved, but sending failed: {exc}"


def send_contact_notification(message):
    smtp = get_smtp_config()
    if not smtp["admin_email"]:
        return False, "Admin notification email is not set."
    body = (
        f"New contact message from {message['name']}\n\n"
        f"Email: {message['email']}\n"
        f"Country: {message.get('country_name') or ''} {message.get('country_code') or ''}\n"
        f"Subject: {message.get('subject') or 'No subject'}\n\n"
        f"{message['message']}"
    )
    return send_email_reply(smtp["admin_email"], f"New site message: {message.get('subject') or message['name']}", body)


def get_github_data():
    now = time.time()
    if CACHE["profile"] and now - CACHE["time"] < CACHE_TTL:
        return CACHE

    profile = github_get(f"/users/{GITHUB_USER}", REAL_PROFILE_FALLBACK)
    repos = github_get(f"/users/{GITHUB_USER}/repos?sort=updated&per_page=12", REAL_REPO_FALLBACK)
    events = github_get(f"/users/{GITHUB_USER}/events/public?per_page=8", [])

    language_totals = {}
    for repo in repos:
        lang = repo.get("language") or "Other"
        language_totals[lang] = language_totals.get(lang, 0) + 1

    CACHE.update({
        "profile": profile,
        "repos": repos,
        "events": events,
        "languages": language_totals,
        "time": now,
    })
    return CACHE


def rows(query, args=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, args).fetchall()


def row(query, args=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, args).fetchone()


def save_upload(field_name):
    file = request.files.get(field_name)
    if not file or not file.filename:
        return request.form.get("url", "").strip()
    filename = f"{int(time.time())}-{secure_filename(file.filename)}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return url_for("uploaded_file", filename=filename)


def save_uploads(field_name):
    urls = []
    for file in request.files.getlist(field_name):
        if not file or not file.filename:
            continue
        filename = f"{int(time.time())}-{secrets.token_hex(3)}-{secure_filename(file.filename)}"
        path = os.path.join(UPLOAD_DIR, filename)
        file.save(path)
        urls.append(url_for("uploaded_file", filename=filename))
    typed_urls = request.form.get("asset_urls", "").strip()
    if typed_urls:
        urls.extend([line.strip() for line in typed_urls.splitlines() if line.strip()])
    single_url = request.form.get("url", "").strip()
    if single_url and single_url not in urls:
        urls.insert(0, single_url)
    return urls


def content_assets(item):
    assets = []
    raw = item["assets"] if "assets" in item.keys() else ""
    if raw:
        try:
            assets = [url for url in json.loads(raw) if url]
        except (TypeError, json.JSONDecodeError):
            assets = []
    if item["url"] and item["url"] not in assets:
        assets.insert(0, item["url"])
    return assets


def content_style(item):
    styles = []
    if "background_url" in item.keys() and item["background_url"]:
        styles.append(f"--block-bg-image: url('{item['background_url']}')")
    if "text_color" in item.keys() and item["text_color"]:
        styles.append(f"--block-text-color: {item['text_color']}")
    return "; ".join(styles)


def content_is_live(item, now=None):
    now = now or datetime.now(timezone.utc).isoformat()
    return (
        int(item.get("visible", 1) if hasattr(item, "get") else item["visible"] if "visible" in item.keys() else 1)
        and (not item["starts_at"] or item["starts_at"] <= now)
        and (not item["ends_at"] or item["ends_at"] >= now)
    )


def page_blocks(page):
    now = datetime.now(timezone.utc).isoformat()
    items = rows(
        """
        SELECT * FROM content_items
        WHERE COALESCE(page, 'home') IN (?, 'all')
          AND COALESCE(visible, 1) = 1
          AND (starts_at IS NULL OR starts_at = '' OR starts_at <= ?)
          AND (ends_at IS NULL OR ends_at = '' OR ends_at >= ?)
        ORDER BY COALESCE(slot, 'main'), COALESCE(sort_order, 0), id DESC
        """,
        (page, now, now),
    )
    grouped = {}
    for item in items:
        slot = item["slot"] or "main"
        grouped.setdefault(slot, []).append(item)
    return grouped


def live_content_by_kind(kind, limit=None):
    now = datetime.now(timezone.utc).isoformat()
    query = """
        SELECT * FROM content_items
        WHERE kind = ?
          AND COALESCE(visible, 1) = 1
          AND (starts_at IS NULL OR starts_at = '' OR starts_at <= ?)
          AND (ends_at IS NULL OR ends_at = '' OR ends_at >= ?)
        ORDER BY COALESCE(sort_order, 0), id DESC
    """
    args = [kind, now, now]
    if limit:
        query += " LIMIT ?"
        args.append(limit)
    return rows(query, args)


def relative_time(value):
    if not value:
        return "unknown"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60} min ago"
        if seconds < 86400:
            return f"{seconds // 3600} hours ago"
        return f"{seconds // 86400} days ago"
    except ValueError:
        return value


def media_type(url):
    if not url:
        return "none"
    clean = url.split("?")[0].lower()
    if clean.endswith((".mp4", ".webm", ".ogg", ".mov")):
        return "video"
    if clean.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg")):
        return "image"
    return "link"


def content_payload_from_form(existing_assets=None):
    assets = save_uploads("assets")
    if assets and existing_assets:
        assets = existing_assets + [url for url in assets if url not in existing_assets]
    elif not assets and existing_assets:
        assets = existing_assets
    primary_url = assets[0] if assets else request.form.get("url", "").strip()
    return {
        "kind": request.form.get("kind", "project"),
        "title": request.form.get("title", "").strip(),
        "subtitle": request.form.get("subtitle", "").strip(),
        "description": request.form.get("description", "").strip(),
        "url": primary_url,
        "assets": json.dumps(assets),
        "status": request.form.get("status", "").strip(),
        "page": request.form.get("page", "home"),
        "slot": request.form.get("slot", "main"),
        "layout": request.form.get("layout", "card"),
        "media_behavior": request.form.get("media_behavior", "scroll"),
        "button_label": request.form.get("button_label", "").strip(),
        "button_url": request.form.get("button_url", "").strip(),
        "starts_at": request.form.get("starts_at", "").strip(),
        "ends_at": request.form.get("ends_at", "").strip(),
        "visible": 1 if request.form.get("visible") else 0,
        "sort_order": int(request.form.get("sort_order", "0") or 0),
        "text_effect": request.form.get("text_effect", "normal"),
        "font_family": request.form.get("font_family", "default"),
        "text_align": request.form.get("text_align", "left"),
        "text_color": request.form.get("text_color", "").strip(),
        "background_url": request.form.get("background_url", "").strip(),
        "transparent_bg": 1 if request.form.get("transparent_bg") else 0,
        "html_content": request.form.get("html_content", "").strip(),
        "display_seconds": int(request.form.get("display_seconds", "0") or 0) or None,
        "pause_seconds": int(request.form.get("pause_seconds", "0") or 0) or None,
        "carousel_direction": request.form.get("carousel_direction", "left"),
    }


def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def validate_csrf():
    sent = request.form.get("_csrf", "")
    saved = session.get("_csrf", "")
    if not saved or not hmac.compare_digest(sent, saved):
        flash("Security check failed. Please try again.")
        return False
    return True


@app.before_request
def prepare_request():
    g.is_admin = bool(session.get("admin"))
    if request.endpoint and request.endpoint.startswith("admin"):
        session.permanent = True


@app.after_request
def secure_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.context_processor
def inject_helpers():
    public_contacts = rows("SELECT * FROM contact_links WHERE visible = 1 ORDER BY sort_order, id")
    return {
        "relative_time": relative_time,
        "github_user": GITHUB_USER,
        "csrf_token": csrf_token,
        "public_contacts": public_contacts,
        "media_type": media_type,
        "content_assets": content_assets,
        "content_style": content_style,
        "country_flag": country_flag,
        "site_settings": get_site_settings(),
    }


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    gh = get_github_data()
    testimonials = rows("SELECT * FROM testimonials WHERE approved = 1 AND flagged = 0 ORDER BY recommended DESC, id DESC LIMIT 6")
    comments = rows("SELECT * FROM comments WHERE approved = 1 ORDER BY id DESC LIMIT 4")
    home_sections = live_content_by_kind("homepage", 3)
    about_photos = live_content_by_kind("about_photo", 4)
    achievements = live_content_by_kind("achievement", 6)
    return render_template("index.html", gh=gh, testimonials=testimonials, comments=comments, home_sections=home_sections, about_photos=about_photos, achievements=achievements, page_blocks=page_blocks("home"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/about")
def about():
    gh = get_github_data()
    about_photos = live_content_by_kind("about_photo", 6)
    achievements = live_content_by_kind("achievement", 8)
    return render_template("about.html", gh=gh, about_photos=about_photos, achievements=achievements, page_blocks=page_blocks("about"))


@app.route("/projects")
def projects():
    gh = get_github_data()
    managed_projects = live_content_by_kind("project")
    return render_template("projects.html", gh=gh, managed_projects=managed_projects, page_blocks=page_blocks("projects"))


@app.route("/ecosystem")
def ecosystem():
    gh = get_github_data()
    videos = live_content_by_kind("video")
    challenges = live_content_by_kind("challenge")
    return render_template("ecosystem.html", gh=gh, videos=videos, challenges=challenges, page_blocks=page_blocks("ecosystem"))


@app.route("/community", methods=["GET", "POST"])
def community():
    if request.method == "POST":
        if not validate_csrf():
            return redirect(url_for("community"))
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        visibility = request.form.get("visibility", "public")
        country_code = request.form.get("country_code", "").strip().upper()[:2]
        country_name = request.form.get("country_name", "").strip()
        if name and message:
            with sqlite3.connect(DB_PATH) as conn:
                if visibility == "private":
                    conn.execute(
                        "INSERT INTO messages (name, email, subject, message, country_code, country_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (name, email, "Community message", message, country_code, country_name, datetime.now(timezone.utc).isoformat()),
                    )
                    sent, note = send_contact_notification({"name": name, "email": email, "subject": "Community message", "message": message, "country_code": country_code, "country_name": country_name})
                    flash("Private message sent." if sent else f"Private message saved. {note}")
                elif visibility == "testimonial":
                    conn.execute(
                        "INSERT INTO testimonials (name, role, quote, rating, approved, recommended, flagged, country_code, country_name, created_at) VALUES (?, ?, ?, 5, 1, 0, 0, ?, ?, ?)",
                        (name, request.form.get("role", "Community member").strip() or "Community member", message, country_code, country_name, datetime.now(timezone.utc).isoformat()),
                    )
                    flash("Your testimonial is live.")
                else:
                    conn.execute(
                        "INSERT INTO comments (name, email, message, approved, country_code, country_name, created_at) VALUES (?, ?, ?, 1, ?, ?, ?)",
                        (name, email, message, country_code, country_name, datetime.now(timezone.utc).isoformat()),
                    )
                    flash("Your comment is live.")
        return redirect(url_for("community"))
    comments = rows("SELECT * FROM comments WHERE approved = 1 ORDER BY id DESC")
    testimonials = rows("SELECT * FROM testimonials WHERE approved = 1 AND flagged = 0 ORDER BY recommended DESC, id DESC")
    return render_template("community.html", comments=comments, testimonials=testimonials, page_blocks=page_blocks("community"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        if not validate_csrf():
            return redirect(url_for("contact"))
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        country_code = request.form.get("country_code", "").strip().upper()[:2]
        country_name = request.form.get("country_name", "").strip()
        if name and email and message:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO messages (name, email, subject, message, country_code, country_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, email, subject, message, country_code, country_name, datetime.now(timezone.utc).isoformat()),
                )
            sent, note = send_contact_notification({"name": name, "email": email, "subject": subject, "message": message, "country_code": country_code, "country_name": country_name})
            flash("Message sent to Oxy-Jen Tech." if sent else f"Message saved. {note}")
        return redirect(url_for("contact"))
    return render_template("contact.html", page_blocks=page_blocks("contact"))


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if not validate_csrf():
            return redirect(url_for("admin_login"))
        password = request.form.get("password")
        if verify_admin_password(password):
            session["admin"] = True
            session.permanent = True
            return redirect(url_for("admin"))
        flash("Invalid admin password.")
    return render_template("admin_login.html")


@app.route("/admin/dashboard", methods=["GET", "POST"])
@admin_required
def admin():
    if request.method == "POST":
        if not validate_csrf():
            return redirect(url_for("admin"))
        action = request.form.get("action")
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if action == "testimonial":
                conn.execute(
                    "INSERT INTO testimonials (name, role, quote, rating, approved, recommended, flagged, country_code, country_name, created_at) VALUES (?, ?, ?, ?, 1, ?, 0, ?, ?, ?)",
                    (
                        request.form.get("name", "").strip(),
                        request.form.get("role", "").strip(),
                        request.form.get("quote", "").strip(),
                        int(request.form.get("rating", "5")),
                        1 if request.form.get("recommended") else 0,
                        request.form.get("country_code", "").strip().upper()[:2],
                        request.form.get("country_name", "").strip(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            elif action == "testimonial_status":
                conn.execute(
                    "UPDATE testimonials SET approved = ?, recommended = ?, flagged = ? WHERE id = ?",
                    (
                        1 if request.form.get("approved") else 0,
                        1 if request.form.get("recommended") else 0,
                        1 if request.form.get("flagged") else 0,
                        request.form.get("id"),
                    ),
                )
            elif action == "approve_comment":
                conn.execute("UPDATE comments SET approved = 1 WHERE id = ?", (request.form.get("id"),))
            elif action == "delete_comment":
                conn.execute("DELETE FROM comments WHERE id = ?", (request.form.get("id"),))
            elif action == "content":
                payload = content_payload_from_form()
                conn.execute(
                    """
                    INSERT INTO content_items
                    (kind, title, subtitle, description, url, assets, status, page, slot, layout, media_behavior, button_label, button_url, starts_at, ends_at, visible, sort_order, text_effect, font_family, text_align, text_color, background_url, transparent_bg, html_content, display_seconds, pause_seconds, carousel_direction, created_at)
                    VALUES (:kind, :title, :subtitle, :description, :url, :assets, :status, :page, :slot, :layout, :media_behavior, :button_label, :button_url, :starts_at, :ends_at, :visible, :sort_order, :text_effect, :font_family, :text_align, :text_color, :background_url, :transparent_bg, :html_content, :display_seconds, :pause_seconds, :carousel_direction, :created_at)
                    """,
                    {**payload, "created_at": datetime.now(timezone.utc).isoformat()},
                )
            elif action == "content_update":
                item_id = request.form.get("id")
                existing = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
                existing_assets = content_assets(existing) if existing else []
                payload = content_payload_from_form(existing_assets)
                conn.execute(
                    """
                    UPDATE content_items
                    SET kind = :kind, title = :title, subtitle = :subtitle, description = :description,
                        url = :url, assets = :assets, status = :status, page = :page, slot = :slot,
                        layout = :layout, media_behavior = :media_behavior, button_label = :button_label,
                        button_url = :button_url, starts_at = :starts_at, ends_at = :ends_at,
                        visible = :visible, sort_order = :sort_order, text_effect = :text_effect,
                        font_family = :font_family, text_align = :text_align, text_color = :text_color,
                        background_url = :background_url, transparent_bg = :transparent_bg,
                        html_content = :html_content, display_seconds = :display_seconds,
                        pause_seconds = :pause_seconds, carousel_direction = :carousel_direction
                    WHERE id = :id
                    """,
                    {**payload, "id": item_id},
                )
            elif action == "delete_content":
                conn.execute("DELETE FROM content_items WHERE id = ?", (request.form.get("id"),))
            elif action == "contact_link":
                conn.execute(
                    "INSERT INTO contact_links (label, url, note, visible, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        request.form.get("label", "").strip(),
                        request.form.get("url", "").strip(),
                        request.form.get("note", "").strip(),
                        1 if request.form.get("visible") else 0,
                        int(request.form.get("sort_order", "0") or 0),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            elif action == "site_settings":
                for key in ["brand_name", "footer_bio", "nav_home", "nav_about", "nav_projects", "nav_ecosystem", "nav_community", "nav_contact", "nav_github", "location_name", "country_name", "country_code", "collaboration_note", "about_heading", "about_story"]:
                    save_setting(conn, key, request.form.get(key, ""))
            elif action == "security_email":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_admin_password", "")
                confirm_password = request.form.get("confirm_admin_password", "")
                if new_password or confirm_password:
                    if not verify_admin_password(current_password):
                        flash("Current admin password is incorrect.")
                        return redirect(url_for("admin"))
                    if len(new_password) < 10:
                        flash("New admin password must be at least 10 characters.")
                        return redirect(url_for("admin"))
                    if new_password != confirm_password:
                        flash("New admin password confirmation does not match.")
                        return redirect(url_for("admin"))
                    save_setting(conn, "admin_password_hash", generate_password_hash(new_password))
                    flash("Admin password updated securely.")
                for key in ["smtp_host", "smtp_port", "smtp_username", "smtp_from", "smtp_admin_email", "smtp_use_tls"]:
                    save_setting(conn, key, request.form.get(key, ""))
                smtp_password = request.form.get("smtp_password", "")
                if smtp_password:
                    save_setting(conn, "smtp_password", smtp_password)
                    flash("SMTP password updated.")
            elif action == "delete_contact":
                conn.execute("DELETE FROM contact_links WHERE id = ?", (request.form.get("id"),))
            elif action == "message_status":
                conn.execute(
                    "UPDATE messages SET status = ?, flagged = ? WHERE id = ?",
                    (
                        request.form.get("status", "new"),
                        1 if request.form.get("flagged") else 0,
                        request.form.get("id"),
                    ),
                )
            elif action == "reply_message":
                message_row = conn.execute("SELECT * FROM messages WHERE id = ?", (request.form.get("id"),)).fetchone()
                reply = request.form.get("reply", "").strip()
                sent = False
                if request.form.get("send_now") and message_row and reply:
                    sent, note = send_email_reply(
                        message_row[2],
                        f"Reply from Oxy-Jen Tech: {message_row[3] or 'Your message'}",
                        reply,
                    )
                    flash(note)
                conn.execute(
                    "UPDATE messages SET reply = ?, status = 'replied', replied_at = ?, reply_sent = ? WHERE id = ?",
                    (
                        reply,
                        datetime.now(timezone.utc).isoformat(),
                        1 if sent else 0,
                        request.form.get("id"),
                    ),
                )
        return redirect(url_for("admin"))

    pending = rows("SELECT * FROM comments WHERE approved = 0 ORDER BY id DESC")
    approved = rows("SELECT * FROM comments WHERE approved = 1 ORDER BY id DESC LIMIT 10")
    testimonials = rows("SELECT * FROM testimonials ORDER BY id DESC")
    content = rows("SELECT * FROM content_items ORDER BY id DESC")
    messages = rows("SELECT * FROM messages ORDER BY flagged DESC, id DESC")
    contacts = rows("SELECT * FROM contact_links ORDER BY sort_order, id")
    return render_template("admin.html", pending=pending, approved=approved, testimonials=testimonials, content=content, messages=messages, contacts=contacts)

@app.route("/reset-admin")
def reset_admin():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM site_settings WHERE key='admin_password_hash'")
    return "Admin password reset"


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
