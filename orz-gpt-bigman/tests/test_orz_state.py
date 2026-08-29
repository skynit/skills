from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.orz_state import (
    LedgerError,
    assess_thread_lifecycle,
    bind_task,
    checkpoint,
    consume_event,
    init_ledger,
    mark_dispatch_failed,
    mark_stalled,
    record_event,
    record_skill_result,
    register_task,
    reserve_task,
    resume_summary,
    status,
    transition_task,
    verify_ledger,
)


class OrzStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.tempdir.name) / "ledger.json"
        init_ledger(self.state_file, "batch-1", "master-1", "Coordinate one bounded task")
        register_task(
            self.state_file,
            task_id="task-1",
            thread_id="thread-1",
            host_id="host-1",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="targeted verification passes",
            skill_bindings=[
                {
                    "selector": "openai-docs",
                    "required": False,
                    "purpose": "consult official documentation when needed",
                }
            ],
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_register_is_idempotent_and_status_is_compact(self) -> None:
        duplicate = register_task(
            self.state_file,
            task_id="task-1",
            thread_id="thread-1",
            host_id="host-1",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="targeted verification passes",
            skill_bindings=[
                {
                    "selector": "openai-docs",
                    "required": False,
                    "purpose": "consult official documentation when needed",
                }
            ],
        )
        self.assertEqual(duplicate["result"], "duplicate")
        summary = status(self.state_file)
        self.assertEqual(summary["tasks"]["task-1"]["status"], "ASSIGNED")
        self.assertEqual(summary["event_count"], 0)

    def test_event_is_idempotent_and_canonical(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        first = record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/result.md")
        self.assertEqual(first["event"]["event_id"], "thread-1:task-1:DONE:1")
        duplicate = record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/result.md")
        self.assertEqual(duplicate["result"], "duplicate")
        with self.assertRaises(LedgerError) as implicit_conflict:
            record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/other.md")
        self.assertEqual(
            str(implicit_conflict.exception),
            "same-state event conflicts with last event: thread-1:task-1:DONE:1",
        )
        with self.assertRaises(LedgerError) as explicit_conflict:
            record_event(
                self.state_file,
                task_id="task-1",
                state="DONE",
                result_reference="/tmp/other.md",
                event_id="thread-1:task-1:DONE:1",
            )
        self.assertEqual(
            str(explicit_conflict.exception),
            "event_id already exists with conflicting payload: thread-1:task-1:DONE:1",
        )
        verify_ledger(json.loads(self.state_file.read_text(encoding="utf-8")))

    def test_approval_then_done_uses_new_sequence(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        approval = record_event(
            self.state_file,
            task_id="task-1",
            state="NEEDS_APPROVAL",
            result_reference="/tmp/approval.md",
            decision_required=True,
            blocker="needs review",
        )
        self.assertEqual(approval["event"]["event_id"], "thread-1:task-1:NEEDS_APPROVAL:1")
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="approved")
        done = record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/result.md")
        self.assertEqual(done["event"]["event_id"], "thread-1:task-1:DONE:2")

    def test_invalid_transition_and_conflicting_identity_fail_closed(self) -> None:
        with self.assertRaises(LedgerError):
            record_event(self.state_file, task_id="task-1", state="PARTIAL", result_reference="/tmp/result.md")
        with self.assertRaises(LedgerError):
            register_task(
                self.state_file,
                task_id="task-1",
                thread_id="thread-other",
                host_id="host-1",
                role="worker",
                project="/tmp/project",
                model="configured-default",
                scope="/tmp/project/package",
                acceptance="targeted verification passes",
            )
        with self.assertRaises(LedgerError):
            transition_task(self.state_file, task_id="task-1", target="DONE", reason="bypass")

    def test_verify_rejects_event_without_matching_transition(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/result.md")
        ledger = json.loads(self.state_file.read_text(encoding="utf-8"))
        ledger["tasks"]["task-1"]["transitions"] = [
            transition
            for transition in ledger["tasks"]["task-1"]["transitions"]
            if transition["reason"] != "TASK_EVENT"
        ]
        with self.assertRaises(LedgerError):
            verify_ledger(ledger)

    def test_reserve_then_bind_records_real_thread(self) -> None:
        reserved = reserve_task(
            self.state_file,
            task_id="task-pending",
            client_thread_id="client:opaque/id",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="targeted verification passes",
        )
        self.assertEqual(reserved["task"]["status"], "PENDING_DISPATCH")
        duplicate = reserve_task(
            self.state_file,
            task_id="task-pending",
            client_thread_id="client:opaque/id",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="targeted verification passes",
        )
        self.assertEqual(duplicate["result"], "duplicate")
        bound = bind_task(
            self.state_file,
            task_id="task-pending",
            thread_id="thread:opaque/id",
            host_id="host-1",
        )
        self.assertEqual(bound["task"]["status"], "ASSIGNED")
        self.assertEqual(bound["task"]["thread_id"], "thread:opaque/id")

    def test_dispatch_failure_can_block_without_a_real_thread(self) -> None:
        reserve_task(
            self.state_file,
            task_id="task-failed-dispatch",
            client_thread_id="client:failed",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="targeted verification passes",
        )
        blocked = mark_dispatch_failed(
            self.state_file,
            task_id="task-failed-dispatch",
            error_reference="thread creation failed",
        )
        self.assertEqual(blocked["task"]["status"], "BLOCKED")
        ledger = json.loads(self.state_file.read_text(encoding="utf-8"))
        ledger["tasks"]["task-failed-dispatch"]["thread_id"] = "thread-unexpected"
        ledger["tasks"]["task-failed-dispatch"]["host_id"] = "host-1"
        with self.assertRaises(LedgerError):
            verify_ledger(ledger)
        ledger = json.loads(self.state_file.read_text(encoding="utf-8"))
        ledger["tasks"]["task-failed-dispatch"]["result_reference"] = None
        with self.assertRaises(LedgerError):
            verify_ledger(ledger)
        closed = transition_task(
            self.state_file,
            task_id="task-failed-dispatch",
            target="CLOSED",
            reason="failure-recorded",
        )
        self.assertEqual(closed["task"]["status"], "CLOSED")

    def test_dependency_must_succeed_before_work_starts(self) -> None:
        register_task(
            self.state_file,
            task_id="task-2",
            thread_id="thread-2",
            host_id="host-1",
            role="validator",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="independent verification passes",
            depends_on=["task-1"],
        )
        with self.assertRaises(LedgerError):
            transition_task(self.state_file, task_id="task-2", target="IN_PROGRESS", reason="early")
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/result.md")
        started = transition_task(self.state_file, task_id="task-2", target="IN_PROGRESS", reason="ready")
        self.assertEqual(started["task"]["status"], "IN_PROGRESS")

    def test_compact_resume_includes_closed_dependency_results(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        done = record_event(
            self.state_file,
            task_id="task-1",
            state="DONE",
            result_reference="/tmp/upstream-result.md",
        )
        consume_event(self.state_file, event_id=done["event"]["event_id"])
        transition_task(self.state_file, task_id="task-1", target="CLOSED", reason="consumed")
        register_task(
            self.state_file,
            task_id="task-2",
            thread_id="thread-2",
            host_id="host-1",
            role="validator",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="independent verification passes",
            depends_on=["task-1"],
        )
        resumed = resume_summary(self.state_file)
        self.assertNotIn("task-1", resumed["tasks"])
        self.assertIn("task-2", resumed["tasks"])
        self.assertEqual(
            resumed["resolved_dependencies"]["task-1"],
            {
                "status": "CLOSED",
                "terminal_state": "DONE",
                "result_reference": "/tmp/upstream-result.md",
            },
        )

    def test_waiting_task_becomes_stalled_only_after_deadline(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        transition_task(
            self.state_file,
            task_id="task-1",
            target="WAITING_EVENT",
            reason="wait",
            wait_cursor="cursor-1",
            deadline_at="2025-01-01T00:00:00Z",
        )
        with self.assertRaises(LedgerError):
            transition_task(self.state_file, task_id="task-1", target="STALLED", reason="bypass")
        stalled = mark_stalled(
            self.state_file,
            task_id="task-1",
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(stalled["task"]["status"], "STALLED")

    def test_checkpoint_and_resume_keep_recovery_pointer(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        transition_task(
            self.state_file,
            task_id="task-1",
            target="WAITING_EVENT",
            reason="wait",
            wait_cursor="cursor-1",
        )
        saved = checkpoint(self.state_file, next_action="wait for task-1", reason="compaction-ready")
        self.assertEqual(saved["checkpoint"]["task_count"], 1)
        self.assertNotIn("tasks", saved["checkpoint"])
        self.assertTrue(resume_summary(self.state_file)["checkpoint_current"])
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="resumed")
        resumed = resume_summary(self.state_file)
        self.assertEqual(resumed["master_thread_id"], "master-1")
        self.assertEqual(resumed["state_file"], str(self.state_file))
        self.assertFalse(resumed["checkpoint_current"])
        self.assertEqual(resumed["tasks_scope"], "open")
        restored = resumed["tasks"]["task-1"]
        self.assertEqual(restored["status"], "IN_PROGRESS")
        self.assertEqual(restored["wait_cursor"], "cursor-1")
        self.assertEqual(restored["role"], "worker")
        self.assertEqual(restored["scope"], "/tmp/project/package")
        self.assertEqual(restored["skill_bindings"][0]["selector"], "openai-docs")

    def test_required_skill_must_be_loaded_before_done(self) -> None:
        register_task(
            self.state_file,
            task_id="task-required",
            thread_id="thread-required",
            host_id="host-1",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="official guidance is cited",
            skill_bindings=[
                {
                    "selector": "openai-docs",
                    "required": True,
                    "purpose": "use official OpenAI documentation",
                }
            ],
        )
        transition_task(self.state_file, task_id="task-required", target="IN_PROGRESS", reason="start")
        with self.assertRaises(LedgerError):
            record_event(
                self.state_file,
                task_id="task-required",
                state="DONE",
                result_reference="/tmp/result.md",
            )
        record_skill_result(
            self.state_file,
            task_id="task-required",
            selector="openai-docs",
            available=True,
            loaded=False,
            source_locator="/skills/openai-docs/SKILL.md",
            frontmatter_name="openai-docs",
        )
        evidence = record_skill_result(
            self.state_file,
            task_id="task-required",
            selector="openai-docs",
            available=True,
            loaded=True,
        )
        self.assertTrue(evidence["skill_binding"]["loaded"])
        done = record_event(
            self.state_file,
            task_id="task-required",
            state="DONE",
            result_reference="/tmp/result.md",
        )
        self.assertEqual(done["task"]["status"], "DONE")
        restored = resume_summary(self.state_file)["tasks"]["task-required"]["skill_bindings"][0]
        self.assertTrue(restored["loaded"])
        self.assertEqual(restored["source_locator"], "/skills/openai-docs/SKILL.md")

    def test_strict_loaded_skill_requires_reproducible_provenance(self) -> None:
        skill_path = Path(self.tempdir.name) / "SKILL.md"
        skill_path.write_text("---\nname: openai-docs\n---\n", encoding="utf-8")
        digest = f"sha256:{hashlib.sha256(skill_path.read_bytes()).hexdigest()}"
        register_task(
            self.state_file,
            task_id="task-strict",
            thread_id="thread-strict",
            host_id="host-1",
            role="reviewer",
            project="/tmp/project",
            model="configured-default",
            mode="STRICT_MODE",
            scope="/tmp/project/package",
            acceptance="strict review passes",
            skill_bindings=[
                {
                    "selector": "openai-docs",
                    "required": True,
                    "purpose": "use official OpenAI documentation",
                }
            ],
        )
        with self.assertRaises(LedgerError):
            record_skill_result(
                self.state_file,
                task_id="task-strict",
                selector="openai-docs",
                available=True,
                loaded=True,
                source_locator=str(skill_path),
                frontmatter_name="openai-docs",
            )
        evidence = record_skill_result(
            self.state_file,
            task_id="task-strict",
            selector="openai-docs",
            available=True,
            loaded=True,
            source_locator=str(skill_path),
            frontmatter_name="openai-docs",
            content_digest=digest,
        )
        self.assertEqual(evidence["skill_binding"]["content_digest"], digest)
        with self.assertRaises(LedgerError):
            record_skill_result(
                self.state_file,
                task_id="task-strict",
                selector="openai-docs",
                available=True,
                loaded=True,
                source_locator=str(skill_path),
                content_digest=f"sha256:{'a' * 64}",
            )

    def test_thread_lifecycle_requires_host_and_consumed_closed_task(self) -> None:
        self.assertFalse(
            assess_thread_lifecycle(
                self.state_file,
                thread_id="thread-1",
                host_status="idle",
            )["lifecycle_ready"]
        )
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        done = record_event(
            self.state_file,
            task_id="task-1",
            state="DONE",
            result_reference="/tmp/result.md",
        )
        with self.assertRaises(LedgerError):
            transition_task(self.state_file, task_id="task-1", target="CLOSED", reason="early")
        consume_event(self.state_file, event_id=done["event"]["event_id"])
        transition_task(self.state_file, task_id="task-1", target="CLOSED", reason="consumed")
        self.assertTrue(
            assess_thread_lifecycle(
                self.state_file,
                thread_id="thread-1",
                host_status="idle",
            )["lifecycle_ready"]
        )
        self.assertTrue(
            assess_thread_lifecycle(
                self.state_file,
                thread_id="thread-1",
                host_status="notLoaded",
            )["lifecycle_ready"]
        )
        active = assess_thread_lifecycle(
            self.state_file,
            thread_id="thread-1",
            host_status="active",
        )
        self.assertFalse(active["lifecycle_ready"])
        self.assertIn("host-status-active", active["reasons"])
        compact = resume_summary(self.state_file)
        self.assertNotIn("task-1", compact["tasks"])
        self.assertEqual(compact["closed_task_count"], 1)
        complete = resume_summary(self.state_file, include_closed=True)
        self.assertIn("task-1", complete["tasks"])
        self.assertEqual(complete["tasks_scope"], "all")

    def test_unavailable_required_skill_can_block_but_not_complete(self) -> None:
        register_task(
            self.state_file,
            task_id="task-missing",
            thread_id="thread-missing",
            host_id="host-1",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="required workflow completes",
            skill_bindings=[
                {
                    "selector": "missing-skill",
                    "required": True,
                    "purpose": "required workflow",
                }
            ],
        )
        transition_task(self.state_file, task_id="task-missing", target="IN_PROGRESS", reason="start")
        record_skill_result(
            self.state_file,
            task_id="task-missing",
            selector="missing-skill",
            available=False,
            loaded=False,
        )
        blocked = record_event(
            self.state_file,
            task_id="task-missing",
            state="BLOCKED",
            result_reference="thread-final",
            blocker="required skill unavailable",
        )
        self.assertEqual(blocked["task"]["status"], "BLOCKED")

    def test_unavailable_optional_skill_does_not_block_done(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        record_skill_result(
            self.state_file,
            task_id="task-1",
            selector="openai-docs",
            available=False,
            loaded=False,
        )
        done = record_event(
            self.state_file,
            task_id="task-1",
            state="DONE",
            result_reference="/tmp/result.md",
        )
        self.assertEqual(done["task"]["status"], "DONE")

    def test_checkpoint_requires_all_events_to_be_consumed(self) -> None:
        transition_task(self.state_file, task_id="task-1", target="IN_PROGRESS", reason="start")
        done = record_event(self.state_file, task_id="task-1", state="DONE", result_reference="/tmp/result.md")
        with self.assertRaises(LedgerError):
            checkpoint(self.state_file, next_action="finish", reason="compaction-ready")
        event_id = done["event"]["event_id"]
        consumed = consume_event(self.state_file, event_id=event_id)
        self.assertEqual(consumed["result"], "consumed")
        self.assertEqual(consume_event(self.state_file, event_id=event_id)["result"], "duplicate")
        checkpoint(self.state_file, next_action="finish", reason="compaction-ready")
        self.assertEqual(resume_summary(self.state_file)["unconsumed_events"], [])

    def test_verify_rejects_checkpoint_task_snapshot(self) -> None:
        transition_task(
            self.state_file,
            task_id="task-1",
            target="WAITING_EVENT",
            reason="wait",
        )
        checkpoint(self.state_file, next_action="wait", reason="compaction-ready")
        ledger = json.loads(self.state_file.read_text(encoding="utf-8"))
        ledger["checkpoint"]["tasks"] = {}
        with self.assertRaises(LedgerError):
            verify_ledger(ledger)

    def test_verify_rechecks_required_skill_completion_contract(self) -> None:
        register_task(
            self.state_file,
            task_id="task-corrupt",
            thread_id="thread-corrupt",
            host_id="host-1",
            role="worker",
            project="/tmp/project",
            model="configured-default",
            scope="/tmp/project/package",
            acceptance="required workflow completes",
            skill_bindings=[
                {
                    "selector": "openai-docs",
                    "required": True,
                    "purpose": "required workflow",
                }
            ],
        )
        transition_task(self.state_file, task_id="task-corrupt", target="IN_PROGRESS", reason="start")
        record_skill_result(
            self.state_file,
            task_id="task-corrupt",
            selector="openai-docs",
            available=True,
            loaded=True,
            source_locator="/skills/openai-docs/SKILL.md",
        )
        record_event(
            self.state_file,
            task_id="task-corrupt",
            state="DONE",
            result_reference="/tmp/result.md",
        )
        ledger = json.loads(self.state_file.read_text(encoding="utf-8"))
        ledger["tasks"]["task-corrupt"]["skill_bindings"][0]["loaded"] = False
        with self.assertRaises(LedgerError):
            verify_ledger(ledger)


if __name__ == "__main__":
    unittest.main()
