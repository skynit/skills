#!/usr/bin/env python3
"""Small, dependency-free task/event ledger for event-driven agent work.

The script never creates or contacts agent sessions. It only validates and
atomically persists state supplied by the coordinator. Callers must choose an
explicit state path and confirm its parent is an approved, ignored location
before using a mutating command.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 4
WAKE_STATES = frozenset({"DONE", "FAILED", "BLOCKED", "NEEDS_APPROVAL"})
MODES = frozenset({"LIGHT_MODE", "STRICT_MODE"})
LIFECYCLE_READY_HOST_STATUSES = frozenset({"idle", "notLoaded"})
HOST_STATUSES = LIFECYCLE_READY_HOST_STATUSES | frozenset({"active", "systemError"})
STATUSES = frozenset(
    {
        "PENDING_DISPATCH",
        "ASSIGNED",
        "IN_PROGRESS",
        "WAITING_EVENT",
        "STALLED",
        "PARTIAL",
        "NEEDS_APPROVAL",
        "DONE",
        "FAILED",
        "BLOCKED",
        "CLOSED",
    }
)
TRANSITIONS = {
    "PENDING_DISPATCH": frozenset({"ASSIGNED", "BLOCKED"}),
    "ASSIGNED": frozenset(
        {"IN_PROGRESS", "WAITING_EVENT", "PARTIAL", "DONE", "FAILED", "BLOCKED", "NEEDS_APPROVAL"}
    ),
    "IN_PROGRESS": frozenset(
        {"WAITING_EVENT", "PARTIAL", "DONE", "FAILED", "BLOCKED", "NEEDS_APPROVAL"}
    ),
    "WAITING_EVENT": frozenset(
        {"IN_PROGRESS", "STALLED", "PARTIAL", "DONE", "FAILED", "BLOCKED", "NEEDS_APPROVAL"}
    ),
    "STALLED": frozenset({"IN_PROGRESS", "WAITING_EVENT", "FAILED", "BLOCKED"}),
    "PARTIAL": frozenset({"IN_PROGRESS", "WAITING_EVENT", "DONE", "FAILED", "BLOCKED", "NEEDS_APPROVAL"}),
    "NEEDS_APPROVAL": frozenset({"IN_PROGRESS", "WAITING_EVENT", "DONE", "FAILED", "BLOCKED"}),
    "DONE": frozenset({"CLOSED"}),
    "FAILED": frozenset({"CLOSED"}),
    "BLOCKED": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DELIVERY_MODES = frozenset({"cross-thread-message", "host-wait", "unavailable"})
CONTENT_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class LedgerError(ValueError):
    """An invalid ledger or state transition."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: Any, label: str) -> str | None:
    return _required_text(value, label) if value is not None else None


def _identifier(value: Any, label: str) -> str:
    value = _required_text(value, label)
    if not IDENTIFIER.fullmatch(value):
        raise LedgerError(f"{label} must contain only letters, digits, '.', '_' or '-'")
    return value


