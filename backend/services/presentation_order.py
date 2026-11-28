"""The respondent's own order of questions and options (FR-16).

Each item is ranked by a SHA-256 hash of the scope, the survey, the respondent and the item.
A good hash spreads the ranks evenly, so every respondent gets a uniform shuffle of their own.
The same inputs always give the same ranks, so the order never changes between visits and a
respondent who resumes a saved draft (FR-06) sees what they saw before; nothing is stored, so
no table or column is needed.
"""

import hashlib


def respondent_order(items, item_key, survey_id, respondent_id, scope):
    """Return a new list of items in this respondent's fixed order for the given scope.

    Scopes: "questions" for the questions of a survey (key question_id), and
    f"options:{question_id}" for the options of one question (key option_id).
    """

    def rank(item):
        seed = f"{scope}:{survey_id}:{respondent_id}:{item_key(item)}"
        return hashlib.sha256(seed.encode()).hexdigest()

    return sorted(items, key=rank)
