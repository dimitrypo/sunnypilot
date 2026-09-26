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

This is a personal installation used only on Dmitry's Tesla Model 3 Highland.
Compatibility with other owners' workflows is not a requirement. The software
uses the shared `TESLA_MODEL_3` fingerprint for Highland and older Model 3s; do
not claim the personal behavior has a separate Highland-only detection rule.

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
silently removing their context.

### TESLA-001 - Forced cooperative steering and temporary driver handover

- Request: preserve cooperative steering for small corrections; temporarily yield
  steering for larger ordinary corrections, keep speed control active, and resume
  automatically after input settles. A hard override must still fully disengage.
  The user explicitly chose the Python-only approximation, retaining the current
  firmware cutoff. This is not a request to reproduce FrogTesla's firmware policy.
- Before: the saved `TeslaCoopSteering` value was captured at car initialization,
  the UI could show a different/stale value, and no soft pause/recovery state
  machine existed. Tesla hands-on level 3 or the high-angle-rate safety fault
  triggered full disengagement in both Python and Panda safety.
- After: Model 3 initialization always selects cooperative mode, independent of
  the stored preference. The local Tesla settings UI displays it checked/locked.
  The legacy encoding map and existing EPS restrictions remain in effect (see
  TESLA-002 for improved detection). A
  temporary handover gates actual `CarControl.latActive`; engagement, longitudinal
  control, cruise cancellation, and driver-monitoring contact signals are not
  rewritten. The healthy main UI reflects steering unavailable as `long_only`.
- Entry: at least 0.8 Nm of torque plus wheel motion of at least 5 degrees/s or
  planner-angle disagreement of at least 3 degrees, sustained for 0.05 seconds.
  At least 1.5 Nm yields immediately. These are initial, uncalibrated thresholds
  in `TeslaSteeringPause`, not measured guarantees about this vehicle.
- While paused: at least 0.3 Nm with continuing movement/angle disagreement keeps
  the pause, including a stationary wheel holding an offset; at least 1.5 Nm also
  keeps it paused. Otherwise, continuous torque at or below 0.2 Nm resumes after
  0.5 seconds, light input below 0.8 Nm after 1 second, and firm settled input
  after 3 seconds. A change of input category starts its own quiet period. A clear
  release takes the 0.5-second path even after a firm hold or with residual angle
  disagreement. Renewed correction resets recovery.
- Signals: torque, wheel angle/rate, and an independent live planner target.
  No physical hand-contact/count sensor is available to this helper. Raw Tesla
  `hands_on_level` is not in the published CarState schema; the firmware still
  reads it independently. A relaxed hold can resemble release after EPS yields.
- Integration: the lateral controller resets/tracks actual steering while paused;
  return goes through existing curvature and angle/rate limits. Automatic recovery
  also waits until measured steering and the fresh reported last actuator angle
  are inside the existing Tesla angle envelope at the current raw speed, using
  the same fixed Model Y safety vehicle model as CarController. Checking both
  angles covers the different controls/CAN update rates. The existing limiter
  clips absolute angle after rate limiting; without this guard, re-entry from
  outside that envelope could request an abrupt
  step. Quiet time still accumulates while waiting for the angle to become valid.
  Duplicate carState samples cannot advance recovery; invalid/stale carState or
  planner data resets its quiet timer. Temporary actuator gates do not
  erase the handover/hard-override latch; reset follows upstream engagement.
  `publish()` uses the computed `CC.latActive`, avoiding a second update of the
  blinker timer during one controls cycle (also corrects that all-platform timer
  double update). No CAN schema, safety policy, firmware, or binaries changed.
- Limits: early yielding may avoid the hard cutoff, but slow force can still
  reach hands-on level 3 and fully disengage. A timed pause must never re-enable
  a fully disengaged system. The 0.5-second delay is a signal-based recovery
  target, not proof of hands-off or a guarantee against lane departure. Faults or
  an angle outside the existing envelope can delay recovery beyond that timer,
  potentially indefinitely until the condition clears.