def _state_file(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise LedgerError("--state-file must be an absolute path")
    return path


def _new_ledger(path: Path, batch_id: str, master_thread_id: str, objective: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "batch_id": _identifier(batch_id, "batch_id"),
        "master_thread_id": _required_text(master_thread_id, "master_thread_id"),
        "state_file": str(path),
        "objective": _required_text(objective, "objective"),
        "revision": 0,
        "checkpoint": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "tasks": {},
        "events": {},
        "event_order": [],
        "consumed_event_count": 0,
    }


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise LedgerError(f"state file does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read state file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LedgerError("state file root must be a JSON object")
    verify_ledger(value)
    return value


def _atomic_write(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def _lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f"{path.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _touch(ledger: dict[str, Any]) -> None:
    ledger["revision"] += 1
    ledger["updated_at"] = utc_now()


def _transition_allowed(source: str, target: str) -> bool:
    return target in TRANSITIONS.get(source, frozenset())


def _task(ledger: dict[str, Any], task_id: str) -> dict[str, Any]:
    task_id = _identifier(task_id, "task_id")
    task = ledger["tasks"].get(task_id)
    if task is None:
        raise LedgerError(f"unknown task: {task_id}")
    return task


def _append_transition(task: dict[str, Any], target: str, reason: str) -> None:
    current = task["status"]
    if target not in STATUSES:
        raise LedgerError(f"invalid status: {target}")
    if not _transition_allowed(current, target):
        raise LedgerError(f"invalid transition: {current} -> {target}")
    now = utc_now()
    task["transitions"].append({"from": current, "to": target, "reason": reason, "at": now})
    task["status"] = target
    task["updated_at"] = now


def init_ledger(path: Path, batch_id: str, master_thread_id: str, objective: str) -> dict[str, Any]:
    with _lock(path):
        if path.exists():
            ledger = _read(path)
            if ledger["batch_id"] != batch_id:
                raise LedgerError(f"existing batch_id differs: {ledger['batch_id']}")
            if ledger["master_thread_id"] != master_thread_id:
                raise LedgerError(f"existing master_thread_id differs: {ledger['master_thread_id']}")
            if ledger["objective"] != objective:
                raise LedgerError("existing objective differs")
            return ledger
        ledger = _new_ledger(path, batch_id, master_thread_id, objective)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return ledger


def _new_task(
    *,
    task_id: str,
    status: str,
    thread_id: str | None,
    host_id: str | None,
    client_thread_id: str | None,
    role: str,
    project: str,
    model: str,
    mode: str,
    scope: str,
    acceptance: str,
    depends_on: list[str],
    delivery_mode: str,
    deadline_at: str | None,
    skill_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    now = utc_now()
    return {
        "task_id": task_id,
        "thread_id": thread_id,
        "host_id": host_id,
        "client_thread_id": client_thread_id,
        "role": role,
        "project": project,
        "model": model,
        "mode": mode,
        "scope": scope,
        "acceptance": acceptance,
        "depends_on": depends_on,
        "delivery_mode": delivery_mode,
        "wait_cursor": None,
        "deadline_at": deadline_at,
        "last_seen_at": now,
        "result_reference": None,
        "skill_bindings": skill_bindings,
        "status": status,
        "attempt": 0,
        "created_at": now,
        "updated_at": now,
        "transitions": [{"from": None, "to": status, "reason": "register", "at": now}],
        "events": [],
        "last_event_id": None,
    }


def _normalize_skill_bindings(bindings: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for binding in bindings or []:
        if not isinstance(binding, dict):
            raise LedgerError("skill binding must be an object")
        selector = _required_text(binding.get("selector"), "skill.selector")
        if selector.startswith("$"):
            raise LedgerError("skill.selector must not include the '$' invocation prefix")
        required = binding.get("required")
        if not isinstance(required, bool):
            raise LedgerError("skill.required must be a boolean")
        available = binding.get("available")
        loaded = binding.get("loaded")
        if available is not None and not isinstance(available, bool):
            raise LedgerError("skill.available must be a boolean or null")
        if loaded is not None and not isinstance(loaded, bool):
            raise LedgerError("skill.loaded must be a boolean or null")
        if loaded is True and available is not True:
            raise LedgerError("a loaded skill must be available")
        source_locator = binding.get("source_locator")
        if available is True and source_locator is None:
            raise LedgerError("an available skill requires source_locator")
        normalized.append(
            {
                "selector": selector,
                "required": required,
                "purpose": _required_text(binding.get("purpose"), "skill.purpose"),
                "source_locator": _optional_text(source_locator, "skill.source_locator"),
                "frontmatter_name": _optional_text(
                    binding.get("frontmatter_name"), "skill.frontmatter_name"
                ),
                "source_version": _optional_text(
                    binding.get("source_version"), "skill.source_version"
                ),
                "content_digest": _optional_text(
                    binding.get("content_digest"), "skill.content_digest"
                ),
                "available": available,
                "loaded": loaded,
            }
        )
        content_digest = normalized[-1]["content_digest"]
        if content_digest is not None and not CONTENT_DIGEST.fullmatch(content_digest):
            raise LedgerError("skill.content_digest must use sha256:<64 lowercase hex characters>")
    if len(normalized) > 2:
        raise LedgerError("a worker may load at most two direct skills")
    selectors = [binding["selector"] for binding in normalized]
    if len(set(selectors)) != len(selectors):
        raise LedgerError("skill selectors must be unique")
    return normalized


def _verify_local_content_digest(source_locator: str | None, content_digest: str) -> None:
    if source_locator is None:
        raise LedgerError("content_digest requires source_locator")
    source_path = Path(source_locator)
    if not source_path.is_absolute() or not source_path.is_file():
        raise LedgerError("content_digest requires an existing absolute local source_locator")
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        raise LedgerError(f"cannot read skill source for digest verification: {exc}") from exc
    actual = f"sha256:{hashlib.sha256(source_bytes).hexdigest()}"
    if actual != content_digest:
        raise LedgerError("content_digest does not match source_locator content")


def _normalize_task_fields(
    *,
    task_id: str,
    role: str,
    project: str,
    model: str,
    mode: str,
    scope: str,
    acceptance: str,
    depends_on: list[str] | None,
    delivery_mode: str,
    deadline_at: str | None,
    skill_bindings: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    task_id = _identifier(task_id, "task_id")
    normalized_dependencies = [_identifier(value, "depends_on") for value in (depends_on or [])]
    if task_id in normalized_dependencies:
        raise LedgerError("task cannot depend on itself")
    if len(set(normalized_dependencies)) != len(normalized_dependencies):
        raise LedgerError("depends_on values must be unique")
    if delivery_mode not in DELIVERY_MODES:
        raise LedgerError(f"delivery_mode must be one of: {', '.join(sorted(DELIVERY_MODES))}")
    if mode not in MODES:
        raise LedgerError(f"mode must be one of: {', '.join(sorted(MODES))}")
    return {
        "task_id": task_id,
        "role": _required_text(role, "role"),
        "project": _required_text(project, "project"),
        "model": _required_text(model, "model"),
        "mode": mode,
        "scope": _required_text(scope, "scope"),
        "acceptance": _required_text(acceptance, "acceptance"),
        "depends_on": normalized_dependencies,
        "delivery_mode": delivery_mode,
        "deadline_at": _optional_text(deadline_at, "deadline_at"),
        "skill_bindings": _normalize_skill_bindings(skill_bindings),
    }


def reserve_task(
    path: Path,
    *,
    task_id: str,
    client_thread_id: str,
    role: str,
    project: str,
    model: str,
    mode: str = "LIGHT_MODE",
    scope: str,
    acceptance: str,
    depends_on: list[str] | None = None,
    delivery_mode: str = "host-wait",
    deadline_at: str | None = None,
    skill_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fields = _normalize_task_fields(
        task_id=task_id,
        role=role,
        project=project,
        model=model,
        mode=mode,
        scope=scope,
        acceptance=acceptance,
        depends_on=depends_on,
        delivery_mode=delivery_mode,
        deadline_at=deadline_at,
        skill_bindings=skill_bindings,
    )
    client_thread_id = _required_text(client_thread_id, "client_thread_id")
    with _lock(path):
        ledger = _read(path)
        existing = ledger["tasks"].get(fields["task_id"])
        identity = {"client_thread_id": client_thread_id, **fields}
        if existing is not None:
            if any(existing[key] != value for key, value in identity.items()):
                raise LedgerError(f"task already reserved with conflicting identity: {fields['task_id']}")
            return {"result": "duplicate", "task": existing}
        task = _new_task(
            **identity,
            status="PENDING_DISPATCH",
            thread_id=None,
            host_id=None,
        )
        ledger["tasks"][fields["task_id"]] = task
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "reserved", "task": task}


def bind_task(path: Path, *, task_id: str, thread_id: str, host_id: str) -> dict[str, Any]:
    thread_id = _required_text(thread_id, "thread_id")
    host_id = _required_text(host_id, "host_id")
    with _lock(path):
        ledger = _read(path)
        task = _task(ledger, task_id)
        if task["thread_id"] is not None:
            if task["thread_id"] == thread_id and task["host_id"] == host_id:
                return {"result": "duplicate", "task": task}
            raise LedgerError(f"task already bound to a different thread: {task_id}")
        if task["status"] != "PENDING_DISPATCH":
            raise LedgerError(f"only PENDING_DISPATCH tasks can be bound: {task_id}")
        task["thread_id"] = thread_id
        task["host_id"] = host_id
        _append_transition(task, "ASSIGNED", "bind-thread")
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "bound", "task": task}


def mark_dispatch_failed(path: Path, *, task_id: str, error_reference: str) -> dict[str, Any]:
    error_reference = _required_text(error_reference, "error_reference")
    with _lock(path):
        ledger = _read(path)
        task = _task(ledger, task_id)
        if task["status"] != "PENDING_DISPATCH" or task["thread_id"] is not None:
            raise LedgerError("only an unbound PENDING_DISPATCH task can record dispatch failure")
        _append_transition(task, "BLOCKED", "DISPATCH_FAILURE")
        task["result_reference"] = error_reference
        task["last_seen_at"] = utc_now()
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "dispatch-failed", "task": task}


def record_skill_result(
    path: Path,
    *,
    task_id: str,
    selector: str,
    available: bool,
    loaded: bool,
    source_locator: str | None = None,
    frontmatter_name: str | None = None,
    source_version: str | None = None,
    content_digest: str | None = None,
) -> dict[str, Any]:
    selector = _required_text(selector, "selector")
    candidate = {
        "available": available,
        "loaded": loaded,
        "source_locator": source_locator,
        "frontmatter_name": frontmatter_name,
        "source_version": source_version,
        "content_digest": content_digest,
    }
    if loaded and not available:
        raise LedgerError("a loaded skill must be available")
    with _lock(path):
        ledger = _read(path)
        task = _task(ledger, task_id)
        binding = next(
            (value for value in task["skill_bindings"] if value["selector"] == selector),
            None,
        )
        if binding is None:
            raise LedgerError(f"skill selector is not assigned to task: {selector}")
        merged = {
            key: value if value is not None else binding[key]
            for key, value in candidate.items()
        }
        if content_digest is not None:
            _verify_local_content_digest(merged["source_locator"], content_digest)
        if task["mode"] == "STRICT_MODE" and merged["loaded"] is True:
            if merged["source_version"] is None and merged["content_digest"] is None:
                raise LedgerError(
                    "STRICT_MODE loaded skill requires source_version or content_digest"
                )
        for key, value in candidate.items():
            if value is None or binding[key] is None or binding[key] == value:
                continue
            if key == "loaded" and binding[key] is False and value is True and available:
                continue
            raise LedgerError(f"skill result conflicts for {selector}: {key}")
        for key, value in candidate.items():
            if value is not None:
                binding[key] = value
        task["last_seen_at"] = utc_now()
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "recorded", "skill_binding": binding, "task": task}


def register_task(
    path: Path,
    *,
    task_id: str,
    thread_id: str,
    host_id: str,
    role: str,
    project: str,
    model: str,
    mode: str = "LIGHT_MODE",
    scope: str,
    acceptance: str,
    depends_on: list[str] | None = None,
    delivery_mode: str = "cross-thread-message",
    deadline_at: str | None = None,
    skill_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fields = _normalize_task_fields(
        task_id=task_id,
        role=role,
        project=project,
        model=model,
        mode=mode,
        scope=scope,
        acceptance=acceptance,
        depends_on=depends_on,
        delivery_mode=delivery_mode,
        deadline_at=deadline_at,
        skill_bindings=skill_bindings,
    )
    thread_id = _required_text(thread_id, "thread_id")
    host_id = _required_text(host_id, "host_id")
    with _lock(path):
        ledger = _read(path)
        existing = ledger["tasks"].get(fields["task_id"])
        identity = {
            "thread_id": thread_id,
            "host_id": host_id,
            "client_thread_id": None,
            **fields,
        }
        if existing is not None:
            if any(existing[key] != value for key, value in identity.items()):
                raise LedgerError(f"task already registered with conflicting identity: {fields['task_id']}")
            return {"result": "duplicate", "task": existing}
        task = _new_task(
            **identity,
            status="ASSIGNED",
        )
        ledger["tasks"][fields["task_id"]] = task
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "registered", "task": task}


def _dependency_succeeded(task: dict[str, Any]) -> bool:
    if task["status"] == "DONE":
        return True
    return task["status"] == "CLOSED" and task["transitions"][-1]["from"] == "DONE"


def _ensure_dependencies_succeeded(ledger: dict[str, Any], task: dict[str, Any]) -> None:
    incomplete = [
        task_id
        for task_id in task["depends_on"]
        if not _dependency_succeeded(ledger["tasks"][task_id])
    ]
    if incomplete:
        raise LedgerError(f"dependencies are not complete: {', '.join(incomplete)}")


def transition_task(
    path: Path,
    *,
    task_id: str,
    target: str,
    reason: str = "manual",
    wait_cursor: str | None = None,
    deadline_at: str | None = None,
) -> dict[str, Any]:
    target = _required_text(target, "status")
    reason = _required_text(reason, "reason")
    if target == "STALLED":
        raise LedgerError("use the stalled command to enforce deadline_at")
    if target in WAKE_STATES:
        raise LedgerError("use the event command for TASK_EVENT wake states")
    if target != "WAITING_EVENT" and (wait_cursor is not None or deadline_at is not None):
        raise LedgerError("wait_cursor and deadline_at require WAITING_EVENT")
    with _lock(path):
        ledger = _read(path)
        task = _task(ledger, task_id)
        if target == "IN_PROGRESS":
            _ensure_dependencies_succeeded(ledger, task)
        if target == "CLOSED":
            last_event_id = task["last_event_id"]
            consumed = ledger["event_order"][: ledger["consumed_event_count"]]
            dispatch_failed = (
                task["thread_id"] is None
                and task["status"] == "BLOCKED"
                and task["transitions"][-1]["reason"] == "DISPATCH_FAILURE"
            )
            if not dispatch_failed and (last_event_id is None or last_event_id not in consumed):
                raise LedgerError("cannot close a task before its final TASK_EVENT is consumed")
        _append_transition(task, target, reason)
        if target == "IN_PROGRESS":
            task["attempt"] += 1
        if wait_cursor is not None:
            task["wait_cursor"] = _required_text(wait_cursor, "wait_cursor")
        if deadline_at is not None:
            task["deadline_at"] = _required_text(deadline_at, "deadline_at")
        task["last_seen_at"] = utc_now()
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "transitioned", "task": task}


def mark_stalled(path: Path, *, task_id: str, now: dt.datetime | None = None) -> dict[str, Any]:
    with _lock(path):
        ledger = _read(path)
        task = _task(ledger, task_id)
        if task["status"] != "WAITING_EVENT":
            raise LedgerError("only WAITING_EVENT tasks can become STALLED")
        if task["deadline_at"] is None:
            raise LedgerError("task has no deadline_at")
        try:
            deadline = dt.datetime.fromisoformat(task["deadline_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise LedgerError("deadline_at must be an ISO-8601 timestamp") from exc
        current = now or dt.datetime.now(dt.timezone.utc)
        if deadline.tzinfo is None:
            raise LedgerError("deadline_at must include a timezone")
        if current.tzinfo is None:
            raise LedgerError("current time must include a timezone")
        if current < deadline:
            raise LedgerError("task deadline has not passed")
        _append_transition(task, "STALLED", "deadline-expired")
        task["last_seen_at"] = utc_now()
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "stalled", "task": task}


def checkpoint(path: Path, *, next_action: str, reason: str) -> dict[str, Any]:
    next_action = _required_text(next_action, "next_action")
    reason = _required_text(reason, "reason")
    with _lock(path):
        ledger = _read(path)
        if ledger["consumed_event_count"] != len(ledger["event_order"]):
            raise LedgerError("cannot checkpoint with unconsumed TASK_EVENT records")
        unsafe = [
            task_id
            for task_id, task in ledger["tasks"].items()
            if task["status"] in {"PENDING_DISPATCH", "ASSIGNED", "IN_PROGRESS", "NEEDS_APPROVAL"}
        ]
        if unsafe:
            raise LedgerError(f"cannot checkpoint while tasks need active coordination: {', '.join(sorted(unsafe))}")
        now = utc_now()
        _touch(ledger)
        ledger["checkpoint"] = {
            "created_at": now,
            "reason": reason,
            "next_action": next_action,
            "ledger_revision": ledger["revision"],
            "event_count": len(ledger["events"]),
            "consumed_event_count": ledger["consumed_event_count"],
            "task_count": len(ledger["tasks"]),
        }
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "checkpointed", "checkpoint": ledger["checkpoint"]}


def _recovery_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": task["status"],
        "thread_id": task["thread_id"],
        "host_id": task["host_id"],
        "client_thread_id": task["client_thread_id"],
        "role": task["role"],
        "project": task["project"],
        "model": task["model"],
        "mode": task["mode"],
        "scope": task["scope"],
        "acceptance": task["acceptance"],
        "depends_on": task["depends_on"],
        "delivery_mode": task["delivery_mode"],
        "skill_bindings": task["skill_bindings"],
        "wait_cursor": task["wait_cursor"],
        "deadline_at": task["deadline_at"],
        "result_reference": task["result_reference"],
    }


def resume_summary(path: Path, *, include_closed: bool = False) -> dict[str, Any]:
    with _lock(path):
        ledger = _read(path)
        checkpoint_value = ledger["checkpoint"]
        visible_tasks = {
            task_id: task
            for task_id, task in ledger["tasks"].items()
            if include_closed or task["status"] != "CLOSED"
        }
        hidden_dependency_ids = sorted(
            {
                dependency_id
                for task in visible_tasks.values()
                for dependency_id in task["depends_on"]
                if dependency_id not in visible_tasks
            }
        )
        resolved_dependencies = {}
        for task_id in hidden_dependency_ids:
            dependency = ledger["tasks"][task_id]
            resolved_dependencies[task_id] = {
                "status": dependency["status"],
                "terminal_state": dependency["transitions"][-1]["from"],
                "result_reference": dependency["result_reference"],
            }
        return {
            "batch_id": ledger["batch_id"],
            "master_thread_id": ledger["master_thread_id"],
            "state_file": ledger["state_file"],
            "objective": ledger["objective"],
            "revision": ledger["revision"],
            "checkpoint": checkpoint_value,
            "checkpoint_current": (
                checkpoint_value is not None
                and checkpoint_value["ledger_revision"] == ledger["revision"]
            ),
            "tasks_scope": "all" if include_closed else "open",
            "tasks": {
                task_id: _recovery_task(task)
                for task_id, task in sorted(visible_tasks.items())
            },
            "closed_task_count": sum(
                task["status"] == "CLOSED" for task in ledger["tasks"].values()
            ),
            "resolved_dependencies": resolved_dependencies,
            "unconsumed_events": [
                ledger["events"][event_id]
                for event_id in ledger["event_order"][ledger["consumed_event_count"] :]
            ],
        }


def _event_matches(
    event: dict[str, Any],
    task: dict[str, Any],
    state: str,
    result_reference: str,
    decision_required: bool,
    blocker: str,
) -> bool:
    return (
        event["task_id"] == task["task_id"]
        and event["state"] == state
        and event["result_reference"] == result_reference
        and event["decision_required"] == decision_required
        and event["blocker"] == blocker
    )


def _resolve_duplicate_event(
    ledger: dict[str, Any],
    task: dict[str, Any],
    event_id: str | None,
    state: str,
    result_reference: str,
    decision_required: bool,
    blocker: str,
) -> tuple[str | None, dict[str, Any] | None]:
    implicit_retry = event_id is None and task["status"] == state and task["last_event_id"] is not None
    if implicit_retry:
        event_id = task["last_event_id"]
    elif event_id is not None:
        event_id = _required_text(event_id, "event_id")
    else:
        return None, None
    previous = ledger["events"].get(event_id)
    if previous is None:
        return event_id, None
    if not _event_matches(previous, task, state, result_reference, decision_required, blocker):
        if implicit_retry:
            raise LedgerError(f"same-state event conflicts with last event: {event_id}")
        raise LedgerError(f"event_id already exists with conflicting payload: {event_id}")
    return event_id, {"result": "duplicate", "event": previous, "task": task}


def _new_task_event(
    task: dict[str, Any],
    state: str,
    result_reference: str,
    decision_required: bool,
    blocker: str,
    requested_id: str | None,
) -> dict[str, Any]:
    sequence = len(task["events"]) + 1
    event_id = f"{task['thread_id']}:{task['task_id']}:{state}:{sequence}"
    if requested_id is not None and requested_id != event_id:
        raise LedgerError(f"event_id must be {event_id}")
    return {
        "event_id": event_id,
        "event_sequence": sequence,
        "task_id": task["task_id"],
        "source_thread_id": task["thread_id"],
        "state": state,
        "result_reference": result_reference,
        "decision_required": decision_required,
        "blocker": blocker,
        "created_at": utc_now(),
    }


def _store_task_event(ledger: dict[str, Any], task: dict[str, Any], event: dict[str, Any]) -> None:
    event_id = event["event_id"]
    _append_transition(task, event["state"], "TASK_EVENT")
    task["events"].append(event_id)
    task["last_event_id"] = event_id
    task["result_reference"] = event["result_reference"]
    task["last_seen_at"] = event["created_at"]
    ledger["events"][event_id] = event
    ledger["event_order"].append(event_id)


def record_event(
    path: Path,
    *,
    task_id: str,
    state: str,
    result_reference: str,
    decision_required: bool = False,
    blocker: str = "none",
    event_id: str | None = None,
) -> dict[str, Any]:
    state = _required_text(state, "event state")
    if state not in WAKE_STATES:
        raise LedgerError(f"event state must be one of: {', '.join(sorted(WAKE_STATES))}")
    result_reference = _required_text(result_reference, "result_reference")
    blocker = _required_text(blocker, "blocker")
    with _lock(path):
        ledger = _read(path)
        task = _task(ledger, task_id)
        if task["thread_id"] is None:
            raise LedgerError("TASK_EVENT requires a bound thread_id")
        if state == "DONE":
            missing = [
                binding["selector"]
                for binding in task["skill_bindings"]
                if binding["required"] and binding["loaded"] is not True
            ]
            if missing:
                raise LedgerError(f"required skills are not loaded: {', '.join(missing)}")
        event_id, duplicate = _resolve_duplicate_event(
            ledger,
            task,
            event_id,
            state,
            result_reference,
            decision_required,
            blocker,
        )
        if duplicate is not None:
            return duplicate
        if not _transition_allowed(task["status"], state):
            raise LedgerError(f"invalid event transition: {task['status']} -> {state}")
        event = _new_task_event(
            task,
            state,
            result_reference,
            decision_required,
            blocker,
            event_id,
        )
        _store_task_event(ledger, task, event)
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "recorded", "event": event, "task": task}


