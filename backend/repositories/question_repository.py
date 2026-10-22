from apps.core.models import Question, QuestionOption


class QuestionRepository:
    """Provides database access for survey questions and options."""

    def save(self, question):
        """Persist a survey question."""
        question.save()
        return question

    def find_by_id(self, question_id):
        """Return a question by its primary key."""
        return Question.objects.filter(question_id=question_id).first()

    def find_by_survey_id(self, survey_id):
        """Return questions belonging to a survey."""
        return Question.objects.filter(survey_id=survey_id)

    def update(self, question):
        """Persist changes to a question."""
        question.save()
        return question

    def delete(self, question_id):
        """Delete a question by primary key."""
        return Question.objects.filter(question_id=question_id).delete()

    def save_option(self, option):
        """Persist a multiple-choice question option."""
        option.save()
        return option

    def find_options_by_question_id(self, question_id):
        """Return options belonging to a question."""
        return QuestionOption.objects.filter(question_id=question_id)
