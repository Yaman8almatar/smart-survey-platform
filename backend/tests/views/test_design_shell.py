"""Design foundation v2 on the web shell (TASK-17 Part A)."""

import pytest
from django.template.loader import render_to_string
from django.urls import reverse


def test_signal_ring_renders_value_and_label():
    html = render_to_string(
        "partials/signal_ring.html",
        {"value": 57, "size": 48, "label": "57 percent of the response target"},
    )

    assert 'stroke-dasharray="57 100"' in html
    assert 'aria-label="57 percent of the response target"' in html
    assert 'role="img"' in html
    assert 'width="48"' in html


def test_signal_ring_text_replaces_the_centre():
    html = render_to_string(
        "partials/signal_ring.html", {"value": 0, "text": "<5", "label": "Reach"}
    )

    assert ">&lt;5</text>" in html
    assert "0%" not in html


@pytest.mark.parametrize("value", [0, None, ""])
def test_signal_ring_without_a_value_keeps_an_empty_arc(value):
    html = render_to_string("partials/signal_ring.html", {"value": value, "label": "Reach"})

    assert 'class="signal-ring__arc signal-ring__arc--empty"' in html
    assert 'stroke-dasharray="0 100"' in html


def test_signal_ring_with_a_value_has_a_visible_arc():
    html = render_to_string("partials/signal_ring.html", {"value": 24, "label": "Reach"})

    assert 'class="signal-ring__arc"' in html
    assert ">24%</text>" in html


def test_decorative_signal_ring_is_hidden_from_assistive_technology():
    html = render_to_string(
        "partials/signal_ring.html", {"value": 24, "label": "Reach", "decorative": True}
    )

    assert 'aria-hidden="true"' in html
    assert 'role="img"' not in html
    assert "aria-label" not in html


@pytest.mark.django_db
def test_shell_loads_tokens_and_marks_current_page(client):
    content = client.get(reverse("home")).content.decode()

    assert content.index("css/tokens.css") < content.index("css/site.css")
    assert (
        f'<a class="nav-link" aria-current="page" href="{reverse("home")}">'
        in content
    )
    assert "bi-bar-chart-line-fill" not in content
