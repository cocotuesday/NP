#!/usr/bin/env python3
"""Download each park's featured photo from its official NPS website page."""
import html
import json
import mimetypes
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "parks-data.js"
PHOTO_FILE = ROOT / "park-photos.js"
IMAGE_DIR = ROOT / "images"
USER_AGENT = "NationalParksQuizPhotoPack/1.0 (personal quiz using official NPS park pages)"


def read_js(path, symbol):
    source = path.read_text(encoding="utf-8")
    match = re.search(rf"window\.{symbol}\s*=\s*(.*);\s*$", source, re.S)
    if not match:
        raise ValueError(f"Could not read {symbol} from {path}")
    return json.loads(match.group(1))


class ParkPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.og_image = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property") == "og:image" and attrs.get("content"):
            self.og_image = attrs["content"]
        if tag == "img":
            src = attrs.get("src") or attrs.get("data-src") or ""
            alt = html.unescape(attrs.get("alt", "")).strip()
            if "/common/uploads/structured_data/" in src and alt:
                self.images.append((src, alt))


def fetch(url, limit=16 * 1024 * 1024):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=35) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Response exceeded size limit")
        return data, response.headers.get("Content-Type", "")


def download_park(park):
    page_code = park.get("pageCode", park["code"])
    page_url = f"https://www.nps.gov/{page_code}/index.htm"
    page_bytes, _ = fetch(page_url, limit=8 * 1024 * 1024)
    parser = ParkPage()
    parser.feed(page_bytes.decode("utf-8", "replace"))
    if parser.images:
        photo_index = min(park.get("photoIndex", 0), len(parser.images) - 1)
        image_url, caption = parser.images[photo_index]
        image_url = urljoin(page_url, image_url)
    elif parser.og_image:
        image_url, caption = parser.og_image, "Featured image on the official NPS park page"
        image_url = urljoin(page_url, image_url)
    else:
        raise ValueError("No featured image found on the NPS park page")
    image_bytes, content_type = fetch(image_url)
    content_type = content_type.split(";", 1)[0].lower()
    if not content_type.startswith("image/"):
        raise ValueError(f"Unexpected image content type: {content_type}")
    extension = mimetypes.guess_extension(content_type) or ".jpg"
    file_path = IMAGE_DIR / f"{park['code']}{extension}"
    file_path.write_bytes(image_bytes)
    return {
        "src": file_path.relative_to(ROOT).as_posix(),
        "sourceUrl": page_url,
        "caption": caption,
        "source": "National Park Service",
    }


def write_photos(photos):
    PHOTO_FILE.write_text(
        "window.NP_PHOTOS = " + json.dumps(photos, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def main():
    parks = read_js(DATA_FILE, "NP_PARKS")
    IMAGE_DIR.mkdir(exist_ok=True)
    try:
        photos = read_js(PHOTO_FILE, "NP_PHOTOS") if PHOTO_FILE.exists() else {}
    except Exception:
        photos = {}
    failures = []
    for i, park in enumerate(parks, 1):
        code = park["code"]
        existing = photos.get(code, {}).get("src", "")
        if existing and (ROOT / existing).is_file():
            continue
        error = ""
        for attempt in range(3):
            try:
                photos[code] = download_park(park)
                break
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                error = str(exc)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        else:
            failures.append({"code": code, "name": park["name"], "error": error})
        write_photos(photos)
        if i % 5 == 0 or i == len(parks):
            print(f"Processed {i}/{len(parks)} parks; saved {len(photos)} images; failed {len(failures)}", flush=True)
        time.sleep(0.35)
    (ROOT / "photo-download-errors.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    write_photos(photos)
    print(f"Done: {len(photos)} local park photos; {len(failures)} unavailable.", flush=True)


if __name__ == "__main__":
    main()
