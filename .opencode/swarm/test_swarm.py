"""
Unit tests for Swarm Cascade components.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.volume_velocity import calculate_volume_velocity, compute_decay_lambda, IngressTelemetry, VelocityStatus, RoutingAction
from swarm.macd_oscillator import MACDOscillator
from swarm.mad_triage import calculate_modified_z, RoutingDecision
from swarm.citation_context import CitationContextExtractor
from swarm.methodological_filter import (
    MethodologicalPreFilter,
    SourceMetadata,
    SourceTier,
    BypassDecision,
)
from swarm.blind_matrix import BlindMatrixEvaluator, ContradictionType, EvidenceVerdict


def test_volume_velocity_zero_day():
    result = calculate_volume_velocity(0, 0)
    assert result.status == VelocityStatus.STABLE_VOLUME
    assert result.velocity_ratio == 1.0
    print("PASS: test_volume_velocity_zero_day")


def test_volume_velocity_spike():
    result = calculate_volume_velocity(50, 0)
    assert result.status == VelocityStatus.ZERO_DAY_SPIKE
    assert result.action == RoutingAction.BYPASS_MACD
    assert result.lambda_value == 0.30
    print("PASS: test_volume_velocity_spike")


def test_volume_velocity_trending():
    result = calculate_volume_velocity(10, 2)
    assert result.status == VelocityStatus.TRENDING_VOLATILE
    assert result.action == RoutingAction.ELEVATE_MACD_FLOOR
    print("PASS: test_volume_velocity_trending")


def test_volume_velocity_stable():
    result = calculate_volume_velocity(5, 5)
    assert result.status == VelocityStatus.STABLE_VOLUME
    assert result.action == RoutingAction.NORMAL_MACD
    print("PASS: test_volume_velocity_stable")


def test_macd_oscillator():
    osc = MACDOscillator()
    for _ in range(30):
        osc.update(5.0)
    result = osc.update(10.0)
    assert result.macd_line != 0
    assert osc.has_sufficient_data()
    print("PASS: test_macd_oscillator")


def test_mad_triage_vault():
    scores = [0.95, 0.50, 0.48, 0.45, 0.42]
    result = calculate_modified_z(scores)
    assert result.decision == RoutingDecision.VAULT_ONLY
    print("PASS: test_mad_triage_vault")


def test_mad_triage_speculative():
    scores = [0.50, 0.50, 0.50, 0.50, 0.50]
    result = calculate_modified_z(scores)
    assert result.decision == RoutingDecision.SPECULATIVE
    print("PASS: test_mad_triage_speculative")


def test_mad_triage_with_decay():
    scores = [0.95, 0.90, 0.88, 0.85, 0.82]
    result = calculate_modified_z(scores, decay_factor=0.3)
    assert result.decision == RoutingDecision.SPECULATIVE
    print("PASS: test_mad_triage_with_decay")


def test_citation_context_extractor():
    extractor = CitationContextExtractor()
    text = "The study by Smith et al. found that. However previous work was flawed. Smith [14] utilized this approach."
    tokens = text.split()
    citation_idx = tokens.index("[14]")
    context = extractor.extract(text, citation_idx, "[14]")
    assert context.token_count <= 151
    assert "[14]" in context.context_block
    print("PASS: test_citation_context_extractor")


def test_methodological_filter_drop():
    support = [SourceMetadata(doi="10.1000/s1", tier=SourceTier.TIER_1, publication_date=time.time() - 86400 * 365, domain="nature.com")]
    contra = [
        SourceMetadata(doi="10.2000/c1", tier=SourceTier.TIER_3, publication_date=time.time() - 86400 * 100, domain="preprint.org"),
        SourceMetadata(doi="10.2000/c2", tier=SourceTier.TIER_4, publication_date=time.time() - 86400 * 50, domain="blog.com"),
    ]
    f = MethodologicalPreFilter()
    result = f.evaluate(support, contra)
    assert result.decision == BypassDecision.DROP_CONTRADICTION
    print("PASS: test_methodological_filter_drop")


def test_methodological_filter_escalate():
    support = [SourceMetadata(doi="10.1000/s1", tier=SourceTier.TIER_2, publication_date=time.time() - 86400 * 100, domain="journal.com")]
    contra = [SourceMetadata(doi="10.2000/c1", tier=SourceTier.TIER_2, publication_date=time.time() - 86400 * 50, domain="journal2.com")]
    f = MethodologicalPreFilter()
    result = f.evaluate(support, contra)
    assert result.decision == BypassDecision.ESCALATE_TO_MATRIX
    print("PASS: test_methodological_filter_escalate")


if __name__ == "__main__":
    test_volume_velocity_zero_day()
    test_volume_velocity_spike()
    test_volume_velocity_trending()
    test_volume_velocity_stable()
    test_macd_oscillator()
    test_mad_triage_vault()
    test_mad_triage_speculative()
    test_mad_triage_with_decay()
    test_citation_context_extractor()
    test_methodological_filter_drop()
    test_methodological_filter_escalate()
    print("\n=== ALL TESTS PASSED ===")