def consume_event(path: Path, *, event_id: str) -> dict[str, Any]:
    event_id = _required_text(event_id, "event_id")
    with _lock(path):
        ledger = _read(path)
        consumed = ledger["consumed_event_count"]
        if event_id in ledger["event_order"][:consumed]:
            return {"result": "duplicate", "event_id": event_id}
        if consumed >= len(ledger["event_order"]):
            raise LedgerError("no unconsumed TASK_EVENT records")
        expected = ledger["event_order"][consumed]
        if event_id != expected:
            raise LedgerError(f"next event to consume is {expected}")
        ledger["consumed_event_count"] += 1
        _touch(ledger)
        verify_ledger(ledger)
        _atomic_write(path, ledger)
        return {"result": "consumed", "event_id": event_id}


def status(path: Path, task_id: str | None = None) -> dict[str, Any]:
    with _lock(path):
        ledger = _read(path)
        if task_id is None:
            return {
                "batch_id": ledger["batch_id"],
                "updated_at": ledger["updated_at"],
                "tasks": {
                    key: {"status": value["status"], "thread_id": value["thread_id"], "role": value["role"]}
                    for key, value in sorted(ledger["tasks"].items())
                },
                "event_count": len(ledger["events"]),
                "consumed_event_count": ledger["consumed_event_count"],
                "unconsumed_event_count": len(ledger["event_order"]) - ledger["consumed_event_count"],
            }
        task = _task(ledger, task_id)
        return {"task": task, "events": [ledger["events"][event_id] for event_id in task["events"]]}


