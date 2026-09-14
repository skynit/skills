---
name: iso-recreate
description: Fully recreate a CWNAS Ubuntu installer ISO, including a fresh target RootFS, by running the project's complete build path. Use for installer, OS, package, service, kernel, initrd, boot, build-script, or other RootFS changes; use iso-refresh when only cwnas and frontend root changed.
---

# CWNAS ISO Recreate

Use this skill when the user requests a full CWNAS ISO package or when changes cannot be represented by replacing only `/opt/cwnas/cwnas` and `/var/lib/cwnas/root` in an existing image.

Use `$iso-refresh` instead when the only payload changes are the `cwnas` binary and the complete frontend `root/` directory and the user wants to reuse the latest known-good ISO.

## Resolve scope

1. Read the target project's instructions and inspect its status before building. Preserve all existing source changes and unrelated files; this workflow does not authorize source edits, commits, stashes, resets, or cleanup.
2. Confirm the requested variant before running a build:
   - Ordinary: `/home/skynit/workspace/build/cwnas-installer`.
   - Intel: `/home/skynit/workspace/build/cwnas-intel`.
   - Both: build each project separately only when the user explicitly requests both.
3. Use the target project's own `build-ubuntu.sh`. Do not mix binaries, frontend assets, output directories, or build scripts across variants.
4. Before building, require executable `cw/cwnas`, complete `cw/root/` with `web/index.html`, the expected installer binaries, and the build inputs validated by the script.
5. State the project and exact output directory. A full recreation replaces generated RootFS and ISO artifacts in that output directory.

## Recreate

From each requested project, run the complete build path:

```bash
cd /absolute/path/to/project
sudo env OUT_DIR="$PWD/out-ubuntu" ./build-ubuntu.sh all
```

Always use `all` in this skill. Do not use `iso`, because that reuses an existing `target-rootfs.squashfs` and cannot package RootFS-copied changes.

Do not run a repository-wide test suite. If code risk warrants tests before packaging, run only focused tests for the changed package, then proceed with the build. Do not modify source to repair a failure unless the user separately authorizes source changes.

## Verify artifacts

Verify each requested output from its actual output directory:

```bash
cd /absolute/path/to/project/out-ubuntu
sha256sum -c target-rootfs.squashfs.sha256
sha256sum -c cwnas-*.iso.sha256
xorriso -indev cwnas-*.iso -report_el_torito plain
```

Require both BIOS and UEFI El Torito entries. Extract the ISO's embedded `/cwnas/target-rootfs.squashfs` and checksum to a temporary directory, verify the nested checksum, and inspect the final squashfs for the inputs relevant to the change. For ordinary builds, at minimum compare the embedded `/opt/cwnas/cwnas` with `cw/cwnas` and confirm `/var/lib/cwnas/root/web/index.html` matches `cw/root/web/index.html`.

Use a temporary directory for extraction and remove only that resolved temporary directory after verification. Do not remove source or generated output artifacts.

## Report boundaries

Report the project, ISO path, ISO SHA256, RootFS checksum result, embedded payload checks, and BIOS/UEFI metadata result. Keep build/artifact proof separate from VM boot, installation, deployment, and physical-device proof. Run those runtime checks only when separately requested.
