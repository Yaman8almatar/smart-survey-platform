"""Disclosure band for people counts shown to service providers (P-19).

A count of 1 to 4 is never shown as a number: a provider who narrows the criteria until
only a handful of respondents match could otherwise learn facts about those few people.
Every count of people that leaves the services for a provider goes through band().

pool_groups() is the pooling helper of DESIGN-INC2 3.6 (P-15), first used by FR-05; FR-09
and FR-13 reuse it.
"""

MIN_GROUP_SIZE = 5


def band(count):
    """Return a count as a disclosure state: none (0), few (1 to 4, no number) or exact."""
    if count == 0:
        return {"state": "none", "count": 0}
    if count < MIN_GROUP_SIZE:
        return {"state": "few", "count": None}
    return {"state": "exact", "count": count}


def results_open(response_count):
    """Return whether a survey's results may be shown to its provider (P-20, D-168).

    The rule covers the whole survey, not only filtered views: with FR-03 a provider can
    target a combination that he knows holds one person, so the survey itself can be a
    group of one, and a band on its counts cannot stop that because counts can be
    subtracted. Below MIN_GROUP_SIZE responses no count, chart, rate or answer leaves the
    services; every provider-facing view of answers goes through this function.
    """
    return response_count >= MIN_GROUP_SIZE


def pool_groups(counts):
    """Split groups into shown ones and one pool so no figure covers 1 to 4 people (P-15).

    counts maps a group label to its count; counts of 0 are ignored. Every group under
    MIN_GROUP_SIZE is pooled. Hiding the small groups one by one would not be enough: the
    total minus the shown groups would give the hidden ones back, so while the pool itself
    holds 1 to 4 people the smallest shown group joins it (between equal counts, the one
    listed last). shown is ordered by count, highest first, then by label. enough is true
    only when at least two rows (shown groups plus a non-empty pool) remain to compare.
    """
    def order(label):
        return (-counts[label], label)

    groups = sorted((label for label, count in counts.items() if count > 0), key=order)
    shown = [label for label in groups if counts[label] >= MIN_GROUP_SIZE]
    pooled = [label for label in groups if counts[label] < MIN_GROUP_SIZE]

    pooled_total = sum(counts[label] for label in pooled)
    while shown and 0 < pooled_total < MIN_GROUP_SIZE:
        label = shown.pop()
        pooled.append(label)
        pooled_total += counts[label]

    pooled.sort(key=order)
    rows = len(shown) + (1 if pooled else 0)
    return {"shown": shown, "pooled": pooled, "enough": rows >= 2}