def assess_thread_lifecycle(path: Path, *, thread_id: str, host_status: str) -> dict[str, Any]:
    """Combine a real host status with ledger closure evidence."""
    thread_id = _required_text(thread_id, "thread_id")
    if host_status not in HOST_STATUSES:
        raise LedgerError(f"host_status must be one of: {', '.join(sorted(HOST_STATUSES))}")
    with _lock(path):
        ledger = _read(path)
        tasks = [task for task in ledger["tasks"].values() if task["thread_id"] == thread_id]
        reasons: list[str] = []
        if host_status not in LIFECYCLE_READY_HOST_STATUSES:
            reasons.append(f"host-status-{host_status}")
        if not tasks:
            reasons.append("thread-not-registered")
        open_tasks = sorted(task["task_id"] for task in tasks if task["status"] != "CLOSED")
        if open_tasks:
            reasons.append(f"tasks-not-closed:{','.join(open_tasks)}")
        unconsumed_ids = ledger["event_order"][ledger["consumed_event_count"] :]
        if any(ledger["events"][event_id]["source_thread_id"] == thread_id for event_id in unconsumed_ids):
            reasons.append("unconsumed-task-event")
        return {
            "thread_id": thread_id,
            "host_status": host_status,
            "lifecycle_ready": not reasons,
            "reasons": reasons,
            "task_ids": sorted(task["task_id"] for task in tasks),
        }


