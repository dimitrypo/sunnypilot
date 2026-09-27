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
  Verified with comma 4 setup headers after the INSTALL-001 alias repair below;
  the user subsequently confirmed successful installation and operation. See
  TESLA-003 for feedback on recovery timing and the follow-up update.
- GitHub installer alias: `dimitrypo/openpilot` redirects to this `sunnypilot`
  repository. The unused FrogTesla repository is now `dimitrypo/legacy_openpilot`.
  Preserve this alias: do not create or rename another repository to `openpilot`.

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
  At least 1.5 Nm yields immediately. TESLA-004 exempts alignment within 1 degree
  and suppresses moderate entry while fresh EPS release is confirmed. These are
  uncalibrated thresholds, not measured guarantees about this vehicle.
- Current recovery (TESLA-004 supersedes TESLA-003): alignment within 1 degree
  of the independent planner target resumes immediately regardless of ordinary
  torque or movement. Outside that band, release qualifies after 0.2 seconds
  without settling; settled light input qualifies after 0.5 seconds; firm input
  remains paused with no automatic timeout. Fresh EPS hands-on level zero can
  establish release below 1.5 Nm despite residual torque; the original torque
  <=0.2 Nm path remains available. Hard disengagement, faults, freshness, and
  the existing re-entry angle envelope still take priority.
- Signals: torque, wheel angle/rate, and an independent live planner target.
  No physical hand-contact/count sensor is available to this helper. Raw Tesla
  `hands_on_level` is not in the published CarState schema; TESLA-004 reads fresh
  EPS CAN messages separately, without changing that schema. The firmware still
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
  a fully disengaged system. The 0.2-second delay is a signal-based recovery
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
  storage. No host dependency installation. This original validation did not
  include a vehicle, real-route replay, or physical handover; subsequent user
  feedback and updated tests are recorded in TESLA-003 and TESLA-004.
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

### TESLA-003 - Faster recovery after steering handover

- Status: historical recovery policy, superseded by TESLA-004 below. Its delivery
  instructions and unchanged hard-disengagement/actuator limits still apply.
- Request: after successful installation, the user reported delayed recovery
  after avoiding a pothole, recentering, and releasing the wheel, allowing drift
  toward another lane. Reduce release recovery to 0.2 seconds, allow recovery
  while holding the wheel within 1 degree of the planner target, and reduce
  light/firm quiet periods from 1/3 seconds to 0.5/1.5 seconds. Publish through
  the existing updater without requiring reinstallation.
- Before: TESLA-001 required 0.5/1/3 seconds for released/light/firm input and
  had no faster recovery when the held wheel agreed with the live planner.
- After: released input (absolute torque <=0.2 Nm) qualifies after 0.2 seconds,
  even while the wheel returns or differs from the planner. Settled alignment
  within +/-1 degree qualifies after 0.2 seconds with hands still present,
  provided absolute wheel rate is below 5 degrees/s and torque below 1.5 Nm.
  Otherwise settled light input takes 0.5 seconds and firm input 1.5 seconds.
  Strong input and continued torque-qualified maneuvering still keep the pause.
  The angle comparison uses the independent live planner wheel angle, including
  the learned steering offset; it does not prove lane position or obstacle
  clearance. Recovery uses normal controller limits, not an abrupt steering step.
- Timers: release/alignment share continuous fast eligibility so torque noise
  around 0.2 Nm does not repeatedly reset it. The ordinary torque-category timer
  is independent, so jitter just inside/outside 1 degree cannot indefinitely
  restart the 0.5/1.5-second fallback. Renewed correction, invalid/faulted data,
  and sample gaps reset both timers. Duplicate samples cannot advance recovery.
- Retained limits: full disengagement/hard override never auto-resumes. The
  measured and last applied angle envelope, actuator suppression, and freshness
  checks remain authoritative. Low torque estimates release; no physical hands
  sensor was added. Tesla's published `steeringPressed` is itself filtered torque
  above 1 Nm, so false does not establish hands-off and is not used to override
  continued corrections. Timers are not guarantees of real EPS acceptance or
  recovery through a fault/angle-limit condition.
- Diagnosis limit: the old delays and torque/movement categorization can explain
  long recovery, but there are no driving logs identifying the actual blocking
  condition in the reported event. Do not claim the reported drift is reproduced
  or that this update is physically validated on the car.
