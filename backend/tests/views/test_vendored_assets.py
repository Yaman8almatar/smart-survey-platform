import re
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse

VENDORED = [
    "vendor/fonts/fonts.css",
    "vendor/bootstrap/bootstrap.min.css",
    "vendor/bootstrap-icons/bootstrap-icons.min.css",
    "vendor/bootstrap/bootstrap.bundle.min.js",
    "vendor/chartjs/chart.umd.js",
]
EXTERNAL_HOSTS = ["cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"]


def vendor_dir():
    return Path(finders.find("vendor/fonts/fonts.css")).parent.parent


@pytest.mark.django_db
def test_login_page_loads_only_vendored_assets(client):
    response = client.get(reverse("users:login"))
    content = response.content.decode()

    assert response.status_code == 200
    for host in EXTERNAL_HOSTS:
        assert host not in content
    for path in VENDORED:
        assert f"/static/{path}" in content


@pytest.mark.parametrize("path", VENDORED)
def test_vendored_file_is_found_by_staticfiles(path):
    assert finders.find(path) is not None


def test_vendored_css_names_no_remote_url():
    css_files = sorted(vendor_dir().rglob("*.css"))

    assert css_files
    for css in css_files:
        text = css.read_text(encoding="utf-8")
        for remote in ("url(http", 'url("http', "url('http"):
            assert remote not in text, css


def test_every_font_file_exists_on_disk():
    fonts_dir = vendor_dir() / "fonts"
    names = re.findall(r"url\((files/[^)]+\.woff2)\)", (fonts_dir / "fonts.css").read_text(encoding="utf-8"))

    assert names
    for name in names:
        assert (fonts_dir / name).is_file(), name
    for icon_font in ("bootstrap-icons.woff2", "bootstrap-icons.woff"):
        assert (vendor_dir() / "bootstrap-icons" / "fonts" / icon_font).is_file()
