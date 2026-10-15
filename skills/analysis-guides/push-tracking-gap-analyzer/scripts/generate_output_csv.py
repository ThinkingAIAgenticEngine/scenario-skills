#!/usr/bin/env python3
'Generate nine-column CSV and lossless single-column merge operations.'

import csv
import json
import os


def safe_cell(value):
    """Keep text-like fields literal when imported through lark-cli +csv-put."""
    if isinstance(value, str) and value.startswith('='):
        return "'" + value
    return value


def generate(gap_list, header_row=1):
    if header_row < 1:
        raise ValueError("header_row must be positive")
    rows = []
    current_row = header_row  # Destination coordinate, not CSV line number

    # Header
    rows.append(["排期","事件标签","事件名","事件显示名","事件说明","属性名","属性显示名","属性类型","属性说明"])
    current_row += 1

    def write_event(evt_data, prefix=""):
        nonlocal current_row
        event_start = current_row
        props = evt_data.get('props', [])

        # First row: event info
        row = [
            "一期交付",
            evt_data['tag'],
            evt_data['name'],
            evt_data['display'],
            prefix + evt_data.get('desc', ''),
            props[0]['name'] if props else '',
            props[0]['display'] if props else '',
            props[0]['type'] if props else '',
            props[0]['desc'] if props else '',
        ]
        rows.append([safe_cell(value) for value in row])
        current_row += 1

        # Sub-property rows (5 commas = A-E empty)
        for p in props[1:]:
            row = ["","","","","",p['name'],p['display'],p['type'],p['desc']]
            rows.append([safe_cell(value) for value in row])
            current_row += 1

        event_end = current_row - 1
        return event_start, event_end

    # Build all events in order
    all_events = gap_list.get('ops_events', []) + \
                 gap_list.get('new_events', []) + \
                 gap_list.get('patch_events', [])

    event_ranges = []  # (start, end, name, tag) for merge calculation
    for evt in all_events:
        start, end = write_event(evt)
        event_ranges.append((start, end, evt['name'], evt['tag']))

    # --- Generate merge ranges ---
    merges = []
    data_start = header_row + 1 if event_ranges else None
    data_end = current_row - 1 if event_ranges else None

    if len(event_ranges) > 0:
        # A column: phase label across all data rows
        merges.append(('A', data_start, data_end))

        # Merge only contiguous tag runs, preserving intervening labels.
        group_start, group_end, _, group_tag = event_ranges[0]
        for start, end, name, tag in event_ranges[1:]:
            if tag == group_tag:
                group_end = end
            else:
                merges.append(('B', group_start, group_end))
                group_start, group_end, group_tag = start, end, tag
        merges.append(('B', group_start, group_end))

        # C/D/E columns: merge per event
        for start, end, name, tag in event_ranges:
            if end > start:  # only merge if event has >1 row
                merges.append(('C', start, end))
                merges.append(('D', start, end))
                merges.append(('E', start, end))

        # Preserve every property description in I; never merge this column.

    # Convert to lark-cli batch-update format
    merge_ops = []
    for col, start, end in merges:
        if end <= start:
            continue
        merge_ops.append({
            'shortcut': '+cells-merge',
            'input': {'sheet_id': '{SHEET_ID}', 'range': f'{col}{start}:{col}{end}'}
        })

    return rows, merge_ops, data_start, data_end


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--gap-list', required=True)
    p.add_argument('--output-csv', required=True)
    p.add_argument('--output-merges', required=True)
    p.add_argument('--header-row', type=int, default=1, help='Destination header row; import CSV at this row')
    args = p.parse_args()

    path = args.gap_list.lstrip('@')
    with open(path) as f:
        gap_list = json.load(f)

    rows, merges, data_start, data_end = generate(gap_list, args.header_row)
    write_csv(rows, args.output_csv)

    os.makedirs(os.path.dirname(args.output_merges) or '.', exist_ok=True)
    with open(args.output_merges, 'w', encoding='utf-8') as f:
        json.dump(merges, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        'status': 'SUCCESS',
        'row_count': len(rows),
        'merge_count': len(merges),
        'data_rows': f'{data_start}-{data_end}' if data_start is not None else None
    }))
