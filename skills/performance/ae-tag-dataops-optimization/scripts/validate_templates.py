#!/usr/bin/env python3
"""Synthetic SQLite-adapted semantic checks; validate platform syntax, date parameters, and schedules separately."""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re
import sqlite3


class CountIf:
    def __init__(self):
        self.count = 0

    def step(self, value):
        self.count += bool(value)

    def finalize(self):
        return self.count


class Scenario:
    def __init__(self, assets, offset):
        self.assets, self.offset = assets, offset
        self.start = dt.date(2026, 1, 1)
        self.today = dt.date(2026, 1, 10)
        self.back = math.ceil(max(offset + 12, 0) / 24)
        self.forward = math.ceil(max(14 - offset, 0) / 24)
        minutes = round(abs(offset) * 60)
        self.zone = ('+' if offset >= 0 else '-') + f'{minutes // 60:02d}:{minutes % 60:02d}'
        self.c = sqlite3.connect(':memory:')
        self.c.create_aggregate('count_if', 1, CountIf)
        self.c.create_function('date_add', 3, self.date_add)
        self.c.create_function('as_timestamp', 1, lambda value: value[:10] + ' 00:00:00')
        self.c.create_function('biz_time', 3, self.biz_time)
        self.c.create_function('assert_valid', 1, self.assert_valid)
        self.c.executescript('''
          CREATE TABLE events(uid INTEGER, event_time TEXT, part_date TEXT,
                              event_name TEXT, amount INTEGER, event_zone REAL);
          CREATE TABLE daily_data(user_id INTEGER,daily_amount INTEGER,event_count INTEGER,stat_date TEXT);
          CREATE TABLE state(user_id INTEGER,total_amount INTEGER,event_count INTEGER,stat_date TEXT);
        ''')
        self.expected_events = []

    @staticmethod
    def date_add(unit, value, day):
        assert unit == 'day'
        return (dt.date.fromisoformat(day[:10]) + dt.timedelta(days=value)).isoformat()

    @staticmethod
    def biz_time(value, event_offset, target):
        when = dt.datetime.fromisoformat(value)
        if event_offset is not None and -12 <= event_offset <= 14:
            when += dt.timedelta(hours=target - event_offset)
        return when.isoformat(sep=' ', timespec='seconds')

    @staticmethod
    def assert_valid(value):
        if not value:
            raise ValueError('validation gate rejected the fixture')
        return 1

    def sql(self, name, day):
        text = (self.assets / name).read_text()
        bindings = {
            'ACCEPTANCE_TABLE': 'acceptance',
            'DAILY_TABLE': 'daily_data', 'STATE_TABLE': 'state', 'EVENT_TABLE': 'events',
            'USER_ID': 'uid', 'EVENT_NAME': 'event_name', 'PART_DATE': 'part_date',
            'AMOUNT': 'amount', 'USER_ID_TYPE': 'BIGINT', 'AMOUNT_TYPE': 'BIGINT',
            'TARGET_EVENT_LITERALS': "'metric_event','adjustment_event'",
            'BUSINESS_TIME_EXPR': "biz_time(event_time,event_zone,CAST('${tag_tz_offset}' AS DOUBLE))",
            'HISTORY_START_TS': str(self.start) + ' 00:00:00',
            'HISTORY_PART_START': str(self.start - dt.timedelta(days=self.back)),
            'SCAN_BACK_DAYS': str(self.back), 'SCAN_FORWARD_DAYS': str(self.forward),
        }
        for key, value in bindings.items():
            text = text.replace('{{' + key + '}}', value)
        for key, value in {'bd': day, 'tag_tz_offset': str(self.offset), 'tag_tz_name': self.zone}.items():
            text = text.replace('${' + key + '}', str(value))
        # Test only the documented single-day selection, not TE's macro expander.
        next_day = dt.date.fromisoformat(str(day)) + dt.timedelta(days=1)
        text = text.replace('${PartDate:date1}',
                            f'''"$part_date"='{day}' AND "@vpc_tz_#event_time">='{day} 00:00:00'
                            AND "@vpc_tz_#event_time"<'{next_day} 00:00:00' ''')
        text = re.sub(r'--[^\n]*', '', text)
        assert not re.search(r'\{\{.*?\}\}|\$\{', text), name
        text = re.sub(r"CAST\(CURRENT_TIMESTAMP AT TIME ZONE '[^']+' AS DATE\)",
                      f"'{self.today}'", text)
        text = re.sub(r"\b(?:DATE|TIMESTAMP) ('[^']+')", r'\1', text)
        text = re.sub(r"CAST\((date_add\('day',\s*-?\d+,\s*'[^']+'\)) AS TIMESTAMP\)",
                      r'as_timestamp(\1)', text)
        text = re.sub(r"CAST\(('[^']+'|stat_date) AS TIMESTAMP\)", r'as_timestamp(\1)', text)
        # SQLite returns NULL on division by zero. Preserve fail-closed behavior
        # with a raising UDF while leaving every predicate from the template intact.
        text = text.replace('1/IF(', 'assert_valid(')
        text = re.sub(r',\s*1,\s*0\)(\s+AS)', r')\1', text)
        return text

    def execute(self, name, day):
        return self.c.execute(self.sql(name, day))

    def event(self, user, business_time, kind, amount, zone=None):
        business = dt.datetime.fromisoformat(business_time)
        zone = self.offset if zone is None else zone
        raw = business + dt.timedelta(hours=zone - self.offset)
        self.c.execute('INSERT INTO events VALUES (?,?,?,?,?,?)',
                       (user, str(raw), str(raw.date()), kind, amount, zone))
        # Independent expected business time is the input, not SQL normalization.
        self.expected_events.append((user, business, kind, amount))

    def rows(self, day, table='state'):
        assert table in ['state', 'daily']
        return self.c.execute(f'SELECT * FROM {table + ("_data" if table == "daily" else "")} WHERE stat_date=? ORDER BY user_id',
                              (str(day),)).fetchall()

    def all_rows(self):
        return (self.c.execute('SELECT * FROM state ORDER BY stat_date,user_id').fetchall(),
                self.c.execute('SELECT * FROM daily_data ORDER BY stat_date,user_id').fetchall())

    def initialize(self, day):
        self.execute('03_check_business_date.sql', day)
        self.c.execute('CREATE TABLE IF NOT EXISTS acceptance (user_count BIGINT, stat_date VARCHAR)')
        self.c.execute('DELETE FROM acceptance WHERE stat_date=?', (day,))
        self.execute('08_clear_state_partition.sql', day)
        self.execute('11_initialize.sql', day)
        self.reconcile(day)
        self.publish_acceptance(day)

    def publish_acceptance(self, day):
        self.c.execute('INSERT INTO acceptance SELECT COUNT(*), ? FROM state WHERE stat_date=?', (day, day))

    def merge_after_daily(self, day):
        self.execute('06_check_daily.sql', day).fetchall()
        self.execute('07_check_previous.sql', day).fetchall()
        self.c.execute('DELETE FROM acceptance WHERE stat_date=?', (day,))
        self.execute('08_clear_state_partition.sql', day)
        self.execute('09_merge.sql', day)
        self.execute('10_check_cumulative.sql', day).fetchall()
        self.publish_acceptance(day)

    def rebuild(self, day):
        self.execute('03_check_business_date.sql', day).fetchall()
        self.execute('04_clear_daily_partition.sql', day)
        self.execute('05_daily.sql', day)
        self.merge_after_daily(day)

    def expected(self, day):
        cutoff = dt.datetime.combine(dt.date.fromisoformat(str(day)) + dt.timedelta(days=1), dt.time())
        groups = {}
        for user, when, kind, amount in self.expected_events:
            if kind not in ['metric_event', 'adjustment_event'] or not dt.datetime.combine(self.start, dt.time()) <= when < cutoff:
                continue
            entry = groups.setdefault(user, [None, 0])
            entry[1] += 1
            if amount is not None:
                entry[0] = (entry[0] or 0) + amount
        return [(user, *state, str(day)) for user, state in sorted(groups.items())]

    def reconcile(self, day):
        row = self.execute('12_reconcile_full.sql', day).fetchone()
        assert row[0] == row[1] and row[2:7] == (0, 0, 0, 0, 0), (day, row)
        assert self.rows(day) == self.expected(day), (day, self.rows(day), self.expected(day))

    def rejects(self, operation):
        try:
            operation()
        except sqlite3.OperationalError as error:
            if str(error) != "user-defined function raised exception":
                raise
            return
        raise AssertionError('a required validation gate did not reject')


