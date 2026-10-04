# Development workflow

## Start each task

Read `../AGENTS.md` and its mandatory documents. Inspect Git status and the
existing implementation. State the intended outcome and relevant acceptance
criteria. Preserve unrelated edits. Implement only within authorized scope.

## Batch size

A batch is one coherent, reviewable outcome, including its relevant tests and
documentation. Normal size: 3–8 manually authored files; never pad small work.
Default upper bound: 12 files and approximately 500 added/removed lines.
Generated files and lockfiles are excluded from this estimate but still reviewed.

Split work that exceeds either bound into independently understandable batches.
Do not split in a way that leaves the application broken or omits necessary
verification. A necessary exception must be explained in the progress report
with its reason and verification. Initial documentation bootstrap is exempt
from these numeric limits because it establishes the complete reading contract.

Recommended sequence: contract/model → implementation → integration, with
tests and docs attached to each relevant step rather than deferred wholesale.

## Batch boundary

1. Inspect the complete diff for scope, correctness, secrets, and unrelated edits.
2. Run checks relevant to behavior; record unavailable environments honestly.
3. Update affected specifications, roadmap items, and changelog when appropriate.
4. Summarize completed work, evidence, limitations, and next batch.
5. Commit if commit/implementation work is authorized and the batch is complete.

Do not continue accumulating unrelated changes after reaching a boundary.
Physical acceptance and CI results are separate from local test results.

## Commit authorization and timing

A request to create documentation alone does not authorize committing it.
If the user authorizes commits or asks for implementation with commits, commit
each coherent completed batch after relevant checks. Authorization persists
within that task. Do not ask again for routine batch commits already authorized.
Do not commit failing implementation as completed work. If intentionally saving
an incomplete checkpoint is requested, label it clearly and report limitations.

Never push, create tags, publish releases, or modify live installations without
authorization covering that action. A roadmap is not authorization.

## Commit format and staging

Use `type(scope): concise imperative summary`, for example:

```text
docs(project): define product and development contracts
feat(daemon): reconcile tablet switch after resume
fix(updater): retain previous version on failed activation
test(state): cover conflicting sensor observations
```

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`.
Use a body for meaningful rationale, compatibility changes, and limitations.
Commit one outcome, not arbitrary file groups. Stage explicit paths; inspect
the staged diff. Avoid `git add .`, unrelated edits, amend/rebase of shared
history, and fabricated authorship. New branches use `codex/` unless instructed
otherwise. Do not create a branch merely to edit documentation unless needed.

## Verification

Before code exists, validate documentation links, consistency, and whitespace.
Once Rust tooling exists: formatting, Clippy, relevant tests, and Linux builds
as defined by CI. Do not invent passing commands or install tooling unnecessarily.
See `testing.md` for behavior-specific acceptance.

## Documentation rules

Public repository documentation is English. User communication may be German.
Use UTF-8. Mark planned features clearly. Update decisions before implementing
changes to agreed architecture. Never turn a proposed device into tested support
or mark a roadmap item complete without evidence.

## Executable development checks

The workspace pins Rust 1.99. On Linux, install GTK4/libadwaita development
libraries, a C compiler, pkg-config, Node/npm, Python 3 and OpenSSL as build
prerequisites. These OS prerequisites do not replace project-owned distribution.

```sh
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
cargo build --workspace --release --locked
(cd extension && npm ci && npm test)
python3 -m unittest discover -s updater -t . -v
python3 -m unittest discover -s installer -t . -v
python3 scripts/check-docs.py
```

The isolated session integration test requires a private bus:
`timeout 90s dbus-run-session -- cargo test -p convertibled-session -- --ignored`.
The native startup scripts create disposable display/bus contexts and never
install into the developer's real GNOME profile. See testing.md for limits.
Workspace path dependency version and extension package version must stay in
sync with the canonical workspace version when preparing a version change.
