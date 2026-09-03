# Architecture

`kstt.cli` owns argument parsing and delegates to independently testable modules. `Database` stores normalized targets, cases, observations, findings, and execution metadata. Integrations should construct argument arrays and call `runner.run_command`; they must never build shell strings from target input.

The default implementation uses only Python's standard library. Rich and PyYAML are optional enhancements listed in `requirements.txt`.
