# Metric contract

Establish source, row grain, reporting periods, cutoff, revenue and COGS definitions, signed return treatment, currency, and comparable quantity units before calculating.

- Gross profit = net revenue - COGS. Never call it net profit without operating expenses.
- Margin = total gross profit / total revenue, not the mean of row margins. For revenue <= 0 show amounts and mark ordinary margin non-interpretable.
- For a positive prior baseline, growth = (current-prior)/prior. Otherwise show absolute movement and baseline status.
- Express margin movement in percentage points.
- Missing days do not establish zero sales or completeness. Compare aligned cutoffs.
- Keep currencies separate unless explicit rates and conversion policy are supplied.
- Do not sum kilograms, cases, and individual items as comparable units.
- Establish unique keys and join cardinality before joining or deduplicating. Never silently remove repeated rows.
- Separate observed facts, estimates, arithmetic contributions, hypotheses, and actions.
