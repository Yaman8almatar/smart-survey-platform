"""FR-04 Part 2 (TASK-42): no flag, score or band ever reaches a respondent."""

import pytest

from apps.core.models import Question

pytestmark = pytest.mark.django_db

FORBIDDEN_KEYS = {
    "flag",
    "flags",
    "not_checked",
    "score",
    "band",
    "quality",
    "is_excluded",
    "excluded_at",
    "rules_version",
}


def keys_of(value):
    """Return every dictionary key anywhere in a JSON value."""
    if isinstance(value, dict):
        found = set(value)
        for item in value.values():
            found |= keys_of(item)
        return found
    if isinstance(value, list):
        found = set()
        for item in value:
            found |= keys_of(item)
        return found
    return set()


def test_survey_detail_and_submit_body_hold_no_quality_key(
    client, authenticate, respondent, survey
):
    choice, rating, _ = survey.questions.order_by("order_index")
    expected, given = choice.options.order_by("order_index")
    Question.objects.filter(pk=choice.pk).update(is_attention_check=True, expected_option=expected)
    authenticate(respondent)

    detail = client.get(f"/api/v1/surveys/{survey.survey_id}/")
    submitted = client.post(
        f"/api/v1/surveys/{survey.survey_id}/responses/",
        {
            # A failed attention check: the response is flagged on read, never in the body.
            "answers": [
                {"question_id": choice.question_id, "selected_option_id": given.option_id},
                {"question_id": rating.question_id, "rating_value": 4},
            ]
        },
        format="json",
    )

    assert detail.status_code == 200
    assert submitted.status_code == 201
    assert keys_of(detail.json()) & FORBIDDEN_KEYS == set()
    assert keys_of(submitted.json()) & FORBIDDEN_KEYS == set()
