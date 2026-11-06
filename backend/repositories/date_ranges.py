import datetime

from django.utils import timezone


def aware_day_range(date_from, date_to):
    """Return an aware (start, end) pair covering whole days for plain dates.

    A plain ``date`` becomes the start of that day (``date_from``) or the end of that day
    (``date_to``) in the current time zone. A ``datetime`` is returned unchanged.
    """
    return (
        _as_aware_bound(date_from, datetime.time.min),
        _as_aware_bound(date_to, datetime.time.max),
    )


def _as_aware_bound(value, day_time):
    """Turn a plain date into an aware datetime at ``day_time``; keep datetimes as given."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return timezone.make_aware(datetime.datetime.combine(value, day_time))
    return value
