from core.enums import AccountStatus, SurveyStatus, UserType
from core.exceptions import AccountNotFound, UnauthorizedAction, ValidationError
from repositories.response_repository import ResponseRepository
from repositories.survey_repository import SurveyRepository
from repositories.user_repository import UserRepository


class AdminService:
    """Handles Admin account management and System reports."""

    def __init__(
        self,
        user_repository=None,
        survey_repository=None,
        response_repository=None,
    ):
        """Wire repositories used by administrator workflows and reports."""
        self.user_repository = user_repository or UserRepository()
        self.survey_repository = survey_repository or SurveyRepository()
        self.response_repository = response_repository or ResponseRepository()

    def activate_account(self, admin_user, user_id):
        """Activate an existing user account."""
        self._ensure_admin(admin_user)
        user = self._get_user(user_id)
        user.activate()
        return self.user_repository.update(user)

    def suspend_account(self, admin_user, user_id):
        """Suspend a user account while preventing the administrator from suspending self."""
        self._ensure_admin(admin_user)
        self._reject_self_destructive_action(admin_user, user_id)
        user = self._get_user(user_id)
        user.suspend()
        return self.user_repository.update(user)

    def delete_account(self, admin_user, user_id):
        """Soft-delete a user account while preventing the administrator from deleting self."""
        self._ensure_admin(admin_user)
        self._reject_self_destructive_action(admin_user, user_id)
        user = self._get_user(user_id)
        user.mark_deleted()
        return self.user_repository.update(user)

    def list_users(self, admin_user):
        """List all user accounts for an admin user."""
        self._ensure_admin(admin_user)
        return self.user_repository.list_all()

    def list_user_management_items(self, admin_user):
        """Return user accounts with action flags for administrator account management."""
        self._ensure_admin(admin_user)
        return [
            {
                "user": user,
                **self._account_action_flags(admin_user, user),
            }
            for user in self.user_repository.list_all()
        ]

    def generate_system_report(self, admin_user, date_from, date_to):
        """Build administrator-level platform metrics and chart-ready report data."""
        self._ensure_admin(admin_user)
        self._validate_date_range(date_from, date_to)

        # System reports are assembled from repository-provided aggregates.
        users_by_type = self._counts_by_category(
            self.user_repository.count_by_user_type(),
            "user_type",
            UserType,
        )
        surveys_by_status = self._counts_by_category(
            self.survey_repository.count_by_status(),
            "status",
            SurveyStatus,
        )
        response_counts = list(self.response_repository.count_by_survey())
        responses_over_time = self._date_count_rows(
            self.response_repository.count_submitted_by_date(date_from, date_to),
            "submitted_date",
        )
        user_growth_over_time = self._date_count_rows(
            self.user_repository.count_created_by_date(date_from, date_to),
            "created_date",
        )
        most_active_surveys = self._most_active_survey_rows()

        return {
            "total_users": sum(users_by_type.values()),
            "total_surveys": sum(surveys_by_status.values()),
            "total_responses": self._total_response_count(response_counts),
            "active_surveys": surveys_by_status[SurveyStatus.PUBLISHED.value],
            "users_by_type": users_by_type,
            "surveys_by_status": surveys_by_status,
            "responses_over_time": responses_over_time,
            "user_growth_over_time": user_growth_over_time,
            "most_active_surveys": most_active_surveys,
            "has_users_by_type_data": self._has_count_data(users_by_type),
            "has_surveys_by_status_data": self._has_count_data(surveys_by_status),
            "has_responses_over_time_data": self._has_row_count_data(
                responses_over_time
            ),
            "has_user_growth_over_time_data": self._has_row_count_data(
                user_growth_over_time
            ),
            "has_user_growth_data": self._has_row_count_data(user_growth_over_time),
            "has_most_active_surveys_data": self._has_row_count_data(
                most_active_surveys,
                count_key="response_count",
            ),
        }

    def _ensure_admin(self, user):
        """Ensure only administrators can perform admin operations."""
        if user.user_type != UserType.ADMIN:
            raise UnauthorizedAction("Only admins can perform this action.")

    def _reject_self_destructive_action(self, admin_user, user_id):
        """Prevent administrators from suspending or deleting their own account."""
        if admin_user.user_id == user_id:
            raise UnauthorizedAction("Admins cannot suspend or delete their own account.")

    def _account_action_flags(self, admin_user, user):
        """Build allowed account action flags for the admin management page."""
        # Build Admin account management flags for activate, suspend, and soft delete.
        is_self = admin_user.user_id == user.user_id
        is_active = user.account_status == AccountStatus.ACTIVE
        is_suspended = user.account_status == AccountStatus.SUSPENDED
        is_deleted = user.account_status == AccountStatus.DELETED

        return {
            "is_self": is_self,
            "can_activate": is_suspended or is_deleted,
            "can_suspend": is_active and not is_self,
            "can_delete": not is_deleted and not is_self,
        }

    def _get_user(self, user_id):
        """Return a user account or raise the admin-facing not-found error."""
        user = self.user_repository.find_by_id(user_id)
        if user is None:
            raise AccountNotFound("Account not found.")
        return user

    def _validate_date_range(self, date_from, date_to):
        """Validate the system report date range."""
        if date_from is None or date_to is None or date_from > date_to:
            raise ValidationError("date_from must be less than or equal to date_to.")

    def _counts_by_category(self, rows, key_name, choices):
        """Build a complete count dictionary for enum-based report categories."""
        counts = {choice.value: 0 for choice in choices}
        for row in rows:
            key = row[key_name]
            if key in counts:
                counts[key] = row["count"]
        return counts

    def _date_count_rows(self, rows, date_key):
        """Build chart-ready date/count rows for system reports."""
        return [
            {
                "date": row[date_key].isoformat(),
                "count": row["count"],
            }
            for row in rows
            if row[date_key] is not None
        ]

    def _total_response_count(self, response_counts):
        """Calculate the total response count from grouped response rows."""
        return sum(row["response_count"] for row in response_counts)

    def _has_count_data(self, counts):
        """Return whether grouped count data contains any non-zero values."""
        return any(count > 0 for count in counts.values())

    def _has_row_count_data(self, rows, count_key="count"):
        """Return whether chart row data contains any non-zero values."""
        return any(row[count_key] > 0 for row in rows)

    def _most_active_survey_rows(self):
        """Build chart-ready rows for the most active surveys report."""
        return [
            {
                "survey_id": survey.survey_id,
                "title": survey.title,
                "response_count": survey.response_count,
            }
            for survey in self.survey_repository.find_most_active(limit=5)
        ]
