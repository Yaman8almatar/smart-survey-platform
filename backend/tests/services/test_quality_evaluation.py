"""FR-04 Part 2 (TASK-42): QualityService evaluates a survey and stores include or exclude."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    ResponseQuality,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import ResponseNotFound, SurveyNotFound, UnauthorizedAction, ValidationError
from services.quality_rules import (
    ATTENTION_FAILED,
    BANDS,
    BEFORE_CHECKS,
    EVALUATED,
    FLAG_CODES,
    SPEEDING,
)
from services.quality_service import QualityService
from services.response_service import ResponseService

pytestmark = pytest.mark.django_db

RESULT_KEYS = {
    "survey_id",
    "locked",
    "rules_version",
    "response_count",
    "included_count",
    "before_checks_count",
    "flag_counts",
    "not_checked_counts",
    "band_counts",
    "flagged_included_count",
    "responses",
}
ENTRY_KEYS = {
    "response_id",
    "submitted_at",
    "is_excluded",
    "status",
    "flags",
    "not_checked",
    "score",
    "band",
    "active_ms",
}
DEVICE_HASH = "d" * 64


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
    return make_user("provider-evaluation@example.com", UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    """Published open survey: one choice, two ratings."""
    survey = Survey.objects.create(provider=provider, title="Eval", status=SurveyStatus.PUBLISHED)
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
    return survey


def add_response(
    survey,
    active_ms=5_000,
    evidence=True,
    signals_ok=True,
    attention_total=0,
    attention_failed=0,
    device_hash="",
    excluded=False,
):
    """Store one response that answered every question, with or without evidence."""
    index = Response.objects.count()
    respondent = make_user(f"respondent-evaluation-{index}@example.com", UserType.RESPONDENT)
    response = Response.objects.create(survey=survey, respondent=respondent, is_excluded=excluded)
    questions = list(survey.questions.order_by("order_index"))
    for question in questions:
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            Answer.objects.create(
                response=response, question=question, selected_option=question.options.first()
            )
        else:
            Answer.objects.create(response=response, question=question, rating_value=3)
    if evidence:
        ResponseQuality.objects.create(
            response=response,
            survey=survey,
            timings=[{"question_id": q.question_id, "active_ms": active_ms} for q in questions],
            active_ms=active_ms * len(questions),
            attention_total=attention_total,
            attention_failed=attention_failed,
            rating_count=2,
            rating_all_same=True,
            device_hash=device_hash,
            signals_ok=signals_ok,
        )
    return response


def add_responses(survey, count, **kwargs):
    return [add_response(survey, **kwargs) for _ in range(count)]


def entry_of(result, response):
    return next(e for e in result["responses"] if e["response_id"] == response.response_id)


# --- evaluate_survey -----------------------------------------------------------------


def test_locked_state_reads_no_evidence(provider, survey):
    add_responses(survey, 4)

    with CaptureQueriesContext(connection) as captured:
        result = QualityService().evaluate_survey(provider, survey.survey_id)

    assert result == {
        "survey_id": survey.survey_id,
        "locked": True,
        "response_count": 4,
        "min_responses": 5,
    }
    sql = " ".join(query["sql"] for query in captured.captured_queries)
    assert len(captured.captured_queries) == 2
    assert '"response_quality"' not in sql
    assert '"answers"' not in sql


@pytest.mark.parametrize("count", [5, 25])
def test_evaluate_runs_four_queries_whatever_the_number_of_responses(
    provider, survey, count, django_assert_num_queries
):
    add_responses(survey, count)

    with django_assert_num_queries(4):
        result = QualityService().evaluate_survey(provider, survey.survey_id)

    assert len(result["responses"]) == count


def test_result_shape_and_no_forbidden_key_or_value(provider, survey):
    responses = add_responses(survey, 5, device_hash=DEVICE_HASH)

    result = QualityService().evaluate_survey(provider, survey.survey_id)

    assert set(result) == RESULT_KEYS
    assert result["locked"] is False
    assert result["rules_version"] == 1
    for entry in result["responses"]:
        assert set(entry) == ENTRY_KEYS
    text = str(result)
    assert DEVICE_HASH not in text
    assert "timings" not in text
    assert "respondent" not in text
    assert "snap_" not in text
    assert responses[0].respondent.email not in text


def test_counts_hold_every_code_and_band_with_zeros(provider, survey):
    add_responses(survey, 4)
    add_response(survey, attention_total=1, attention_failed=1)

    result = QualityService().evaluate_survey(provider, survey.survey_id)

    assert result["response_count"] == 5
    assert result["included_count"] == 5
    assert result["before_checks_count"] == 0
    assert set(result["flag_counts"]) == set(FLAG_CODES)
    assert result["flag_counts"][ATTENTION_FAILED] == 1
    assert result["flag_counts"][SPEEDING] == 0
    assert set(result["not_checked_counts"]) == set(FLAG_CODES)
    assert result["not_checked_counts"][ATTENTION_FAILED] == 4
    assert result["band_counts"] == {"CLEAN": 4, "CHECK": 1, "LOW": 0}
    assert set(result["band_counts"]) == set(BANDS)
    assert result["flagged_included_count"] == 1


def test_a_response_without_evidence_is_before_checks_and_listed_last(provider, survey):
    old = add_response(survey, evidence=False)
    low = add_response(survey, attention_total=2, attention_failed=2)
    add_responses(survey, 3)

    result = QualityService().evaluate_survey(provider, survey.survey_id)

    last = result["responses"][-1]
    assert last["response_id"] == old.response_id
    assert last["status"] == BEFORE_CHECKS
    assert last["flags"] == []
    assert last["score"] is None
    assert last["band"] is None
    assert last["active_ms"] is None
    assert result["before_checks_count"] == 1
    assert sum(result["band_counts"].values()) == 4
    assert result["responses"][0]["response_id"] == low.response_id
    assert result["responses"][0]["score"] == 20


def test_responses_are_sorted_by_score_then_id(provider, survey):
    clean = add_responses(survey, 3)
    check = add_response(survey, attention_total=1, attention_failed=1)
    missing = add_response(survey, signals_ok=False)

    result = QualityService().evaluate_survey(provider, survey.survey_id)

    ids = [entry["response_id"] for entry in result["responses"]]
    assert ids == [check.response_id, missing.response_id] + [r.response_id for r in clean]
    assert [entry["score"] for entry in result["responses"]] == [60, 70, 100, 100, 100]
    assert all(entry["status"] == EVALUATED for entry in result["responses"])


@pytest.mark.parametrize("method", ["evaluate_survey", "exclude_flagged", "include_all"])
def test_only_the_owner_may_evaluate_or_change(provider, survey, method):
    add_responses(survey, 5)
    other = make_user("other-evaluation@example.com", UserType.SERVICE_PROVIDER)
    respondent = make_user("respondent-not-owner@example.com", UserType.RESPONDENT)
    service = QualityService()

    with pytest.raises(UnauthorizedAction):
        getattr(service, method)(other, survey.survey_id)
    with pytest.raises(UnauthorizedAction):
        getattr(service, method)(respondent, survey.survey_id)
    with pytest.raises(SurveyNotFound):
        getattr(service, method)(provider, 999_999)


def test_only_the_owner_may_set_inclusion(provider, survey):
    responses = add_responses(survey, 5)
    other = make_user("other-inclusion@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        QualityService().set_inclusion(
            other, survey.survey_id, [responses[0].response_id], True
        )

    assert not Response.objects.filter(is_excluded=True).exists()


def test_excluding_responses_changes_no_verdict_and_no_median(provider, survey):
    # 20 responses with signals: 19 at 4,000 ms per question and one at 2,000 ms, so the
    # median is 4,000 and the fast one has an RSI of exactly 2.0.
    others = add_responses(survey, 19, active_ms=4_000)
    fast = add_response(survey, active_ms=2_000)
    service = QualityService()
    before = service.evaluate_survey(provider, survey.survey_id)
    assert entry_of(before, fast)["flags"] == [SPEEDING]

    service.set_inclusion(
        provider, survey.survey_id, [r.response_id for r in others[:10]] + [fast.response_id], True
    )
    after = service.evaluate_survey(provider, survey.survey_id)

    def verdicts(result):
        return [{k: v for k, v in e.items() if k != "is_excluded"} for e in result["responses"]]

    assert verdicts(after) == verdicts(before)
    assert after["flag_counts"] == before["flag_counts"]
    assert after["included_count"] == 9
    assert after["flagged_included_count"] == 0


# --- set_inclusion -------------------------------------------------------------------


def test_set_inclusion_sets_and_clears_excluded_at(provider, survey):
    responses = add_responses(survey, 5)
    target = responses[0]
    service = QualityService()

    changed = service.set_inclusion(
        provider, survey.survey_id, [target.response_id, target.response_id], True
    )
    target.refresh_from_db()
    assert changed == 1
    assert target.is_excluded is True
    assert target.excluded_at is not None
    first_excluded_at = target.excluded_at

    assert service.set_inclusion(provider, survey.survey_id, [target.response_id], True) == 0
    target.refresh_from_db()
    assert target.excluded_at == first_excluded_at

    assert service.set_inclusion(provider, survey.survey_id, [target.response_id], False) == 1
    target.refresh_from_db()
    assert target.is_excluded is False
    assert target.excluded_at is None


def test_set_inclusion_with_a_foreign_id_changes_nothing(provider, survey):
    responses = add_responses(survey, 5)
    other_survey = Survey.objects.create(provider=provider, title="Other")
    foreign = add_response(other_survey)

    with pytest.raises(ResponseNotFound):
        QualityService().set_inclusion(
            provider,
            survey.survey_id,
            [responses[0].response_id, foreign.response_id],
            True,
        )

    assert not Response.objects.filter(is_excluded=True).exists()


def test_set_inclusion_is_refused_while_results_are_locked(provider, survey):
    responses = add_responses(survey, 4)

    with pytest.raises(ValidationError, match="Results open at 5 responses."):
        QualityService().set_inclusion(
            provider, survey.survey_id, [responses[0].response_id], True
        )

    assert not Response.objects.filter(is_excluded=True).exists()


@pytest.mark.parametrize(
    "response_ids, excluded",
    [("1", True), ([1, "2"], True), ([True], True), ([1], "yes"), ([1], None)],
)
def test_set_inclusion_rejects_bad_input(provider, survey, response_ids, excluded):
    add_responses(survey, 5)

    with pytest.raises(ValidationError):
        QualityService().set_inclusion(provider, survey.survey_id, response_ids, excluded)


def test_set_inclusion_with_no_id_changes_nothing(provider, survey):
    add_responses(survey, 5)

    assert QualityService().set_inclusion(provider, survey.survey_id, [], True) == 0


# --- exclude_flagged and include_all -------------------------------------------------


def test_exclude_flagged_takes_only_flagged_and_included_responses(provider, survey):
    clean = add_responses(survey, 3)
    flagged = add_response(survey, attention_total=1, attention_failed=1)
    flagged_excluded = add_response(survey, signals_ok=False)
    service = QualityService()
    service.set_inclusion(provider, survey.survey_id, [flagged_excluded.response_id], True)
    flagged_excluded.refresh_from_db()
    first_excluded_at = flagged_excluded.excluded_at

    changed = service.exclude_flagged(provider, survey.survey_id)

    assert changed == 1
    excluded_ids = set(
        Response.objects.filter(is_excluded=True).values_list("response_id", flat=True)
    )
    assert excluded_ids == {flagged.response_id, flagged_excluded.response_id}
    flagged_excluded.refresh_from_db()
    assert flagged_excluded.excluded_at == first_excluded_at
    assert all(not Response.objects.get(pk=r.pk).is_excluded for r in clean)


def test_exclude_flagged_is_refused_while_results_are_locked(provider, survey):
    add_response(survey, attention_total=1, attention_failed=1)

    with pytest.raises(ValidationError, match="Results open at 5 responses."):
        QualityService().exclude_flagged(provider, survey.survey_id)


def test_include_all_includes_every_excluded_response(provider, survey):
    responses = add_responses(survey, 5)
    service = QualityService()
    service.set_inclusion(
        provider, survey.survey_id, [r.response_id for r in responses[:3]], True
    )

    assert service.include_all(provider, survey.survey_id) == 3
    assert not Response.objects.filter(is_excluded=True).exists()
    assert not Response.objects.filter(excluded_at__isnull=False).exists()
    assert service.include_all(provider, survey.survey_id) == 0


# --- nothing is excluded automatically -----------------------------------------------


class FakeAnalysisService:
    def queue_open_text_answers(self, answers):
        pass


def test_a_submit_leaves_is_excluded_false_even_when_flagged(provider, survey):
    respondent = make_user("respondent-flagged-submit@example.com", UserType.RESPONDENT)
    RespondentProfile.objects.create(
        user=respondent,
        age=30,
        gender=Gender.FEMALE,
        region="DAMASCUS",
        interests=["TECHNOLOGY"],
        education="BACHELOR",
        occupation="STUDENT",
        marital_status="SINGLE",
    )
    choice, first_rating, second_rating = survey.questions.order_by("order_index")
    Question.objects.filter(pk=choice.pk).update(
        is_attention_check=True, expected_option=choice.options.order_by("order_index").last()
    )
    add_responses(survey, 4)

    response = ResponseService(analysis_service=FakeAnalysisService()).submit_response(
        respondent,
        survey.survey_id,
        [
            {
                "question_id": choice.question_id,
                "selected_option_id": choice.options.order_by("order_index").first().option_id,
            },
            {"question_id": first_rating.question_id, "rating_value": 4},
            {"question_id": second_rating.question_id, "rating_value": 4},
        ],
    )

    response.refresh_from_db()
    assert response.is_excluded is False
    assert response.excluded_at is None
    result = QualityService().evaluate_survey(provider, survey.survey_id)
    assert ATTENTION_FAILED in entry_of(result, response)["flags"]
    assert result["flagged_included_count"] >= 1
