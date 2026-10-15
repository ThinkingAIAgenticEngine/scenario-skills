#!/usr/bin/env python3
'Check proposed properties against all event and public property definitions.'

import json
import os
import sys


def check_properties(tracking_data, additions):
    events = tracking_data.get('events', {})
    public_props = tracking_data.get('public_props', {})
    results = []
    seen_additions = {}

    for item in additions:
        prop = item['prop']
        evt = item['event']
        display = item.get('display', '')
        ptype = item.get('type', '')
        addition_key = (evt, prop)

        result = {
            'event': evt,
            'prop': prop,
            'status': 'new',
            'conflict_detail': None,
            'recommended_name': prop,
            'recommended_display': display,
            'recommended_type': ptype,
        }

        if addition_key in seen_additions:
            first = seen_additions[addition_key]
            result['recommended_display'] = first['display']
            result['recommended_type'] = first['type']
            if display != first['display'] or ptype != first['type']:
                result['status'] = 'conflict'
                result['conflict_detail'] = (
                    'Repeated proposal has inconsistent metadata; first proposal: '
                    f"display={first['display']}, type={first['type']}"
                )
            else:
                result['status'] = 'duplicate_in_additions'
                result['conflict_detail'] = (
                    f'Already proposed for {evt}; keep one addition only'
                )
            results.append(result)
            continue

        seen_additions[addition_key] = {'display': display, 'type': ptype}

        # Compare all definitions, including same-event and public fields.
        occurrences = []
        if prop in public_props:
            occurrences.append(('public', public_props[prop]))
        for other_evt, info in events.items():
            if prop in info.get('props', {}):
                occurrences.append((other_evt, info['props'][prop]))
        conflicts = [(where, item) for where, item in occurrences
                     if display != item.get('display', '') or ptype != item.get('type', '')]
        if occurrences:
            source, existing = (conflicts or occurrences)[0]
            result['recommended_display'] = existing.get('display', '')
            result['recommended_type'] = existing.get('type', '')
            if conflicts:
                result['status'] = 'conflict'
                result['conflict_detail'] = '; '.join(
                    f"{where}: display={item.get('display', '')}, type={item.get('type', '')}"
                    for where, item in conflicts)
            elif evt in events and prop in events[evt].get('props', {}):
                result['status'] = 'duplicate_on_event'
                result['conflict_detail'] = f"Already present on {evt}"
            elif prop in public_props:
                result['status'] = 'public_prop'
                result['conflict_detail'] = 'Already defined as a public property'
            else:
                result['status'] = 'exists_elsewhere'
                result['conflict_detail'] = f"Reuse the definition from {source}"

        results.append(result)

    # Summary
    summary = {
        'new_count': sum(1 for r in results if r['status'] == 'new'),
        'conflict_count': sum(1 for r in results if r['status'] == 'conflict'),
        'public_prop_count': sum(1 for r in results if r['status'] == 'public_prop'),
        'duplicate_on_event_count': sum(1 for r in results if r['status'] == 'duplicate_on_event'),
        'duplicate_in_additions_count': sum(
            1 for r in results if r['status'] == 'duplicate_in_additions'
        ),
        'exists_elsewhere_count': sum(1 for r in results if r['status'] == 'exists_elsewhere'),
    }

    return {'results': results, 'summary': summary}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--tracking-data', required=True)
    p.add_argument('--additions', required=True, help='JSON file with additions list, or @filename')
    p.add_argument('--output', required=True)
    args = p.parse_args()

    with open(args.tracking_data) as f:
        tracking_data = json.load(f)

    # Load additions
    additions_path = args.additions.lstrip('@')
    with open(additions_path) as f:
        additions = json.load(f)

    result = check_properties(tracking_data, additions)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    s = result['summary']
    has_errors = (
        s['conflict_count'] > 0
        or s['duplicate_on_event_count'] > 0
        or s['duplicate_in_additions_count'] > 0
    )
    status = 'ERROR' if has_errors else 'SUCCESS'
    print(json.dumps({'status': status, 'summary': s}))
    if has_errors:
        sys.exit(1)
