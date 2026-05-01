from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.core.models import Response, Survey, User
from core.enums import AccountStatus, SurveyStatus, UserType
from core.exceptions import AccountNotFound, UnauthorizedAction, ValidationError
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from services.admin_service import AdminService


@pytest.fixture
def admin_service():
    return AdminService()


def create_user(email, user_type, account_status=AccountStatus.ACTIVE):
    return User.objects.create_user(
        email=email,
        password="strong-password",
        name="Test User",
        user_type=user_type,
        account_status=account_status,
    )


def create_survey(provider, status=SurveyStatus.DRAFT, title="Survey"):
    survey = SurveyRepository().save(
        Survey(provider=provider, title=title, description="Description")
    )

    if status == SurveyStatus.PUBLISHED:
        survey.publish()
        SurveyRepository().update(survey)
    elif status == SurveyStatus.CLOSED:
        survey.close()
        SurveyRepository().update(survey)

    return survey


def create_response(survey, respondent_email):
    respondent = create_user(respondent_email, UserType.RESPONDENT)
    return ResponseRepository().save(Response(survey=survey, respondent=respondent))


def current_report_range():
    today = timezone.now().date()
    return today - timedelta(days=1), today + timedelta(days=1)


def user_management_item(admin_service, admin, user):
    return next(
        item
        for item in admin_service.list_user_management_items(admin)
        if item["user"].user_id == user.user_id
    )


@pytest.mark.django_db
def test_admin_can_activate_account(admin_service):
    admin = create_user("admin-activate@example.com", UserType.ADMIN)
    user = create_user(
        "user-activate@example.com",
        UserType.RESPONDENT,
        account_status=AccountStatus.SUSPENDED,
    )

    updated = admin_service.activate_account(admin, user.user_id)

    assert updated.account_status == AccountStatus.ACTIVE


@pytest.mark.django_db
def test_admin_can_suspend_another_user(admin_service):
    admin = create_user("admin-suspend@example.com", UserType.ADMIN)
    user = create_user("user-suspend@example.com", UserType.RESPONDENT)

    updated = admin_service.suspend_account(admin, user.user_id)

    assert updated.account_status == AccountStatus.SUSPENDED


@pytest.mark.django_db
def test_admin_can_soft_delete_another_user(admin_service):
    admin = create_user("admin-delete@example.com", UserType.ADMIN)
    user = create_user("user-delete@example.com", UserType.RESPONDENT)

    updated = admin_service.delete_account(admin, user.user_id)

    assert updated.account_status == AccountStatus.DELETED
    assert User.objects.filter(user_id=user.user_id).exists()


@pytest.mark.django_db
def test_admin_cannot_suspend_own_account(admin_service):
    admin = create_user("admin-self-suspend@example.com", UserType.ADMIN)

    with pytest.raises(UnauthorizedAction):
        admin_service.suspend_account(admin, admin.user_id)

    admin.refresh_from_db()
    assert admin.account_status == AccountStatus.ACTIVE


@pytest.mark.django_db
def test_admin_cannot_soft_delete_own_account(admin_service):
    admin = create_user("admin-self-delete@example.com", UserType.ADMIN)

    with pytest.raises(UnauthorizedAction):
        admin_service.delete_account(admin, admin.user_id)

    admin.refresh_from_db()
    assert admin.account_status == AccountStatus.ACTIVE


