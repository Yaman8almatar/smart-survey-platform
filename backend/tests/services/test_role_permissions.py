"""FR-15 Part A: every public service method that acts for a user refuses the wrong role.

MATRIX lists, for each such method, the one role that may call it and the arguments of a
call. test_wrong_role_is_refused_and_changes_nothing calls it with each of the two other
roles. test_every_user_method_is_in_the_matrix fails when a method is added to a service
class without a row (or an entry in EXCEPTIONS), and when a row names a method that is gone.
"""

import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.core.models import (
    Answer,
    Question,
    QuestionOption,
    RespondentProfile,
    Response,
    ResponseDraft,
    Survey,
    TargetingCriteria,
    User,
)
from core.enums import AccountStatus, Gender, QuestionType, SurveyStatus, UserType
from core.exceptions import UnauthorizedAction
from services.admin_service import AdminService
from services.analysis_service import AnalysisService
from services.profile_service import ProfileService
from services.quality_service import QualityService
from services.question_service import QuestionService
from services.response_review_service import ResponseReviewService
from services.response_service import ResponseService
from services.survey_review_service import SurveyReviewService
from services.survey_service import SurveyService
from services.targeting_service import TargetingService

pytestmark = pytest.mark.django_db

SERVICES_DIR = Path(__file__).resolve().parents[2] / "services"

RESPONDENT = UserType.RESPONDENT
PROVIDER = UserType.SERVICE_PROVIDER
ADMIN = UserType.ADMIN
ROLES = (RESPONDENT, PROVIDER, ADMIN)

SERVICES = {
    service.__name__: service
    for service in (
        AdminService,
        AnalysisService,
        ProfileService,
        QualityService,
        QuestionService,
        ResponseReviewService,
        ResponseService,
        SurveyReviewService,
        SurveyService,
        TargetingService,
    )
}

