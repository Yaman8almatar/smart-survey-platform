"""FR-14 (board W-07): the included responses and their quality verdicts as CSV or Excel."""

import csv
import io

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_GET
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from core.enums import QuestionType
from core.exceptions import SmartSurveyException
from services import quality_rules
from services.response_review_service import ResponseReviewService

from .response_views import BAND_NAMES, FLAG_NAMES, SENTIMENT_NAMES
from .views import QUALITY_FLAG_ORDER, _redirect_if_unauthenticated

# A spreadsheet runs a cell that starts with one of these as a formula (CSV injection).
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@require_GET
def response_export_csv(request, survey_id):
    """Download the included responses as a UTF-8 CSV file with a byte-order mark."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response
    table, refusal = _export_table_or_redirect(request, survey_id)
    if refusal:
        return refusal

    text = io.StringIO()
    csv.writer(text).writerows(table)
    response = HttpResponse(
        text.getvalue().encode("utf-8-sig"), content_type="text/csv; charset=utf-8"
    )
    response["Content-Disposition"] = f'attachment; filename="survey-{survey_id}-responses.csv"'
    return response


@require_GET
def response_export_xlsx(request, survey_id):
    """Download the included responses as an Excel workbook with one sheet, "Responses"."""
    response = _redirect_if_unauthenticated(request)
    if response:
        return response
    table, refusal = _export_table_or_redirect(request, survey_id)
    if refusal:
        return refusal

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Responses"
    for row in table:
        # openpyxl refuses control characters that the XML format cannot hold.
        sheet.append(
            [ILLEGAL_CHARACTERS_RE.sub("", cell) if isinstance(cell, str) else cell for cell in row]
        )
    content = io.BytesIO()
    workbook.save(content)
    response = HttpResponse(content.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="survey-{survey_id}-responses.xlsx"'
    return response


def _export_table_or_redirect(request, survey_id):
    """Return (table, None), or (None, a redirect) when refused or while results are locked."""
    try:
        result = ResponseReviewService().export_responses(request.user, survey_id)
    except SmartSurveyException as error:
        messages.error(request, str(error), extra_tags="danger")
        return None, redirect("surveys:provider_dashboard")
    if result["locked"]:
        # The list page shows the locked card.
        return None, redirect("analysis:response_list", survey_id)
    return export_table(result), None


def export_table(result):
    """Return the rows both formats write: the header row, then one row per exported response."""
    questions = result["questions"]
    is_open = [question["question_type"] == QuestionType.OPEN_TEXT for question in questions]

    header = ["Response", "Submitted", "Score", "Band", "Flags"]
    for question, open_text in zip(questions, is_open):
        header.append(f"Q{question['position']}. {question['question_text']}")
        if open_text:
            header.append(f"Q{question['position']} sentiment")
    table = [[_guard(cell) for cell in header]]

    for row in result["rows"]:
        if row["status"] == quality_rules.BEFORE_CHECKS:
            score, band, flags = "", "Before quality checks", "Not checked"
        else:
            names = [FLAG_NAMES[code] for code in QUALITY_FLAG_ORDER if code in row["flags"]]
            score, band, flags = row["score"], BAND_NAMES[row["band"]], "; ".join(names) or "No flag"
        cells = [
            row["number"],
            timezone.localdate(row["submitted_at"]).isoformat(),
            score,
            band,
            flags,
        ]
        for answer, open_text in zip(row["answers"], is_open):
            cells.append("" if answer["value"] is None else answer["value"])
            if open_text:
                cells.append(SENTIMENT_NAMES.get(answer["sentiment"], ""))
        table.append([_guard(cell) for cell in cells])
    return table


def _guard(cell):
    """Return a text cell that a spreadsheet could run as a formula with a leading "'"."""
    if isinstance(cell, str) and cell.startswith(FORMULA_STARTS):
        return f"'{cell}"
    return cell
