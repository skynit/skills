from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.orz_state import STATUSES


ROOT = Path(__file__).resolve().parents[1]


def section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"missing section {heading!r} in {path}")
    return match.group("body")


class SkillContractTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self) -> None:
        for path in [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md"))]:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^]]+\]\(([^)]+\.md)\)", text):
                if "://" in target:
                    continue
                resolved = (path.parent / target).resolve()
                self.assertTrue(resolved.is_file(), f"broken link in {path}: {target}")

    def test_strict_decomposition_template_has_owner_contract(self) -> None:
        body = section(ROOT / "references" / "templates.md", "分解决策")
        required_fields = {
            "Message type",
            "Mode",
            "Outputs",
            "task_id",
            "owner_role",
            "repository_or_package",
            "write_set",
            "depends_on",
            "acceptance",
            "Execution",
            "Independent validator",
            "Single-worker exception",
        }
        present = {
            match.group(1)
            for match in re.finditer(r"^\s*(?:-\s+)?([A-Za-z_][A-Za-z_ -]*):", body, re.MULTILINE)
        }
        self.assertTrue(required_fields <= present, required_fields - present)

    def test_core_routes_strict_work_to_decomposition_reference(self) -> None:
        core = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/decomposition-and-ownership.md", core)
        self.assertIn("DECOMPOSITION_DECISION", core)
        self.assertIn("实现 owner 不能兼任要求独立证据的 validator", core)

    def test_code_quality_skill_routing_is_discoverable_and_bounded(self) -> None:
        routing = ROOT / "references" / "skill-routing.md"
        body = section(routing, "代码质量 Skill")
        for skill_name in {"cursor-clean-code", "code-simplification", "refactor"}:
            self.assertIn(f"`{skill_name}`", body)
        self.assertIn("不要因三者相关就全部加载", body)
        self.assertIn("优先保留决定正确性的领域 Skill", body)

        template = (ROOT / "references" / "templates.md").read_text(encoding="utf-8")
        self.assertIn("Required skills: <$selector (one-line purpose); ... | none>", template)
        self.assertIn("Optional skills: <$selector (one-line purpose); ... | none>", template)
        for field in ("Skills requested:", "Skills loaded:", "Skills unavailable:", "Skill conflicts:"):
            self.assertIn(field, template)

    def test_runtime_statuses_and_delivery_terms_do_not_drift(self) -> None:
        contract_files = [
            ROOT / "SKILL.md",
            ROOT / "references" / "runtime-ledger.md",
            ROOT / "references" / "session-protocol.md",
            ROOT / "references" / "quality-and-recovery.md",
            ROOT / "references" / "templates.md",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in contract_files)
        for status_name in {"PENDING_DISPATCH", "WAITING_EVENT", "STALLED", "NEEDS_APPROVAL"}:
            self.assertIn(status_name, STATUSES)
            self.assertIn(status_name, combined)
        self.assertNotIn("NEEDS_REVIEW", combined)
        self.assertNotIn("Completion callback", combined)
        self.assertIn("Completion delivery: cross-thread-message | host-wait | unavailable", combined)
        self.assertIn("Required skills: <$selector (one-line purpose); ... | none>", combined)
        self.assertIn("Optional skills: <$selector (one-line purpose); ... | none>", combined)
        self.assertNotIn("READY_FOR_NEXT_TASK", combined)
        self.assertIn("`idle`", combined)
        self.assertIn("`notLoaded`", combined)
        self.assertIn("thread-lifecycle-ready", combined)
        self.assertNotIn("thread-reusable", combined)

    def test_context_management_is_routed_from_entrypoint(self) -> None:
        core = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        context_reference = ROOT / "references" / "context-management.md"
        self.assertTrue(context_reference.is_file())
        self.assertIn("references/context-management.md", core)
        context = context_reference.read_text(encoding="utf-8")
        self.assertIn("checkpoint", context)
        self.assertIn("resolved_dependencies", context)

    def test_thread_scan_happens_only_after_delegation_decision(self) -> None:
        core = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        session = (ROOT / "references" / "session-protocol.md").read_text(encoding="utf-8")
        combined = core + session
        self.assertIn("先完成 `MASTER_DIRECT` 与独立分派决策", core)
        self.assertIn("已经决定独立分派", session)
        self.assertIn("直接执行、只读分析和无需复用", combined)
        self.assertNotIn("首次触发、新任务开始、上下文压缩或恢复后", core)

    def test_light_assign_is_compact_and_strict_template_is_separate(self) -> None:
        core_body = section(ROOT / "SKILL.md", "最小分派")
        session_body = section(ROOT / "references" / "session-protocol.md", "轻量 ASSIGN")
        template = (ROOT / "references" / "templates.md").read_text(encoding="utf-8")
        for body in (core_body, session_body):
            self.assertIn("Return to Master:", body)
            self.assertIn("Constraints:", body)
            self.assertNotIn("Progress notifications:", body)
            self.assertNotIn("Completion event:", body)
            self.assertNotIn("Assistant threadId:", body)
        self.assertIn("## 严格 Task Brief", template)
        self.assertIn("Mode: STRICT_MODE", template)

    def test_cross_domain_work_prefers_a_new_thread(self) -> None:
        core = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        context = (ROOT / "references" / "context-management.md").read_text(encoding="utf-8")
        session = (ROOT / "references" / "session-protocol.md").read_text(encoding="utf-8")
        combined = core + context + session
        self.assertIn("领域明显不同", combined)
        self.assertIn("优先创建新 thread", context)
        self.assertIn("不要通过压缩强行复用", session)

    def test_external_skill_preflight_contract_is_documented(self) -> None:
        routing = (ROOT / "references" / "skill-routing.md").read_text(encoding="utf-8")
        session = (ROOT / "references" / "session-protocol.md").read_text(encoding="utf-8")
        for phrase in ("目标线程注册表", "Required selector", "Optional selector", "source locator"):
            self.assertIn(phrase, routing + session)
        self.assertIn("sha256:<64 lowercase hex>", routing + session)


if __name__ == "__main__":
    unittest.main()
