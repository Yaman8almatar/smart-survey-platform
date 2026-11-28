"""TASK-43 (board W-04): the attention option on the question form and the questions list."""

import pytest
from django.urls import reverse

from apps.core.models import Question, Survey, TargetingCriteria, User
from core.enums import AccountStatus, QuestionType, UserType
from services.question_service import QuestionService

pytestmark = pytest.mark.django_db

CHOOSE = "Choose the expected answer."
OPEN_TEXT_ERROR = "Attention checks work on multiple-choice and rating questions."
READY_CHOICE = 'To show that you are reading, choose "{answer}" for this question.'
READY_RATING = "To show that you are reading, choose {answer} on this scale."
# The approved captions (board W-04, D-188; TASK-43B).
HELPER = (
    "The question asks respondents to pick a stated answer, to show they are reading. "
    "One or two per survey are enough."
)
LIMIT = "This survey already has 2 attention checks. Delete one to add another."


@pytest.fixture
def provider():
    return User.objects.create_user(
        email="provider-form@example.com",
        password="strong-password",
        name="Test User",
        user_type=UserType.SERVICE_PROVIDER,
        account_status=AccountStatus.ACTIVE,
    )


@pytest.fixture
def survey(provider):
    survey = Survey.objects.create(provider=provider, title="Form")
    TargetingCriteria.objects.create(survey=survey, regions=[], gender=None)
    return survey


def url(survey):
    return reverse("surveys:manage_questions", args=[survey.survey_id])


def post(client, provider, survey, **data):
    client.force_login(provider)
    payload = {"question_text": "Pick one", "order_index": "0", **data}
    return client.post(url(survey), payload)


def page(client, provider, survey):
    client.force_login(provider)
    return client.get(url(survey)).content.decode()


def add_check(provider, survey, order_index, question_type=QuestionType.RATING_SCALE, **kwargs):
    kwargs.setdefault("expected_rating", 3)
    return QuestionService().add_question_with_options(
        provider,
        survey.survey_id,
        f"Check {order_index}",
        question_type,
        True,
        order_index,
        is_attention_check=True,
        **kwargs,
    )


def test_a_rating_check_is_saved_required_without_is_required_posted(client, provider, survey):
    response = post(
        client,
        provider,
        survey,
        question_type="RATING_SCALE",
        is_attention_check="on",
        expected_rating="4",
    )

    assert response.status_code == 302
    question = Question.objects.get(survey=survey)
    assert question.is_attention_check is True
    assert question.expected_rating == 4
    assert question.is_required is True


def test_a_choice_check_stores_the_option_at_the_position(client, provider, survey):
    post(
        client,
        provider,
        survey,
        question_type="MULTIPLE_CHOICE",
        options="Agree\nNeutral\nDisagree",
        is_attention_check="on",
        expected_option="0",
    )

    question = Question.objects.get(survey=survey)
    assert question.is_attention_check is True
    assert question.expected_option.option_text == "Agree"


def test_a_blank_option_line_does_not_shift_the_position(client, provider, survey):
    post(
        client,
        provider,
        survey,
        question_type="MULTIPLE_CHOICE",
        options="Agree\n\n  \nNeutral\nDisagree",
        is_attention_check="on",
        expected_option="1",
    )

    assert Question.objects.get(survey=survey).expected_option.option_text == "Neutral"


