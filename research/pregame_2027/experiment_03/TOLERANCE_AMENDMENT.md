# Proposed per-PA numerical tolerance amendment

Status: for Tom's agreement. The approved normalized restart stopped at gamma=1 before challenger or outer evaluation.

Change only normalized gradient infinity tolerance from 1e-9 to 1e-8 in both L-BFGS options and the acceptance guard in run.py. Keep whole-objective/gradient normalization, all penalties, model equations, data, gamma grid, optimizer, iteration bounds and predictive gate. Preserve both earlier failures. Use another separate private restart directory and publish a new pre-fit commit. Validate synthetic gradient and saved probabilities. No numerical threshold is selected from an inspected performance result.

This relaxes the numerical acceptance criterion explicitly; it does not retrospectively accept a failed run or claim the comparison passed. If another configuration fails, stop visibly again.
