---
name: iso-refresh
description: Refresh an existing CWNAS installer ISO by replacing the cwnas binary and frontend root inside its target squashfs, with an optional verified early-start tty2 console unit replacement. Use a full build for other installer, OS, service, kernel, initrd, boot, package, or build-script changes.
---

# CWNAS ISO Refresh

Use this skill only when the requested ISO variant already has a known-good current image and the changed payload is limited to:

- `/usr/lib/cwnas-installer/cwnas`, sourced from the project's `cw/cwnas`.
- `/usr/lib/cwnas-installer/root`, sourced from the project's complete `cw/root/` directory.
- Optionally, `/etc/systemd/system/cwnas-console.service`, supplied explicitly with
  `--console-unit`, when the only service change is removing its boot-time network
  and CWNAS ordering so tty2 can render before those services are ready.

Older images may store the same payload at `/opt/cwnas/cwnas` and
`/var/lib/cwnas/root`; the bundled script detects either layout.

Do not use this path when any other RootFS or ISO input changed. In particular, changes to `cwnas-installer`, `cwnas-installer-gui`, packages, systemd units other than the supported tty2 console unit, installer/startup scripts, kernel/modules, initrd assets, bootloader/theme files, or build scripts require the normal full build.

## Resolve inputs

1. Read the target project's instructions and inspect its status without modifying source files. Preserve unrelated dirty work.
2. Confirm the user requested the ordinary or Intel variant. Resolve the newest ISO only inside that variant's output directory; never select an ISO across project boundaries. State the exact source ISO before rebuilding.
3. Verify the source ISO's adjacent `.sha256` file when present.
4. Require an executable x86-64 ELF `cw/cwnas` and a complete `cw/root/` containing `web/index.html`.
5. Choose a new output name in the same output directory. Never overwrite the source ISO or an existing output.

## Refresh

Run the bundled script as root so squashfs ownership, modes, links, and metadata survive extraction and repacking:

```bash
sudo /home/skynit/.codex/skills/iso-refresh/scripts/refresh_iso.sh \
  --iso /absolute/path/to/source.iso \
  --cwnas /absolute/path/to/cw/cwnas \
  --root /absolute/path/to/cw/root \
  --console-unit /absolute/path/to/cwnas-console.service \
  --output /absolute/path/to/refreshed.iso
```

Omit `--console-unit` for a payload-only refresh. When supplied, the unit must target
`/dev/tty2`, start after `systemd-vconsole-setup.service`, and contain no ordering or
wants dependency on `network-online.target` or `cwnas.service`.

The script uses `xorriso` to unpack the selected ISO, updates the nested `target-rootfs.squashfs`, refreshes its checksum and `MEDIA_ID`, synchronizes the same media identity into `/etc/cwnas-media-id` inside `install.amd/gtk/initrd.gz`, regenerates the ISO checksum manifest, and rebuilds the original BIOS/UEFI hybrid layout. The ISO and initrd media identities must remain equal because the early-boot media helper rejects an ISO whose identity differs from the value embedded in initrd. The script uses a temporary working directory and removes it on exit.

Do not edit `VERSION`, `.disk/info`, or other release metadata unless the user explicitly requests a version change. Do not run the full build in this mode.

## Evidence boundary

The script verifies the final ISO SHA256, embedded squashfs SHA256, ISO `MEDIA_ID`, initrd `/etc/cwnas-media-id`, byte identity of the embedded `cwnas`, frontend file identity, optional console unit identity and mode, and BIOS/UEFI El Torito entries. Report the output path and SHA256.

These checks prove artifact composition only. Do not claim VM boot, installation, deployment, or physical-device behavior unless those checks were separately requested and performed.
