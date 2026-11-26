"""Parse timestamps without guessing the calendar or interpreting naive time as UTC."""
import warnings
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


_EXPLICIT_OFFSET = r"[Tt ]\d{1,2}:?\d{2}.*(?:[Zz]|[+-]\d{2}(?::?\d{2})?|\s(?:UTC|GMT))$"


def parse_timestamps(values, field="event_time", *, project_timezone=None):
    """Keep naive wall times and convert explicit instants to the declared calendar."""
    try:
        calendar = ZoneInfo(project_timezone) if project_timezone is not None else None
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise ValueError(f"invalid project timezone {project_timezone!r}; use an IANA timezone name") from exc
    if values.isna().any():
        raise ValueError(f"{field} contains missing timestamps")
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*mixed time zones.*", category=FutureWarning)
            parsed = pd.to_datetime(values, format="mixed")
    except (TypeError, ValueError):
        parsed = None

    if parsed is None or not pd.api.types.is_datetime64_any_dtype(parsed.dtype):
        explicit = values.astype(str).str.strip().str.contains(_EXPLICIT_OFFSET, regex=True)
        if not explicit.all():
            raise ValueError(f"{field} requires valid timestamps with consistent awareness. "
                             "For mixed UTC offsets, supply an explicit offset on every row.")
        if calendar is None:
            raise ValueError(f"{field} contains mixed UTC offsets. Confirm and supply the project timezone.")
        parsed = pd.to_datetime(values, format="mixed", utc=True)

    if parsed.isna().any():
        raise ValueError(f"{field} contains missing timestamps")
    if parsed.dt.tz is not None and calendar is not None:
        parsed = parsed.dt.tz_convert(calendar)
    return parsed
