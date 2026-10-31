#!/usr/bin/env python3
"""Reconcile explicitly mapped sales CSVs. Python 3.10+, standard library only."""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

ZERO = Decimal(0)
TOLERANCE = Decimal('0.000001')
FIELDS = ('quantity', 'revenue', 'cost')


def number(raw, decimal_separator, thousands_separator):
    s = raw.strip()
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    group = re.escape(thousands_separator) if thousands_separator else None
    integer = rf'(?:[0-9]+|[0-9]{{1,3}}(?:{group}[0-9]{{3}})+)' if group else r'[0-9]+'
    pattern = rf'[+-]?{integer}(?:{re.escape(decimal_separator)}[0-9]+)?'
    if not re.fullmatch(pattern, s):
        raise ValueError('invalid numeric format')
    if thousands_separator:
        s = s.replace(thousands_separator, '')
    value = Decimal(s.replace(decimal_separator, '.'))
    if not value.is_finite() or len(value.as_tuple().digits) > 24:
        raise ValueError('nonfinite or over-precision number (maximum 24 digits)')
    return value


def total(rows):
    result = {k: sum((r[k] for r in rows), ZERO) for k in FIELDS}
    result['gross_profit'] = result['revenue'] - result['cost']
    result['margin'] = result['gross_profit'] / result['revenue'] if result['revenue'] > 0 else None
    result['row_count'] = len(rows)
    return result


def growth(current, prior):
    return (current - prior) / prior if prior > 0 else None


def eligible(t):
    return t['quantity'] > 0 and t['revenue'] > 0 and t['cost'] >= 0


def bridge(products):
    result = dict.fromkeys(('volume', 'mix', 'price', 'unit_cost', 'entrants', 'exits', 'other_adjustments'), ZERO)
    common = []
    for p in products:
        a, b = p['prior'], p['current']
        if a['row_count'] and b['row_count'] and eligible(a) and eligible(b):
            common.append((a, b))
        elif not a['row_count'] and eligible(b):
            result['entrants'] += b['gross_profit']
        elif not b['row_count'] and eligible(a):
            result['exits'] -= a['gross_profit']
        else:
            result['other_adjustments'] += b['gross_profit'] - a['gross_profit']
    q0 = sum((a['quantity'] for a, _ in common), ZERO)
    q1 = sum((b['quantity'] for _, b in common), ZERO)
    if common:
        for a, b in common:
            m0 = a['gross_profit'] / a['quantity']
            result['volume'] += (q1-q0) * a['quantity']/q0 * m0
            result['mix'] += q1 * (b['quantity']/q1 - a['quantity']/q0) * m0
            result['price'] += b['quantity'] * (b['revenue']/b['quantity'] - a['revenue']/a['quantity'])
            result['unit_cost'] -= b['quantity'] * (b['cost']/b['quantity'] - a['cost']/a['quantity'])
    expected = sum((p['gross_profit_change'] for p in products), ZERO)
    residual = expected - sum(result.values(), ZERO)
    return {'order': ['volume', 'mix', 'price', 'unit_cost'], 'components': result,
            'gross_profit_change': expected, 'residual': residual,
            'tolerance': TOLERANCE, 'reconciled': abs(residual) <= TOLERANCE,
            'interpretation': 'Order-dependent arithmetic decomposition; not causal attribution.'}


def validate_contract(c):
    if not isinstance(c, dict) or not isinstance(c.get('columns'), dict) or not isinstance(c.get('periods'), dict):
        raise ValueError('contract, columns, and periods must be JSON objects')
    columns = c['columns']
    for key in ('date', 'product', *FIELDS):
        if not isinstance(columns.get(key), str) or not columns[key]:
            raise ValueError(f'missing column mapping: {key}')
    if any(not isinstance(v, str) or not v for v in columns.values()):
        raise ValueError('column mappings must be nonempty strings')
    if not columns.get('currency') and (not isinstance(c.get('default_currency'), str) or not c['default_currency'].strip()):
        raise ValueError('map currency or supply default_currency')
    if len(set(columns.values())) != len(columns):
        raise ValueError('column mappings must be distinct')
    dec, sep = c['decimal_separator'], c['thousands_separator']
    if dec not in ('.', ',') or sep not in ('', '.', ',', ' ', '\u00a0') or dec == sep:
        raise ValueError('invalid decimal/thousands separators')
    if not isinstance(c['date_format'], str) or not c['date_format']:
        raise ValueError('date_format is required')
    if c.get('quantity_unit') is not None and (not isinstance(c['quantity_unit'], str) or not c['quantity_unit'].strip()):
        raise ValueError('quantity_unit must be a nonempty string or null')
    ranges = {}
    for key in ('prior', 'current'):
        p = c['periods'][key]
        if not isinstance(p, dict):
            raise ValueError(f'period must be a JSON object: {key}')
        start, end = date.fromisoformat(p['start']), date.fromisoformat(p['end'])
        if start > end or not p.get('label'):
            raise ValueError(f'invalid period: {key}')
        ranges[key] = (start, end)
    if max(ranges['prior'][0], ranges['current'][0]) <= min(ranges['prior'][1], ranges['current'][1]):
        raise ValueError('comparison periods must not overlap')
    return ranges


