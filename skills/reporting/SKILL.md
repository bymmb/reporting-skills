---
name: reporting
description: Prepare evidence-based business reports from sales and cost data, including monthly management reporting, revenue and gross-profit comparisons, margin analysis, product-mix analysis, and explanations of rising sales with falling profit. Use when the user asks to analyze business performance, explain changes, or create a management report from tables, files, or connected data. Do not trigger for writing-only progress reports, investment advice, generic spreadsheet formatting, or an isolated formula question.
---

# Reporting

Turn a business question into a reproducible report with reconciled numbers and traceable findings. Reply in the user's language. Keep English implementation and column names out of business-facing prose.

## 1. Establish the reporting contract

Read the data and existing metric definitions before asking questions. Capture the question, audience, source, row grain, reporting periods, currency, units, revenue definition, cost definition, return treatment, and data cutoff in a compact working contract.

Ask only for information that changes the result and cannot be established from the source. Continue independent profiling while awaiting answers. Never invent a completed period, currency conversion, budget, product identifier, or cost definition.

Use gross profit = net revenue - cost of goods sold only when the inputs support those definitions. Label revenue minus an unspecified cost as a reported difference, not net profit or gross profit. Never call gross profit net profit. Consult [metric-contract.md](references/metric-contract.md) for period, sign, tax, currency, and weighting rules.

## 2. Profile before aggregating

Inspect missing fields, invalid dates and numbers, candidate duplicates, join cardinality, cancellations, negative amounts, zero quantities, currencies, and data coverage. Keep sources intact. Distinguish an invalid record from a valid return or an unusual observation.

- Identify the actual grain before joining. Aggregate one-to-many sources to a compatible grain first; reconcile row counts and amounts before and after every join.
- Do not silently drop repeated rows. Require an explicitly unique business key before treating a repeat as a duplicate defect.
- Quarantine malformed rows and state their impact. Do not present totals as complete while unresolved rows or currencies are omitted.
- Compare a partial month with the equivalent prior cutoff where supported, or mark the full-period comparison as non-comparable. File bounds alone do not prove completeness.
- Keep currencies separate unless an explicit conversion policy and rates are supplied. Never sum product quantities with incompatible units.

Stop the affected numerical conclusion when a material input is unresolved; still deliver useful inspection findings and the precise missing requirement.

## 3. Calculate and reconcile

Use available table tools, SQL, or a local runtime. Prefer existing dependencies; require no additional API account or paid service. Inspect spreadsheet formulas and cached values separately when relevant. Use the host's spreadsheet or document skills for those output formats.

For normalized CSV, use the bundled standard-library engine:

```bash
python3 scripts/analyze_sales.py --input sales.csv --config contract.json --out analysis.json
```

Resolve paths relative to this skill. Read [engine-contract.md](references/engine-contract.md) before adapting `assets/contract.example.json`. Map the actual columns explicitly, configure numeric/date conventions, and declare comparison periods and quantity units. The engine supports two non-overlapping periods, per-currency metrics, product contributions, and an arithmetic gross-profit bridge. It does not read XLSX, establish source completeness, infer business definitions, perform FX conversion, or prove causation. Export a normalized CSV locally when needed and preserve source coordinates in the evidence ledger.

If no runtime is available, use the host's reliable calculation tool or explicitly bounded manual calculations for small tables. Do not claim that scripts, reconciliations, or benchmarks ran when they did not.

Check revenue - COGS = gross profit; sum of segment totals = overall totals; and bridge components = current GP - prior GP within an explicit rounding tolerance. Calculate margins as total profit / total revenue, never the mean of row margins. Report margin changes in percentage points. Suppress conventional percentage growth where the baseline is zero or negative and show the absolute movement instead.

## 4. Explain changes with evidence

Read [profit-bridge.md](references/profit-bridge.md) when explaining performance drivers. Separate observed changes, arithmetic contributions, hypotheses, and proposed actions.

- Rank product contributions by absolute impact and show the reconciliation to total change. Include negative contributors.
- Use volume/mix/price/unit-cost decomposition only for comparable units and eligible positive sales aggregates. Keep entrants, exits, returns, and other adjustments visible as separate components.
- State decomposition order and limitations. Do not describe an order-dependent bridge as unique causal attribution.
- Attach every headline number to a source field and reproducible calculation. Preserve a compact ledger: finding ID, source location/query, filters, formula, unrounded result, and limitations.
- Do not infer demand, competitor action, seasonality, or operational failures from correlation alone. Mark untested explanations as hypotheses and specify the evidence needed to check them.

## 5. Deliver the requested report

Follow [report-spec.md](references/report-spec.md). Default to a concise management summary in conversation; create a file only when requested or useful for the requested deliverable. Use the host's saving workflow for user-facing files. Never publish, email, or schedule the report without authorization.

Lead with what changed and its business implication. Include comparable-period KPI totals, major contributors, supported next steps, definitions, source cutoff, and material limitations. Choose a chart only when it improves the explanation. Use tables for exact values. Match the requested output format rather than forcing a dashboard or slide deck.

## Release gate

Before presenting a numerical conclusion, confirm: definitions established; units/currencies handled; comparison period justified; missing/duplicate/join issues accounted for; totals reconciled; growth and margin denominators valid; bridge reconciled where used; claims traceable; unsupported causes labeled; and actual verification accurately reported. If a check fails, mark the affected conclusion provisional or blocked and explain exactly why.
