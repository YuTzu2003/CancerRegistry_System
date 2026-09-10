from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from flask import jsonify, render_template, session
from modules.services.db import get_conn

TWCR_SOURCES = (("latest", "最新公告", "https://twcr.tw/?page_id=1314"), ("downloads", "最新下載", "https://twcr.tw/?page_id=1809"))
cache = {"expires_at": datetime.min, "updates": {"latest": [], "downloads": []}}

def fetch_twcr_updates():
    with Lock():
        if datetime.now() < cache["expires_at"]:
            return cache["updates"]
    updates = {}
    for key, source, url in TWCR_SOURCES:
        try:
            items = _fetch_twcr_source(source, url)
            updates[key] = items[2:7] if key == "latest" else items
        except Exception:
            updates[key] = []
    with Lock():
        cache.update(updates=updates, expires_at=datetime.now() + timedelta(minutes=30))
    return updates


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
            updates.append({"source": source, "title": title, "url": url})
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