def check(assets, offset):
    x = Scenario(assets, offset)
    b, d, e, f = '2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04'
    for args in [
        (1, '2025-12-31 23:59:59', 'metric_event', 999),
        (1, b + ' 00:00:00', 'metric_event', 10),
        (2, b + ' 11:00:00', 'metric_event', None),
        (3, b + ' 12:00:00', 'metric_event', 0),
        (4, b + ' 13:00:00', 'adjustment_event', -2),
        (1, d + ' 11:00:00', 'metric_event', 5),
        (1, d + ' 12:00:00', 'adjustment_event', -2),
        (2, d + ' 13:00:00', 'metric_event', 4),
        (4, d + ' 14:00:00', 'metric_event', None),
        (5, d + ' 15:00:00', 'metric_event', None),
        (6, d + ' 16:00:00', 'metric_event', 0),
        (7, d + ' 00:30:00', 'metric_event', 2, -12),
        (8, d + ' 23:30:00', 'metric_event', 3, 14),
        (9, e + ' 00:00:00', 'metric_event', 100),
        (1, e + ' 12:00:00', 'adjustment_event', -13),
        (10, e + ' 13:00:00', 'metric_event', None),
        (20, e + ' 14:00:00', 'other', 999),
    ]:
        x.event(*args)
    x.initialize(b)
    baseline = x.rows(b)
    x.rebuild(d)
    x.reconcile(d)
    first = x.rows(d)
    assert {r[0]: r[1] for r in first} == {1: 13, 2: 4, 3: 0, 4: -2, 5: None, 6: 0, 7: 2, 8: 3}
    x.rebuild(d)
    assert x.rows(d) == first and x.rows(b) == baseline

    x.c.execute('DELETE FROM state WHERE stat_date=? AND user_id=?', (b, baseline[0][0]))
    assert x.rows(b) and len(x.rows(b)) == len(baseline) - 1
    x.rejects(lambda: x.merge_after_daily(d))
    assert x.rows(d) == first
    assert x.c.execute('SELECT user_count FROM acceptance WHERE stat_date=?', (d,)).fetchall() == [(len(first),)]
    x.c.execute('INSERT INTO state VALUES (?, ?, ?, ?)', baseline[0])
    x.c.execute('DELETE FROM acceptance WHERE stat_date=?', (b,))
    x.rejects(lambda: x.merge_after_daily(d))
    assert x.rows(d) == first
    x.reconcile(b)
    x.publish_acceptance(b)

    # A wrong/partial/duplicated daily result must fail before cumulative preSql.
    x.c.execute('UPDATE daily_data SET daily_amount=999 WHERE stat_date=? AND user_id=1', (d,))
    x.rejects(lambda: x.merge_after_daily(d))
    assert x.rows(d) == first and x.rows(b) == baseline
    x.c.execute('DELETE FROM daily_data WHERE stat_date=?', (d,))
    x.rejects(lambda: x.merge_after_daily(d))
    assert x.rows(d) == first
    x.rebuild(d)
    x.c.execute('INSERT INTO daily_data SELECT * FROM daily_data WHERE stat_date=? AND user_id=1', (d,))
    x.rejects(lambda: x.merge_after_daily(d))
    assert x.rows(d) == first
    x.rebuild(d)
    x.rebuild(e)
    x.reconcile(e)
    x.rebuild(f)
    x.reconcile(f)
    assert x.rows(f, 'daily') == [] and x.rows(f) == [(*r[:3], f) for r in x.rows(e)]

    untouched = x.all_rows()
    x.rejects(lambda: x.rebuild(str(x.today)))
    assert x.all_rows() == untouched
    selected = x.execute('13_tag_yesterday.sql', e).fetchall()
    assert sorted(selected) == [(r[0], r[1]) for r in x.rows(e)]
    assert x.execute('13_tag_yesterday.sql', '2026-01-05').fetchall() == []

    # Repairing history requires forward propagation rather than only fixing D.
    x.event(1, d + ' 15:30:00', 'metric_event', 1)
    x.rebuild(d)
    x.reconcile(d)
    stale = x.execute('12_reconcile_full.sql', e).fetchone()
    assert stale[5] > 0
    x.rebuild(e)
    x.rebuild(f)
    x.reconcile(e)
    x.reconcile(f)
    assert x.rows(b) == baseline
    return {'offset': offset, 'back_days': x.back, 'forward_days': x.forward,
            'snapshots': {day: len(x.rows(day)) for day in [b, d, e, f]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skill-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = {
        'result': 'PASS', 'engine': 'SQLite ' + sqlite3.sqlite_version,
        'scope': 'Local synthetic semantic fixtures with SQL adaptation; no TE/Trino/scheduler execution or native macro expansion.',
        'checks': ['initialization', 'signed and NULL values', 'event-count state',
                   'fractional and negative source-tag timezone offsets', 'cross-partition inclusion',
                   'exclusive next-midnight bound', 'consecutive increments', 'no-event day',
                   'daily corruption/missing/duplicate gate before cumulative cleanup',
                   'partially missing prior snapshot or missing receipt blocks cumulative cleanup',
                   'idempotent rerun', 'historical retention', 'future-day rejection before cleanup',
                   'single selected date and missing-date empty result', 'independent full reconciliation',
                   'late-correction forward rebuild'],
        'scenarios': [check(args.skill_dir / 'assets/sql', offset) for offset in [8, 5.5, -12]],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
