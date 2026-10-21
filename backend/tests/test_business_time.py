from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.business_time import Calendar, active_business_minutes, business_minutes

CCS = ZoneInfo("America/Caracas")


def at(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=CCS)


def calendar(**kwargs) -> Calendar:
    week = {d: [(time(7), time(19))] for d in range(5)} | {5: [(time(7), time(13))]}
    return Calendar(tz=CCS, default=week, **kwargs)


def test_inside_business_hours():
    # Martes 20 de octubre de 2026
    assert business_minutes(at(20, 10), at(20, 10, 30), calendar(), None) == 30


def test_after_hours_counts_only_next_morning():
    assert business_minutes(at(20, 21), at(21, 7, 5), calendar(), None) == 5


def test_weekend_with_saturday_half_day():
    # Viernes 23 18:50 → lunes 26 07:10: 10 + sábado 360 + 10
    assert business_minutes(at(23, 18, 50), at(26, 7, 10), calendar(), None) == 380


def test_holiday_is_skipped():
    # Lunes 12 de octubre es feriado: viernes 60 + sábado 360 + lunes 0 + martes 30
    cal = calendar(holidays_all={at(12, 0).date()})
    assert business_minutes(at(9, 18), at(13, 7, 30), cal, None) == 450


def test_area_schedule_and_area_holiday_override_default():
    cal = calendar(by_area={3: {1: [(time(8), time(9))]}}, holidays_by_area={3: {at(27, 0).date()}})
    # Área 3 solo abre martes 8–9; el martes 27 tiene feriado propio
    assert business_minutes(at(20, 7), at(20, 12), cal, 3) == 60
    assert business_minutes(at(27, 7), at(27, 12), cal, 3) == 0
    assert business_minutes(at(27, 7), at(27, 12), cal, None) == 300


def test_pauses_are_subtracted_and_clipped():
    pauses = [(at(20, 9, 10), at(20, 10, 10)), (at(20, 6), at(20, 7, 30))]
    assert active_business_minutes(at(20, 7), at(20, 11), pauses, calendar(), None) == 240 - 60 - 30


def test_without_schedule_uses_clock_minutes():
    cal = Calendar(tz=CCS)
    assert business_minutes(at(20, 21), at(21, 7, 5), cal, None) == 605
    assert business_minutes(at(20, 10), at(20, 9), cal, None) == 0
    assert business_minutes(at(20, 10), at(20, 10) + timedelta(seconds=90), cal, None) == 1.5
