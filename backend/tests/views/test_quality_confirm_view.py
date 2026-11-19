"""TASK-43 (board W-04): the exclude and include confirmation pages and their POSTs."""

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from apps.core.models import Response, ResponseQuality, Survey, User
from core.enums import AccountStatus, SurveyStatus, UserType

pytestmark = pytest.mark.django_db


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def provider():
    return make_user("provider-confirm@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    return Survey.objects.create(provider=provider, title="Confirm", status=SurveyStatus.PUBLISHED)


def add_response(survey, flagged=False, excluded=False):
    """A response with no question answered; flagged means one failed attention check."""
    index = Response.objects.count()
    respondent = make_user(f"respondent-confirm-{index}@example.com", UserType.RESPONDENT)
    response = Response.objects.create(survey=survey, respondent=respondent, is_excluded=excluded)
    ResponseQuality.objects.create(
        response=response,
        survey=survey,
        timings=[],
        attention_total=1,
        attention_failed=1 if flagged else 0,
        rating_count=0,
        rating_all_same=False,
        device_hash="",
        signals_ok=True,
    )
    return response


def add_responses(survey, count, **kwargs):
    return [add_response(survey, **kwargs) for _ in range(count)]


def exclude_url(survey):
    return reverse("analysis:exclude_flagged", args=[survey.survey_id])


def include_url(survey):
    return reverse("analysis:include_all", args=[survey.survey_id])


def dashboard_url(survey):
    return reverse("analysis:analytics_dashboard", args=[survey.survey_id])


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def exclusion_states(survey):
    return list(
        Response.objects.filter(survey=survey).order_by("pk").values_list("is_excluded", flat=True)
    )


def get(client, user, url):
    client.force_login(user)
    return client.get(url)


def test_exclude_page_in_plural_changes_nothing(client, provider, survey):
    add_responses(survey, 3)
    add_responses(survey, 2, flagged=True)
    before = exclusion_states(survey)

    response = get(client, provider, exclude_url(survey))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Exclude 2 flagged responses?" in content
    assert (
        "They stay saved. The charts, the summaries and the export leave them out until "
        "you include them again."
    ) in content
    assert "Exclude 2 responses" in content
    assert 'class="btn btn-danger" type="submit"' in content
    assert f'href="{dashboard_url(survey)}">Cancel</a>' in content
    assert content.index(">Cancel</a>") < content.index("Exclude 2 responses")
    assert 'name="csrfmiddlewaretoken"' in content
    assert exclusion_states(survey) == before


def test_exclude_page_in_singular(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, flagged=True)

    content = get(client, provider, exclude_url(survey)).content.decode()

    assert "Exclude 1 flagged response?" in content
    assert (
        "It stays saved. The charts, the summaries and the export leave it out until you "
        "include it again."
    ) in content
    assert "Exclude 1 response<" in content.replace("\n", "").replace("  ", "")


def test_include_page_in_plural_and_singular(client, provider, survey):
    add_responses(survey, 4)
    excluded = add_response(survey, excluded=True)

    content = get(client, provider, include_url(survey)).content.decode()
    assert "Include all 5 responses?" in content
    assert "The 1 excluded response counts again in the charts, the summaries and the export." in content
    assert "Include all 5" in content
    assert 'class="btn btn-primary" type="submit"' in content

    Response.objects.filter(pk__in=[excluded.pk, Response.objects.first().pk]).update(
        is_excluded=True
    )
    before = exclusion_states(survey)
    content = get(client, provider, include_url(survey)).content.decode()
    assert "The 2 excluded responses count again in the charts, the summaries and the export." in content
    assert exclusion_states(survey) == before


@pytest.mark.parametrize("url_of", [exclude_url, include_url])
def test_get_redirects_without_a_message_while_locked(client, provider, survey, url_of):
    add_responses(survey, 4, flagged=True, excluded=True)

    response = get(client, provider, url_of(survey))

    assert response.status_code == 302
    assert response.url == dashboard_url(survey)
    assert messages_of(response) == []


@pytest.mark.parametrize("url_of", [exclude_url, include_url])
def test_get_redirects_without_a_message_when_there_is_nothing_to_do(
    client, provider, survey, url_of
):
    add_responses(survey, 5)

    response = get(client, provider, url_of(survey))

    assert response.status_code == 302
    assert response.url == dashboard_url(survey)
    assert messages_of(response) == []


@pytest.mark.parametrize("url_of", [exclude_url, include_url])
def test_a_non_owner_is_refused(client, survey, url_of):
    add_responses(survey, 5, flagged=True)
    other = make_user("other-confirm@example.com", UserType.SERVICE_PROVIDER)

    response = get(client, other, url_of(survey))

    assert response.status_code == 302
    assert response.url == reverse("surveys:provider_dashboard")
    assert messages_of(response) == ["Only the survey owner can view survey analytics."]


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize("url_of", [exclude_url, include_url])
def test_an_anonymous_user_goes_to_login(client, survey, url_of, method):
    response = getattr(client, method)(url_of(survey))

    assert response.status_code == 302
    assert response.url == reverse("users:login")


def test_post_exclude_excludes_only_the_flagged_included_responses(client, provider, survey):
    clean = add_responses(survey, 3)
    flagged = add_responses(survey, 2, flagged=True)
    already = add_response(survey, flagged=True, excluded=True)
    client.force_login(provider)

    response = client.post(exclude_url(survey))

    assert response.status_code == 302
    assert response.url == dashboard_url(survey)
    assert messages_of(response) == [
        "2 flagged responses are excluded. You can include them again at any time."
    ]
    states = dict(Response.objects.filter(survey=survey).values_list("pk", "is_excluded"))
    assert [states[r.pk] for r in clean] == [False, False, False]
    assert [states[r.pk] for r in flagged] == [True, True]
    assert states[already.pk] is True


def test_post_exclude_message_in_singular(client, provider, survey):
    add_responses(survey, 4)
    add_response(survey, flagged=True)
    client.force_login(provider)

    response = client.post(exclude_url(survey))

    assert messages_of(response) == [
        "1 flagged response is excluded. You can include it again at any time."
    ]


def test_post_exclude_shows_no_message_when_nothing_is_flagged(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    response = client.post(exclude_url(survey))

    assert response.url == dashboard_url(survey)
    assert messages_of(response) == []
    assert set(exclusion_states(survey)) == {False}


def test_post_include_includes_all(client, provider, survey):
    add_responses(survey, 3)
    add_responses(survey, 2, flagged=True, excluded=True)
    client.force_login(provider)

    response = client.post(include_url(survey))

    assert response.status_code == 302
    assert response.url == dashboard_url(survey)
    assert messages_of(response) == ["All 5 responses are included."]
    assert set(exclusion_states(survey)) == {False}


def test_post_while_locked_shows_the_service_message(client, provider, survey):
    add_responses(survey, 4, flagged=True)
    client.force_login(provider)

    response = client.post(exclude_url(survey))

    assert response.url == dashboard_url(survey)
    assert messages_of(response) == ["Results open at 5 responses."]
    assert set(exclusion_states(survey)) == {False}


@pytest.mark.parametrize("url_of", [exclude_url, include_url])
def test_a_post_without_the_csrf_token_is_refused(provider, survey, url_of):
    # Either POST would change a row: one flagged included response, one excluded response.
    add_responses(survey, 3)
    add_response(survey, flagged=True)
    add_response(survey, excluded=True)
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(provider)

    response = csrf_client.post(url_of(survey))

    assert response.status_code == 403
    assert exclusion_states(survey) == [False, False, False, False, True]


@pytest.mark.parametrize("url_of", [exclude_url, include_url])
def test_other_methods_are_refused(client, provider, survey, url_of):
    client.force_login(provider)

    assert client.put(url_of(survey)).status_code == 405


def test_the_respondent_home_card_is_in_sentence_case(client):
    respondent = make_user("respondent-home@example.com", UserType.RESPONDENT)
    client.force_login(respondent)

    content = client.get(reverse("home")).content.decode()

    assert "Answer surveys in the app" in content
    # The old title in title case; the whole phrase stays out of the code (acceptance grep).
    assert "Answer Surveys" not in content