def _verify_checkpoint(ledger: dict[str, Any]) -> None:
    checkpoint_value = ledger.get("checkpoint")
    if checkpoint_value is None:
        return
    if not isinstance(checkpoint_value, dict):
        raise LedgerError("checkpoint must be an object or null")
    for field in ("created_at", "reason", "next_action"):
        _required_text(checkpoint_value.get(field), f"checkpoint.{field}")
    for field in ("ledger_revision", "event_count", "consumed_event_count", "task_count"):
        if not isinstance(checkpoint_value.get(field), int):
            raise LedgerError(f"checkpoint.{field} must be an integer")
    if "tasks" in checkpoint_value:
        raise LedgerError("checkpoint must not duplicate ledger.tasks")
    if not 0 <= checkpoint_value["ledger_revision"] <= ledger["revision"]:
        raise LedgerError("checkpoint.ledger_revision is out of range")
    counts = {
        "event_count": len(ledger["events"]),
        "consumed_event_count": ledger["consumed_event_count"],
        "task_count": len(ledger["tasks"]),
    }
    if any(not 0 <= checkpoint_value[field] <= current for field, current in counts.items()):
        raise LedgerError("checkpoint count exceeds current ledger state")
    if checkpoint_value["ledger_revision"] == ledger["revision"]:
        if any(checkpoint_value[field] != current for field, current in counts.items()):
            raise LedgerError("current checkpoint disagrees with ledger state")


