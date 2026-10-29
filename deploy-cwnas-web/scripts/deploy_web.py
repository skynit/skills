#!/usr/bin/env python3
"""Atomically deploy a packaged CWNAS Web release on the target server."""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def service_state(service: str) -> str:
    return subprocess.check_output(
        [
            "systemctl",
            "show",
            service,
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "MainPID",
            "-p",
            "NRestarts",
        ],
        text=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    return parser.parse_args()


def validate_run_id(run_id: str) -> None:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if not run_id or any(character not in allowed for character in run_id):
        raise ValueError("run-id contains unsupported characters")


def exchange(first: Path, second: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = libc.renameat2
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(first), -100, os.fsencode(second), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def main() -> int:
    args = parse_args()
    validate_run_id(args.run_id)
    expected = args.expected_sha256.lower()
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise ValueError("expected-sha256 must be a SHA-256 hex digest")
    if digest(args.package) != expected:
        raise ValueError("uploaded package checksum mismatch")
    if args.target.resolve() != args.target or not args.target.is_dir():
        raise ValueError("target must be an existing absolute directory")

    backup = args.backup_root / args.run_id
    if backup.exists():
        raise FileExistsError(f"backup already exists: {backup}")

    backend_before = digest(args.backend)
    service_before = service_state(args.service)
    if "ActiveState=active" not in service_before or "SubState=running" not in service_before:
        raise RuntimeError("service is not active/running")

    backup.mkdir(mode=0o700, parents=True)
    try:
        with zipfile.ZipFile(args.package) as archive:
            names: set[str] = set()
            for entry in archive.infolist():
                path = PurePosixPath(entry.filename)
                if not path.parts or path.parts[0] != "web":
                    raise ValueError(f"archive entry is outside web/: {entry.filename}")
                if ".." in path.parts or path.is_absolute() or "\\" in entry.filename:
                    raise ValueError(f"unsafe archive entry: {entry.filename}")
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError(f"symbolic link is not allowed: {entry.filename}")
                if entry.filename in names:
                    raise ValueError(f"duplicate archive entry: {entry.filename}")
                names.add(entry.filename)
            invalid = archive.testzip()
            if invalid is not None:
                raise ValueError(f"corrupt archive entry: {invalid}")
            archive.extractall(backup)

        staged = backup / "web"
        version = json.loads((staged / "version.json").read_text())
        main_script = (staged / "main.dart.js").read_text()
        if "configureCwnasPlatformWeb(!0)" not in main_script:
            raise ValueError("official platform mode is disabled")

        for path in [staged, *staged.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)

        files = {
            path.relative_to(staged).as_posix(): digest(path)
            for path in staged.rglob("*")
            if path.is_file()
        }
        required = [
            "index.html",
            "version.json",
            "flutter_bootstrap.js",
            "main.dart.js",
            "flutter_service_worker.js",
            "canvaskit/canvaskit.wasm",
            "assets/FontManifest.json",
        ]
        missing = [name for name in required if name not in files]
        if missing:
            raise ValueError(f"required Web files are missing: {missing}")

        (backup / "new-files-sha256.json").write_text(json.dumps(files, indent=2))
        (backup / "deployment.json").write_text(
            json.dumps(
                {
                    "package_sha256": expected,
                    "new_version": version,
                    "old_version": json.loads((args.target / "version.json").read_text()),
                    "backend_sha256": backend_before,
                    "service_before": service_before,
                },
                indent=2,
            )
        )

        exchange(args.target, staged)
        try:
            deployed = {
                path.relative_to(args.target).as_posix(): digest(path)
                for path in args.target.rglob("*")
                if path.is_file()
            }
            if deployed != files:
                raise RuntimeError("deployed file manifest differs from staged release")

            authority = args.origin.removeprefix("https://")
            for name in required:
                data = subprocess.check_output(
                    [
                        "curl",
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--location",
                        "--max-time",
                        "30",
                        "--resolve",
                        f"{authority}:443:127.0.0.1",
                        f"{args.origin}/web/{name}?deployment={args.run_id}",
                    ]
                )
                if hashlib.sha256(data).hexdigest() != files[name]:
                    raise RuntimeError(f"HTTP checksum mismatch: {name}")
                print(f"HTTP checksum OK: {name}", flush=True)

            if digest(args.backend) != backend_before:
                raise RuntimeError("backend binary changed during Web deployment")
            if service_state(args.service) != service_before:
                raise RuntimeError("service state changed during Web deployment")
        except BaseException:
            exchange(args.target, staged)
            print("ROLLED BACK: original Web directory restored", flush=True)
            raise

        print(
            json.dumps(
                {
                    "status": "deployed",
                    "version": version,
                    "file_count": len(files),
                    "backup": str(staged),
                    "main_sha256": files["main.dart.js"],
                    "backend_unchanged": True,
                },
                indent=2,
            ),
            flush=True,
        )
    except BaseException:
        if backup.exists() and not (backup / "web").exists():
            try:
                backup.rmdir()
            except OSError:
                pass
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
