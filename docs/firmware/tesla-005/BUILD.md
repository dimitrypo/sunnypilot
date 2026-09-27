# TESLA-005 H7 application build and rollback

This personal Model 3 policy replaces EPS hands-on level 3 full cancellation
with an independent steering inhibit. The high-angle-rate EPS safety fault
still fully disengages. Source, Python policy, and the signed H7 application
must travel together. This is experimental firmware: automated checks do not
establish successful flashing, hardware timing, or safe vehicle behavior.

## Build provenance

Built on 2026-09-27 from upstream source
`6a17f75c6bcb67c85f252a1acc342d94d5b8a4d2` with the personal changes recorded in
`AGENTS.md`. The adjacent Dockerfile and hash-pinned requirements record the
actual build environment. Python requirements come from the repository locks;
no project dependencies were installed on macOS.

- Base image: `python:3.12-slim` at
  `sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f`.
- Local build image: `sunnypilot-fw-test:20260927`, ID
  `sha256:2d1a54ae672ded22309cc98f1f5d875a1a0c59af2579582cf2963942761003a0`.
- Linux ARM64; Debian 13.7; cross compiler
  `gcc-arm-none-eabi=15:14.2.rel1-1`; binutils
  `binutils-arm-none-eabi=2.44-3+23+b2`; native GCC 14.2.0.
- SCons 4.10.1, Python 3.12, PyCryptodome 3.23.0, gcovr 7.2.
- Debian package resolution in the recorded Dockerfile is not frozen to a
  package snapshot. A future build must verify these versions and rerun checks;
  this recipe alone does not guarantee byte-for-byte reproduction later.

The runtime build container used a read-only root and repository mount, uid
501:20, no network, dropped capabilities, no-new-privileges, and temporary
writable source/dependency storage. Repository `.git`, `AGENTS.md`, and `.vscode`
were masked. Copies in `/work/base` and `/work/current` excluded Git metadata.
The baseline was obtained with `git archive` from the upstream commit above.

From the copied current source, with working directory `/work/current/panda`:

```sh
PYTHONPATH=/work/current/opendbc_repo scons -j4 board/obj/panda_h7.bin.signed
```

The unchanged build system emits `DEV-unknown-DEBUG` without Git metadata,
matching the version text in the original tracked prebuilt tree. Debug signing
uses the repository's public development key at `panda/board/certs/debug`.
The original shipped application also verifies with that debug key. This is
signature compatibility evidence, not production signing or hardware validation.

Only `panda/board/obj/panda_h7.bin.signed` is replaced. Keep the original bootstub,
`prebuilt` marker, host binaries, models, and protocol definitions. The baseline
rebuilt application is not byte-identical to the shipped artifact with this
different compiler: its hash is
`bbf98707af2b55778288425d0fc1fdf52427a01092ae9e0041c4428d1261e7ec`
(98,284 bytes). The original is 98,528 bytes. Do not claim otherwise.

## Image and source verification

Source SHA-256 values:

- `opendbc_repo/opendbc/safety/modes/tesla.h`:
  `0dc2fd51c380b568916e504284e3de35a9229154c84081c893b251ea16738421`.
- `panda/SConscript`:
  `4448a776fab4562734a9f15ecc5367f7ae63757a3d5a6a75b484c2bd6f3f2a72`.
- `panda/board/main.c`:
  `426202ee869bc74bd4208536a45801aa9987dbb8568baf210a6a0fdca485b3e7`.

Final signed H7 application: **98,420 bytes**, SHA-256
`bce76f09637897b807000aeae308dc87137687f9d35721f3091dfdd4a43a25df`.
The signed payload byte-matches the final rebuilt `panda_h7/main.bin`, with the
format's length/trailer transformation. The final signed target was deleted
and regenerated in the disposable build copy to avoid retaining a stale SCons
output. The exported file and tracked replacement have the same SHA-256.

Both old and rebuilt firmware use the unchanged host packet versions:

| Packet | Version |
| --- | --- |
| Health | `0xBE6AD9D2` |
| CAN | `0x75ABF276` |
| Jungle health | `0xA39967B7` |

The application has the existing signed format: a 128-byte RSA signature and
`VERS` trailer format 2. Verification checks the declared length and trailer,
then verifies the signature over the payload after the four-byte length. The old
bootstub contains the debug and release public key moduli; the device's installed
bootstub was not read or flashed during this task.

## Validation

The focused Python command is recorded under TESLA-001 in `AGENTS.md`, augmented
with the hands-on monitor, steering-protocol, and steering-pause-policy tests.
The native suite runs from `opendbc_repo/opendbc/safety/tests` in the copied
source, with `PYTHONPATH` pointing at the copied `opendbc_repo`:

```sh
python -m unittest discover -s . -q
```

No safety test files are excluded. Two existing runner defects were repaired:
non-vehicle fixtures have no `TX_MSGS` attribute, and release-build tests pass
`release=True` to a helper that previously accepted no argument. The helper now
actually omits `ALLOW_DEBUG` for that build. These fixes affect tests only.

The focused Python suite passed **184 tests and 26 subtests**. Ruff passed on
all changed Python files. The final complete native safety suite passed:
**8,384 tests run, 902 skipped** (abstract/not-applicable fixtures). The old base
under the same repaired harness/toolchain passed 8,332 tests, 901 skipped.
New cases cover all four combinations of steering encoding and longitudinal
mode, MADS/brake, vehicle-bus setup, EPS faults, freshness, timer wrap, inactive
angle tracking, and retained actuator limits.

Tesla C line coverage is **186/186 (100%)**, versus 177/177 on the old base.
The unmodified project-wide `--fail-under-line=100` gate still exits 2:
current 2,480/2,481, baseline 2,471/2,472. Both miss only the unchanged
`modes/hyundai_common.h:105` release-only branch. No coverage objects or test
files were excluded for these reported results. This existing gap is retained
and disclosed; the overall coverage gate is not reported as passing.

Cppcheck 2.16.0 with the MISRA addon passed on both the original baseline and
the final changed header: exit 0, no error/style/MISRA diagnostics. The generated
MISRA coverage table byte-matches the checked-in table. Baseline and current
checker inventories match each other; both differ from the older checked-in
inventory. These are static checks, not a certification of the vehicle system.

Used the dependency pinned by `opendbc_repo/uv.lock`, dependency Git revision
`d7f7aeedd5b9b3eddb4945ae81434ac0fd4fe549`. The ARM64 Cppcheck wheel SHA-256 is
`0bb58566161fac0817c9ea19dcbb74f1ffe2c29c6fe4cb23bb023dab908650fb`, and the
checker ELF SHA-256 is
`ad52d1c8057896aef1600c15e6c21a9a00d3e088c5dc220e85e9c316193ce068`.
The repository's underlying checker command was run directly in an isolated
offline source copy; its setup/uv-sync and Git-workspace wrappers were omitted.
With `TESLA_005_OPENDBC` pointing at the copied `opendbc_repo`:

```sh
cppcheck --inline-suppr -I "$TESLA_005_OPENDBC" \
  --suppress=missingIncludeSystem \
  --suppressions-list="$TESLA_005_OPENDBC/opendbc/safety/tests/misra/suppressions.txt" \
  --error-exitcode=2 --check-level=exhaustive --safety \
  --platform=arm32-wchar_t4 -D__GNUC__=9 --checkers-report=/tmp/tesla-005-checkers \
  --std=c11 --enable=all --enable=unusedFunction --addon=misra \
  "$TESLA_005_OPENDBC/opendbc/safety/tests/misra/main.c"
```

Vehicle replay, Panda hardware-in-the-loop, physical update/rollback, and
vehicle behavior have not been tested. Retaining speed through a driver override
can retain unwanted acceleration, and the high-angle-rate fault may still cancel
during a sharp turn. No logs identify the user's original trigger conclusively.

## Update and rollback

Publish the source and signed application in the same commit on `release-mici`.
The normal updater stages the entire commit. On startup, existing `pandad.py`
compares the installed Panda signature with the image in the checkout, flashes
on mismatch, then verifies it. This is a Panda application update, not a Tesla
EPS firmware or comma OS update. No device was remotely operated by this task.

The pre-change local backup branch is
`backup/release-mici-before-level3-pause-20260927`, at `2141791`.
For rollback, create and publish a new forward commit reverting TESLA-005's
runtime source and signed application together. Preserve later unrelated fixes
and add the rollback to `AGENTS.md`; do not rewind the update branch blindly.

- Known-good original H7 app SHA-256:
  `1aa3cdbf797cd2f9324c08344685996065f5518bca3bc7640a83670c002ea703`.
- Original bootstub SHA-256, unchanged in this update:
  `2e64a697c3e15bf2a85067b3dd0e8800853c650e44918d165f7861bddb63209e`.

The normal updater can deliver that rollback while startup, UI, and flashing
remain functional. Uninstall alone does not restore MCU firmware. A failed
startup may require reinstalling, and a failed flash can require Panda recovery.
The transient `old_openpilot` directory is not a dependable backup. Preserve the
old application in Git and rebuild/retest against each future upstream release;
never copy this compiled application onto unrelated upstream host binaries.