def _verify_task_identity(key: str, task: Any, tasks: dict[str, Any]) -> None:
    _identifier(key, "task_id")
    if not isinstance(task, dict) or task.get("task_id") != key:
        raise LedgerError(f"invalid task record: {key}")
    thread_id = task.get("thread_id")
    host_id = task.get("host_id")
    if (thread_id is None) != (host_id is None):
        raise LedgerError(f"thread_id and host_id must be set together: {key}")
    if thread_id is not None:
        _required_text(thread_id, "thread_id")
        _required_text(host_id, "host_id")
    client_thread_id = task.get("client_thread_id")
    if client_thread_id is not None:
        _required_text(client_thread_id, "client_thread_id")
    for field in ("role", "project", "model", "scope", "acceptance", "created_at", "updated_at", "last_seen_at"):
        _required_text(task.get(field), field)
    if task.get("mode") not in MODES:
        raise LedgerError(f"invalid mode for task: {key}")
    if task.get("status") not in STATUSES:
        raise LedgerError(f"invalid task status: {task.get('status')}")
    if task["status"] == "PENDING_DISPATCH" and client_thread_id is None:
        raise LedgerError(f"PENDING_DISPATCH task requires client_thread_id: {key}")
    if task["status"] not in {"PENDING_DISPATCH", "BLOCKED", "CLOSED"} and thread_id is None:
        raise LedgerError(f"bound thread required for status {task['status']}: {key}")
    if task.get("delivery_mode") not in DELIVERY_MODES:
        raise LedgerError(f"invalid delivery_mode for task: {key}")
    dependencies = task.get("depends_on")
    if not isinstance(dependencies, list) or any(not isinstance(value, str) for value in dependencies):
        raise LedgerError(f"invalid depends_on for task: {key}")
    if len(set(dependencies)) != len(dependencies):
        raise LedgerError(f"invalid depends_on for task: {key}")
    for dependency in dependencies:
        _identifier(dependency, "depends_on")
        if dependency not in tasks:
            raise LedgerError(f"unknown dependency for task {key}: {dependency}")
    for field in ("wait_cursor", "deadline_at", "result_reference"):
        if task.get(field) is not None:
            _required_text(task[field], field)
    if not isinstance(task.get("attempt"), int) or task["attempt"] < 0:
        raise LedgerError(f"invalid attempt for task: {key}")


def _verify_task_skills(key: str, task: dict[str, Any]) -> None:
    bindings = task.get("skill_bindings")
    if not isinstance(bindings, list):
        raise LedgerError(f"invalid skill_bindings for task: {key}")
    if _normalize_skill_bindings(bindings) != bindings:
        raise LedgerError(f"non-canonical skill_bindings for task: {key}")
    if task["mode"] == "STRICT_MODE":
        missing_provenance = [
            binding["selector"]
            for binding in bindings
            if binding["loaded"] is True
            and binding["source_version"] is None
            and binding["content_digest"] is None
        ]
        if missing_provenance:
            raise LedgerError(f"STRICT_MODE loaded skills lack provenance: {key}")


def _verify_transition_history(key: str, task: dict[str, Any]) -> list[str]:
    transitions = task.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        raise LedgerError(f"task has no transition history: {key}")
    previous = None
    event_states: list[str] = []
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict) or transition.get("to") not in STATUSES:
            raise LedgerError(f"invalid transition record for task: {key}")
        source = transition.get("from")
        if index == 0:
            if source is not None or transition["to"] not in {"PENDING_DISPATCH", "ASSIGNED"}:
                raise LedgerError(f"task must start at PENDING_DISPATCH or ASSIGNED: {key}")
        elif source != previous or not _transition_allowed(source, transition["to"]):
            raise LedgerError(f"invalid transition history for task: {key}")
        reason = _required_text(transition.get("reason"), "transition.reason")
        dispatch_failure = (
            source == "PENDING_DISPATCH"
            and transition["to"] == "BLOCKED"
            and task["thread_id"] is None
            and task["host_id"] is None
            and task["result_reference"] is not None
        )
        if transition["to"] in WAKE_STATES and reason != "TASK_EVENT":
            if not dispatch_failure or reason != "DISPATCH_FAILURE":
                raise LedgerError(f"wake state transition lacks valid evidence: {key}")
        if reason == "TASK_EVENT":
            event_states.append(transition["to"])
        _required_text(transition.get("at"), "transition.at")
        previous = transition["to"]
    if previous != task["status"]:
        raise LedgerError(f"task status disagrees with transition history: {key}")
    return event_states


def _verify_completion_contract(key: str, task: dict[str, Any]) -> None:
    successful = task["status"] == "DONE" or (
        task["status"] == "CLOSED" and task["transitions"][-1]["from"] == "DONE"
    )
    if not successful:
        return
    missing = [
        binding["selector"]
        for binding in task["skill_bindings"]
        if binding["required"] and binding["loaded"] is not True
    ]
    if missing:
        raise LedgerError(f"completed task has unloaded required skills: {key}")


