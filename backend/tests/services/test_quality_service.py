"""FR-04 Part 1 (TASK-41): evidence and profile snapshot stored at submit; facts only."""

import hashlib
import hmac
from datetime import timedelta

import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.core.models import (
    Question,
    QuestionOption,
    RespondentProfile,
    ResponseDraft,
    ResponseQuality,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import QuestionNotFound, ValidationError
from services.profile_service import ProfileService
from services.quality_service import QualityService
from services.response_service import ResponseService

pytestmark = pytest.mark.django_db

DEVICE = "device-id-0123456789abcdef"
OTHER_DEVICE = "device-id-fedcba9876543210"


class FakeAnalysisService:
    def queue_open_text_answers(self, answers):
        pass


@pytest.fixture
def service():
    return ResponseService(analysis_service=FakeAnalysisService())


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def respondent():
    user = make_user("respondent-quality@example.com", UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=user,
        age=30,
        gender=Gender.FEMALE,
        region="DAMASCUS",
        interests=["TECHNOLOGY", "SPORTS"],
        education="BACHELOR",
        occupation="STUDENT",
        marital_status="SINGLE",
    )
    return user


@pytest.fixture
def survey():
    """Published open survey: a choice, two ratings and an optional open text."""
    provider = make_user("provider-quality@example.com", UserType.SERVICE_PROVIDER)
    survey = Survey.objects.create(
        provider=provider, title="Quality", status=SurveyStatus.PUBLISHED
    )
    TargetingCriteria.objects.create(survey=survey, regions=[], gender=None)
    choice = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order_index=0,
    )
    QuestionOption.objects.create(question=choice, option_text="A", order_index=0)
    QuestionOption.objects.create(question=choice, option_text="B", order_index=1)
    for index in (1, 2):
        Question.objects.create(
            survey=survey,
            question_text=f"Rate {index}",
            question_type=QuestionType.RATING_SCALE,
            order_index=index,
        )
    Question.objects.create(
        survey=survey,
        question_text="Comments",
        question_type=QuestionType.OPEN_TEXT,
        is_required=False,
        order_index=3,
    )
    return survey


def questions(survey):
    return list(survey.questions.order_by("order_index"))


def options(question):
    return list(question.options.order_by("order_index"))


def answers(survey, option_index=0, ratings=(4, 4)):
    choice, first_rating, second_rating, _ = questions(survey)
    return [
        {
            "question_id": choice.question_id,
            "selected_option_id": options(choice)[option_index].option_id,
        },
        {"question_id": first_rating.question_id, "rating_value": ratings[0]},
        {"question_id": second_rating.question_id, "rating_value": ratings[1]},
    ]


def timings(survey, active_ms=1000):
    return [{"question_id": q.question_id, "active_ms": active_ms} for q in questions(survey)]


def quality_of(response):
    return ResponseQuality.objects.get(response=response)


def keyed_hash(device_id):
    return hmac.new(
        settings.DEVICE_HASH_KEY.encode(), device_id.encode(), hashlib.sha256
    ).hexdigest()


def test_submit_stores_its_own_timings_and_the_device_hash(service, respondent, survey):
    service.save_draft(respondent, survey.survey_id, [], timings=timings(survey, 500))

    response = service.submit_response(
        respondent,
        survey.survey_id,
        answers(survey),
        timings=timings(survey, 1000),
        device_id=DEVICE,
    )

    quality = quality_of(response)
    assert quality.survey_id == survey.survey_id
    assert quality.timings == timings(survey, 1000)
    assert quality.active_ms == 4000
    assert quality.device_hash == keyed_hash(DEVICE)
    assert quality.signals_ok is True


def test_submit_without_timings_uses_the_draft_timings(service, respondent, survey):
    service.save_draft(respondent, survey.survey_id, [], timings=timings(survey, 500))

    response = service.submit_response(
        respondent, survey.survey_id, answers(survey), device_id=DEVICE
    )

    quality = quality_of(response)
    assert quality.timings == timings(survey, 500)
    assert quality.active_ms == 2000
    assert quality.signals_ok is True


def test_draft_timings_are_replaced_when_sent_and_kept_when_not(service, respondent, survey):
    service.save_draft(respondent, survey.survey_id, [], timings=timings(survey, 500))
    service.save_draft(respondent, survey.survey_id, [], timings=timings(survey, 900))

    draft = service.save_draft(respondent, survey.survey_id, [])

    assert draft.timings == timings(survey, 900)
    assert ResponseDraft.objects.get(draft_id=draft.draft_id).timings == timings(survey, 900)


@pytest.mark.parametrize("active_ms, signals_ok", [(29_000, True), (31_000, False)])
def test_active_time_is_checked_against_wall_time_plus_10_seconds(
    service, respondent, survey, active_ms, signals_ok
):
    service.save_draft(respondent, survey.survey_id, [])
    ResponseDraft.objects.filter(survey=survey).update(
        started_at=timezone.now() - timedelta(seconds=20)
    )
    first = questions(survey)[0]

    response = service.submit_response(
        respondent,
        survey.survey_id,
        answers(survey),
        timings=[{"question_id": first.question_id, "active_ms": active_ms}],
        device_id=DEVICE,
    )

    assert response.response_id is not None
    assert quality_of(response).signals_ok is signals_ok


def test_missing_timings_set_signals_ok_false(service, respondent, survey):
    service.save_draft(respondent, survey.survey_id, [])

    response = service.submit_response(
        respondent, survey.survey_id, answers(survey), device_id=DEVICE
    )

    quality = quality_of(response)
    assert quality.timings == []
    assert quality.active_ms is None
    assert quality.signals_ok is False


