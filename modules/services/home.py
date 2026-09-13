import json
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from flask import jsonify, render_template, session
from modules.services.audit import write_audit_log
from modules.services.db import get_conn

TWCR_SOURCES = (("latest", "最新公告", "https://twcr.tw/?page_id=1314"), ("downloads", "最新下載", "https://twcr.tw/?page_id=1809"))
TWCR_UPDATES_FILE = Path(__file__).resolve().parents[2] / "tasks" / "home" / "twcr_updates.json"
DOWNLOAD_FILE_TYPES = {
    ".csv": ("CSV", "bi-filetype-csv"),
    ".pdf": ("PDF", "bi-filetype-pdf"),
    ".txt": ("TXT", "bi-filetype-txt"),
    ".xls": ("Excel", "bi-file-earmark-spreadsheet"),
    ".xlsx": ("Excel", "bi-file-earmark-spreadsheet"),
    ".doc": ("Word", "bi-file-earmark-word"),
    ".docx": ("Word", "bi-file-earmark-word"),
    ".zip": ("ZIP", "bi-file-earmark-zip"),
}


def _get_download_file_type(url):
    extension = PurePosixPath(unquote(urlparse(url).path)).suffix.lower()
    label, icon = DOWNLOAD_FILE_TYPES.get(extension, (chr(0x6a94) + chr(0x6848), "bi-file-earmark-arrow-down"))
    return {"file_type": label, "file_icon": icon, "file_type_class": label.lower()}


def refresh_twcr_updates():
    """Fetch current announcements and save them for the homepage to read."""
    updates = {}
    for key, source, url in TWCR_SOURCES:
        try:
            items = _fetch_twcr_source(source, url)
            updates[key] = items[2:7] if key == "latest" else items
        except Exception:
            updates[key] = []
    TWCR_UPDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = TWCR_UPDATES_FILE.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(updates, ensure_ascii=False), encoding="utf-8")
    temporary_file.replace(TWCR_UPDATES_FILE)
    write_audit_log(
        "system_home_updates_auto",
        {
            "execution_mode": "system_automatic",
            "latest_count": len(updates["latest"]),
            "downloads_count": len(updates["downloads"]),
        },
        user_id="SYSTEM",
    )
    return updates


def fetch_twcr_updates():
    """Read the most recent daily announcement snapshot without a network request."""
    try:
        updates = json.loads(TWCR_UPDATES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"latest": [], "downloads": []}
    return {
        "latest": updates.get("latest", []) if isinstance(updates.get("latest"), list) else [],
        "downloads": updates.get("downloads", []) if isinstance(updates.get("downloads"), list) else [],
    }


def _fetch_twcr_source(source, source_url):
    with urlopen(Request(source_url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as response:
        soup = BeautifulSoup(response.read(), "html.parser")
    links = soup.select("a[href]")
    if source == "最新公告":
        content = soup.select_one(".entry-content, .post-content, main") or soup
        links = content.select("li a[href], article h2 a[href], article h3 a[href], p a[href]")
    else:
        links = [link for link in links if "/wp-content/uploads/" in link["href"]]
    updates, seen = [], set()
    for link in links:
        title, url = link.get_text(" ", strip=True), urljoin(source_url, link["href"])
        if title and url not in seen:
            seen.add(url)
            updates.append({"source": source, "title": title, "url": url, **_get_download_file_type(url)})
    return updates


def register_main_routes(app, app_env, login_required):
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "environment": app_env})

    @app.route("/")
    @login_required
    def index():
        pending_application_count, key_application_status = 0, ""
        announcements = fetch_twcr_updates()
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(TotalCount) AS Sum_TotalCount, AVG(CompletenessScore) AS Avg_CompletenessScore FROM [Job]")
            row = cursor.fetchone()
            stats = {"sum_total_count": f"{int(getattr(row, 'Sum_TotalCount', 0) or 0):,}", "avg_completeness_score": f"{(getattr(row, 'Avg_CompletenessScore', 0) or 0) * 100:.2f}%"}
            if session.get("position") == "Admin":
                cursor.execute("SELECT COUNT(*) AS PendingCount FROM dbo.User_applications WHERE Status = 'Pending'")
                pending_application_count = int(getattr(cursor.fetchone(), "PendingCount", 0) or 0)
            else:
                cursor.execute("SELECT TOP 1 Status FROM dbo.User_applications WHERE UserID = ? ORDER BY CreatedAt DESC", session["userid"])
                row = cursor.fetchone()
                key_application_status = row[0] if row and row[0] in {"Approved", "Rejected"} else ""
            conn.close()
        except Exception as error:
            app.logger.error("Error fetching dashboard stats: %s", error)
            stats = {"sum_total_count": "0", "avg_completeness_score": "0.0%"}
        return render_template("index.html", active="index", stats=stats, pending_application_count=pending_application_count, key_application_status=key_application_status, announcements=announcements)
