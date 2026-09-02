"""
Citation Context Extractor
Extracts ±75 token radius around citation index with NER-based
dependency resolution and agnostic entity injection.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict


TOKEN_RADIUS = 75
MAX_CENTRALITY_WARNINGS = 2


@dataclass(frozen=True)
class ExtractedEntity:
    name: str
    frequency: int
    syntactic_weight: float
    definition: Optional[str]
    is_defined: bool


@dataclass
class CitationContext:
    citation_token: str
    context_block: str
    glossary: List[ExtractedEntity]
    warnings: List[str]
    token_count: int

    def to_prompt_payload(self) -> str:
        parts = [self.context_block]

        defined = [e for e in self.glossary if e.is_defined]
        if defined:
            glossary_text = "Defined terms:\n"
            for e in defined:
                glossary_text += f"- {e.name}: {e.definition}\n"
            parts.append(glossary_text)

        if self.warnings:
            parts.append("\n".join(self.warnings))

        return "\n\n".join(parts)


class CitationContextExtractor:
    """
    Extracts citation context with ±75 token radius and
    resolves dependency graph for undefined entities.
    """

    def __init__(
        self,
        vault_lookup=None,
        token_radius: int = TOKEN_RADIUS,
        max_warnings: int = MAX_CENTRALITY_WARNINGS,
    ):
        self._vault_lookup = vault_lookup
        self._token_radius = token_radius
        self._max_warnings = max_warnings

    def extract(
        self,
        text: str,
        citation_index: int,
        citation_token: str,
    ) -> CitationContext:
        """
        Extract context around citation with glossary resolution.

        Args:
            text: Full source text.
            citation_index: Token position of citation in text.
            citation_token: The citation marker (e.g., "[14]").
        """
        tokens = text.split()

        start = max(0, citation_index - self._token_radius)
        end = min(len(tokens), citation_index + self._token_radius + 1)
        context_tokens = tokens[start:end]
        context_block = " ".join(context_tokens)

        entities = self._extract_entities(context_tokens)

        glossary = self._resolve_dependencies(entities)

        warnings = self._build_warnings(glossary)

        return CitationContext(
            citation_token=citation_token,
            context_block=context_block,
            glossary=glossary,
            warnings=warnings,
            token_count=len(context_tokens),
        )

    def _extract_entities(self, tokens: List[str]) -> List[ExtractedEntity]:
        """
        Extract named entities and compute centrality scores.
        Uses simple heuristic NER for technical domains.
        """
        entity_counts: Dict[str, int] = {}
        entity_positions: Dict[str, List[int]] = {}

        combined = " ".join(tokens)

        patterns = [
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
            r"\b([A-Z]{2,})\b",
            r"\b(\d+(?:\.\d+)?)\s+(mg|ml|kg|Hz|ms|nm)\b",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, combined):
                entity = match.group(1)
                entity_lower = entity.lower()
                entity_counts[entity_lower] = entity_counts.get(entity_lower, 0) + 1

                if entity_lower not in entity_positions:
                    entity_positions[entity_lower] = []
                entity_positions[entity_lower].append(match.start())

        entities = []
        for entity, count in entity_counts.items():
            positions = entity_positions[entity]
            syntactic_weight = self._compute_syntactic_weight(
                positions, len(combined)
            )
            entities.append(
                ExtractedEntity(
                    name=entity,
                    frequency=count,
                    syntactic_weight=round(syntactic_weight, 4),
                    definition=None,
                    is_defined=False,
                )
            )

        entities.sort(
            key=lambda e: e.frequency * e.syntactic_weight, reverse=True
        )

        return entities

    def _compute_syntactic_weight(
        self, positions: List[int], total_length: int
    ) -> float:
        """Weight entities appearing earlier or in subject position higher."""
        if not positions or total_length == 0:
            return 0.0

        position_scores = []
        for pos in positions:
            relative_pos = pos / total_length
            if relative_pos < 0.2:
                position_scores.append(1.0)
            elif relative_pos < 0.5:
                position_scores.append(0.7)
            else:
                position_scores.append(0.4)

        return sum(position_scores) / len(position_scores)

    def _resolve_dependencies(
        self, entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """
        Resolve entity definitions via Vault lookup.
        Returns entities with is_defined flag set.
        """
        resolved = []
        for entity in entities:
            definition = None
            is_defined = False

            if self._vault_lookup:
                definition = self._vault_lookup(entity.name)
                is_defined = definition is not None

            resolved.append(
                ExtractedEntity(
                    name=entity.name,
                    frequency=entity.frequency,
                    syntactic_weight=entity.syntactic_weight,
                    definition=definition,
                    is_defined=is_defined,
                )
            )

        return resolved

    def _build_warnings(self, glossary: List[ExtractedEntity]) -> List[str]:
        """
        Build agnostic warnings for top N undefined entities.
        Prevents context window suffocation.
        """
        undefined = [e for e in glossary if not e.is_defined]

        critical = undefined[: self._max_warnings]

        return [
            f"[WARNING: Core Concept '{e.name}' is undefined in current memory. Do not infer.]"
            for e in critical
        ]


class VaultEntityResolver:
    """
    Wraps Vault lookups for entity definition resolution.
    """

    def __init__(self, vector_store, fallback_definition: str = None):
        self._vector_store = vector_store
        self._fallback = fallback_definition

    def __call__(self, entity_name: str) -> Optional[str]:
        if not self._vector_store:
            return self._fallback

        results = self._vector_store.query(
            f"definition of {entity_name}", k=1
        )

        if results and results[0].score > 0.8:
            return results[0].text[:200]

        return self._fallback
