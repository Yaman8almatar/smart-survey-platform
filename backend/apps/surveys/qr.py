"""QR code of a survey's invitation link (FR-10), drawn by segno."""

from io import BytesIO

import segno


def qr_data_uri(link):
    """Return the QR code of link as an SVG data URI for an <img> on the share page."""
    return segno.make(link, error="m").svg_data_uri(scale=6)


def qr_svg_bytes(link):
    """Return the QR code of link as an SVG file for download."""
    buffer = BytesIO()
    segno.make(link, error="m").save(
        buffer, kind="svg", scale=8, title="QR code for the invitation link"
    )
    return buffer.getvalue()
