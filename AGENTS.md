# Personal sunnypilot fork

## Purpose and setup

Maintain Dmitry's changes for a Tesla running sunnypilot on a comma 4. Keep the
changes as a small, understandable series of commits on top of the official
`release-mici` release, periodically carry them onto a newer upstream release,
resolve conflicts, validate, and push the result to the fork.

- Local checkout: `/Users/dmitrypopov/Documents/Dev/sunnypilot`.
- `origin`: `https://github.com/dimitrypo/sunnypilot.git` (personal fork; push here).
- `upstream`: `https://github.com/sunnypilot/sunnypilot.git` (official releases;
  fetch only, never push here).
- Working and device update branch: `release-mici`. This is also the fork's
  default branch; do not substitute `master`, `main`, or the old FrogTesla fork.
- Setup context: `codex://threads/01a0dcdf-8627-7372-a2ab-f1650ba93749`.
- Fork installer URL: `https://install.sunnypilot.ai/fork/dimitrypo/release-mici`.
  The setup task verified the URL, but did not confirm installation on the device.

The intended code changes are Python only. This is a prebuilt release tree:
preserve its binaries, models, firmware, and `prebuilt` marker. Changes requiring
compilation or different dependencies need a separately established build plan;
pushing source changes alone does not produce new compiled artifacts.

## Start every task

1. Read this file, including the current base and change register below.
2. Check `git status --short --branch`, `git remote -v`, and recent commits.
   Preserve existing work and stage only files belonging to the task.
3. Review the affected code and current upstream behavior before editing. Keep
   each change narrow and retain the intent of earlier personal changes.
4. Before executing repository code, installing dependencies, or using containers,
   follow `~/.codex/DOCKER_HARDENING.md` and its referenced playbook. Never install
   project dependencies directly on macOS.

## Implementing and committing changes

- Implement the requested behavior and inspect the resulting diff. Prefer one
  commit per independently understandable change; use multiple commits when the
  changes should be maintained or retired separately.
- Validate the affected Python behavior using appropriate available checks and
  tests. Record the actual commands, results, and anything not tested. A syntax
  check alone is not evidence that driving behavior is correct.
- Update this file in the same commit as each behavior change. Document the
  request, before/after behavior, affected files, validation, and any details that
  will matter when resolving a future upstream conflict.
- Use stable change IDs and descriptive commit subjects in the register. Commit
  hashes change during replay/rebase; do not embed a commit's own hash in itself.
- Review the staged diff and run `git diff --cached --check` before committing.
  Keep unrelated edits, generated artifacts, secrets, and driving logs out.
- Complete requested work with local commit(s). Push when publishing is included
  in the task; a documentation-only task does not require a push or device update.

## Updating from upstream

Do not assume that releases form continuous Git history. At initial setup the
checkout was shallow, and the raw current release commit also had **no parent**:
it was a genuine root snapshot. Future releases must be inspected again. The
default for replaced/squashed release snapshots is to start at the new release
and cherry-pick only our personal commits onto it.

### 1. Preserve and identify the existing patch series

- Start with a clean working tree. Preserve unrelated unfinished work separately
  before proceeding; do not discard it or silently include it in maintenance.
- Read the exact old upstream base from the current-base section below. Verify
  that it exists and is an ancestor of the personal branch. If this record or
  history is missing, recover it before choosing commits to replay.
- Fetch the two specific branches, allowing replacement of remote-tracking refs:

  ```sh
  git fetch origin +refs/heads/release-mici:refs/remotes/origin/release-mici
  git fetch upstream +refs/heads/release-mici:refs/remotes/upstream/release-mici
  ```

- Record the full fetched `origin/release-mici` SHA as the expected remote value
  for a later push. Inspect local/remote divergence and account for every remote
  commit before proceeding. A force-with-lease push does not protect remote work
  that was already present when the expected SHA was captured.
- Create a uniquely named backup branch, such as
  `backup/release-mici-YYYYMMDD-HHMMSS`, at the reconciled personal branch tip.
  Record the old base, backup tip, and new upstream SHA in the task.
- List the personal series oldest first with
  `git log --reverse --format='%H %s' OLD_BASE..BACKUP_BRANCH`. Review every entry,
  including documentation commits. `OLD_BASE` and `BACKUP_BRANCH` here are
  placeholders for the verified SHA and actual backup branch name.
  If the series contains a merge commit, inspect its parents and choose an
  explicit replay strategy; do not cherry-pick it as an ordinary commit.

