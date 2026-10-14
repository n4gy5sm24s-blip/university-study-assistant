from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import tempfile

from .answers import GroundedAnswerService
from .courses import CourseRepository
from .documents import DocumentRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = PROJECT_ROOT / "evals" / "cases.json"
DEFAULT_MATERIALS = PROJECT_ROOT / "evals" / "materials"


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    expected: str
    section: str = ""
    keyword: str = ""


@dataclass(frozen=True)
class EvalResult:
    id: str
    passed: bool
    expected: str
    actual: str
    citation_valid: bool
    detail: str


@dataclass(frozen=True)
class EvalSummary:
    total: int
    passed: int
    pass_rate: float
    grounded_recall: float
    refusal_accuracy: float
    citation_accuracy: float
    results: list[EvalResult]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_cases(path: Path = DEFAULT_CASES) -> list[EvalCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(**item) for item in data]


def run_eval(
    cases_path: Path = DEFAULT_CASES,
    materials_directory: Path = DEFAULT_MATERIALS,
) -> EvalSummary:
    temporary_root = Path(tempfile.mkdtemp(prefix="study-assistant-eval-"))
    try:
        database = temporary_root / "eval.db"
        courses = CourseRepository(database)
        documents = DocumentRepository(database, temporary_root / "uploads")
        answers = GroundedAnswerService(
            database, use_environment_generator=False
        )
        course = courses.create("自制管理学评估课程")
        for material in sorted(materials_directory.glob("*.md")):
            documents.create(
                course.id,
                material.name,
                material.read_text(encoding="utf-8"),
            )

        cases = load_cases(cases_path)
        results = [_evaluate_case(case, answers, course.id) for case in cases]
        grounded = [result for result in results if result.expected == "grounded"]
        refusals = [result for result in results if result.expected == "no_evidence"]
        cited = [result for result in grounded if result.actual == "grounded"]
        return EvalSummary(
            total=len(results),
            passed=sum(result.passed for result in results),
            pass_rate=_ratio(sum(result.passed for result in results), len(results)),
            grounded_recall=_ratio(
                sum(result.actual == "grounded" for result in grounded), len(grounded)
            ),
            refusal_accuracy=_ratio(
                sum(result.actual == "no_evidence" for result in refusals),
                len(refusals),
            ),
            citation_accuracy=_ratio(
                sum(result.citation_valid for result in cited), len(cited)
            ),
            results=results,
        )
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _evaluate_case(
    case: EvalCase, answers: GroundedAnswerService, course_id: int
) -> EvalResult:
    answer = answers.answer(course_id, case.question)
    if case.expected == "no_evidence":
        passed = answer.grounding_status == "no_evidence" and not answer.citations
        return EvalResult(
            case.id,
            passed,
            case.expected,
            answer.grounding_status,
            not answer.citations,
            "正确拒答" if passed else "不应返回资料引用",
        )

    citation_valid = any(
        citation.section_title == case.section
        and case.keyword in citation.excerpt
        for citation in answer.citations
    )
    passed = answer.grounding_status == "grounded" and citation_valid
    return EvalResult(
        case.id,
        passed,
        case.expected,
        answer.grounding_status,
        citation_valid,
        "命中正确章节和依据" if passed else "未命中预期章节或关键词",
    )


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="运行学习助手固定评估集")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON")
    args = parser.parse_args()
    summary = run_eval()
    if args.json:
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Cases: {summary.passed}/{summary.total}")
        print(f"Pass rate: {summary.pass_rate:.1%}")
        print(f"Grounded recall: {summary.grounded_recall:.1%}")
        print(f"Refusal accuracy: {summary.refusal_accuracy:.1%}")
        print(f"Citation accuracy: {summary.citation_accuracy:.1%}")
        for result in summary.results:
            if not result.passed:
                print(f"FAIL {result.id}: {result.detail}")
    return 0 if summary.pass_rate >= 0.9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