- Files: `opendbc_repo/opendbc/sunnypilot/car/interfaces.py`,
  `selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/tesla.py`,
  `sunnypilot/selfdrive/controls/lib/tesla_steering_pause.py`,
  `sunnypilot/selfdrive/controls/controlsd_ext.py`, `selfdrive/controls/controlsd.py`,
  `selfdrive/ui/ui_state.py`, `selfdrive/ui/sunnypilot/tesla_status.py`, and their
  focused tests. Container ignore files protect local test configuration.
- Commit subject: `feat: add personal Model 3 cooperative steering handover`.
- Validation: 65 tests and 10 subtests passed across state-machine, integration,
  cooperative-mode and UI tests,
  existing Tesla vehicle and blinker tests, Ruff on changed Python files, and Git
  whitespace checks passed. Actual-controller integration covers retained speed
  control, measured-angle tracking, timed recovery, hard overrides across faults,
  and blocking recovery beyond the existing angle envelope. Used isolated Python
  3.12 with dependencies pinned from `uv.lock`, read-only
  repository mount, masked `AGENTS.md`/`.vscode`/`.git`, and temporary dependency
  storage. No host dependency installation. No vehicle, real-route replay, or
  physical handover validation has been performed.
- Upstream maintenance: retain Tesla firmware detection, independent hard
  overrides, and controller limits; reconcile upstream changes to `latActive`,
  MADS, planner target selection, timestamps, and UI status carefully. A broader
  firmware change needs its own scope and build plan.

Focused test command in the hardened `sunnypilot-python-test` container (dependency
directory `/deps`, `PYTHONPATH=/deps:/repo`, repository mounted read-only at `/repo`):

```sh
docker exec -e PARAMS_ROOT=/tmp/tesla-test-params sunnypilot-python-test python -m pytest \
  --noconftest -c /dev/null -p no:cacheprovider -q \
  sunnypilot/selfdrive/controls/lib/tests/test_tesla_steering_pause.py \
  sunnypilot/selfdrive/controls/lib/tests/test_tesla_steering_pause_integration.py \
  selfdrive/ui/tests/test_tesla_status.py \
  opendbc_repo/opendbc/sunnypilot/car/tesla/tests/test_coop_steering.py \
  opendbc_repo/opendbc/car/tesla/tests/test_tesla.py \
  sunnypilot/selfdrive/controls/lib/tests/test_blinker_pause_lateral.py
```

`--noconftest` isolates these tests from the unrelated full-manager startup fixture;
it does not replace their tested controllers. `PARAMS_ROOT` keeps the blinker
tests' temporary settings off the read-only root filesystem. Ruff command:
`docker exec sunnypilot-python-test python -m ruff check --no-cache PATHS`, with
`PATHS` expanded to every changed/new Python file. Whitespace: `git diff --check`
and `git diff --cached --check`. These local tests do not validate Panda firmware
on hardware; its source and prebuilt binaries are unchanged.

#### Intermittent cooperative steering investigation

- User reports blocked corrections at approximately 30-60 km/h, sometimes fixed
  by toggling/restarting or apparently by itself; Tesla software `2026.27.300`.
  This is a reported symptom, not a reproduced fault. The documented minimum of
  23 km/h cannot by itself explain the reported speed range.
- Confirmed source behavior: `selfdrive/car/card.py` captures settings before
  fingerprinting; the running controller uses that initialized `CP_SP` flag.
  `ToggleSP` originally read its displayed state only at widget construction.
  Later settings restores/remote changes can therefore disagree with runtime or
  the display. The force-on and refreshed UI remove these dependencies for the
  personal Model 3. AlwaysOffroad normally restarts the car process; do not claim
  it bypasses initialization.