@pytest.mark.parametrize(
    "question_type, options, group_class",
    [
        ("MULTIPLE_CHOICE", "Agree\nDisagree", "attention-choices is-invalid"),
        ("RATING_SCALE", "", "ss-segmented ss-segmented--five is-invalid"),
    ],
)
def test_a_missing_expected_answer_shows_the_error_and_saves_nothing(
    client, provider, survey, question_type, options, group_class
):
    response = post(
        client,
        provider,
        survey,
        question_type=question_type,
        options=options,
        is_attention_check="on",
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert not Question.objects.filter(survey=survey).exists()
    assert f'class="{group_class}"' in content
    group = content.index(f'class="{group_class}"')
    error = content.index(f"<span>{CHOOSE}</span>")
    assert group < error
    assert 'class="field-error"' in content[group:error + 40]


def test_open_text_with_the_option_gives_the_field_error(client, provider, survey):
    response = post(
        client, provider, survey, question_type="OPEN_TEXT", is_attention_check="on"
    )

    assert response.status_code == 200
    assert f"<span>{OPEN_TEXT_ERROR}</span>" in response.content.decode()
    assert not Question.objects.filter(survey=survey).exists()


def test_an_unticked_option_with_leftover_values_saves_an_ordinary_question(
    client, provider, survey
):
    response = post(
        client,
        provider,
        survey,
        question_type="MULTIPLE_CHOICE",
        options="Agree\nDisagree",
        expected_option="1",
        expected_rating="2",
    )

    assert response.status_code == 302
    question = Question.objects.get(survey=survey)
    assert question.is_attention_check is False
    assert question.expected_option is None
    assert question.expected_rating is None
    assert question.is_required is False


@pytest.mark.parametrize("question_type", ["RATING_SCALE", "OPEN_TEXT"])
def test_options_left_over_from_multiple_choice_do_not_block_the_save(
    client, provider, survey, question_type
):
    # TASK-47 (D-194 (5)): the option builder keeps lines typed under "Multiple choice".
    client.force_login(provider)
    response = client.post(
        url(survey),
        {
            "question_text": "How was it?",
            "order_index": "0",
            "question_type": question_type,
            "options": "Agree\nDisagree",
        },
        follow=True,
    )

    assert "Question added successfully." in response.content.decode()
    question = Question.objects.get(survey=survey)
    assert question.question_type == question_type
    assert not question.options.exists()


def test_a_rating_check_with_leftover_options_saves_as_a_check(client, provider, survey):
    response = post(
        client,
        provider,
        survey,
        question_type="RATING_SCALE",
        options="Agree\nDisagree",
        is_attention_check="on",
        expected_rating="4",
    )

    assert response.status_code == 302
    question = Question.objects.get(survey=survey)
    assert question.is_attention_check is True
    assert question.expected_rating == 4
    assert not question.options.exists()


def test_at_two_checks_the_page_shows_the_limit_and_a_disabled_checkbox(
    client, provider, survey
):
    add_check(provider, survey, 0)
    add_check(provider, survey, 1)

    content = page(client, provider, survey)

    assert f'data-attention-caption="limit">{LIMIT}</div>' in content
    assert f'data-attention-caption="help" hidden>{HELPER}</div>' in content
    toggle = content[content.index("data-attention-toggle"):]
    assert toggle.index("disabled") < toggle.index(">")
    assert "2 of 2 attention checks used in this survey." in content


def test_below_the_limit_the_checkbox_is_enabled(client, provider, survey):
    content = page(client, provider, survey)

    toggle = content[content.index("data-attention-toggle"):]
    assert "disabled" not in toggle[: toggle.index(">")]
    assert f'data-attention-caption="help">{HELPER}</div>' in content
    assert f'data-attention-caption="open" hidden>{OPEN_TEXT_ERROR}</div>' in content
    assert f'data-attention-caption="limit" hidden>{LIMIT}</div>' in content


def test_the_attention_section_sits_under_the_options(client, provider, survey):
    content = page(client, provider, survey)

    required_caption = content.index("data-attention-required-caption")
    builder = content.index("data-option-builder")
    section = content.index("data-attention-check")
    submit = content.index('<button class="btn btn-primary w-100" type="submit">')
    assert required_caption < builder < section < submit


def test_the_list_shows_the_badge_the_expected_answer_and_the_usage(client, provider, survey):
    add_check(
        provider,
        survey,
        0,
        QuestionType.MULTIPLE_CHOICE,
        options=["Agree", "Disagree"],
        expected_option_index=0,
        expected_rating=None,
    )

    content = page(client, provider, survey)

    assert '<span class="attention-badge">' in content
    assert "Expected answer: <strong>Agree</strong>" in content
    assert (
        '<span class="option-pill option-pill--expected">'
        '<i class="bi bi-check-lg" aria-hidden="true"></i>Agree</span>'
    ) in content
    assert "1 of 2 attention checks used in this survey." in content


def test_no_usage_line_and_no_badge_without_attention_checks(client, provider, survey):
    QuestionService().add_question_with_options(
        provider, survey.survey_id, "Plain", QuestionType.RATING_SCALE, True, 0
    )

    content = page(client, provider, survey)

    assert "attention checks used in this survey." not in content
    assert '<span class="attention-badge">' not in content


def test_both_ready_texts_are_in_the_page(client, provider, survey):
    content = page(client, provider, survey)

    assert f"data-ready-choice='{READY_CHOICE}'" in content
    assert f"data-ready-rating='{READY_RATING}'" in content


def test_a_redisplay_renders_the_posted_options_as_radios(client, provider, survey):
    response = post(
        client,
        provider,
        survey,
        question_type="MULTIPLE_CHOICE",
        options="Agree\n\nDisagree",
        is_attention_check="on",
        expected_option="9",
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert 'name="expected_option" value="0"' in content
    assert 'name="expected_option" value="1"' in content
    assert 'name="expected_option" value="2"' not in content
