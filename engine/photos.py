"""Public-domain photos for Every How news scenes.

Searches Openverse (which indexes Wikimedia Commons, Flickr, rawpixel and others) for images that are
CC0 or public-domain marked only, so no licence obligations ride along with the video. We still credit
every photo in the YouTube description. Photos of people are skipped on purpose: the channel never
shows real people's faces (privacy, and public figures are off-limits), so queries should name places,
objects, ships, buildings or landscapes.
"""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.request

UA = "EveryHowBot/1.0 (https://github.com/HiretechUK/video-autopilot)"
API = "https://api.openverse.org/v1/images/"
PEOPLE = re.compile(r"\b(person|people|man|men|woman|women|girl|boy|child|children|kid|portrait|face|selfie|crowd|protest|"
                    r"president|minister|soldier|soldiers|troops|politician|leader|king|queen|prince|family|worker|workers|"
                    r"student|students|player|actor|actress|model|baby|nude|body|bodies|corpse|blood|wounded|victim)\b", re.I)


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def search(query, n=20):
    q = urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "size": "large", "mature": "false", "page_size": n, "category": "photograph"})
    for attempt in range(3):
        try:
            return json.loads(_get(f"{API}?{q}")).get("results", [])
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def commons(query, n=20):
    """Fallback: Wikimedia Commons directly, public-domain and CC0 files only, as Openverse-shaped results."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": n,
                                "gsrsearch": f"filetype:bitmap {query}", "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1920})
    pages = json.loads(_get(f"https://commons.wikimedia.org/w/api.php?{q}")).get("query", {}).get("pages", {})
    out = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        lic = (m.get("LicenseShortName", {}).get("value") or "").lower()
        if not (lic.startswith("public domain") or lic in ("cc0", "pd")):
            continue
        who = re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value") or "").strip()[:60]
        cats = m.get("Categories", {}).get("value", "").replace("|", " ")
        out.append({"url": ii.get("thumburl") or ii.get("url"), "width": ii.get("thumbwidth") or ii.get("width"), "height": ii.get("thumbheight") or ii.get("height"),
                    "title": pg.get("title", "") + " " + cats, "tags": [], "creator": who, "source": "wikimedia_commons",
                    "license": "pdm" if lic.startswith("public") else "cc0", "foreign_landing_url": ii.get("descriptionurl")})
    return out


def ok(r):
    words = " ".join([r.get("title") or ""] + [t.get("name", "") for t in (r.get("tags") or [])[:25]])
    return (r.get("width") or 0) >= 1200 and (r.get("height") or 0) >= 650 and not PEOPLE.search(words) \
        and (r.get("width") or 1) / max(1, r.get("height") or 1) < 2.6 \
        and not re.search(r"image_png|\.png|\.svg|vector|illustration|drawing|clipart|cartoon|icon|logo", (r.get("url") or "") + " " + words, re.I)


def fetch(query, cache_dir, used=()):
    """Return {path, credit, url} for the best usable photo, or None. Never raises."""
    os.makedirs(cache_dir, exist_ok=True)
    try:
        results = [r for r in search(query) if ok(r)]
    except Exception as e:
        print(f"  openverse search failed for {query!r}: {e}", file=sys.stderr)
        results = []
    if not results:
        try:
            results = [r for r in commons(query) if ok(r)]
        except Exception as e:
            print(f"  commons search failed for {query!r}: {e}", file=sys.stderr)
    for r in results:
        if r["url"] in used:
            continue
        path = os.path.join(cache_dir, hashlib.sha1(r["url"].encode()).hexdigest()[:16] + ".jpg")
        if not os.path.exists(path):
            try:
                data = _get(r["url"], 60)
            except Exception:
                continue
            if len(data) < 60_000 or data[:3] != b"\xff\xd8\xff":  # JPEG only, and not a tiny placeholder
                continue
            open(path, "wb").write(data)
        who = (r.get("creator") or "").strip() or "unknown"
        lic = "public domain" if r.get("license") == "pdm" else "CC0"
        return {"path": path, "url": r["url"], "page": r.get("foreign_landing_url") or r["url"],
                "credit": f"Photo: {who} / {r.get('source', '').replace('_', ' ').title()} ({lic})"}
    print(f"  no usable photo for {query!r}", file=sys.stderr)
    return None


def fill_episode(scenes, cache_dir):
    """Attach src/credit to every photo scene that has a query. Returns the list of credits used."""
    credits, used = [], set()
    for sc in scenes:
        v = sc.get("visual") or {}
        if v.get("type") != "photo" or not v.get("query") or v.get("src"):
            continue
        got = fetch(v["query"], cache_dir, used)
        time.sleep(1)
        if got:
            used.add(got["url"])
            v["src"], v["credit"] = got["path"], got["credit"]
            credits.append({"credit": got["credit"], "page": got["page"]})
    return credits


if __name__ == "__main__":
    print(json.dumps(fetch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "/tmp/eh_photos"), indent=1))
