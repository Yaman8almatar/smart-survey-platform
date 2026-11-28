"""TASK-51 (FR-14, board W-07): the CSV and Excel downloads of the included responses.

These tests run at the real threshold, services.disclosure.MIN_GROUP_SIZE (5 responses).
"""

import csv
import html
import io
import zipfile

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from openpyxl import load_workbook

from apps.core.models import Answer, Question, SentimentAnalysisResult
from core.enums import AnalysisStatus, QuestionType, SentimentLabel, UserType
from tests.views.test_response_pages_view import (
    DEVICE_HASH,
    SECRET_EMAIL,
    SECRET_NAME,
    add_response,
    add_responses,
    make_survey,
    make_user,
)

pytestmark = pytest.mark.django_db

HEADERS = [
    "Response",
    "Submitted",
    "Score",
    "Band",
    "Flags",
    "Q1. Pick one",
    "Q2. Rate the service",
    "Q3. Any comments?",
    "Q3 sentiment",
]
CAPTION = (
    '<p class="quality-caption">Downloads hold the included responses only, one row each, '
    "under these numbers. They show no names, accounts or times of day.</p>"
)
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def provider():
    return make_user(UserType.SERVICE_PROVIDER)


@pytest.fixture
def survey(provider):
    return make_survey(provider)


def csv_url(survey):
    return reverse("analysis:response_export_csv", args=[survey.survey_id])


def xlsx_url(survey):
    return reverse("analysis:response_export_xlsx", args=[survey.survey_id])


def list_url(survey):
    return reverse("analysis:response_list", args=[survey.survey_id])


def csv_rows(response):
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def xlsx_rows(response):
    """Return the sheet's rows, with an empty cell read back as ""."""
    sheet = load_workbook(io.BytesIO(response.content)).active
    return [
        ["" if value is None else value for value in row]
        for row in sheet.iter_rows(values_only=True)
    ]


def download(client, provider, survey):
    client.force_login(provider)
    return client.get(csv_url(survey)), client.get(xlsx_url(survey))