- Files: `sunnypilot/selfdrive/controls/lib/tesla_steering_pause.py`,
  `sunnypilot/selfdrive/controls/lib/tests/test_tesla_steering_pause.py`,
  `sunnypilot/selfdrive/controls/lib/tests/test_tesla_steering_pause_integration.py`,
  and `AGENTS.md`. Commit subject:
  `fix: shorten Tesla steering handover recovery`.
- Validation: 102 tests and 26 subtests passed using the focused command above
  plus `opendbc_repo/opendbc/sunnypilot/car/tesla/tests/test_steering_protocol.py`.
  Ruff on all three changed Python files and Git whitespace checks passed.
  Added timing boundaries, signed alignment/torque boundaries, continued
  maneuver/strong override cases, both kinds of timer noise, live-plan offset,
  retained speed control, hands-present recovery, and envelope/hard-latch checks.
  Shortening the pause exposed lag in the intermediate curvature request; the
  integration test now verifies the final command through the unchanged Tesla
  limiter remains within its rate and angle bounds. No limiter was relaxed.
  Independent review covered both timers and reset paths. Tests used Python 3.12
  with exact versions and wheel hashes from `uv.lock`, temporary dependencies,
  read-only repository/root, masked agent/Git/editor files, non-root execution,
  and a disconnected network during tests. No host dependencies were installed.
- Delivery: ordinary fast-forward commit on `origin/release-mici`; no version,
  release-note, dependency, firmware, model, or prebuilt artifact changes needed.
  The updater compares remote commit SHAs and stages Python source from origin;
  the `openpilot` alias must continue to resolve to this fork. While parked and
  online: Settings -> Software, keep Target Branch `release-mici`, then Download
  -> CHECK -> DOWNLOAD, and Install Update -> INSTALL. The displayed Current
  Version after reboot should contain the published commit's short SHA. A push
  does not establish that the user has downloaded or installed the new update.
- Upstream maintenance: retain the independent planner target and two timer
  roles, inclusive 1-degree boundary, movement/strong-input veto, and original
  hard-disengagement/envelope guards. Revalidate actual applied steering limits
  rather than assuming the intermediate curvature request has already caught up.

### TESLA-004 - Immediate aligned handback and EPS-assisted release

- Request: the user reports TESLA-003 is substantially better, but releasing the
  wheel can still feel like a 1.5-second wait. Resume immediately within +/-1
  degree even with strong input or active steering. Outside alignment, keep firm
  input paused, recover after 0.5 seconds of settled light input, and after 0.2
  seconds of release without requiring the wheel to settle. Publish for the
  existing updater. The clarification removes the former firm-input timeout.
- Before: alignment required 0.2 seconds below both the strong-torque and motion
  thresholds; settled firm input could resume after 1.5 seconds. Release used
  only torque <=0.2 Nm, so residual torque could prevent that fast path. There
  are no driving logs identifying the actual cause of the reported delay.
- After, in priority order: unchanged hard-disengagement/fault/freshness guards;
  immediate aligned recovery; release after 0.2 seconds; settled light input
  after 0.5 seconds. Alignment is inclusive at +/-1 degree and ignores ordinary
  torque and wheel rate, including while already active. Recovery from a pause
  still requires measured and last-applied angles within the existing envelope.
  Alignment does not bypass full disengagement or force an abrupt wheel step;
  the existing downstream curvature, angle, and rate limits remain unchanged.
- Outside alignment: torque >=0.8 Nm keeps steering paused unless fresh EPS
  release qualifies below the strong threshold. Torque >=1.5 Nm always vetoes
  timed release and yields immediately while active. Light input must have wheel
  rate below 5 degrees/s and cannot hold a >=3-degree offset with >=0.3 Nm.
  Continued input resets the quiet timer. There is no 1.5-second firm fallback.
  As before, these torque thresholds are provisional vehicle-activity estimates.
- Release detection: torque <=0.2 Nm or a fresh continuous EPS hands-on level
  zero interval qualifies without a wheel-motion or angle-disagreement veto.
  A Python-only `TeslaHandsOnMonitor` subscribes read-only to existing CAN in
  controls and decodes `EPAS3S_sysStatus` (0x370, bus 0) with the existing parser.
  It checks event validity, timestamps, frame length, parser checksum/counter
  validity, and a 100 ms maximum gap. Missing/stale/invalid data is not release.
  Nonzero levels reset the zero interval, including intermediate frames drained
  during one controls cycle. Old zero time before the pause cannot count toward
  recovery; duplicate carState samples cannot advance it. No schema, DBC,
  dependency, driver-monitoring contact signal, firmware, or binary changed.
