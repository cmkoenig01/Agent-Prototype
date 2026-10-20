# CPIC source fixture

`cpic_carbamazepine.json` was created by `CPICClient.retrieve` and `save_snapshot`
from successful real CPIC API requests on **2026-10-19 at 22:55:49.034971 UTC**.
It contains 24 recommendation records, one drug, one guideline, and two publications.
The source fields are retained, including fields not used in matching.

The bundle records each request URL, retrieval time, and per-record version. It is
fixed evidence for offline tests and explicitly selected snapshot assessments. Tests
do not make live CPIC requests.

Sources:

- [CPIC API data documentation](https://github.com/cpicpgx/cpic-data/wiki)
- [Carbamazepine drug](https://api.cpicpgx.org/v1/drug?name=eq.carbamazepine)
- [Linked guideline](https://api.cpicpgx.org/v1/guideline?id=eq.100423)
- [Recommendations](https://api.cpicpgx.org/v1/recommendation?drugid=eq.RxNorm:2002)
- [Publications](https://api.cpicpgx.org/v1/publication?guidelineid=eq.100423)
- [Guideline publication, Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC5847474/)

When refreshing, use a new successful live retrieval and review the clinical source
and matching expectations together. Do not edit recommendation text to make a test
pass. Consult CPIC's linked licensing and citation information before redistribution.