@pytest.mark.django_db
def test_non_admin_cannot_activate_account(admin_service):
    provider = create_user("provider-activate@example.com", UserType.SERVICE_PROVIDER)
    user = create_user("user-non-admin-activate@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction):
        admin_service.activate_account(provider, user.user_id)


@pytest.mark.django_db
def test_non_admin_cannot_suspend_account(admin_service):
    provider = create_user("provider-suspend@example.com", UserType.SERVICE_PROVIDER)
    user = create_user("user-non-admin-suspend@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction):
        admin_service.suspend_account(provider, user.user_id)


@pytest.mark.django_db
def test_non_admin_cannot_delete_account(admin_service):
    provider = create_user("provider-delete@example.com", UserType.SERVICE_PROVIDER)
    user = create_user("user-non-admin-delete@example.com", UserType.RESPONDENT)

    with pytest.raises(UnauthorizedAction):
        admin_service.delete_account(provider, user.user_id)


@pytest.mark.django_db
def test_admin_can_list_users(admin_service):
    admin = create_user("admin-list-users@example.com", UserType.ADMIN)
    provider = create_user("provider-list-users@example.com", UserType.SERVICE_PROVIDER)

    users = admin_service.list_users(admin)

    assert list(users.order_by("email")) == [admin, provider]


@pytest.mark.django_db
def test_non_admin_cannot_list_users(admin_service):
    provider = create_user("provider-cannot-list@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        admin_service.list_users(provider)


@pytest.mark.django_db
def test_active_user_management_action_flags_are_correct(admin_service):
    admin = create_user("admin-active-flags@example.com", UserType.ADMIN)
    user = create_user(
        "user-active-flags@example.com",
        UserType.RESPONDENT,
        account_status=AccountStatus.ACTIVE,
    )

    item = user_management_item(admin_service, admin, user)

    assert item["is_self"] is False
    assert item["can_activate"] is False
    assert item["can_suspend"] is True
    assert item["can_delete"] is True


@pytest.mark.django_db
def test_suspended_user_management_action_flags_are_correct(admin_service):
    admin = create_user("admin-suspended-flags@example.com", UserType.ADMIN)
    user = create_user(
        "user-suspended-flags@example.com",
        UserType.RESPONDENT,
        account_status=AccountStatus.SUSPENDED,
    )

    item = user_management_item(admin_service, admin, user)

    assert item["is_self"] is False
    assert item["can_activate"] is True
    assert item["can_suspend"] is False
    assert item["can_delete"] is True


@pytest.mark.django_db
def test_deleted_user_management_action_flags_are_correct(admin_service):
    admin = create_user("admin-deleted-flags@example.com", UserType.ADMIN)
    user = create_user(
        "user-deleted-flags@example.com",
        UserType.RESPONDENT,
        account_status=AccountStatus.DELETED,
    )

    item = user_management_item(admin_service, admin, user)

    assert item["is_self"] is False
    assert item["can_activate"] is True
    assert item["can_suspend"] is False
    assert item["can_delete"] is False


@pytest.mark.django_db
def test_current_admin_cannot_suspend_self_in_management_flags(admin_service):
    admin = create_user("admin-self-suspend-flags@example.com", UserType.ADMIN)

    item = user_management_item(admin_service, admin, admin)

    assert item["is_self"] is True
    assert item["can_suspend"] is False


@pytest.mark.django_db
def test_current_admin_cannot_delete_self_in_management_flags(admin_service):
    admin = create_user("admin-self-delete-flags@example.com", UserType.ADMIN)

    item = user_management_item(admin_service, admin, admin)

    assert item["is_self"] is True
    assert item["can_delete"] is False


@pytest.mark.django_db
def test_non_admin_cannot_list_user_management_items(admin_service):
    provider = create_user(
        "provider-cannot-list-management@example.com",
        UserType.SERVICE_PROVIDER,
    )

    with pytest.raises(UnauthorizedAction):
        admin_service.list_user_management_items(provider)


@pytest.mark.django_db
def test_missing_account_raises_account_not_found(admin_service):
    admin = create_user("admin-missing@example.com", UserType.ADMIN)

    with pytest.raises(AccountNotFound):
        admin_service.activate_account(admin, 999999)


@pytest.mark.django_db
def test_generate_system_report_works_for_admin(admin_service):
    admin = create_user("admin-report@example.com", UserType.ADMIN)

    report = admin_service.generate_system_report(
        admin,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert isinstance(report, dict)


@pytest.mark.django_db
def test_generate_system_report_rejects_non_admin_user(admin_service):
    provider = create_user("provider-report@example.com", UserType.SERVICE_PROVIDER)

    with pytest.raises(UnauthorizedAction):
        admin_service.generate_system_report(
            provider,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )


@pytest.mark.django_db
def test_generate_system_report_rejects_invalid_date_range(admin_service):
    admin = create_user("admin-invalid-report@example.com", UserType.ADMIN)

    with pytest.raises(ValidationError):
        admin_service.generate_system_report(
            admin,
            date(2026, 2, 1),
            date(2026, 1, 1),
        )


@pytest.mark.django_db
def test_generated_report_contains_total_users(admin_service):
    admin = create_user("admin-total-users@example.com", UserType.ADMIN)
    create_user("provider-total-users@example.com", UserType.SERVICE_PROVIDER)

    report = admin_service.generate_system_report(
        admin,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert report["total_users"] == 2


@pytest.mark.django_db
def test_generated_report_contains_total_surveys(admin_service):
    admin = create_user("admin-total-surveys@example.com", UserType.ADMIN)
    provider = create_user("provider-total-surveys@example.com", UserType.SERVICE_PROVIDER)
    create_survey(provider)
    create_survey(provider)

    report = admin_service.generate_system_report(
        admin,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert report["total_surveys"] == 2


@pytest.mark.django_db
def test_generated_report_contains_total_responses(admin_service):
    admin = create_user("admin-total-responses@example.com", UserType.ADMIN)
    provider = create_user("provider-total-responses@example.com", UserType.SERVICE_PROVIDER)
    respondent = create_user("respondent-total-responses@example.com", UserType.RESPONDENT)
    survey = create_survey(provider)
    ResponseRepository().save(Response(survey=survey, respondent=respondent))

    report = admin_service.generate_system_report(
        admin,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert report["total_responses"] == 1


@pytest.mark.django_db
def test_generated_report_contains_active_surveys(admin_service):
    admin = create_user("admin-active-surveys@example.com", UserType.ADMIN)
    provider = create_user("provider-active-surveys@example.com", UserType.SERVICE_PROVIDER)
    create_survey(provider, status=SurveyStatus.PUBLISHED)
    create_survey(provider, status=SurveyStatus.DRAFT)

    report = admin_service.generate_system_report(
        admin,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert report["active_surveys"] == 1


@pytest.mark.django_db
def test_admin_can_generate_enhanced_system_report(admin_service):
    admin = create_user("admin-enhanced-report@example.com", UserType.ADMIN)
    provider = create_user("provider-enhanced-report@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider, status=SurveyStatus.PUBLISHED)
    create_response(survey, "respondent-enhanced-report@example.com")
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["total_users"] == 3
    assert report["total_surveys"] == 1
    assert report["total_responses"] == 1
    assert report["active_surveys"] == 1
    assert "users_by_type" in report
    assert "surveys_by_status" in report
    assert "responses_over_time" in report
    assert "user_growth_over_time" in report
    assert "most_active_surveys" in report
    assert report["has_users_by_type_data"] is True
    assert report["has_surveys_by_status_data"] is True
    assert report["has_responses_over_time_data"] is True
    assert report["has_user_growth_over_time_data"] is True
    assert report["has_user_growth_data"] is True
    assert report["has_most_active_surveys_data"] is True


@pytest.mark.django_db
def test_generated_report_includes_users_by_type(admin_service):
    admin = create_user("admin-users-by-type@example.com", UserType.ADMIN)
    create_user("provider-users-by-type@example.com", UserType.SERVICE_PROVIDER)
    create_user("respondent-users-by-type@example.com", UserType.RESPONDENT)
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["users_by_type"] == {
        UserType.SERVICE_PROVIDER.value: 1,
        UserType.RESPONDENT.value: 1,
        UserType.ADMIN.value: 1,
    }


@pytest.mark.django_db
def test_generated_report_includes_surveys_by_status(admin_service):
    admin = create_user("admin-surveys-by-status@example.com", UserType.ADMIN)
    provider = create_user("provider-surveys-by-status@example.com", UserType.SERVICE_PROVIDER)
    create_survey(provider, status=SurveyStatus.DRAFT)
    create_survey(provider, status=SurveyStatus.PUBLISHED)
    create_survey(provider, status=SurveyStatus.CLOSED)
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["surveys_by_status"] == {
        SurveyStatus.DRAFT.value: 1,
        SurveyStatus.PUBLISHED.value: 1,
        SurveyStatus.CLOSED.value: 1,
    }


@pytest.mark.django_db
def test_generated_report_includes_responses_over_time(admin_service):
    today = timezone.now().date()
    admin = create_user("admin-responses-over-time@example.com", UserType.ADMIN)
    provider = create_user("provider-responses-over-time@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider, status=SurveyStatus.PUBLISHED)
    create_response(survey, "respondent-responses-over-time@example.com")
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["responses_over_time"] == [
        {"date": today.isoformat(), "count": 1}
    ]


@pytest.mark.django_db
def test_generated_report_includes_user_growth_over_time(admin_service):
    today = timezone.now().date()
    admin = create_user("admin-user-growth@example.com", UserType.ADMIN)
    create_user("provider-user-growth@example.com", UserType.SERVICE_PROVIDER)
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["user_growth_over_time"] == [
        {"date": today.isoformat(), "count": 2}
    ]


@pytest.mark.django_db
def test_generated_report_includes_most_active_surveys(admin_service):
    admin = create_user("admin-most-active@example.com", UserType.ADMIN)
    provider = create_user("provider-most-active@example.com", UserType.SERVICE_PROVIDER)
    survey = create_survey(provider, status=SurveyStatus.PUBLISHED, title="Active Survey")
    create_response(survey, "respondent-most-active@example.com")
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["most_active_surveys"] == [
        {
            "survey_id": survey.survey_id,
            "title": "Active Survey",
            "response_count": 1,
        }
    ]


@pytest.mark.django_db
def test_generated_report_missing_user_types_return_zero(admin_service):
    admin = create_user("admin-missing-user-types@example.com", UserType.ADMIN)
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["users_by_type"][UserType.SERVICE_PROVIDER.value] == 0
    assert report["users_by_type"][UserType.RESPONDENT.value] == 0
    assert report["users_by_type"][UserType.ADMIN.value] == 1


@pytest.mark.django_db
def test_generated_report_missing_survey_statuses_return_zero(admin_service):
    admin = create_user("admin-missing-survey-statuses@example.com", UserType.ADMIN)
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert report["surveys_by_status"][SurveyStatus.DRAFT.value] == 0
    assert report["surveys_by_status"][SurveyStatus.PUBLISHED.value] == 0
    assert report["surveys_by_status"][SurveyStatus.CLOSED.value] == 0


@pytest.mark.django_db
def test_most_active_surveys_are_ordered_by_response_count_descending(admin_service):
    admin = create_user("admin-active-order@example.com", UserType.ADMIN)
    provider = create_user("provider-active-order@example.com", UserType.SERVICE_PROVIDER)
    less_active = create_survey(provider, status=SurveyStatus.PUBLISHED, title="Less Active")
    most_active = create_survey(provider, status=SurveyStatus.PUBLISHED, title="Most Active")
    inactive = create_survey(provider, status=SurveyStatus.PUBLISHED, title="Inactive")
    create_response(less_active, "respondent-active-order-1@example.com")
    create_response(most_active, "respondent-active-order-2@example.com")
    create_response(most_active, "respondent-active-order-3@example.com")
    date_from, date_to = current_report_range()

    report = admin_service.generate_system_report(admin, date_from, date_to)

    assert [item["survey_id"] for item in report["most_active_surveys"]] == [
        most_active.survey_id,
        less_active.survey_id,
    ]
    assert inactive.survey_id not in [
        item["survey_id"] for item in report["most_active_surveys"]
    ]