- EPS classification is filtered, not a physical contact sensor. Confirmed EPS
  release also suppresses moderate pause entry after handback so residual torque
  cannot immediately pause steering again. The tradeoff is that renewed moderate
  input (0.8 to <1.5 Nm) can wait for EPS to leave level zero before the existing
  0.05-second entry debounce. The current CarState source documents about 0.25
  seconds of filtering. Strong force still wins immediately outside alignment.
  The old FrogTesla source also used EPS level zero, but with its own one-second
  interval; this change follows the user's 0.2-second request, not that timeout.
- Limits: immediate alignment has no dwell timer or wider sticky band; strong
  input crossing the 1-degree boundary can alternate pause/active permission.
  The planner target remains independent of paused actuator tracking and includes
  the learned steering offset. Neither alignment nor EPS zero proves road
  clearance or hands-off. Faults and angle limits may still delay recovery.
  Speed control and true hard-disengagement behavior remain unchanged. Added
  once-per-second paused diagnostics with reason, EPS release evidence, re-entry
  permission, torque, angle error, and wheel rate to diagnose future delays.
- Files: `sunnypilot/selfdrive/controls/controlsd_ext.py`,
  `sunnypilot/selfdrive/controls/lib/tesla_steering_pause.py`,
  `sunnypilot/selfdrive/controls/lib/tesla_hands_on.py`, their three focused test
  files under `sunnypilot/selfdrive/controls/lib/tests/`, and `AGENTS.md`.
  Commit subject: `fix: prioritize Tesla alignment and EPS release recovery`.
- Validation: 143 tests and 26 subtests passed using the focused command above
  plus `sunnypilot/selfdrive/controls/lib/tests/test_tesla_hands_on.py` and
  `opendbc_repo/opendbc/sunnypilot/car/tesla/tests/test_steering_protocol.py`.
  Ruff passed on all six changed/new Python files; Git whitespace checks passed.
  Coverage includes strong/moving aligned recovery, indefinite firm hold, both
  timed paths, residual-torque recovery remaining active, renewed-input latency,
  CAN freshness/validity/order, actual CAN packer through controls integration,
  retained speed control/contact signals, hard latches, and actuator limits.
  Independent review covered the state machine and CAN monitor. Tests used
  isolated Python 3.12, exact wheel versions/hashes from `uv.lock`, temporary
  dependencies, read-only repository/root, masked agent/Git/editor files,
  non-root execution, and a disconnected network. No host dependency installs.
  The user subsequently reported approximately 15 minutes of driving with no
  observed recovery issues. This is positive user feedback, not controlled
  validation or a route replay. Hard-turn disengagement still occurs as intended;
  the user deferred any change to that behavior to a future task.
- Delivery/maintenance: use the same fast-forward `release-mici` publication and
  normal updater as TESLA-003; no reinstall or version bump is required. Preserve
  existing prebuilt artifacts and installer alias. Reconcile CAN timestamp/parser
  changes, the independent planner angle, alignment priority, EPS classification
  latency, and the hard/fault/envelope guards during future upstream integration.
  Reassess the separate CAN subscription if upstream publishes this raw signal.

### INVESTIGATION-001 - Tesla Autopark cancellation (no runtime change)

- Report: Autopark begins but cancels before the vehicle moves; enabling Always
  Offroad lets it work. User confirmed sunnypilot steering and speed were fully
  disengaged and Tesla was set to TACC. No CAN capture from the failure was
  available. Selecting TACC does not establish the comma's alpha-long setting.
- Strongest explanation: the existing safety header explicitly documents that
  only Summon is supported because Autopark does not set the expected state.
  `DI_autoparkState` values 3/4/9 gate its handoff. Without that latch, firmware
  blocks stock `APS_eacMonitor` (0x27d) and steering (0x488, except its stock-LKAS
  exception), even while sunnypilot is disengaged; with openpilot longitudinal it
  also blocks `DAS_control` (0x2b9) except during stock AEB. Python stopping its
  own commands cannot restore these blocked stock frames. This matches the
  symptom but is not a log-confirmed diagnosis of this particular car.
