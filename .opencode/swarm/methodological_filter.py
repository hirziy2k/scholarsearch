"""
Methodological Pre-Filter with Citation Graph Reversal
Filters low-quality contradictions and detects temporal invalidation
bypasses via citation graph topology analysis.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict


class SourceTier(Enum):
    TIER_1 = 1  # Systematic reviews, RCTs, meta-analyses
    TIER_2 = 2  # Peer-reviewed journals, conferences
    TIER_3 = 3  # Preprints, aggregators, technical reports
    TIER_4 = 4  # Social media, unverified


class BypassDecision(Enum):
    DROP_CONTRADICTION = "DROP_CONTRADICTION"
    ESCALATE_TO_MATRIX = "ESCALATE_TO_MATRIX"
    TEMPORAL_LAG_BYPASS = "TEMPORAL_LAG_BYPASS"


@dataclass(frozen=True)
class SourceMetadata:
    doi: str
    tier: SourceTier
    publication_date: float
    domain: str
    has_retraction_flag: bool = False
    has_update_flag: bool = False

    @property
    def is_invalidation_source(self) -> bool:
        return self.has_retraction_flag or self.has_update_flag

    @property
    def date_days_ago(self) -> float:
        return (time.time() - self.publication_date) / 86400


@dataclass(frozen=True)
class FilterResult:
    decision: BypassDecision
    support_tier: SourceTier
    contradiction_tier: SourceTier
    tier_gap_days: Optional[float]
    citation_graph_valid: bool
    invalidation_marker_found: bool

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "support_tier": self.support_tier.value,
            "contradiction_tier": self.contradiction_tier.value,
            "tier_gap_days": self.tier_gap_days,
            "citation_graph_valid": self.citation_graph_valid,
            "invalidation_marker_found": self.invalidation_marker_found,
        }


# Temporal threshold for bypass (180 days)
TEMPORAL_BYPASS_DAYS = 180


class CitationGraphValidator:
    """
    Validates citation graph topology for temporal invalidation bypass.
    """

    def __init__(self, citation_store=None):
        self._citation_store = citation_store

    def has_citation_link(
        self, citing_doi: str, cited_doi: str
    ) -> bool:
        """
        Check if citing_doi explicitly references cited_doi.
        """
        if not self._citation_store:
            return False

        references = self._citation_store.get_references(citing_doi)
        return cited_doi in references

    def has_invalidation_context(
        self, citing_doi: str, cited_doi: str
    ) -> bool:
        """
        Extract citation sentence and check for critical sentiment.
        """
        if not self._citation_store:
            return False

        sentence = self._citation_store.get_citation_context(
            citing_doi, cited_doi
        )

        if not sentence:
            return False

        critical_markers = [
            "failed to",
            "incorrectly",
            "contrary to",
            "disputes",
            "refutes",
            "retracts",
            "methodological flaw",
            "invalidates",
            "does not support",
            "inconsistent with",
        ]

        sentence_lower = sentence.lower()
        return any(marker in sentence_lower for marker in critical_markers)


class MethodologicalPreFilter:
    """
    Filters contradictions based on source tier hierarchy
    and temporal invalidation bypass rules.
    """

    def __init__(self, citation_validator: Optional[CitationGraphValidator] = None):
        self._citation_validator = citation_validator or CitationGraphValidator()

    def evaluate(
        self,
        support_sources: List[SourceMetadata],
        contradiction_sources: List[SourceMetadata],
    ) -> FilterResult:
        """
        Evaluate whether contradictions should be passed to Blind Matrix.

        Args:
            support_sources: Sources supporting the claim.
            contradiction_sources: Sources contradicting the claim.
        """
        if not support_sources or not contradiction_sources:
            return FilterResult(
                decision=BypassDecision.ESCALATE_TO_MATRIX,
                support_tier=SourceTier.TIER_3,
                contradiction_tier=SourceTier.TIER_3,
                tier_gap_days=None,
                citation_graph_valid=False,
                invalidation_marker_found=False,
            )

        best_support = min(support_sources, key=lambda s: s.tier.value)
        worst_contradiction = max(
            contradiction_sources, key=lambda s: s.tier.value
        )

        tier_gap = worst_contradiction.tier.value - best_support.tier.value

        if tier_gap <= 0:
            return FilterResult(
                decision=BypassDecision.ESCALATE_TO_MATRIX,
                support_tier=best_support.tier,
                contradiction_tier=worst_contradiction.tier,
                tier_gap_days=None,
                citation_graph_valid=False,
                invalidation_marker_found=False,
            )

        if tier_gap >= 2:
            temporal_gap = (
                best_support.publication_date
                - worst_contradiction.publication_date
            ) / 86400

            if temporal_gap > TEMPORAL_BYPASS_DAYS:
                citation_valid = False
                invalidation_found = False

                for contra in contradiction_sources:
                    for supp in support_sources:
                        if self._citation_validator.has_citation_link(
                            contra.doi, supp.doi
                        ):
                            citation_valid = True
                            if self._citation_validator.has_invalidation_context(
                                contra.doi, supp.doi
                            ):
                                invalidation_found = True
                                break
                    if invalidation_found:
                        break

                if citation_valid and invalidation_found:
                    return FilterResult(
                        decision=BypassDecision.TEMPORAL_LAG_BYPASS,
                        support_tier=best_support.tier,
                        contradiction_tier=worst_contradiction.tier,
                        tier_gap_days=round(temporal_gap, 1),
                        citation_graph_valid=True,
                        invalidation_marker_found=True,
                    )

            all_contradictions_tier3_plus = all(
                c.tier.value >= SourceTier.TIER_3.value
                for c in contradiction_sources
            )

            if all_contradictions_tier3_plus:
                return FilterResult(
                    decision=BypassDecision.DROP_CONTRADICTION,
                    support_tier=best_support.tier,
                    contradiction_tier=worst_contradiction.tier,
                    tier_gap_days=round(temporal_gap, 1),
                    citation_graph_valid=False,
                    invalidation_marker_found=False,
                )

        return FilterResult(
            decision=BypassDecision.ESCALATE_TO_MATRIX,
            support_tier=best_support.tier,
            contradiction_tier=worst_contradiction.tier,
            tier_gap_days=None,
            citation_graph_valid=False,
            invalidation_marker_found=False,
        )