- Confirmed compatibility gap: upstream describes Tesla's steering mode growing
  from two to three bits, including non-FSD releases. Without the legacy encoding
  flag, our cooperative command can select FSD mode instead of lane keeping.
  See [opendbc #3797](https://github.com/commaai/opendbc/pull/3797), merged as
  `d2599bf817bdcfb5e032e0fa9a5468dc191ebebd` on 2026-09-19.
- Upstream's replacement detector uses fresh CAN messages and identified cases
  where cached firmware lagged the updated protocol. TESLA-002 adopts that
  detection for this personal cooperative path. The software label `2026.27.300`
  alone is not detection evidence. Do not add guessed firmware matches, clear
  caches automatically, or remove the remaining unknown-firmware guard.
- Startup log `tesla_cooperative_steering_config` records fingerprint, stored
  preference, effective forced state, legacy encoding flag, and active CAN mode.
  `tesla_steering_protocol` records CAN/EPS detection evidence.
  `tesla_steering_pause` records handover, blocked recovery, and hard overrides.
  These record requested configuration/control state, not proof of EPS acceptance.
  To diagnose a recurrence, correlate logs with CarParams EPS firmware and live
  steering torque/angle, EPAS status/error/hands level, requested CAN mode, and
  vehicle speed. No real-device evidence has yet identified the user's root cause.

### TESLA-002 - Detect modern steering encoding from live CAN

- Request: investigate and address enabled cooperative steering that intermittently
  refuses driver corrections; retain the Python-only scope.
- Before: only known EPS firmware strings selected the existing encoding map.
  Missing or cached strings could select an incompatible cooperative mode.
- After: for `TESLA_MODEL_3`, either `0x489` on bus 2 or `0x054` on bus 0 also
  selects the map. This matches the detector in
  [opendbc #3802](https://github.com/commaai/opendbc/pull/3802), merged as
  `594700b86cd03347c6650ecf14feb1b543b0d72a` on 2026-09-21. Existing EPS matches
  remain a fallback; other platforms keep their original detection.
- Scope: set existing `TeslaFlags.FSD_14` and `TeslaSafetyFlags.FSD_14` together.
  Their names are historical, not proof of FSD software. With forced cooperative
  mode, this maps logical mode 2 to old two-bit value 1: the emitted bits `010`
  mean modern lane keeping, and `000` remains steering off. Both commands are
  already supported by the prebuilt firmware. No DBC, safety source, binary,
  longitudinal rule, hard override, or stock-Autosteer requirement changed.
  This is deliberately not the complete upstream three-bit conversion.
- Files: `opendbc_repo/opendbc/car/tesla/interface.py` and
  `opendbc_repo/opendbc/sunnypilot/car/tesla/tests/test_steering_protocol.py`.
- Commit subject: `fix: detect modern Tesla steering encoding from live CAN`.
- Validation: 9 tests and 16 subtests passed, including the real CAN packer and
  CarState, both markers, wrong buses, cached/missing EPS strings, legacy fallback,
  other platforms, paired flags, stock-LKAS detection, and stock-Autosteer lockout.
  Command: `docker exec sunnypilot-python-test python -m pytest --noconftest -c /dev/null -p no:cacheprovider -q opendbc_repo/opendbc/sunnypilot/car/tesla/tests/test_steering_protocol.py`.
  Ruff and Git whitespace checks passed. Together with TESLA-001: 74 tests and
  26 subtests passed. Device acceptance and the user's intermittent symptom remain
  unverified; diagnostic logs are included for that follow-up.
- Upstream maintenance: reassess/retire this supplement when a release adopts the
  native three-bit DBC and matching prebuilt safety. Do not replay the legacy
  mode mapping onto that new format. Revalidate cooperative lane-keeping support
  against the new firmware before carrying over TESLA-001.

## Maintenance history

- 2026-09-26: established this workflow on base
  `6a17f75c6bcb67c85f252a1acc342d94d5b8a4d2`; no upstream integration or device
  modification performed.
- 2026-09-26: implemented TESLA-001 as a Python-only personal change, retaining
  the same upstream base and the existing prebuilt safety firmware. Device
  installation and physical validation remain separate from the repository work.
- 2026-09-26: added TESLA-002 based on upstream protocol evidence; retained the
  existing wire format and firmware. Recorded the reported Tesla software version
  and outstanding device verification instead of assuming a confirmed root cause.