- Always Offroad uses existing `OffroadMode`, which makes pandad select NO_OUTPUT
  and restores the physical stock CAN connection through the intercept relay.
  This explains why it can work when ordinary disengagement does not. There is
  no existing Tesla safety parameter for an Autopark-only passthrough mode.
- Upstream checked 2026-09-26: both live opendbc master and the official
  [release-mici safety source](https://raw.githubusercontent.com/sunnypilot/sunnypilot/release-mici/opendbc_repo/opendbc/safety/modes/tesla.h)
  retain the limitation. [PR #2902, Tesla: Fix Autopark](https://github.com/commaai/opendbc/pull/2902)
  remains an open, unmerged draft, at head
  `73df7251978dcf3ed731b20fdd6a5daa4e14f84c`, updated September 23-24. Its current
  proposal expands stock-steering passthrough beyond LKAS when stock steering
  starts with controls disallowed. It changes safety firmware and Python/test
  code. Physical Autopark/TACC validation remains unfinished in the checklist.
  Do not confuse ordinary driving replay results with parking validation.
- The author's older [Autopark investigation](https://community.sunnypilot.ai/t/tesla-autopark-support/2701)
  describes the same repeated-start/cancel symptom and explored
  `DAS_autopilotState`. The current PR abandoned that detector because of slow
  updates and overlap with FSD. Review the actual current patch, not just the
  older forum post or PR description, before selecting an implementation.
- Assessment: a convenience UI action reusing the established offroad workflow
  could remain Python-only. Seamless stock parking support requires coordinated
  stock-command forwarding and sunnypilot inhibition, a matching Panda safety
  firmware build, and handoff/regression validation. Account for our MADS lateral
  engagement and legacy steering encoding when adapting upstream code. Do not
  deploy broad stock-command forwarding or direct safety-mode switching as an
  unreviewed shortcut. Capture the actual failed sequence before implementing.
- Evidence: `opendbc_repo/opendbc/safety/modes/tesla.h`,
  `opendbc_repo/opendbc/car/tesla/carstate.py` and `carcontroller.py`,
  `selfdrive/pandad/pandad.cc`, `selfdrive/pandad/panda_safety.cc`, and
  `panda/board/main.c`. Read-only source/upstream review, with independent safety
  review; no repository code executed, runtime edits, device operations, or new
  firmware. Only this context record changed; no update was pushed.

### INVESTIGATION-002 - Steering override policy, firmware delivery and rollback

- Request (2026-09-27): after approximately 15 minutes of satisfactory operation,
  assess keeping speed control engaged during hard steering/roundabouts, with
  steering paused during driver input. The user proposes removing steering-based
  full disengagement entirely and asks whether this simplifies implementation,
  its risk, and whether firmware updates and rollback require reinstalling.
  This task is an assessment, not authorization to implement or publish firmware.
- Current triggers: both `opendbc_repo/opendbc/car/tesla/carstate.py:70-73` and
  `opendbc_repo/opendbc/safety/modes/tesla.h:136-141` combine hands-on level >=3
  with EAC_INHIBITED/high-angle-rate safety error. The Python result becomes a
  user-disable event; the firmware result feeds Panda's full-disengagement path
  and MADS. `carcontroller.py:35-45` independently inhibits steering at level 3.
  `TeslaSteeringPause` also latches the hard event. A Python-only removal cannot
  retain engagement against the existing firmware. A steering-output inhibit
  should remain even if a future policy preserves longitudinal engagement.
- Distinction: level 3 classifies driver force; high-angle-rate error is an EPS
  safety fault and also sets `steerFaultTemporary`, independently gating lateral
  output. Removing its full-disengagement event cannot make Tesla accept steering
  through inhibition. No route/CAN capture establishes which signal causes this
  user's hard-turn/roundabout disengagement. Low override resistance and brief
  satisfactory driving are not emergency-maneuver or fault validation.
- Risk: retaining speed control through an evasive maneuver can retain unwanted
  acceleration/speed. TESLA-004's immediate +/-1-degree recovery can request
  steering again as the wheel crosses the planner target under active force.
  Removing the current hard override exposes that interaction during a wider
  range of maneuvers; gentle command limits do not resolve the policy conflict.
  Brake/cancel, driver monitoring, CAN validity, heartbeat, actuator limits and
  real faults must remain effective. Do not describe brake as the sole exit.
- Recommendation: first identify the actual trigger from EPAS level/status/error
  and disengagement events. Consider only a coordinated level-3 lateral pause
  with speed retained, preserving high-angle-rate fault full disengagement and
  independent steering inhibition. Review strong-input priority over aligned
  recovery before extending it to hard overrides. This would change the user's
  previous alignment preference and must be resolved explicitly before coding.
  Literal removal of every steering-triggered disengagement is not recommended;
  fewer conditionals do not make the resulting policy safer or better validated.
- Effort: moderate coordinated C/Python source work; substantially greater build
  and validation work than the previous timer changes. Budget engineering days,
  not a quick threshold edit, for a compatible firmware build, full safety tests
  with new coverage, Python regressions, image verification and suitable replay.
  Controlled hardware/vehicle validation and rollback checks remain separate;
  no reliable road-ready delivery estimate is possible before identifying the
  trigger and establishing the build and validation setup. No build was attempted.
- Delivery: firmware here means the comma's Panda CAN safety microcontroller,
  not Tesla EPS firmware. This release tracks `panda/board/obj/panda_h7.bin.signed`
  and skips compilation with `prebuilt`. A firmware change therefore needs a
  compatible compiled/signed H7 image included with the matching Python change;
  C source alone has no device effect. `selfdrive/pandad/pandad.py:18-58` compares
  the installed image signature to the checkout's image, flashes on mismatch,
  and verifies it before starting C++ pandad. `panda.cc:116-126` also compares
  the image from disk, not a baked-in expected signature. Retain the existing
  host protocol/bootstub where compatible; debug-key/bootstub acceptance and
  build provenance require verification before shipping a custom image.
- Rollback: the normal updater fetches and stages a complete branch commit.
  A new forward revert commit restoring both known-good Python and the original
  signed H7 binary should restore both through the normal parked update/reboot
  path, provided startup/updater/flashing remain functional. The flasher checks
  image signatures, not increasing release dates; the bootstub checks signature
  and a minimum image format version. Keep the original image and commit. The
  launcher's `old_openpilot` staging copy is deleted at subsequent updater setup,
  so it is not a dependable rollback feature. Uninstall alone does not restore
  MCU firmware; the replacement installation must run its flasher. Broken UI or
  startup may require reinstall; failed Panda flashing can require bootstub/DFU
  recovery. Neither path is guaranteed by this source review.
- Evidence/validation: read-only code review and independent safety/update
  reviews, plus current [comma safety documentation](https://docs.comma.ai/SAFETY/)
  and [Panda recovery documentation](https://github.com/commaai/panda/blob/master/board/README.md).
  The safety policy requires retained actuation limits/driver monitoring and a
  passing full safety test suite with added coverage for changes. Documentation
  and Git whitespace checks only; no runtime edits, tests, builds, flashes,
  device operations, or push. Existing local Autopark documentation is preserved.

### INSTALL-001 - Repair comma 4 installer repository alias

- Request: resolve "No custom software found at this URL" from the recorded fork
  installer URL, both with and without `https://`. The user confirmed sunnypilot
  worked on this comma 4 immediately before uninstalling, and explicitly requested
  renaming the unused old FrogTesla repository to `legacy_openpilot`.
- Diagnosis: a plain desktop request returned a 1,295,328-byte installer pointing
  directly to `dimitrypo/sunnypilot`. With `User-Agent: AGNOSSetup-18.4` and
  `X-openpilot-device-type: mici`, the same URL instead returned HTTP 200 with
  61 bytes of text: "This version of openpilot is not compatible with this
  device." `system/ui/mici_setup.py` rejects a non-ELF response with the exact
  message shown in the photo. Neither spelling nor the optional URL scheme was
  the problem. The simulated OS version came from `launch_env.sh`; no real device
  serial was sent and the device's actual OS version was not independently read.
- The official comma 4 installer embeds a GitHub `openpilot.git` address even
  when requested through the sunnypilot fork endpoint. Official
  `sunnypilot/openpilot` already redirects to `sunnypilot/sunnypilot`; the personal
  `dimitrypo/openpilot` instead contained old FrogTesla branches and no
  `release-mici`. Current installer service source was unavailable; the response,
  embedded destination, and successful repair establish the routing dependency.
- Repair: renamed the old repository to `dimitrypo/legacy_openpilot`, preserving
  repository ID `861714415` and default branch `frogtesla`. Then temporarily
  renamed this fork `sunnypilot -> openpilot -> sunnypilot`, preserving repository
  ID `1388928190`, default branch `release-mici`, and all commits. This is the
  [installer generator's documented alias technique](https://github.com/sshane/openpilot-installer-generator#aliases),
  using [GitHub rename redirects](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).
  Canonical origin remains `https://github.com/dimitrypo/sunnypilot.git`. The
  installer may save the `openpilot.git` alias as device origin; Git fetch/push
  redirects then reach the same current sunnypilot repository. The legacy
  repository must now be addressed by its new name.
- Validation: GitHub API confirmed the alias resolves to the current sunnypilot
  repository ID and the old fork remains separate. `git ls-remote` through the
  alias returned the published `release-mici` tip. The original installer URL,
  with the same setup headers that previously failed, now returned a
  2,051,392-byte ELF64 AArch64 installer embedding
  `https://github.com/dimitrypo/openpilot.git` and `release-mici`. This verifies
  endpoint delivery and repository selection, not an end-to-end device install.
- Files/commit: only `AGENTS.md`; commit subject
  `docs: record comma 4 installer alias repair`. No driving code, prebuilt
  artifacts, firmware, dependencies, or device state changed. A dedicated
  installer was considered and prepared temporarily during diagnosis, but was
  not published or retained in this repository after the alias repair worked.
- Future maintenance: preserve the alias and check both GitHub repository IDs
  and branch SHA if installation fails again. Always test installers with the
  setup User-Agent and `X-openpilot-device-type: mici`, then inspect the actual
  payload and embedded repository/branch. HTTP 200 or a desktop-only download is
  insufficient. Do not recreate the old `openpilot` repository name, which would
  replace this redirect and break installation/updates through the alias.

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
- 2026-09-26: user authorized publishing the personal commits to
  `origin/release-mici` for installation on the comma 4. Runtime commits are
  `e6dc91b` (TESLA-001) and `49f2931` (TESLA-002); these are publication-era
  references, not stable IDs after a future replay. No runtime changes were added
  during publication; the recorded 74 tests and 26 subtests remain applicable.
  A desktop request to the exact fork installer URL returned HTTP 200. Read-only
  inspection of that response's ARM64 installer confirmed
  `https://github.com/dimitrypo/sunnypilot.git`,
  `git checkout release-mici`, and `git reset --hard origin/release-mici`:
  it selects the published branch tip, not a pinned older release. The launcher
  sets PYTHONPATH to that checkout; card, controlsd, and UI are Python processes,
  so these source changes are used with the retained prebuilt artifacts. Normal
  updates fetch the configured origin. Uninstall/Custom Software installation
  through the recorded URL is the intended first-install path. This initial
  check omitted setup device headers and therefore did not verify the actual
  comma 4 response; INSTALL-001 records the subsequently reproduced failure and
  repair. Remote publication must be checked against GitHub after pushing; device
  installation and driving behavior still require separate verification.
- 2026-09-26: completed INSTALL-001 after the user's failed installation report.
  Renamed the unused FrogTesla repository to `legacy_openpilot` as requested and
  established `openpilot` as a GitHub alias for the current `sunnypilot` fork.
  Verified the original URL now returns the comma 4 installer with device setup
  headers and Git through the alias reaches the published personal branch.
  Runtime changes remain TESLA-001 and TESLA-002; device installation is pending.
- 2026-09-26: user confirmed INSTALL-001 installation succeeded and the personal
  behavior operates, then reported delayed steering recovery and lane drift.
  Implemented TESLA-003 on the same upstream base for delivery through the normal
  `release-mici` updater. Local validation passed; updated device behavior remains
  unverified until the user installs and evaluates this new revision.
- 2026-09-26: user reported improved TESLA-003 behavior but remaining release
  delays, and clarified immediate alignment and indefinite firm-input pause.
  Implemented TESLA-004 with fresh EPS release evidence on the same upstream base;
  143 tests and 26 subtests passed. Publishing to the existing `release-mici`
  update branch is authorized; physical verification of this revision is pending.
- 2026-09-27: recorded INVESTIGATION-002 on hard-steering disengagement, firmware
  delivery and rollback. Recommended identifying the trigger and preserving real
  EPS fault disengagement before considering a narrower force-override policy.
  Assessment/documentation only; published driving code and firmware unchanged.
