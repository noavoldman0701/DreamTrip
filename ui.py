"""Visual building blocks for DreamTrip: styles, logo, hero and page headers.

Everything here only draws things on the page. The trip logic lives in
planner.py and the page flow lives in app.py.
"""

import base64
from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).parent / "assets"

# Small line icons (24x24) for the page headers.
ICONS = {
    "explore": (
        '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/>'
        '<circle cx="12" cy="9.5" r="2.5"/>'
    ),
    "compare": (
        '<path d="M12 4v16M5 20h14M6 7h12"/>'
        '<path d="M6 7l-3 6a3 3 0 0 0 6 0zM18 7l-3 6a3 3 0 0 0 6 0z"/>'
    ),
    "budget": (
        '<path d="M12 3a9 9 0 1 0 9 9h-9z"/>'
        '<path d="M15 3.5A9 9 0 0 1 20.5 9H15z"/>'
    ),
}

# Image types that can be used for the hero picture, in order of preference.
HERO_IMAGE_NAMES = ["hero.jpg", "hero.jpeg", "hero.png", "hero.webp"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _html(markup):
    """Render raw HTML.

    Leading spaces and line breaks are removed first, because Markdown would
    otherwise treat indented lines as code blocks.
    """
    compact = " ".join(line.strip() for line in markup.splitlines())
    st.markdown(compact, unsafe_allow_html=True)


def _read_asset(name):
    """Return the text of a file in the assets folder."""
    return (ASSETS_DIR / name).read_text(encoding="utf-8")


def _image_data_uri(path):
    """Encode an image file so it can be used directly in an <img> tag."""
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }[path.suffix.lower()]
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _hero_image_path():
    """Use assets/hero.* if the user added a photo, otherwise the line drawing."""
    for name in HERO_IMAGE_NAMES:
        path = ASSETS_DIR / name
        if path.exists():
            return path
    return ASSETS_DIR / "landmark.svg"


# ---------------------------------------------------------------------------
# Public building blocks
# ---------------------------------------------------------------------------

def load_styles():
    """Inject the custom CSS from assets/style.css. Call once per run."""
    # Blank lines are removed so Markdown keeps the whole <style> block as HTML.
    lines = [line for line in _read_asset("style.css").splitlines() if line.strip()]
    css = "\n".join(lines)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def sidebar_logo():
    """Show the DreamTrip logo at the top of the sidebar."""
    with st.sidebar:
        _html(f'<div class="dt-sidebar-logo">{_read_asset("logo.svg")}</div>')


def sidebar_landmark():
    """Show a faint landmark drawing at the bottom of the sidebar."""
    uri = _image_data_uri(ASSETS_DIR / "landmark.svg")
    with st.sidebar:
        _html(f'<div class="dt-sidebar-landmark"><img src="{uri}" width="100%" alt=""></div>')


def hero():
    """Show the Home page banner: logo, tagline and a picture."""
    image_uri = _image_data_uri(_hero_image_path())
    _html(f"""
        <div class="dt-hero">
            <div class="dt-hero-text">
                {_read_asset("logo.svg")}
                <p class="dt-hero-tagline">Plan your perfect trip within your budget</p>
                <p class="dt-hero-sub">
                    Depart from Israel and compare estimated trip costs around the world.
                </p>
            </div>
            <div class="dt-hero-art">
                <img src="{image_uri}" alt="">
            </div>
        </div>
    """)


def page_header(title, subtitle, icon):
    """Show a page title with a round icon and a short subtitle.

    Args:
        title: the main heading, e.g. "Explore Destinations".
        subtitle: one short line under the title.
        icon: a key from ICONS.
    """
    svg = (
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="#7E4E60" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS[icon]}</svg>'
    )
    _html(f"""
        <div class="dt-page-header">
            <div class="dt-icon">{svg}</div>
            <div>
                <div class="dt-title dt-page-title">{title}</div>
                <p>{subtitle}</p>
            </div>
        </div>
    """)


def form_section(label):
    """Show a small uppercase label that separates groups of form fields."""
    _html(f'<p class="dt-form-section">{label}</p>')
