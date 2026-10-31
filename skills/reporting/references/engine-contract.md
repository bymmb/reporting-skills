# Sales engine contract

Python 3.10+, standard library. Inputs: UTF-8 normalized CSV and explicit JSON contract. Required mappings: date, product, quantity, revenue, cost, and currency or explicit default_currency. Optional unique_id must truly be unique at row grain.

Declare inclusive non-overlapping prior/current date ranges, labels, date_format, decimal_separator, and thousands_separator. Reject malformed numbers, ambiguous dates, nonfinite values, and blank required fields.

Set quantity_unit only when all products use comparable units; otherwise suppress quantities and volume/mix bridge. Output decimals as strings. Preserve source SHA-256, contract SHA-256, row counts and source lines.

Malformed records block the whole numerical output. Repeated declared unique IDs block; identical rows without a unique key are retained and flagged. Valid out-of-period records are explicitly excluded. Missing currency-periods are not assumed to mean zero activity.

Exit 0: computed. Exit 2: blocked or needs_review. Computed does not establish source completeness or metric definitions. The engine does not convert currencies, apply VAT/discounts, recalculate Excel, or prove causation. Never overwrite input or contract.