# "Class.method": (role that may call it, w -> arguments after the user).
# w.draft and w.published are survey ids of one provider; w.draft_question a question id
# of the draft survey; w.published_option an option id of the published survey's question.
MATRIX = {
    "AdminService.activate_account": (ADMIN, lambda w: (w.respondent.user_id,)),
    "AdminService.suspend_account": (ADMIN, lambda w: (w.respondent.user_id,)),
    "AdminService.delete_account": (ADMIN, lambda w: (w.respondent.user_id,)),
    "AdminService.list_users": (ADMIN, lambda w: ()),
    "AdminService.list_user_management_items": (ADMIN, lambda w: ()),
    "AdminService.generate_system_report": (
        ADMIN,
        lambda w: (date(2026, 1, 1), date(2026, 12, 31)),
    ),
    "AnalysisService.retry_failed": (PROVIDER, lambda w: (w.published,)),
    "AnalysisService.get_survey_results": (PROVIDER, lambda w: (w.published,)),
    "ProfileService.get_profile": (RESPONDENT, lambda w: ()),
    "ProfileService.update_profile": (
        RESPONDENT,
        lambda w: (31, Gender.FEMALE, "DAMASCUS", ["SPORTS"]),
    ),
    "QualityService.evaluate_survey": (PROVIDER, lambda w: (w.published,)),
    "QualityService.set_inclusion": (PROVIDER, lambda w: (w.published, [], True)),
    "QualityService.exclude_flagged": (PROVIDER, lambda w: (w.published,)),
    "QualityService.include_all": (PROVIDER, lambda w: (w.published,)),
    "QualityService.set_response_inclusion": (PROVIDER, lambda w: (w.published, 1, True)),
    "QuestionService.add_question": (
        PROVIDER,
        lambda w: (w.draft, "New question", QuestionType.OPEN_TEXT, False, 5),
    ),
    "QuestionService.add_question_with_options": (
        PROVIDER,
        lambda w: (w.draft, "New choice", QuestionType.MULTIPLE_CHOICE, False, 5, ["X", "Y"]),
    ),
    "QuestionService.add_question_options": (PROVIDER, lambda w: (w.draft_question, ["C"])),
    "QuestionService.update_question": (
        PROVIDER,
        lambda w: (w.draft_question, "Renamed", False, 0),
    ),
    "QuestionService.delete_question": (PROVIDER, lambda w: (w.draft_question,)),
    "QuestionService.get_response_form_questions": (RESPONDENT, lambda w: (w.published,)),
    "QuestionService.get_response_form": (RESPONDENT, lambda w: (w.published,)),
    "QuestionService.get_survey_question_rows": (PROVIDER, lambda w: (w.draft,)),
    "QuestionService.get_review_question_rows": (ADMIN, lambda w: (w.draft,)),
    "ResponseReviewService.list_responses": (PROVIDER, lambda w: (w.published,)),
    "ResponseReviewService.get_response": (PROVIDER, lambda w: (w.published, 1)),
    "ResponseReviewService.export_responses": (PROVIDER, lambda w: (w.published,)),
    "ResponseService.ensure_can_answer": (RESPONDENT, lambda w: (w.published,)),
    "ResponseService.submit_response": (RESPONDENT, lambda w: (w.published, w.answers)),
    "ResponseService.get_draft": (RESPONDENT, lambda w: (w.published,)),
    "ResponseService.save_draft": (RESPONDENT, lambda w: (w.published, w.answers)),
    "ResponseService.delete_draft": (RESPONDENT, lambda w: (w.published,)),
    "ResponseService.get_answered_surveys": (RESPONDENT, lambda w: ()),
    "SurveyReviewService.count_pending": (ADMIN, lambda w: ()),
    "SurveyReviewService.list_pending": (ADMIN, lambda w: ()),
    "SurveyReviewService.get_review": (ADMIN, lambda w: (w.draft,)),
    "SurveyReviewService.approve": (ADMIN, lambda w: (w.draft,)),
    "SurveyReviewService.reject": (ADMIN, lambda w: (w.draft, "Needs work")),
    "SurveyService.create_survey": (PROVIDER, lambda w: ("New survey", "About it")),
    "SurveyService.update_survey": (PROVIDER, lambda w: (w.draft, "Renamed", "About it")),
    "SurveyService.delete_survey": (PROVIDER, lambda w: (w.draft,)),
    "SurveyService.submit_for_review": (PROVIDER, lambda w: (w.draft,)),
    "SurveyService.get_publish_preview": (PROVIDER, lambda w: (w.draft,)),
    "SurveyService.close_survey": (PROVIDER, lambda w: (w.published,)),
    "SurveyService.pause_survey": (PROVIDER, lambda w: (w.published,)),
    "SurveyService.resume_survey": (PROVIDER, lambda w: (w.published,)),
    "SurveyService.list_provider_surveys": (PROVIDER, lambda w: ()),
    "SurveyService.get_provider_survey": (PROVIDER, lambda w: (w.published,)),
    "SurveyService.list_provider_survey_items": (PROVIDER, lambda w: ()),
    "SurveyService.get_eligible_survey_items": (RESPONDENT, lambda w: ()),
    "TargetingService.save_criteria": (PROVIDER, lambda w: (w.draft,)),
    "TargetingService.reach": (PROVIDER, lambda w: (w.draft,)),
    "TargetingService.get_criteria_initial": (PROVIDER, lambda w: (w.draft,)),
}

# Methods that take a user but act on nothing for it; each has its own test below.
EXCEPTIONS = {
    "TargetingService.match_respondent_to_survey": (
        "Answers whether a profile matches a survey; returns False for any account that is "
        "not a respondent, and acts on nothing."
    ),
    "ResponseService.validate_duplicate_response": (
        "Reads whether the given user has a response; called only from ensure_can_answer, "
        "after its role check."
    ),
}

COUNTED_MODELS = (
    User,
    Survey,
    Question,
    QuestionOption,
    TargetingCriteria,
    Response,
    Answer,
    ResponseDraft,
)

WRONG_ROLE_CALLS = [
    pytest.param(name, role, id=f"{name}-as-{role}")
    for name, (allowed, _) in MATRIX.items()
    for role in ROLES
    if role != allowed
]


