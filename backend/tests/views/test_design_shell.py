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


@pytest.mark.django_db
def test_shell_loads_tokens_and_marks_current_page(client):
    content = client.get(reverse("home")).content.decode()

    assert content.index("css/tokens.css") < content.index("css/site.css")
    assert (
        f'<a class="nav-link" aria-current="page" href="{reverse("home")}">'
        in content
    )
    assert "bi-bar-chart-line-fill" not in content