def test_missing_device_id_sets_signals_ok_false(service, respondent, survey):
    service.save_draft(respondent, survey.survey_id, [], timings=timings(survey))

    response = service.submit_response(respondent, survey.survey_id, answers(survey))

    quality = quality_of(response)
    assert quality.device_hash == ""
    assert quality.signals_ok is False


def test_missing_draft_sets_signals_ok_false(service, respondent, survey):
    response = service.submit_response(
        respondent,
        survey.survey_id,
        answers(survey),
        timings=timings(survey),
        device_id=DEVICE,
    )

    assert response.started_at is None
    assert quality_of(response).signals_ok is False


def test_device_hash_is_stable_for_one_id_and_differs_between_ids():
    quality_service = QualityService()

    first = quality_service.hash_device_id(DEVICE)

    assert first == quality_service.hash_device_id(DEVICE)
    assert first != quality_service.hash_device_id(OTHER_DEVICE)
    assert len(first) == 64
    assert quality_service.hash_device_id(None) == ""


def test_raw_device_id_is_in_no_column_of_response_quality(service, respondent, survey):
    service.submit_response(
        respondent,
        survey.survey_id,
        answers(survey),
        timings=timings(survey),
        device_id=DEVICE,
    )

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM response_quality")
        rows = cursor.fetchall()

    assert len(rows) == 1
    assert all(DEVICE not in str(value) for value in rows[0])


@pytest.mark.parametrize(
    "option_index, rating, failed",
    [(0, 5, 0), (1, 5, 1), (0, 3, 1), (1, 3, 2)],
)
def test_attention_counts_compare_with_the_expected_option_and_rating(
    service, respondent, survey, option_index, rating, failed
):
    choice, first_rating, _, _ = questions(survey)
    Question.objects.filter(pk=choice.pk).update(
        is_attention_check=True, expected_option=options(choice)[0]
    )
    Question.objects.filter(pk=first_rating.pk).update(
        is_attention_check=True, expected_rating=5
    )

    response = service.submit_response(
        respondent,
        survey.survey_id,
        answers(survey, option_index=option_index, ratings=(rating, 4)),
    )

    quality = quality_of(response)
    assert quality.attention_total == 2
    assert quality.attention_failed == failed


def test_attention_question_without_expected_answer_is_not_counted(
    service, respondent, survey
):
    choice = questions(survey)[0]
    Question.objects.filter(pk=choice.pk).update(is_attention_check=True)

    response = service.submit_response(respondent, survey.survey_id, answers(survey))

    quality = quality_of(response)
    assert quality.attention_total == 0
    assert quality.attention_failed == 0


@pytest.mark.parametrize(
    "ratings, rating_all_same",
    [((4, 4), True), ((4, 5), False)],
)
def test_rating_facts_count_answered_ratings(
    service, respondent, survey, ratings, rating_all_same
):
    response = service.submit_response(
        respondent, survey.survey_id, answers(survey, ratings=ratings)
    )

    quality = quality_of(response)
    assert quality.rating_count == 2
    assert quality.rating_all_same is rating_all_same


def test_rating_facts_leave_an_attention_rating_out(service, respondent, survey):
    first_rating = questions(survey)[1]
    Question.objects.filter(pk=first_rating.pk).update(
        is_attention_check=True, expected_rating=5
    )

    response = service.submit_response(
        respondent, survey.survey_id, answers(survey, ratings=(5, 4))
    )

    quality = quality_of(response)
    assert quality.rating_count == 1
    assert quality.rating_all_same is True


def test_snapshot_is_copied_and_unchanged_after_a_profile_edit(service, respondent, survey):
    response = service.submit_response(respondent, survey.survey_id, answers(survey))

    ProfileService().update_profile(respondent, 45, Gender.FEMALE, "HOMS", ["HEALTH"])
    response.refresh_from_db()

    assert response.snap_age == 30
    assert response.snap_gender == Gender.FEMALE
    assert response.snap_region == "DAMASCUS"
    assert response.snap_education == "BACHELOR"
    assert response.snap_occupation == "STUDENT"
    assert response.snap_marital_status == "SINGLE"
    assert response.snap_interests == ["TECHNOLOGY", "SPORTS"]


@pytest.mark.parametrize(
    "bad_timings",
    [
        "not a list",
        ["not a dict"],
        [{"question_id": 1}],
        [{"question_id": "1", "active_ms": 10}],
        [{"question_id": 1, "active_ms": -1}],
        [{"question_id": 1, "active_ms": 3_600_001}],
        [{"question_id": 1, "active_ms": 10}, {"question_id": 1, "active_ms": 20}],
    ],
)
def test_clean_timings_rejects_malformed_out_of_range_and_repeated_entries(bad_timings):
    with pytest.raises(ValidationError):
        QualityService().clean_timings(bad_timings, {1, 2})


def test_clean_timings_rejects_a_question_outside_the_survey():
    with pytest.raises(QuestionNotFound):
        QualityService().clean_timings([{"question_id": 9, "active_ms": 10}], {1, 2})


def test_clean_timings_accepts_the_range_ends():
    entries = [{"question_id": 1, "active_ms": 0}, {"question_id": 2, "active_ms": 3_600_000}]

    assert QualityService().clean_timings(entries, {1, 2}) == entries


@pytest.mark.parametrize(
    "bad_id", ["short-id", "x" * 65, "has space in it 1234", "bad*chars*0123456789"]
)
def test_clean_device_id_rejects_a_bad_format_without_repeating_it(bad_id):
    with pytest.raises(ValidationError) as error:
        QualityService().clean_device_id(bad_id)

    assert bad_id not in str(error.value)
