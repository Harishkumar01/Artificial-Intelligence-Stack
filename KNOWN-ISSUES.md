# Verification and known limitations

**Security update:** Supporting dependency pins, the local viewer launcher, and evaluation error classification were updated after the live runs described below. Those historical live results do not constitute a new live test of this archive. The security update is verified with fresh installations, offline SDK checks, recorded-result replay, and local viewer tests. Models, scoring criteria, reference datasets, and unfinished exercises are preserved.

The completed learner configuration and the separate reference configuration each ran all 11 rows against the live `gpt-5` model on 2026-09-01. There were no runtime/grader errors. They produced 6/11 and 7/11 passing rows respectively; this illustrates grading variability, not a required pass count. Rubrics and thresholds are unchanged.

The course document uses `gpt-5.6-terra` where the repository uses `gpt-5`. The repository choice is retained; course editorial reconciliation is still needed. This lab uses Promptfoo and OpenAI model graders, not the OpenAI Evals API directly. The screenshot shows an earlier illustrative run.

All starter TODOs remain. Generated answers, evaluation histories, credentials, prior resource IDs, and unrelated labs are excluded. Windows and Linux instructions were reviewed, not runtime-tested on those systems. The verification host was macOS with Python 3.13.0 and Node 24.19.0; Python 3.12 was not executed.

The standard [MIT license](LICENSE) was added at the packaging requester’s direction; original source attribution is retained in [ATTRIBUTION.md](ATTRIBUTION.md).