### 2. Carry the changes onto the new release

- Inspect the new upstream commit and ancestry. If ancestry is unclear because
  history is shallow, fetch enough relevant history before deciding; shallow
  history by itself does not prove that upstream rewrote its branch.
- For a replaced/root snapshot, create a temporary branch such as
  `sync/release-mici-YYYYMMDD-HHMMSS` from the verified new upstream SHA. Cherry-pick
  the reviewed personal commit SHAs in their original order. Do not include the
  old upstream snapshot, unrelated upstream commits, or commits from `master`.
- If upstream preserves ancestry, a rebase is also suitable. Create the temporary
  branch at the backed-up personal tip, then use
  `git rebase --onto NEW_UPSTREAM_SHA OLD_BASE` on that temporary branch. This
  explicitly selects our patch series. Avoid blind `git pull` or a plain rebase
  that could replay the entire old release.
- Resolve conflicts by reading both the new upstream behavior and the documented
  purpose of our change. Do not choose all of "ours" or "theirs" mechanically.
  Retire a patch only when its intent is now supplied upstream or is deliberately
  no longer needed; explain that decision here. Inspect empty cherry-picks before
  skipping them. If a material behavior decision is unclear, ask the user while
  keeping the backup intact.
- Replay and preserve `AGENTS.md` too. If upstream introduces its own file, merge
  useful upstream guidance with this personal workflow and change register.

### 3. Validate, document, and publish

- Review the final diff against the new upstream base. It should contain only
  intended personal changes and their documentation; retain upstream's new
  prebuilt artifacts. Compare old and new patch series with
  `git range-diff OLD_BASE..BACKUP_BRANCH NEW_UPSTREAM_SHA..SYNC_BRANCH` and explain
  any differences. Run the checks relevant to the maintained changes.
- Update the current base, change register, and maintenance history in this file.
  Record old/new upstream SHAs, retained/changed/retired patches, conflict choices,
  validation, and remaining device checks. Commit the context update.
- Only after validation, move local `release-mici` to the verified candidate.
  Check worktrees and working-tree state first; preserve the backup so this does
  not destroy the previous personal series or another checkout's work.
- For an ordinary fast-forward publication use
  `git push origin release-mici:release-mici`.
- If replay/rebase requires replacing the fork's published history, use an
  explicit lease tied to the previously inspected remote SHA:

  ```sh
  git push --force-with-lease=refs/heads/release-mici:EXPECTED_ORIGIN_SHA origin release-mici:release-mici
  ```

  Replace `EXPECTED_ORIGIN_SHA` with the recorded full SHA. Never use bare
  `--force`. If the lease fails, inspect the new remote work and reconcile it;
  do not merely refresh the lease and retry. Push only to the personal fork.
- Verify the remote branch SHA equals the intended local commit and report the
  commits, validation, and publication result. Keep the backup through successful
  verification; do not delete backups as incidental cleanup.

Once the device is installed from this fork and follows `release-mici`, later
published updates are intended to use its normal updater while parked/offroad,
without reinstalling each time. A GitHub push is not proof of installation or
testing on the comma 4; report device validation separately. Do not remotely
install, restart, or operate the device as part of a repository-only task.

## Current upstream base

- Base commit: `6a17f75c6bcb67c85f252a1acc342d94d5b8a4d2`.
- Release subject: `sunnypilot v2026.002.002`.
- Recorded: 2026-09-26, from the initial clean `release-mici` checkout.
- This is the base beneath our personal commits, not the personal branch tip.
  Update it after each completed upstream integration.

## Personal change register

### DOC-001 - Personal fork maintenance workflow

- Request: retain personal commits across upstream releases and keep future
  agents informed of every change.
- Behavior: adds this workflow and ongoing context register; no runtime changes.
- Files: `AGENTS.md`.
- Commit subject: `docs: document personal fork maintenance workflow`.
- Validation: documentation review and Git whitespace checks; no device test
  needed for this documentation change.
- Upstream maintenance: retain this file across every replay/rebase and keep the
  base and register accurate.

For each subsequent change, add a stable ID with its request, before/after
behavior, files, commit subject(s), validation and limitations, and upstream
conflict considerations. Mark retired changes with the reason instead of
silently removing their context. There are currently no personal runtime changes.

## Maintenance history

- 2026-09-26: established this workflow on base
  `6a17f75c6bcb67c85f252a1acc342d94d5b8a4d2`; no upstream integration or device
  modification performed.
