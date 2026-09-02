"""
Swarm Cascade Orchestrator
Coordinates the full research pipeline: triage, swarm dispatch,
methodological filtering, blind matrix evaluation, and persistence.
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Any
from enum import Enum

from .volume_velocity import IngressTelemetry, calculate_volume_velocity, compute_decay_lambda
from .macd_oscillator import MACDOscillator, MACDResult
from .mad_triage import calculate_modified_z, RoutingDecision, TriageResult
from .heartbeat_mutex import HeartbeatMutex, LockManager
from .citation_context import CitationContextExtractor, CitationContext
from .methodological_filter import (
    MethodologicalPreFilter,
    SourceMetadata,
    FilterResult,
    BypassDecision,
)
from .blind_matrix import BlindMatrixEvaluator, MatrixResult, EvidenceVerdict


class PipelinePhase(Enum):
    VAULT_ONLY = "VAULT_ONLY"
    SPECULATIVE = "SPECULATIVE"
    SWARM_RUNNING = "SWARM_RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class SwarmState:
    query_hash: str
    phase: PipelinePhase
    velocity_result: Optional[Any] = None
    macd_result: Optional[MACDResult] = None
    triage_result: Optional[TriageResult] = None
    filter_result: Optional[FilterResult] = None
    matrix_result: Optional[MatrixResult] = None
    final_verdict: Optional[str] = None
    boundary_condition: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "query_hash": self.query_hash,
            "phase": self.phase.value,
            "velocity": self.velocity_result.to_dict() if self.velocity_result else None,
            "macd": self.macd_result.to_dict() if self.macd_result else None,
            "triage": self.triage_result.to_dict() if self.triage_result else None,
            "filter": self.filter_result.to_dict() if self.filter_result else None,
            "matrix": self.matrix_result.to_dict() if self.matrix_result else None,
            "final_verdict": self.final_verdict,
            "boundary_condition": self.boundary_condition,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round((self.completed_at - self.started_at) * 1000, 2) if self.completed_at else None,
        }


class SwarmCascade:
    """
    Main orchestrator for the research cascade pipeline.
    """

    def __init__(
        self,
        telemetry: IngressTelemetry,
        lock_manager: LockManager,
        vault_store: Any,
        citation_extractor: CitationContextExtractor,
        pre_filter: MethodologicalPreFilter,
        blind_matrix: BlindMatrixEvaluator,
        macd_oscillators: Optional[dict[str, MACDOscillator]] = None,
        on_state_change: Optional[Callable[[SwarmState], Awaitable[None]]] = None,
    ):
        self._telemetry = telemetry
        self._lock_manager = lock_manager
        self._vault = vault_store
        self._citation_extractor = citation_extractor
        self._pre_filter = pre_filter
        self._blind_matrix = blind_matrix
        self._macd_oscillators = macd_oscillators or {}
        self._on_state_change = on_state_change

    async def execute(
        self,
        query: str,
        query_hash: str,
        support_sources: Optional[list[SourceMetadata]] = None,
        contradiction_sources: Optional[list[SourceMetadata]] = None,
    ) -> SwarmState:
        """
        Execute the full cascade pipeline.
        """
        state = SwarmState(query_hash=query_hash, phase=PipelinePhase.VAULT_ONLY)

        try:
            acquired, mutex = await self._lock_manager.try_acquire(
                query_hash,
                on_expire=self._handle_lock_expire(query_hash),
            )

            if not acquired:
                return await self._wait_for_existing(query_hash, state)

            self._telemetry.record_occurrence(query_hash)

            velocity_result = self._telemetry.evaluate(query_hash)
            state.velocity_result = velocity_result

            macd_result = self._get_or_create_macd(query_hash)
            state.macd_result = macd_result

            final_lambda = compute_decay_lambda(
                velocity_result,
                macd_result.divergence if macd_result else 0.0,
            )

            vault_neighbors = self._vault.query(query, k=10)
            scores = [n.score for n in vault_neighbors] if vault_neighbors else [0.0]

            triage_result = calculate_modified_z(
                scores,
                decay_factor=self._compute_decay_factor(final_lambda, vault_neighbors),
            )
            state.triage_result = triage_result

            if triage_result.decision == RoutingDecision.VAULT_ONLY:
                state.phase = PipelinePhase.COMPLETE
                state.final_verdict = "HIGH_AUTHORITY"
                state.completed_at = time.time()
                await mutex.release()
                await self._emit_state(state)
                return state

            state.phase = PipelinePhase.SPECULATIVE
            await self._emit_state(state)

            if support_sources and contradiction_sources:
                filter_result = self._pre_filter.evaluate(
                    support_sources, contradiction_sources
                )
                state.filter_result = filter_result

                if filter_result.decision == BypassDecision.DROP_CONTRADICTION:
                    state.phase = PipelinePhase.COMPLETE
                    state.final_verdict = "HIGH_AUTHORITY"
                    state.boundary_condition = "Contradiction dropped (low-tier noise)"
                    state.completed_at = time.time()
                    await mutex.release()
                    await self._emit_state(state)
                    return state

            state.phase = PipelinePhase.EVALUATING
            await self._emit_state(state)

            support_excerpts = [s.value for s in (support_sources or [])]
            contra_excerpts = [c.value for c in (contradiction_sources or [])]

            matrix_result = self._blind_matrix.evaluate(
                claim=query,
                support_pool=support_excerpts,
                contradiction_pool=contra_excerpts,
            )
            state.matrix_result = matrix_result
            state.final_verdict = matrix_result.verdict.value
            state.boundary_condition = matrix_result.boundary_condition

            state.phase = PipelinePhase.COMPLETE
            state.completed_at = time.time()

            await mutex.release()
            await self._emit_state(state)

            return state

        except Exception as e:
            state.phase = PipelinePhase.FAILED
            state.final_verdict = f"ERROR: {str(e)}"
            state.completed_at = time.time()
            await self._emit_state(state)
            return state

    def _get_or_create_macd(self, query_hash: str) -> MACDResult:
        if query_hash not in self._macd_oscillators:
            self._macd_oscillators[query_hash] = MACDOscillator()

        oscillator = self._macd_oscillators[query_hash]
        current_rate = self._telemetry.get_current_rate(query_hash)
        return oscillator.update(float(current_rate))

    def _compute_decay_factor(
        self, lam: float, neighbors: list
    ) -> float:
        import math
        if not neighbors:
            return 1.0
        avg_age_days = sum(n.age_days for n in neighbors if hasattr(n, 'age_days')) / len(neighbors)
        return math.exp(-lam * avg_age_days)

    async def _wait_for_existing(
        self, query_hash: str, state: SwarmState
    ) -> SwarmState:
        """Subscribe to existing stream for concurrent requests."""
        state.phase = PipelinePhase.SWARM_RUNNING
        state.boundary_condition = "Waiting for in-flight execution"
        await self._emit_state(state)
        return state

    def _handle_lock_expire(
        self, query_hash: str
    ) -> Callable[[], Awaitable[None]]:
        async def on_expire():
            pass
        return on_expire

    async def _emit_state(self, state: SwarmState) -> None:
        if self._on_state_change:
            await self._on_state_change(state)
