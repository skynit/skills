---
name: deploy-cwnas-web
description: Safely replace and verify the official CWNAS Web client on cwnas.net or another CWNAS host. Use when the user asks to upload, replace, or redeploy a packaged CWNAS Web build; do not use for backend binary deployments.
---

# Deploy CWNAS Web

Deploy only the packaged Web resources. Do not replace the `cwnas` binary, change server configuration, run `cwnas install`, or restart the service unless the user separately requests it.

## Defaults

Use these established values unless the user specifies others:

- SSH target: `root@47.122.107.92`
- Web directory: `/opt/cwnas/root/web`
- Upload directory: `/opt/cwnas/.uploads`
- Backup directory: `/opt/cwnas/backups`
- Public origin: `https://cwnas.net`
- Service: `cwnas.service`
- Backend binary: `/opt/cwnas/cwnas`

## Inspect The Package

Read the exact path supplied by the user. Never substitute a previously uploaded package when a new local or network path is inaccessible.

Before upload, record the package path, size, modification time, and SHA-256. Inspect the ZIP with a structured archive API and require:

- every entry is under one top-level `web/` directory;
- `web/version.json`, `web/index.html`, and `web/main.dart.js` exist;
- `version.json` is valid JSON;
- an official build contains `configureCwnasPlatformWeb(!0)` in `main.dart.js`.

If official mode is absent, stop and report that the build was not compiled with `--dart-define=isPlatformWeb=true`.

## Deploy

1. Confirm non-interactive SSH access, the exact target directory, service state, free space, and current Web version/hash.
2. Generate a unique UTC run ID. Upload the ZIP as `<upload-dir>/<run-id>.zip` and upload [deploy_web.py](scripts/deploy_web.py).
3. Compare the remote ZIP SHA-256 with the local value before executing it.
4. Run the script on the server, passing the package, run ID, target, backup root, public origin, service, and backend binary.

Example:

```powershell
ssh root@47.122.107.92 "python3 /opt/cwnas/.uploads/deploy_web.py --package /opt/cwnas/.uploads/<run-id>.zip --run-id <run-id> --target /opt/cwnas/root/web --backup-root /opt/cwnas/backups --origin https://cwnas.net --service cwnas.service --backend /opt/cwnas/cwnas --expected-sha256 <sha256>"
```

The script validates archive paths and symlinks, stages the release, records manifests, atomically exchanges directories, checks representative HTTP resources, and restores the old directory on failure. After success, `<backup-root>/<run-id>/web` is the previous live Web directory.

## Verify

Fetch public resources with a cache-busting query string and require:

- public `main.dart.js` SHA-256 equals the deployed file;
- public `main.dart.js` still contains `configureCwnasPlatformWeb(!0)`;
- public `version.json` matches the package;
- `/ping` returns `pong`;
- the service remains `active/running`, with unchanged PID and restart count;
- the backend binary SHA-256 is unchanged.

Do not claim login or browser-flow validation unless it was actually completed. Remind the user to use `Ctrl+F5` when the only remaining uncertainty is browser cache.

## Report

Report the package SHA-256, Web version/build, deployed main-script SHA-256, backup path, service state, and whether browser login was tested. If deployment failed, state whether automatic rollback restored the previous release.