def _verify_task_events(
    key: str,
    task: dict[str, Any],
    events: dict[str, Any],
    event_states: list[str],
    consumed_event_ids: set[str],
    seen_event_ids: set[str],
) -> None:
    task_events = task.get("events")
    if not isinstance(task_events, list) or any(not isinstance(value, str) for value in task_events):
        raise LedgerError(f"invalid event index for task: {key}")
    if task.get("last_event_id") != (task_events[-1] if task_events else None):
        raise LedgerError(f"invalid event index for task: {key}")
    stored_states = [events[event_id].get("state") for event_id in task_events if event_id in events]
    if event_states != stored_states:
        raise LedgerError(f"event history disagrees with TASK_EVENT transitions: {key}")
    for sequence, event_id in enumerate(task_events, start=1):
        if event_id in seen_event_ids:
            raise LedgerError(f"duplicate event_id: {event_id}")
        seen_event_ids.add(event_id)
        event = events.get(event_id)
        if not isinstance(event, dict) or event.get("task_id") != key:
            raise LedgerError(f"dangling event: {event_id}")
        if event.get("event_sequence") != sequence:
            raise LedgerError(f"event sequence is not contiguous: {event_id}")
        expected_id = f"{task['thread_id']}:{key}:{event.get('state')}:{sequence}"
        if event_id != expected_id:
            raise LedgerError(f"event_id is not canonical: {event_id}")
        if event.get("source_thread_id") != task["thread_id"] or event.get("state") not in WAKE_STATES:
            raise LedgerError(f"invalid event source/state: {event_id}")
        _required_text(event.get("result_reference"), "result_reference")
        if not isinstance(event.get("decision_required"), bool):
            raise LedgerError(f"invalid decision_required: {event_id}")
        _required_text(event.get("blocker"), "blocker")
        _required_text(event.get("created_at"), "event.created_at")
    if task["status"] == "CLOSED" and task_events and task_events[-1] not in consumed_event_ids:
        raise LedgerError(f"closed task has an unconsumed final event: {key}")


def verify_ledger(ledger: dict[str, Any]) -> None:
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise LedgerError(f"schema_version must be {SCHEMA_VERSION}")
    for field in ("batch_id",):
        _identifier(ledger.get(field), field)
    for field in ("master_thread_id", "state_file", "objective", "created_at", "updated_at"):
        _required_text(ledger.get(field), field)
    if not isinstance(ledger.get("revision"), int) or ledger["revision"] < 0:
        raise LedgerError("revision must be a non-negative integer")
    tasks = ledger.get("tasks")
    events = ledger.get("events")
    if not isinstance(tasks, dict) or not isinstance(events, dict):
        raise LedgerError("tasks and events must be JSON objects")
    event_order = ledger.get("event_order")
    if not isinstance(event_order, list) or any(not isinstance(value, str) for value in event_order):
        raise LedgerError("event_order must be a list of event ids")
    if len(set(event_order)) != len(event_order):
        raise LedgerError("event_order must contain unique event ids")
    consumed_count = ledger.get("consumed_event_count")
    if not isinstance(consumed_count, int) or not 0 <= consumed_count <= len(event_order):
        raise LedgerError("consumed_event_count is out of range")
    _verify_checkpoint(ledger)
    consumed_event_ids = set(event_order[:consumed_count])
    seen_event_ids: set[str] = set()
    for key, task in tasks.items():
        _verify_task_identity(key, task, tasks)
        _verify_task_skills(key, task)
        event_states = _verify_transition_history(key, task)
        _verify_completion_contract(key, task)
        _verify_task_events(key, task, events, event_states, consumed_event_ids, seen_event_ids)
    if set(events) != seen_event_ids:
        raise LedgerError("global events contain dangling or missing records")
    if set(event_order) != seen_event_ids:
        raise LedgerError("event_order disagrees with stored events")


