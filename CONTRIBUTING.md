# Contributing

Thank you for helping improve Ocean Physics Simulator.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment.
3. Install `requirements.txt`.
4. Create a focused feature branch.
5. Run the simulator and verify the factors affected by your change.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python ocean_wave_simulator.py
```

## Pull requests

- Keep each pull request focused on one improvement.
- Explain the physical or visual behavior being changed.
- Include before/after screenshots for interface changes.
- Preserve interactive performance at the default grid and mode counts.
- Note whether a change is physically derived, empirically approximated, or
  intended only for visualization.
- Update the README when adding controls or changing user-facing behavior.

## Reporting bugs

Include your operating system, Python version, the command used to launch the
simulator, and the full error message. A screenshot and the factor values that
triggered the issue are especially useful.

## Scientific changes

When improving the model, cite a primary reference or established textbook
where practical. Keep the distinction between educational approximations and
validated forecasting methods explicit.
