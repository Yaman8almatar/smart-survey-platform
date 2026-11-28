"""FR-16: the respondent's own order of questions and options, computed from a hash (TASK-52)."""

from services.presentation_order import respondent_order

ITEMS = [{"id": number} for number in range(1, 7)]


def order(items=ITEMS, survey_id=5, respondent_id=9, scope="questions"):
    return respondent_order(items, lambda item: item["id"], survey_id, respondent_id, scope)


def ids(items):
    return [item["id"] for item in items]


def test_the_result_is_a_permutation_of_the_input():
    result = order()

    assert sorted(ids(result)) == ids(ITEMS)
    assert result is not ITEMS


def test_the_same_arguments_give_the_same_order():
    assert ids(order()) == ids(order())


def test_the_input_order_does_not_matter():
    assert ids(order(list(reversed(ITEMS)))) == ids(order())


def test_respondents_get_different_orders():
    orders = {tuple(ids(order(respondent_id=respondent))) for respondent in range(1, 21)}

    assert len(orders) >= 2


def test_two_scopes_give_independent_orders():
    pairs = {
        (
            tuple(ids(order(respondent_id=respondent, scope="questions"))),
            tuple(ids(order(respondent_id=respondent, scope="options:3"))),
        )
        for respondent in range(1, 21)
    }

    assert any(first != second for first, second in pairs)


def test_the_input_list_is_left_unchanged():
    items = list(ITEMS)

    order(items)

    assert items == ITEMS
