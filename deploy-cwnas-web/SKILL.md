---
name: deploy-cwnas-web
description: "部署或替换已打包的 CWNAS 官方穿透平台前端静态资源，并验证线上页面与资源。用于用户明确要求发布官方穿透平台前端或上传其 Web 发布包时；不部署知识库 Vue 前端、模型后端或穿透测试平台。"
---

# CWNAS 官方穿透平台前端部署

Default deployment replaces only `root/web/` with the requested Web ZIP. Build or replace the share page or independent app page only when the user explicitly requests that frontend. Changes to the `cwnas` binary, server configuration, installation, or service state require a separate request.

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
- the packaged `main.dart.js` passes `official_mode_enabled(main_script_bytes)` from [deploy_web.py](scripts/deploy_web.py). Import the function with the skill's absolute `scripts/` directory on `PYTHONPATH` and `PYTHONDONTWRITEBYTECODE=1`.

If the check fails, stop before uploading and report that official mode could not be verified. The build flag that enables it is `--dart-define=isPlatformWeb=true`.

## Check The Separate Frontends

Before a Web deployment, check whether the sibling directories `root/share/` and `root/app/` exist relative to the target installation root (default `/opt/cwnas`). Report each missing directory by its absolute path and continue the Web deployment.

Use the file and HTTP checks below only for each separately built frontend the user explicitly asks to deploy. Keep its artifacts at its own installation path and back up the previous directory if present. The main Web ZIP and deployment script are scoped to `web/`.

| Frontend | Build command, run from the `cwnas_client` project root containing `build.dart` | Local output | Installed directory |
| --- | --- | --- | --- |
| Lightweight share page | `dart run build.dart share` | `build/share/` | `root/share/` |
| Independent platform app page | `dart run build.dart app` | `build/app-access/`; ZIP `build/app-access-<version-prefix>.zip` containing `root/app/` | `root/app/` |

Require nonempty regular files, rather than directory existence alone:

- Share: `root/share/index.html`, `root/share/flutter_bootstrap.js`, and `root/share/main.dart.js`. Confirm the HTML base path is `/share-web/`.
- App host (the page that starts the independent app): `root/app/host/index.html`, `app-host.js`, and `app-bootstrap.js` in that same directory.
- App runtime (the static files used to connect and run the app): `root/app/runtime/bridge.html`, `bridge.js`, `client.html`, `app-sw.js`, and `app-runtime.js`.
- App versioned assets: read the version referenced by `root/app/host/app-bootstrap.js`; require `root/app/assets/<version>/flutter_bootstrap.js`, `main.dart.js`, and `canvaskit/canvaskit.wasm`. An unrelated old version directory does not satisfy this check.

Validate the requested frontend's staged files before replacing its installed directory. Record their SHA-256 values and, for the app, the referenced asset version for HTTP verification. Report missing files with the corresponding build command if that frontend's artifact is incomplete.

## Deploy

1. Confirm non-interactive SSH access, the exact target directory, service state, free space, and current Web version/hash. Record the separate frontend directory check.
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
- public `main.dart.js` passes the same official mode check;
- public `version.json` matches the package;
- `/ping` returns `pong`;
- the service remains `active/running`, with unchanged PID and restart count;
- the backend binary SHA-256 is unchanged.

For a separately deployed share page, fetch `/share-web/`, `/share-web/flutter_bootstrap.js`, and `/share-web/main.dart.js` with cache-busting queries. For a separately deployed app page, fetch `/__cwnas/app-assets/<version>/flutter_bootstrap.js` and `/__cwnas/app-assets/<version>/main.dart.js`. Require successful responses and body hashes matching the installed files. Derive the app host and runtime resource URLs from the current backend routes on their respective `cw-<id>` and `cwapp-<id>` subdomains. Report any unchecked host or runtime HTTP access.

Do not claim login or browser-flow validation unless it was actually completed. Remind the user to use `Ctrl+F5` when the only remaining uncertainty is browser cache.

## Report

Report the package SHA-256, Web version/build, deployed main-script SHA-256, backup path, service state, and whether browser login was tested. If deployment failed, state whether automatic rollback restored the previous release.

Explicitly list any missing share or app directories found during a Web deployment. For each separately deployed frontend, report its installed directory, required-file and HTTP checks, the referenced app asset version when applicable, and any missing files or unverified access. Report these results separately from the Web result.