def _skill_bindings_from_args(required: list[str], optional: list[str]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for is_required, values in ((True, required), (False, optional)):
        for value in values:
            parts = value.split("::", 1)
            if len(parts) != 2:
                raise LedgerError("skill argument must use SELECTOR::PURPOSE")
            bindings.append(
                {
                    "selector": parts[0],
                    "required": is_required,
                    "purpose": parts[1],
                    "source_locator": None,
                    "frontmatter_name": None,
                    "source_version": None,
                    "content_digest": None,
                    "available": None,
                    "loaded": None,
                }
            )
    return _normalize_skill_bindings(bindings)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", required=True, help="absolute path to the ledger JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create or verify an empty batch ledger")
    init.add_argument("--batch-id", required=True)
    init.add_argument("--master-thread-id", required=True)
    init.add_argument("--objective", required=True)

    reserve = commands.add_parser("reserve", help="record an asynchronous thread creation")
    for name in ("task-id", "client-thread-id", "role", "project", "model", "scope", "acceptance"):
        reserve.add_argument(f"--{name}", required=True)
    reserve.add_argument("--depends-on", action="append", default=[])
    reserve.add_argument("--mode", choices=sorted(MODES), default="LIGHT_MODE")
    reserve.add_argument("--delivery-mode", choices=sorted(DELIVERY_MODES), default="host-wait")
    reserve.add_argument("--deadline-at")
    reserve.add_argument("--required-skill", action="append", default=[], metavar="SELECTOR::PURPOSE")
    reserve.add_argument("--optional-skill", action="append", default=[], metavar="SELECTOR::PURPOSE")

    bind = commands.add_parser("bind", help="bind a pending task to a real CODEX_THREAD")
    for name in ("task-id", "thread-id", "host-id"):
        bind.add_argument(f"--{name}", required=True)

    dispatch_failed = commands.add_parser(
        "dispatch-failed", help="record failure before a real thread was bound"
    )
    dispatch_failed.add_argument("--task-id", required=True)
    dispatch_failed.add_argument("--error-reference", required=True)

    register = commands.add_parser("register", help="register a real CODEX_THREAD")
    for name in ("task-id", "thread-id", "host-id", "role", "project", "model", "scope", "acceptance"):
        register.add_argument(f"--{name}", required=True)
    register.add_argument("--depends-on", action="append", default=[])
    register.add_argument("--mode", choices=sorted(MODES), default="LIGHT_MODE")
    register.add_argument("--delivery-mode", choices=sorted(DELIVERY_MODES), default="cross-thread-message")
    register.add_argument("--deadline-at")
    register.add_argument("--required-skill", action="append", default=[], metavar="SELECTOR::PURPOSE")
    register.add_argument("--optional-skill", action="append", default=[], metavar="SELECTOR::PURPOSE")

    skill_result = commands.add_parser("skill-result", help="record target-thread skill preflight evidence")
    skill_result.add_argument("--task-id", required=True)
    skill_result.add_argument("--selector", required=True)
    skill_result.add_argument("--available", choices=("yes", "no"), required=True)
    skill_result.add_argument("--loaded", choices=("yes", "no"), required=True)
    skill_result.add_argument("--source-locator")
    skill_result.add_argument("--frontmatter-name")
    skill_result.add_argument("--source-version")
    skill_result.add_argument("--content-digest")

    transition = commands.add_parser("transition", help="apply one legal task status transition")
    transition.add_argument("--task-id", required=True)
    transition.add_argument("--to", required=True, dest="target")
    transition.add_argument("--reason", default="manual")
    transition.add_argument("--wait-cursor")
    transition.add_argument("--deadline-at")

    stalled = commands.add_parser("stalled", help="mark a waiting task stalled after its deadline")
    stalled.add_argument("--task-id", required=True)

    event = commands.add_parser("event", help="record one TASK_EVENT")
    event.add_argument("--task-id", required=True)
    event.add_argument("--state", required=True)
    event.add_argument("--result-reference", required=True)
    event.add_argument("--decision-required", choices=("yes", "no"), default="no")
    event.add_argument("--blocker", default="none")
    event.add_argument("--event-id")

    consume = commands.add_parser("consume-event", help="acknowledge the next TASK_EVENT")
    consume.add_argument("--event-id", required=True)

    show_status = commands.add_parser("status", help="show one task or a compact batch summary")
    show_status.add_argument("--task-id")

    lifecycle = commands.add_parser(
        "thread-lifecycle-ready", help="check host and ledger lifecycle readiness"
    )
    lifecycle.add_argument("--thread-id", required=True)
    lifecycle.add_argument("--host-status", choices=sorted(HOST_STATUSES), required=True)

    save_checkpoint = commands.add_parser("checkpoint", help="persist a safe compaction checkpoint")
    save_checkpoint.add_argument("--next-action", required=True)
    save_checkpoint.add_argument("--reason", required=True)

    resume = commands.add_parser("resume", help="show the compact recovery state")
    resume.add_argument("--include-closed", action="store_true")
    commands.add_parser("verify", help="verify all ledger invariants")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        path = _state_file(args.state_file)
        if args.command == "init":
            result = {
                "result": "ready",
                "ledger": init_ledger(path, args.batch_id, args.master_thread_id, args.objective),
            }
        elif args.command == "reserve":
            skill_bindings = _skill_bindings_from_args(args.required_skill, args.optional_skill)
            result = reserve_task(
                path,
                task_id=args.task_id,
                client_thread_id=args.client_thread_id,
                role=args.role,
                project=args.project,
                model=args.model,
                mode=args.mode,
                scope=args.scope,
                acceptance=args.acceptance,
                depends_on=args.depends_on,
                delivery_mode=args.delivery_mode,
                deadline_at=args.deadline_at,
                skill_bindings=skill_bindings,
            )
        elif args.command == "bind":
            result = bind_task(path, task_id=args.task_id, thread_id=args.thread_id, host_id=args.host_id)
        elif args.command == "dispatch-failed":
            result = mark_dispatch_failed(
                path,
                task_id=args.task_id,
                error_reference=args.error_reference,
            )
        elif args.command == "register":
            skill_bindings = _skill_bindings_from_args(args.required_skill, args.optional_skill)
            result = register_task(
                path,
                task_id=args.task_id,
                thread_id=args.thread_id,
                host_id=args.host_id,
                role=args.role,
                project=args.project,
                model=args.model,
                mode=args.mode,
                scope=args.scope,
                acceptance=args.acceptance,
                depends_on=args.depends_on,
                delivery_mode=args.delivery_mode,
                deadline_at=args.deadline_at,
                skill_bindings=skill_bindings,
            )
        elif args.command == "skill-result":
            result = record_skill_result(
                path,
                task_id=args.task_id,
                selector=args.selector,
                available=args.available == "yes",
                loaded=args.loaded == "yes",
                source_locator=args.source_locator,
                frontmatter_name=args.frontmatter_name,
                source_version=args.source_version,
                content_digest=args.content_digest,
            )
        elif args.command == "transition":
            result = transition_task(
                path,
                task_id=args.task_id,
                target=args.target,
                reason=args.reason,
                wait_cursor=args.wait_cursor,
                deadline_at=args.deadline_at,
            )
        elif args.command == "stalled":
            result = mark_stalled(path, task_id=args.task_id)
        elif args.command == "event":
            result = record_event(
                path,
                task_id=args.task_id,
                state=args.state,
                result_reference=args.result_reference,
                decision_required=args.decision_required == "yes",
                blocker=args.blocker,
                event_id=args.event_id,
            )
        elif args.command == "consume-event":
            result = consume_event(path, event_id=args.event_id)
        elif args.command == "status":
            result = status(path, args.task_id)
        elif args.command == "thread-lifecycle-ready":
            result = assess_thread_lifecycle(
                path,
                thread_id=args.thread_id,
                host_status=args.host_status,
            )
        elif args.command == "checkpoint":
            result = checkpoint(path, next_action=args.next_action, reason=args.reason)
        elif args.command == "resume":
            result = resume_summary(path, include_closed=args.include_closed)
        elif args.command == "verify":
            ledger = _read(path)
            result = {"result": "valid", "batch_id": ledger["batch_id"], "task_count": len(ledger["tasks"]), "event_count": len(ledger["events"])}
        else:
            raise LedgerError(f"unsupported command: {args.command}")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LedgerError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
