# Arithmetic gross-profit bridge

Use a fixed currency and comparable quantity units. Aggregate each product by period.

For products eligible in both periods (q > 0, revenue > 0, cost >= 0), let p = revenue/q, c = cost/q, m = p-c, Q = cohort quantity, and s = q/Q.

In fixed order volume -> mix -> price -> unit cost:
- Volume = (Q1-Q0) * sum(s0*m0)
- Mix = Q1 * sum((s1-s0)*m0)
- Price = sum(q1*(p1-p0))
- Unit cost = -sum(q1*(c1-c0))

Eligible current-only products contribute current GP as entrants. Eligible prior-only products contribute negative prior GP as exits. Other products contribute current GP minus prior GP as other adjustments.

Reconcile all seven components to total GP change within tolerance. Retain unrounded intermediates. Aggregate-positive products can contain return lines; disclose this and separate returns when economically material.

Attribution changes with decomposition order. This is accounting arithmetic, not proof of causation. With incompatible units use exact product GP contributions and suppress volume/mix decomposition.
