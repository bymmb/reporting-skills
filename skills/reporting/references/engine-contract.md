# Sales engine contract

Python 3.10+, standard library. Inputs: UTF-8 normalized CSV and explicit JSON contract. Required mappings: date, product, quantity, revenue, cost, and currency or explicit default_currency. Optional unique_id must truly be unique at row grain.

Declare inclusive non-overlapping prior/current date ranges (prior must end before current starts), labels, date_format, decimal_separator, and thousands_separator. Reject malformed numbers, dates that do not match date_format, nonfinite values, and blank required fields. A date_format such as %d/%m/%Y cannot detect day/month swaps in the source; confirm the convention before running.

Run scripts/check_examples.py to execute the acceptance cases.

Set quantity_unit only when all products use comparable units; otherwise suppress quantities and volume/mix bridge. Output decimals as strings. Preserve source SHA-256, contract SHA-256, row counts and source lines.

Malformed records block the whole numerical output. Repeated declared unique IDs block; identical rows without a unique key are retained and flagged. Valid out-of-period records are explicitly excluded. Missing currency-periods are not assumed to mean zero activity.

Exit 0: computed. Exit 2: blocked or needs_review. Computed does not establish source completeness or metric definitions. The engine does not convert currencies, apply VAT/discounts, recalculate Excel, or prove causation. Never overwrite input or contract.
