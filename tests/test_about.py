"""About page tests — GHOSTPATH X v0.4.

Contract under test (v0.4):
  - GET  /                                     -> dashboard HTML with the
    About page (sidebar nav after Overview, section id ``page-about``)
  - GET  /assets/about/about-hero.svg          -> 200
  - GET  /assets/about/about-noise-vs-path.svg -> 200
  - GET  /assets/about/about-path-chain.svg    -> 200
  - GET  /assets/about/about-isolated-lab.svg -> 200
  - GET  /assets/about/about-path-walk.gif     -> 200, actually a GIF
  - GET  /assets/radar.gif                     -> 200 (reused on About)

The About page is static: no API calls, no scan dependency. All tests
are deterministic and offline-safe — they only hit the local TestClient
and assert on the guaranteed contents listed above, never on wording
beyond them.
"""

import re

# Every About asset the page references, plus the reused radar GIF.
ABOUT_ASSETS = [
    "/assets/about/about-hero.svg",
    "/assets/about/about-noise-vs-path.svg",
    "/assets/about/about-path-chain.svg",
    "/assets/about/about-isolated-lab.svg",
    "/assets/about/about-path-walk.gif",
    "/assets/radar.gif",
]

# Hosts an offline, self-contained dashboard is allowed to link to:
# the local server itself, and the curated CTF homepage domains already
# present in the page. Anything else (CDN, font provider, tracker)
# breaks the offline-safe rule.
ALLOWED_HOSTS = {
    "127.0.0.1",
    "localhost",
    "vulnhub.com",
    "hackthebox.com",
    "tryhackme.com",
    "portswigger.net",
    "overthewire.org",
    "picoctf.org",
    "root-me.org",
    "rapid7.com",
    "github.com",
    "owasp.org",
}

# Substrings that must never appear in any URL the page links to.
BANNED_URL_MARKERS = (
    "cdn",
    "googleapis",
    "gstatic",
    "fonts.",
    "unpkg",
    "jsdelivr",
    "cloudflare",
    "analytics",
    "tracking",
    "doubleclick",
)


def _get_dashboard_html(client):
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / failed: {resp.status_code} {resp.text[:300]}"
    )
    return resp.text


def test_about_page_present_with_guaranteed_content(client):
    """GET / serves the About page with its guaranteed contents."""
    html = _get_dashboard_html(client)
    assert "About" in html, "dashboard HTML has no 'About' nav/section"
    assert "page-about" in html, (
        "dashboard HTML has no About section id 'page-about'"
    )
    assert "real-life problem" in html, (
        "About page must contain the exact phrase 'real-life problem'"
    )
    assert "Follow the ghost. Prove the path." in html, (
        "About page must contain the tagline "
        "'Follow the ghost. Prove the path.'"
    )
    assert "Adarsh" in html, "About page must credit 'Adarsh'"
    assert "Customer B reads Customer A's order" in html, (
        "About page must include the lab example "
        "'Customer B reads Customer A's order'"
    )


def test_about_assets_all_return_200_and_gif_is_a_gif(client):
    """Every About asset (and the reused radar GIF) returns 200.

    The walkthrough GIF must actually be a GIF: content-type
    ``image/gif`` or a body starting with the GIF87a/GIF89a magic.
    """
    for path in ABOUT_ASSETS:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"GET {path} failed: {resp.status_code} {resp.text[:200]}"
        )
        assert resp.content, f"GET {path} returned an empty body"

    gif = client.get("/assets/about/about-path-walk.gif")
    assert gif.status_code == 200
    is_gif_type = "image/gif" in gif.headers.get("content-type", "")
    is_gif_magic = gif.content[:6] in (b"GIF89a", b"GIF87a")
    assert is_gif_type or is_gif_magic, (
        "about-path-walk.gif is not a GIF: content-type "
        f"{gif.headers.get('content-type')!r}, first bytes "
        f"{gif.content[:6]!r}"
    )


def test_about_page_has_no_external_urls(client):
    """The served dashboard HTML links to no CDN, font or tracking host.

    Collects every http/https URL in the served index.html and allows
    only the local server and the curated CTF homepage domains already
    present in the page.
    """
    html = _get_dashboard_html(client)
    urls = re.findall(r"https?://[^\s\"'<>]+", html)
    assert urls, "expected at least one URL in the dashboard HTML"
    for url in urls:
        host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
        host = host[4:] if host.startswith("www.") else host
        assert not any(marker in url.lower() for marker in BANNED_URL_MARKERS), (
            f"dashboard links to a banned external host: {url!r}"
        )
        assert host in ALLOWED_HOSTS or any(
            host.endswith("." + allowed) for allowed in ALLOWED_HOSTS
        ), f"dashboard links to an unapproved external host: {url!r}"
