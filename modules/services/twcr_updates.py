from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

TWCR_SOURCES = (
    ("latest", "最新公告", "https://twcr.tw/?page_id=1314"),
    ("downloads", "最新下載", "https://twcr.tw/?page_id=1809"),
)
_CACHE_TTL = timedelta(minutes=30)
_cache = {"expires_at": datetime.min, "updates": {"latest": [], "downloads": []}}
_cache_lock = Lock()


def fetch_twcr_updates():
    with _cache_lock:
        if datetime.now() < _cache["expires_at"]:
            return _cache["updates"]

    updates = {}
    for key, source_name, source_url in TWCR_SOURCES:
        try:
            items = _fetch_source(source_name, source_url)
            updates[key] = _select_latest(items) if key == "latest" else items
        except Exception:
            updates[key] = []

    with _cache_lock:
        _cache["updates"] = updates
        _cache["expires_at"] = datetime.now() + _CACHE_TTL
    return updates


def _select_latest(items):
    start = next((index for index, item in enumerate(items) if "癌登第115006號通知文" in item["title"]), None)
    return items[start:start + 5] if start is not None else []


def _fetch_source(source_name, source_url):
    request = Request(source_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        page = response.read()

    soup = BeautifulSoup(page, "html.parser")
    content = soup.select_one(".entry-content, .post-content, main") or soup
    updates, seen = [], set()
    links = content.select("li a[href], article h2 a[href], article h3 a[href], p a[href]")
    if source_name == "最新下載":
        links = [link for link in soup.select("a[href]") if "/wp-content/uploads/" in link["href"]]
    for link in links:
        title, href = link.get_text(" ", strip=True), urljoin(source_url, link["href"])
        if not title or href in seen:
            continue
        seen.add(href)
        updates.append({"source": source_name, "title": title, "url": href, "date": link.parent.get_text(" ", strip=True)})
    return updates
