# CPIC test evidence

`cpic_carbamazepine.json` contains a successful live retrieval from
**2026-10-19, 22:55:49.034971 UTC**: one drug, one guideline, 24 recommendations,
and two publications. Original fields, request URLs, timestamps, and versions are
preserved. It supports offline tests and explicitly selected snapshot runs.

Sources:

- [Drug](https://api.cpicpgx.org/v1/drug?name=eq.carbamazepine)
- [Guideline](https://api.cpicpgx.org/v1/guideline?id=eq.100423)
- [Recommendations](https://api.cpicpgx.org/v1/recommendation?drugid=eq.RxNorm:2002)
- [Publications](https://api.cpicpgx.org/v1/publication?guidelineid=eq.100423)
- [Guideline publication, Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC5847474/)
- [CPIC data documentation](https://github.com/cpicpgx/cpic-data/wiki)

Refresh from a successful live retrieval and review changes against the matching
tests. Preserve source text and follow CPIC's licensing and citation terms.