def messages_of(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


def test_both_files_hold_the_same_table(client, provider, survey):
    add_response(survey, minutes=0)
    add_response(survey, minutes=1, attention_failed=2, sentiment=(AnalysisStatus.PENDING, None))
    add_response(survey, minutes=2, evidence=False, text=None)
    add_response(survey, minutes=3, timings=False, signals_ok=False, attention_failed=1)
    add_response(survey, minutes=4, sentiment=(AnalysisStatus.FAILED, None))

    as_csv, as_xlsx = download(client, provider, survey)

    assert as_csv.status_code == 200
    assert as_csv.content.startswith(b"\xef\xbb\xbf")
    assert as_csv["Content-Type"] == "text/csv; charset=utf-8"
    assert as_csv["Content-Disposition"] == (
        f'attachment; filename="survey-{survey.survey_id}-responses.csv"'
    )
    assert as_xlsx.status_code == 200
    assert as_xlsx["Content-Type"] == XLSX_TYPE
    assert as_xlsx["Content-Disposition"] == (
        f'attachment; filename="survey-{survey.survey_id}-responses.xlsx"'
    )
    assert load_workbook(io.BytesIO(as_xlsx.content)).sheetnames == ["Responses"]

    table = xlsx_rows(as_xlsx)
    assert table == [
        HEADERS,
        [1, "2026-11-18", 100, "Clean", "No flag", "Option A", 3, "Great service", "Positive"],
        [
            2,
            "2026-11-18",
            20,
            "Low",
            "Failed attention check",
            "Option A",
            3,
            "Great service",
            "Waiting for analysis",
        ],
        [3, "2026-11-18", "", "Before quality checks", "Not checked", "Option A", 3, "", ""],
        [
            4,
            "2026-11-18",
            30,
            "Low",
            "Failed attention check; Timing or device data missing",
            "Option A",
            3,
            "Great service",
            "Positive",
        ],
        [
            5,
            "2026-11-18",
            100,
            "Clean",
            "No flag",
            "Option A",
            3,
            "Great service",
            "Could not be analysed",
        ],
    ]
    assert csv_rows(as_csv) == [[str(value) for value in row] for row in table]


def test_a_cell_that_could_run_as_a_formula_gets_an_apostrophe(client, provider, survey):
    add_response(survey, minutes=0, text="=1+1")
    add_response(survey, minutes=1, text="-5 stars")
    for text in ("+cmd", "@SUM(A1)", "\tTab", "\rReturn"):
        add_response(survey, minutes=2, text=text)

    as_csv, as_xlsx = download(client, provider, survey)

    guarded = ["'=1+1", "'-5 stars", "'+cmd", "'@SUM(A1)", "'\tTab"]
    for rows in (csv_rows(as_csv), xlsx_rows(as_xlsx)):
        assert [row[7] for row in rows[1:6]] == guarded
        # XML reads a stored "\r" back as "\n"; the leading apostrophe is what matters.
        assert rows[6][7].startswith("'") and rows[6][7][2:] == "Return"
    assert csv_rows(as_csv)[6][7] == "'\rReturn"
    sheet = load_workbook(io.BytesIO(as_xlsx.content)).active
    assert all(cell.data_type != "f" for row in sheet.iter_rows() for cell in row)


def test_control_characters_are_removed_from_both_files(client, provider, survey):
    add_response(survey, minutes=0, text="Bell\x07 and\x0b tab")
    add_responses(survey, 4)

    as_csv, as_xlsx = download(client, provider, survey)

    assert as_xlsx.status_code == 200
    assert xlsx_rows(as_xlsx)[1][7] == "Bell and tab"
    assert csv_rows(as_csv)[1][7] == "Bell and tab"


def test_a_control_character_cannot_hide_a_formula_from_the_guard(client, provider, survey):
    add_response(survey, minutes=0, text="\x07=1+1")
    add_responses(survey, 4)

    as_csv, as_xlsx = download(client, provider, survey)

    assert csv_rows(as_csv)[1][7] == "'=1+1"
    assert xlsx_rows(as_xlsx)[1][7] == "'=1+1"
    sheet = load_workbook(io.BytesIO(as_xlsx.content)).active
    assert sheet.cell(row=2, column=8).data_type == "s"


def test_neither_file_names_times_or_locates_a_respondent(client, provider, survey):
    respondent = make_user(UserType.RESPONDENT, email=SECRET_EMAIL, name=SECRET_NAME)
    add_response(survey, minutes=0, respondent=respondent, device_hash=DEVICE_HASH)
    add_responses(survey, 4)

    as_csv, as_xlsx = download(client, provider, survey)

    workbook = zipfile.ZipFile(io.BytesIO(as_xlsx.content))
    xml = "".join(workbook.read(name).decode("utf-8") for name in workbook.namelist())
    cells = "\n".join(str(value) for row in xlsx_rows(as_xlsx) for value in row)
    for text in (as_csv.content.decode("utf-8-sig"), xml):
        for secret in (SECRET_EMAIL, "rania.secret", SECRET_NAME, "FEMALE", "Female", DEVICE_HASH):
            assert secret not in text
    for text in (as_csv.content.decode("utf-8-sig"), cells):
        assert "2026-11-18" in text
        assert "14:37" not in text
        assert "2:37" not in text


def test_an_excluded_response_is_in_neither_file(client, provider, survey):
    add_responses(survey, 2)
    add_response(survey, minutes=2, excluded=True, text="Left out on purpose")
    add_response(survey, minutes=3)
    add_response(survey, minutes=4)

    as_csv, as_xlsx = download(client, provider, survey)

    for rows in (csv_rows(as_csv), xlsx_rows(as_xlsx)):
        assert [str(row[0]) for row in rows[1:]] == ["1", "2", "4", "5"]
        assert "Left out on purpose" not in str(rows)


def test_a_second_open_question_gets_its_own_sentiment_column(client, provider, survey):
    first = add_response(survey, minutes=0)
    for minutes in range(1, 5):
        add_response(survey, minutes=minutes)
    extra = Question.objects.create(
        survey=survey,
        question_text="Anything else?",
        question_type=QuestionType.OPEN_TEXT,
        order_index=3,
        is_required=False,
    )
    answer = Answer.objects.create(response=first, question=extra, answer_value="Fine")
    SentimentAnalysisResult.objects.create(
        answer=answer, status=AnalysisStatus.COMPLETED, sentiment_label=SentimentLabel.NEGATIVE
    )

    rows = xlsx_rows(download(client, provider, survey)[1])

    assert rows[0][-2:] == ["Q4. Anything else?", "Q4 sentiment"]
    assert rows[1][-2:] == ["Fine", "Negative"]
    assert rows[2][-2:] == ["", ""]


def test_locked_results_redirect_to_the_list_without_a_message(client, provider, survey):
    add_responses(survey, 4)
    client.force_login(provider)

    for url in (csv_url(survey), xlsx_url(survey)):
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == list_url(survey)
        assert messages_of(response) == []


def test_not_logged_in_goes_to_the_login(client, survey):
    add_responses(survey, 5)

    for url in (csv_url(survey), xlsx_url(survey)):
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("users:login")


def test_another_provider_is_sent_to_the_provider_dashboard(client, survey):
    add_responses(survey, 5)
    client.force_login(make_user(UserType.SERVICE_PROVIDER))

    for url in (csv_url(survey), xlsx_url(survey)):
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("surveys:provider_dashboard")
        assert messages_of(response)


def test_a_post_is_405(client, provider, survey):
    add_responses(survey, 5)
    client.force_login(provider)

    assert client.post(csv_url(survey)).status_code == 405
    assert client.post(xlsx_url(survey)).status_code == 405


def test_the_list_page_offers_both_downloads_only_while_open(client, provider, survey):
    add_responses(survey, 4)
    client.force_login(provider)

    locked = html.unescape(client.get(list_url(survey)).content.decode())
    assert "Download CSV" not in locked
    assert "Download Excel" not in locked
    assert csv_url(survey) not in locked
    assert xlsx_url(survey) not in locked
    assert "Downloads hold the included responses only" not in locked

    add_response(survey, minutes=10)
    opened = html.unescape(client.get(list_url(survey)).content.decode())
    assert f'href="{csv_url(survey)}"' in opened
    assert f'href="{xlsx_url(survey)}"' in opened
    assert 'aria-hidden="true"></i>Download CSV</a>' in opened
    assert 'aria-hidden="true"></i>Download Excel</a>' in opened
    assert CAPTION in opened
    assert opened.index("Back to analytics") < opened.index("Download CSV")
    assert opened.index("responses included.") < opened.index(CAPTION)