def analyze(input_path, config_path):
    source = Path(input_path).read_bytes()
    config_bytes = Path(config_path).read_bytes()
    c = json.loads(config_bytes)
    ranges = validate_contract(c)
    columns = c['columns']
    result = {'schema_version': '1.0', 'status': 'blocked',
              'source': {'path': str(Path(input_path).resolve()), 'sha256': hashlib.sha256(source).hexdigest()},
              'contract_sha256': hashlib.sha256(config_bytes).hexdigest(), 'contract': c,
              'input_rows': 0, 'outside_period_rows': 0, 'flags': [], 'errors': [], 'currencies': {}}
    reader = csv.DictReader(io.StringIO(source.decode('utf-8-sig'), newline=''))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError('CSV headers must be nonempty and unique')
    missing = set(columns.values()) - set(reader.fieldnames)
    if missing:
        raise ValueError('missing CSV columns: ' + ', '.join(sorted(missing)))
    grouped = defaultdict(lambda: {'prior': [], 'current': []})
    keys, seen = set(), set()
    period_count = Counter()
    for raw in reader:
        result['input_rows'] += 1
        line = reader.line_num
        try:
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError('row width does not match CSV header')
            if any(not raw[v].strip() for v in columns.values()):
                raise ValueError('blank required mapped field')
            key = columns.get('unique_id')
            if key:
                identifier = raw[key].strip()
                if identifier in keys:
                    raise ValueError('duplicate declared unique_id')
                keys.add(identifier)
            else:
                signature = tuple(raw[k] for k in reader.fieldnames)
                if signature in seen:
                    result['flags'].append({'code': 'identical_row_retained', 'line': line})
                seen.add(signature)
            when = datetime.strptime(raw[columns['date']].strip(), c['date_format']).date()
            record = {k: number(raw[columns[k]], c['decimal_separator'], c['thousands_separator']) for k in FIELDS}
            record['product'] = raw[columns['product']].strip()
            record['line'] = line
            currency = raw[columns['currency']].strip() if columns.get('currency') else str(c['default_currency']).strip()
            if not currency:
                raise ValueError('blank currency')
            period = next((k for k, (start, end) in ranges.items() if start <= when <= end), None)
            if not period:
                result['outside_period_rows'] += 1
                continue
            if any(record[k] < 0 for k in FIELDS) or record['quantity'] == 0:
                result['flags'].append({'code': 'signed_or_zero_quantity_entry', 'line': line, 'currency': currency})
            grouped[currency][period].append(record)
            period_count[period] += 1
        except (ValueError, InvalidOperation) as exc:
            result['errors'].append({'line': line, 'message': str(exc)})
    for period in ('prior', 'current'):
        if not period_count[period]:
            result['errors'].append({'period': period, 'message': 'no valid rows in reporting period; absence is not confirmed zero'})
    if result['errors']:
        return result
    for currency, periods in sorted(grouped.items()):
        a, b = total(periods['prior']), total(periods['current'])
        comparable = bool(a['row_count'] and b['row_count'])
        products = []
        for product in sorted({r['product'] for rows in periods.values() for r in rows}):
            x = total([r for r in periods['prior'] if r['product'] == product])
            y = total([r for r in periods['current'] if r['product'] == product])
            products.append({'product': product, 'prior': x, 'current': y,
                             'gross_profit_change': y['gross_profit']-x['gross_profit']})
        change = {k: b[k] - a[k] for k in ('revenue', 'cost', 'gross_profit')}
        contribution_residual = change['gross_profit'] - sum((p['gross_profit_change'] for p in products), ZERO)
        entry = {'prior': a, 'current': b, 'comparison_established': comparable,
                 'absolute_change': change if comparable else None,
                 'growth': {k: growth(b[k], a[k]) for k in change} if comparable else None,
                 'margin_change_percentage_points': (b['margin']-a['margin'])*100 if comparable and a['margin'] is not None and b['margin'] is not None else None,
                 'products': sorted(products, key=lambda p: abs(p['gross_profit_change']), reverse=True),
                 'source_lines': {k: [r['line'] for r in rows] for k, rows in periods.items()},
                 'reconciliation': {'product_gp_residual': contribution_residual, 'tolerance': TOLERANCE,
                                    'reconciled': abs(contribution_residual) <= TOLERANCE},
                 'profit_bridge': bridge(products) if comparable and c.get('quantity_unit') else None}
        if not comparable:
            result['flags'].append({'code': 'missing_currency_period', 'currency': currency,
                                    'message': 'Missing period totals are placeholders, not confirmed zero; product changes are provisional.'})
        if not c.get('quantity_unit'):
            for item in (a, b, *(p[k] for p in products for k in ('prior', 'current'))):
                item['quantity'] = None
        result['currencies'][currency] = entry
    result['flags'].append({'code': 'source_completeness_not_verified', 'message': 'Confirm cutoff and full coverage outside this engine.'})
    if not c.get('quantity_unit'):
        result['flags'].append({'code': 'quantity_and_bridge_suppressed', 'message': 'Comparable quantity unit not declared.'})
    blocked = any(not e['comparison_established'] or not e['reconciliation']['reconciled'] or
                  (e['profit_bridge'] is not None and not e['profit_bridge']['reconciled']) for e in result['currencies'].values())
    result['status'] = 'needs_review' if blocked else 'computed'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    output = Path(args.out).resolve()
    sources = (Path(args.input).resolve(), Path(args.config).resolve())
    if output in sources or (output.exists() and any(p.exists() and output.samefile(p) for p in sources)):
        parser.error('output must differ from input and config')
    try:
        with localcontext() as ctx:
            ctx.prec = 60
            result = analyze(args.input, args.config)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, UnicodeError, InvalidOperation) as exc:
        result = {'schema_version': '1.0', 'status': 'blocked', 'errors': [{'message': str(exc)}]}
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    except OSError as exc:
        print(f'Cannot write result: {exc}', file=sys.stderr)
        return 2
    print(f"{result['status']}: {output}")
    return 0 if result['status'] == 'computed' else 2


if __name__ == '__main__':
    sys.exit(main())
