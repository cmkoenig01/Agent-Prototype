# AIM pharmacogenetics prototype

Match fictional patient genetic results to CPIC prescribing guidance.

**Current scope:** adults considering carbamazepine for the first time. The application
uses Python rules and live CPIC evidence; it does not use a language model. Reports
cover the checked genetic results, not overall medication suitability.

![Current application workflow](docs/architecture.png)

[Diagram source](docs/architecture.mmd) · [Development roadmap](docs/ROADMAP.md)

## Setup

From your existing clone's root directory (the folder containing `pyproject.toml`),
switch to the application branch. Save any local changes first.

```sh
git fetch origin
git switch kush/aim-prototype
git pull --ff-only
```

Install **uv** if needed:

| Platform | Install command |
| --- | --- |
| macOS | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows PowerShell | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

After installing uv, reopen your terminal in the repo root. Install the project:

```sh
uv sync --locked
```

This creates or updates the project's `.venv` using `uv.lock`, including Python 3.13
if needed. Activate it in each new terminal:

| Platform | Activate |
| --- | --- |
| macOS | `source .venv/bin/activate` |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |

## Run

With the environment active, choose a patient file:

```sh
aim-pgx --case examples/hla_b_positive_a_unknown.json
```

`aim-pgx` is the installed application; `--case` selects the fictional patient JSON.
Change the filename to try another case:

| File in `examples/` | Scenario |
| --- | --- |
| `hla_b_positive_a_unknown.json` | HLA-B positive; HLA-A result unknown |
| `hla_a_positive_alternatives.json` | HLA-A positive; alternatives available |
| `hla_a_positive_no_alternatives.json` | HLA-A positive; alternatives unavailable |
| `hla_a_positive_alternatives_unknown.json` | Alternative availability unknown |
| `both_negative.json` | Both checked alleles negative |
| `both_results_missing.json` | Both results unknown |

Each report shows the patient facts, applicable guidance, missing information, and
sources. Unknown results remain unknown. Copy an example to create a new case.

HLA-A and HLA-B are genes; HLA-A*31:01 and HLA-B*15:02 are specific versions (alleles).
Their input values are `positive`, `negative`, or `unknown`. CPIC is the Clinical
Pharmacogenetics Implementation Consortium, the source of the prescribing guidance.

Useful options:

- `--details`: include source comments, lookup keys, versions, and publication links.
- `--snapshot tests/fixtures/cpic_carbamazepine.json`: use saved evidence offline.
- `--save-snapshot snapshots/cpic.json`: save evidence from a successful live run.
- `--help`: list options.

Live retrieval is the default. Snapshots show their retrieval date; live failures
produce an error rather than switching to saved evidence.

**About `uv run`:** `uv run --locked aim-pgx --case examples/both_negative.json`
uses the same project `.venv`, checks its dependencies, and runs the command there.
It does not activate your shell. `--locked` prevents lockfile changes. With the
environment already activated, the plain `aim-pgx` command above is sufficient.

## Development

Code lives in `src/aim_pgx/`: `cli.py` handles input, `cpic.py` retrieves evidence,
`matching.py` applies the rules, and `reporting.py` formats results.

With the environment active:

```sh
pytest
ruff check src tests
ruff format --check src tests
```

Tests use saved evidence and run offline.

## References

- [CPIC API documentation](https://github.com/cpicpgx/cpic-data/wiki)
- [Carbamazepine/HLA guideline, Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC5847474/)
- [Test evidence provenance](tests/fixtures/README.md)
- [uv installation](https://docs.astral.sh/uv/getting-started/installation/) · [Project environments](https://docs.astral.sh/uv/concepts/projects/run/)
