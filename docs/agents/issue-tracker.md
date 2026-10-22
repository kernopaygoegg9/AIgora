# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.

## Hot files

A feature run with parallel implementers records which ticket may change each hot file in `.scratch/<feature-slug>/hot-files.toml`. `tickets-overview.md` (if any) keeps the prose and points here.

```toml
[files]
"frontend/package.json" = ["01", "06"]   # owned by tickets 01 and 06
".github/workflows/**" = ["02"]          # glob
"backend/tests/test_*_real.py" = ["03"]
"AGENTS.md" = "*"                         # any ticket may change it
```

- Keys are repo-relative paths with `/`, or globs: `*` and `?` match within one path segment, `**` matches across `/`.
- Values are a list of ticket numbers written as in the issue file names (`"07"`, not `"7"`), or `"*"` for any ticket.
- A file matched by several patterns is owned by all their tickets; `"*"` on any match frees it. Files that match no pattern are unrestricted.

Before merging an implementer branch, check it:

```sh
python scripts/check_hot_files.py --feature <slug> --ticket <NN> <base>..<branch>
```

It diffs the branch against its merge base with `<base>` (so later changes on the base are not blamed on the branch) and prints each changed hot file the ticket does not own as `path: owned by NN, NN`. Exit 0: clean; 1: violations; 2: missing table, bad TOML, or a git error.
