import datetime

from django.utils import timezone

from repositories.date_ranges import aware_day_range


def test_plain_dates_cover_the_whole_days_as_aware_datetimes():
    start, end = aware_day_range(datetime.date(2026, 1, 1), datetime.date(2026, 1, 31))

    assert timezone.is_aware(start) and timezone.is_aware(end)
    assert timezone.localtime(start).replace(tzinfo=None) == datetime.datetime(2026, 1, 1, 0, 0)
    assert timezone.localtime(end).replace(tzinfo=None) == datetime.datetime(
        2026, 1, 31, 23, 59, 59, 999999
    )


def test_datetimes_are_returned_unchanged():
    start = timezone.now() - datetime.timedelta(days=1)
    end = timezone.now()

    assert aware_day_range(start, end) == (start, end)
