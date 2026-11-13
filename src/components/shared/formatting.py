from datetime import datetime, timedelta, timezone

BRT = timezone(timedelta(hours=-3))


def format_datetime(value: datetime) -> str:
    """Data/hora em horário de Brasília (o Mongo devolve datas UTC sem fuso)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BRT).strftime("%d/%m/%Y %H:%M")
