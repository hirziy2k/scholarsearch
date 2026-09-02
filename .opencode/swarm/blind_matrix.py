"""
Blind Matrix Evaluation
Single-pass contradiction classification using logit-masked 8B model.
Enforces schema compliance at the inference layer via GBNF grammar.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ContradictionType(Enum):
    POPULATION_MISMATCH = 1
    TEMPORAL_SHIFT = 2
    DEFINITIONAL_VARIANCE = 3
    DIRECT_REFUTATION = 4


class EvidenceVerdict(Enum):
    HIGH_AUTHORITY = "HIGH_AUTHORITY"
    CONFLICTED = "CONFLICTED"


CONTRADICTION_LABELS = {
    ContradictionType.POPULATION_MISMATCH: "Population_Mismatch",
    ContradictionType.TEMPORAL_SHIFT: "Temporal_Shift",
    ContradictionType.DEFINITIONAL_VARIANCE: "Definitional_Variance",
    ContradictionType.DIRECT_REFUTATION: "Direct_Refutation",
}


@dataclass(frozen=True)
class MatrixResult:
    contradiction_type: ContradictionType
    contradiction_label: str
    boundary_condition: Optional[str]
    verdict: EvidenceVerdict
    claim_text: str
    support_count: int
    contradiction_count: int

    def to_dict(self) -> dict:
        return {
            "contradiction_type": self.contradiction_type.value,
            "contradiction_label": self.contradiction_label,
            "boundary_condition": self.boundary_condition,
            "verdict": self.verdict.value,
            "claim_text": self.claim_text,
            "support_count": self.support_count,
            "contradiction_count": self.contradiction_count,
        }


# GBNF Grammar for logit-masked extraction
# First token: category [1-4], then boundary string up to 250 chars
GBNF_GRAMMAR = r"""
root   ::= category " " boundary "\n"
category ::= [1-4]
boundary  ::= [a-zA-Z0-9\., \-:;()]{1,250}
"""


class BlindMatrixEvaluator:
    """
    Evaluates contradictions using a logit-masked 8B model.
    Outputs enum + string only, no JSON generation by model.
    """

    def __init__(self, model_client, max_boundary_length: int = 250):
        self._model = model_client
        self._max_boundary_length = max_boundary_length

    def evaluate(
        self,
        claim: str,
        support_pool: list[str],
        contradiction_pool: list[str],
        glossary_block: Optional[str] = None,
    ) -> MatrixResult:
        """
        Run single-pass Blind Matrix evaluation.

        Args:
            claim: The claim being evaluated.
            support_pool: List of supporting source excerpts.
            contradiction_pool: List of contradicting source excerpts.
            glossary_block: Optional glossary with definitions/warnings.
        """
        prompt = self._build_prompt(
            claim, support_pool, contradiction_pool, glossary_block
        )

        raw_output = self._model.generate(
            prompt=prompt,
            grammar=GBNF_GRAMMAR,
            max_tokens=256,
            temperature=0.1,
        )

        category_num, boundary = self._parse_output(raw_output)

        contradiction_type = ContradictionType(category_num)
        contradiction_label = CONTRADICTION_LABELS[contradiction_type]

        if contradiction_type == ContradictionType.DIRECT_REFUTATION:
            verdict = EvidenceVerdict.CONFLICTED
        else:
            verdict = EvidenceVerdict.HIGH_AUTHORITY

        return MatrixResult(
            contradiction_type=contradiction_type,
            contradiction_label=contradiction_label,
            boundary_condition=boundary,
            verdict=verdict,
            claim_text=claim,
            support_count=len(support_pool),
            contradiction_count=len(contradiction_pool),
        )

    def _build_prompt(
        self,
        claim: str,
        support_pool: list[str],
        contradiction_pool: list[str],
        glossary_block: Optional[str],
    ) -> str:
        support_text = "\n".join(
            f"[S{i+1}] {s}" for i, s in enumerate(support_pool[:5])
        )
        contradiction_text = "\n".join(
            f"[C{i+1}] {c}" for i, c in enumerate(contradiction_pool[:3])
        )

        prompt_parts = [
            "You are a contradiction classifier.",
            "Evaluate the claim against support and contradiction evidence.",
            "",
            f"CLAIM:\n{claim}",
            "",
            f"SUPPORTING EVIDENCE:\n{support_text}",
            "",
            f"CONTRADICTING EVIDENCE:\n{contradiction_text}",
        ]

        if glossary_block:
            prompt_parts.append("")
            prompt_parts.append(glossary_block)

        prompt_parts.extend([
            "",
            "CLASSIFY the contradiction type (1-4):",
            "1 = Population_Mismatch (different populations studied)",
            "2 = Temporal_Shift (different time periods)",
            "3 = Definitional_Variance (different definitions of terms)",
            "4 = Direct_Refutation (fundamental disagreement on facts)",
            "",
            "OUTPUT exactly: <number> <boundary_condition_or_None>",
            "Example: 3 Efficacy varies by dosage above 4000 IU",
            "Example: 4 None",
        ])

        return "\n".join(prompt_parts)

    def _parse_output(self, raw: str) -> tuple[int, Optional[str]]:
        raw = raw.strip()

        if not raw:
            return 4, None

        parts = raw.split(" ", 1)
        category_num = int(parts[0])

        if category_num < 1 or category_num > 4:
            category_num = 4

        boundary = parts[1].strip() if len(parts) > 1 else None
        if boundary and boundary.lower() in ("none", "n/a", ""):
            boundary = None

        if boundary and len(boundary) > self._max_boundary_length:
            boundary = boundary[: self._max_boundary_length]

        return category_num, boundary