def _make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=AccountStatus.ACTIVE,
    )


def _make_survey(provider, status):
    survey = Survey.objects.create(
        provider=provider,
        title=f"{status} survey",
        description="About campus life",
        status=status,
    )
    TargetingCriteria.objects.create(survey=survey, regions=[])
    question = Question.objects.create(
        survey=survey,
        question_text="Pick one",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_required=True,
        order_index=0,
    )
    option = QuestionOption.objects.create(question=question, option_text="A", order_index=0)
    return survey, question, option


@pytest.fixture
def world():
    """One user per role, and a draft and a published survey of the provider, a question each."""
    respondent = _make_user("respondent@example.com", RESPONDENT)
    RespondentProfile.objects.create(
        user=respondent,
        age=30,
        gender=Gender.MALE,
        region="DAMASCUS",
        interests=["SPORTS"],
    )
    provider = _make_user("provider@example.com", PROVIDER)
    admin = _make_user("admin@example.com", ADMIN)
    draft, draft_question, _ = _make_survey(provider, SurveyStatus.DRAFT)
    published, published_question, published_option = _make_survey(
        provider, SurveyStatus.PUBLISHED
    )
    return SimpleNamespace(
        users={RESPONDENT: respondent, PROVIDER: provider, ADMIN: admin},
        respondent=respondent,
        provider=provider,
        draft=draft.survey_id,
        draft_question=draft_question.question_id,
        published=published.survey_id,
        answers=[
            {
                "question_id": published_question.question_id,
                "selected_option_id": published_option.option_id,
            }
        ],
    )


def _row_counts():
    return {model.__name__: model.objects.count() for model in COUNTED_MODELS}


def _call(name, user, args):
    class_name, method_name = name.split(".")
    return getattr(SERVICES[class_name](), method_name)(user, *args)


@pytest.mark.parametrize(("name", "role"), WRONG_ROLE_CALLS)
def test_wrong_role_is_refused_and_changes_nothing(world, name, role):
    _, build_args = MATRIX[name]
    before = _row_counts()

    with pytest.raises(UnauthorizedAction):
        _call(name, world.users[role], build_args(world))

    assert _row_counts() == before


def test_match_respondent_to_survey_is_false_for_other_roles(world):
    service = TargetingService()

    assert service.match_respondent_to_survey(world.respondent, world.published) is True
    assert service.match_respondent_to_survey(world.users[PROVIDER], world.published) is False
    assert service.match_respondent_to_survey(world.users[ADMIN], world.published) is False


def test_validate_duplicate_response_is_reached_only_after_the_role_check(world):
    service = ResponseService()
    Response.objects.create(survey_id=world.published, respondent=world.respondent)

    assert service.validate_duplicate_response(world.respondent, world.published) is True
    assert service.validate_duplicate_response(world.provider, world.published) is False

    with patch.object(ResponseService, "validate_duplicate_response") as duplicate_check:
        for role in (PROVIDER, ADMIN):
            with pytest.raises(UnauthorizedAction):
                service.ensure_can_answer(world.users[role], world.published)
    duplicate_check.assert_not_called()


def _user_methods_in_services():
    """Return "Class.method" for each public method of a service class that takes a user."""
    found = set()
    for path in sorted(SERVICES_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if item.name.startswith("_"):
                    continue
                arguments = item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                if any(a.arg == "user" or a.arg.endswith("_user") for a in arguments):
                    found.add(f"{node.name}.{item.name}")
    return found


def test_every_user_method_is_in_the_matrix():
    found = _user_methods_in_services()
    listed = set(MATRIX) | set(EXCEPTIONS)

    missing = sorted(found - listed)
    stale = sorted(listed - found)

    assert not missing, f"Add a MATRIX row (or an EXCEPTIONS entry) for: {', '.join(missing)}"
    assert not stale, f"These rows name methods that no longer exist: {', '.join(stale)}"
    assert not set(MATRIX) & set(EXCEPTIONS)
