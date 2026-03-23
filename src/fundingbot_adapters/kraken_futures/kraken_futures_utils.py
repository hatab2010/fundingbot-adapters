from datetime import UTC, datetime, timedelta


def calculate_next_funding_timestamp() -> datetime:
    """Вычисляет следующее время funding rate для Kraken Futures.

    Kraken Futures имеет расписание каждый ровный час.

    Returns:
        datetime: Следующее время funding в UTC.

    """
    now_utc = datetime.now(UTC)
    now_plus_1_hour = now_utc + timedelta(hours=1)
    return now_plus_1_hour.replace(minute=0, second=0, microsecond=0)
