"""Disclosure band for people counts shown to service providers (P-19).

A count of 1 to 4 is never shown as a number: a provider who narrows the criteria until
only a handful of respondents match could otherwise learn facts about those few people.
Every count of people that leaves the services for a provider goes through band().

FR-05, FR-09 and FR-13 will add the pooling helper of DESIGN-INC2 3.6 to this module.
"""

MIN_GROUP_SIZE = 5


def band(count):
    """Return a count as a disclosure state: none (0), few (1 to 4, no number) or exact."""
    if count == 0:
        return {"state": "none", "count": 0}
    if count < MIN_GROUP_SIZE:
        return {"state": "few", "count": None}
    return {"state": "exact", "count": count}
