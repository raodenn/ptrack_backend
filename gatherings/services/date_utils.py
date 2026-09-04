from datetime import timedelta, time , datetime
import zoneinfo

def get_period_boundaries(raw_value, period_type, tz_name):
    """
    parses date strings and returns start_datetime and end_datetime
    """
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValueError(f'Unknown timezone: {tz_name}')

    if period_type == 'daily':
        # Expects: YYYY-MM-DD
        dt = datetime.strptime(raw_value,'%Y-%m-%d').date()
        start = datetime.combine(dt, time.min, tzinfo=tz)
        end = start + timedelta(days=1)

    elif period_type == 'weekly':
        # Expects: YYYY-Www 
        monday_dt = datetime.strptime(f'{raw_value}-1', '%G-W%V-%u').date()
        start = datetime.combine(monday_dt,time.min,tzinfo=tz)
        end = start + timedelta(days=7)

    elif period_type == 'monthly':
        # Expects: YYYY-MM
        first_day = datetime.strptime(raw_value, "%Y-%m").date()
        start = datetime.combine(first_day,time.min,tzinfo=tz)

        if first_day.month == 12:
            next_month = first_day.replace(month=1, year=first_day.year + 1)
        else:
            next_month = first_day.replace(month= first_day.month + 1)

        end = datetime.combine(next_month, time.min, tzinfo=tz)

    else:
        raise ValueError("Invalid period type.")

    return start, end

