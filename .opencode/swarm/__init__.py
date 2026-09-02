"""
Swarm Cascade — Production-Grade Deep Research Engine

Architecture:
    1. Volume Velocity Gatekeeper (Laplace-smoothed zero-day detection)
    2. MACD Momentum Oscillator (trend-following volatility)
    3. MAD Triage (outlier-immune routing)
    4. Liveness Heartbeat Mutex (split-brain prevention)
    5. Citation Context Extractor (±75 token radius)
    6. Methodological Pre-Filter (tier-based noise rejection)
    7. Blind Matrix Evaluation (logit-masked 8B model)
    8. Swarm Cascade Orchestrator (coordinates full pipeline)
    9. Redis Streams (bounded ephemeral state)
    10. SSE Handler (cursor-based frame replay)
    11. Mechanic Worker (atomic persistence with hash chain)
    12. Baseline Normalizer (monthly regime drift correction)
    13. Audit Exporter (cryptographic verification for external auditors)
"""

from .volume_velocity import (
    calculate_volume_velocity,
    compute_decay_lambda,
    IngressTelemetry,
    VelocityStatus,
    RoutingAction,
)
from .macd_oscillator import MACDOscillator, MACDResult
from .mad_triage import calculate_modified_z, RoutingDecision, TriageResult
from .heartbeat_mutex import HeartbeatMutex, LockManager, MutexState
from .citation_context import CitationContextExtractor, CitationContext, VaultEntityResolver
from .methodological_filter import (
    MethodologicalPreFilter,
    CitationGraphValidator,
    SourceMetadata,
    SourceTier,
    BypassDecision,
    FilterResult,
)
from .blind_matrix import BlindMatrixEvaluator, MatrixResult, ContradictionType, EvidenceVerdict
from .orchestrator import SwarmCascade, SwarmState, PipelinePhase
from .redis_streams import (
    SwarmStreamWriter,
    SwarmStreamReader,
    StreamOrchestrator,
    StreamEvent,
    StreamEventType,
    StreamState,
)
from .sse_handler import (
    SSEHandler,
    SSEConnectionManager,
    SSEMessage,
    SSEMessageType,
)
from .mechanic_worker import (
    MechanicWorker,
    ReportPayload,
    PersistedReport,
    HashChainValidator,
    WriteStatus,
)
from .baseline_normalizer import BaselineNormalizer, CronScheduler, NormalizationResult
from .audit_export import AuditExporter, AuditExport, AuditRecord

__all__ = [
    "calculate_volume_velocity",
    "compute_decay_lambda",
    "IngressTelemetry",
    "VelocityStatus",
    "RoutingAction",
    "MACDOscillator",
    "MACDResult",
    "calculate_modified_z",
    "RoutingDecision",
    "TriageResult",
    "HeartbeatMutex",
    "LockManager",
    "MutexState",
    "CitationContextExtractor",
    "CitationContext",
    "VaultEntityResolver",
    "MethodologicalPreFilter",
    "CitationGraphValidator",
    "SourceMetadata",
    "SourceTier",
    "BypassDecision",
    "FilterResult",
    "BlindMatrixEvaluator",
    "MatrixResult",
    "ContradictionType",
    "EvidenceVerdict",
    "SwarmCascade",
    "SwarmState",
    "PipelinePhase",
    "SwarmStreamWriter",
    "SwarmStreamReader",
    "StreamOrchestrator",
    "StreamEvent",
    "StreamEventType",
    "StreamState",
    "SSEHandler",
    "SSEConnectionManager",
    "SSEMessage",
    "SSEMessageType",
    "MechanicWorker",
    "ReportPayload",
    "PersistedReport",
    "HashChainValidator",
    "WriteStatus",
    "BaselineNormalizer",
    "CronScheduler",
    "NormalizationResult",
    "AuditExporter",
    "AuditExport",
    "AuditRecord",
]
