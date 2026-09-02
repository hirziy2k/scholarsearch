"""Collision & Spillover Matrix for PDF-to-PPTX converter.

Detects when font emulation expands a text box vertically, causing overlap
with the box below. Resolves collisions by pushing downstream content down.
If pushed beyond the slide margin, splits into a new slide.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math


@dataclass
class LayoutElement:
    index: int
    left: float
    top: float
    width: float
    height: float
    element_type: str
    text: str = ""

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def right(self) -> float:
        return self.left + self.width


@dataclass
class Collision:
    upper: int
    lower: int
    overlap_px: float


@dataclass
class ResolutionResult:
    resolved_elements: List[LayoutElement] = field(default_factory=list)
    spillover_elements: List[LayoutElement] = field(default_factory=list)
    push_count: int = 0
    max_push_px: float = 0.0
    iterations: int = 0


class CollisionDetector:
    """Detect when bounding boxes overlap after font emulation adjustments."""

    MIN_HORIZONTAL_OVERLAP_RATIO = 0.20

    def detect_collisions(self, elements: List[LayoutElement]) -> List[Collision]:
        """Compare all pairs of elements. Return list of collisions."""
        if len(elements) < 2:
            return []

        collisions: List[Collision] = []

        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                a = elements[i]
                b = elements[j]

                upper, lower = (a, b) if a.top <= b.top else (b, a)
                upper_idx, lower_idx = (i, j) if a.top <= b.top else (j, i)

                if lower.top >= upper.bottom:
                    continue

                a_left = min(a.left, a.left + a.width)
                a_right = max(a.left, a.left + a.width)
                b_left = min(b.left, b.left + b.width)
                b_right = max(b.left, b.left + b.width)

                overlap_left = max(a_left, b_left)
                overlap_right = min(a_right, b_right)
                overlap_width = overlap_right - overlap_left

                if overlap_width <= 0:
                    continue

                min_width = min(abs(a.width), abs(b.width))
                if min_width <= 0:
                    continue

                ratio = overlap_width / min_width
                if ratio <= self.MIN_HORIZONTAL_OVERLAP_RATIO:
                    continue

                overlap_vertical = upper.bottom - lower.top
                if overlap_vertical > 0:
                    collisions.append(Collision(
                        upper=upper_idx,
                        lower=lower_idx,
                        overlap_px=overlap_vertical,
                    ))

        return collisions

    def find_groups(self, elements: List[LayoutElement]) -> List[List[int]]:
        """Group colliding elements into connected components."""
        collisions = self.detect_collisions(elements)

        if not collisions:
            return [[i] for i in range(len(elements))]

        parent = list(range(len(elements)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for c in collisions:
            union(c.upper, c.lower)

        groups_map: dict[int, List[int]] = {}
        for i in range(len(elements)):
            root = find(i)
            groups_map.setdefault(root, []).append(i)

        return list(groups_map.values())


class SpilloverResolver:
    """Resolve collisions by pushing elements down, with slide overflow handling."""

    SLIDE_MARGIN_EMU = 360000
    MAX_ITERATIONS = 5

    def resolve(
        self,
        elements: List[LayoutElement],
        slide_height: float,
        page_width: float,
    ) -> ResolutionResult:
        """Main resolution algorithm.

        1. Sort elements top-to-bottom
        2. For each collision group, push lower elements down by overlap
        3. Check if pushed element exceeds slide_height - margin
        4. If yes, mark for slide spillover
        5. Iterate until no collisions remain (max 5 iterations)
        """
        if not elements:
            return ResolutionResult()

        working = [self._copy_element(e) for e in elements]
        working.sort(key=lambda e: e.top)

        total_push_count = 0
        max_push = 0.0

        detector = CollisionDetector()
        final_iteration = 0

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            collisions = detector.detect_collisions(working)
            final_iteration = iteration
            if not collisions:
                break

            for c in collisions:
                if c.upper >= len(working) or c.lower >= len(working):
                    continue

                upper = working[c.upper]
                lower = working[c.lower]

                new_top = upper.bottom
                push_distance = new_top - lower.top

                if push_distance <= 0:
                    continue

                lower.top = new_top
                total_push_count += 1
                max_push = max(max_push, push_distance)

            working.sort(key=lambda e: e.top)

        slide_limit = slide_height - self.SLIDE_MARGIN_EMU
        staying: List[LayoutElement] = []
        spillover: List[LayoutElement] = []

        for e in working:
            if e.top > slide_limit:
                spillover.append(e)
            elif e.bottom > slide_limit:
                spillover.append(e)
            else:
                staying.append(e)

        return ResolutionResult(
            resolved_elements=staying,
            spillover_elements=spillover,
            push_count=total_push_count,
            max_push_px=max_push,
            iterations=final_iteration,
        )

    def split_to_new_slide(
        self,
        overflow_elements: List[LayoutElement],
        original_slide_height: float,
    ) -> Tuple[List[LayoutElement], List[LayoutElement]]:
        """Split elements into (stay_on_slide, spill_to_next).

        Elements that fit: bottom <= slide_height - margin
        Elements that spill: top > slide_height - margin
        Boundary case: element spans the margin line -> split the text.
        """
        slide_limit = original_slide_height - self.SLIDE_MARGIN_EMU
        stay: List[LayoutElement] = []
        spill: List[LayoutElement] = []

        for e in overflow_elements:
            if e.bottom <= slide_limit:
                stay.append(e)
            elif e.top >= slide_limit:
                spill.append(self._copy_element(e))
            else:
                stay_element = self._copy_element(e)
                stay_height = slide_limit - e.top
                if stay_height > 0:
                    stay_element.height = stay_height
                stay.append(stay_element)

                spill_element = self._copy_element(e)
                spill_top = slide_limit
                spill_height = e.bottom - spill_top
                if spill_height > 0:
                    spill_element.top = spill_top
                    spill_element.height = spill_height
                spill.append(spill_element)

        return stay, spill

    @staticmethod
    def _copy_element(e: LayoutElement) -> LayoutElement:
        return LayoutElement(
            index=e.index,
            left=e.left,
            top=e.top,
            width=e.width,
            height=e.height,
            element_type=e.element_type,
            text=e.text,
        )


def resolve_collisions(
    clusters: List[dict],
    slide_height: float,
    page_width: float,
) -> Tuple[List[dict], List[dict]]:
    """One-call API for the orchestrator.

    1. Convert cluster dicts to LayoutElements
    2. Detect collisions
    3. Resolve by pushing down
    4. Handle spillover
    5. Convert back to cluster dicts
    6. Return (adjusted_main, overflow_to_next_slide)
    """
    if not clusters:
        return [], []

    elements: List[LayoutElement] = []
    for i, c in enumerate(clusters):
        elements.append(LayoutElement(
            index=i,
            left=float(c.get("left", 0)),
            top=float(c.get("top", 0)),
            width=float(c.get("width", 0)),
            height=float(c.get("height", 0)),
            element_type=str(c.get("element_type", "text")),
            text=str(c.get("text", "")),
        ))

    detector = CollisionDetector()
    groups = detector.find_groups(elements)

    resolver = SpilloverResolver()
    all_stay: List[LayoutElement] = []
    all_spill: List[LayoutElement] = []

    for group_indices in groups:
        group_elements = [elements[i] for i in group_indices]

        result = resolver.resolve(group_elements, slide_height, page_width)

        if result.spillover_elements:
            stay, spill = resolver.split_to_new_slide(
                result.spillover_elements, slide_height
            )
            all_stay.extend(result.resolved_elements)
            all_stay.extend(stay)
            all_spill.extend(spill)
        else:
            all_stay.extend(result.resolved_elements)

    adjusted = _elements_to_dicts(all_stay)
    overflow = _elements_to_dicts(all_spill)

    return adjusted, overflow


def _elements_to_dicts(elements: List[LayoutElement]) -> List[dict]:
    """Convert LayoutElements back to cluster dicts."""
    result = []
    for e in elements:
        result.append({
            "index": e.index,
            "left": e.left,
            "top": max(0.0, e.top),
            "width": e.width,
            "height": e.height,
            "element_type": e.element_type,
            "text": e.text,
        })
    return result


def _run_test():
    """Standalone test: creates overlapping boxes and resolves collisions."""
    print("=" * 60)
    print("Collision & Spillover Matrix — Standalone Test")
    print("=" * 60)

    SLIDE_HEIGHT = 6858000.0
    PAGE_WIDTH = 9144000.0

    clusters = [
        {
            "left": 457200,
            "top": 457200,
            "width": 8229600,
            "height": 914400,
            "element_type": "text",
            "text": "Title (expanded by font emulation)",
        },
        {
            "left": 457200,
            "top": 1270000,
            "width": 8229600,
            "height": 914400,
            "element_type": "text",
            "text": "Body paragraph 1 — should collide with title",
        },
        {
            "left": 457200,
            "top": 2082800,
            "width": 8229600,
            "height": 914400,
            "element_type": "text",
            "text": "Body paragraph 2 — should be pushed down",
        },
        {
            "left": 457200,
            "top": 3000000,
            "width": 8229600,
            "height": 914400,
            "element_type": "text",
            "text": "Footer — near bottom, may spill over",
        },
    ]

    print("\nOriginal elements:")
    for c in clusters:
        bottom = c["top"] + c["height"]
        print(f"  {c['text'][:40]:40s}  top={c['top']:>10.0f}  bottom={bottom:>10.0f}")

    detector = CollisionDetector()
    elements = [
        LayoutElement(
            index=i,
            left=float(c["left"]),
            top=float(c["top"]),
            width=float(c["width"]),
            height=float(c["height"]),
            element_type=c["element_type"],
            text=c["text"],
        )
        for i, c in enumerate(clusters)
    ]

    collisions = detector.detect_collisions(elements)
    print(f"\nDetected {len(collisions)} collision(s):")
    for c in collisions:
        print(f"  [{c.upper}] overlaps [{c.lower}] by {c.overlap_px:.0f} EMU")

    groups = detector.find_groups(elements)
    print(f"\nConnected groups: {groups}")

    adjusted, overflow = resolve_collisions(clusters, SLIDE_HEIGHT, PAGE_WIDTH)

    print(f"\nResolved elements (slide 1): {len(adjusted)}")
    for e in adjusted:
        bottom = e["top"] + e["height"]
        print(f"  [{e['index']}] {e['text'][:40]:40s}  top={e['top']:>10.0f}  bottom={bottom:>10.0f}")

    if overflow:
        print(f"\nSpillover elements (slide 2): {len(overflow)}")
        for e in overflow:
            bottom = e["top"] + e["height"]
            print(f"  [{e['index']}] {e['text'][:40]:40s}  top={e['top']:>10.0f}  bottom={bottom:>10.0f}")
    else:
        print("\nNo spillover — all elements fit on one slide.")

    print("\n--- Edge case tests ---")

    empty_adj, empty_ovf = resolve_collisions([], SLIDE_HEIGHT, PAGE_WIDTH)
    print(f"Empty list: adjusted={len(empty_adj)}, overflow={len(empty_ovf)}")

    single = [{"left": 0, "top": 0, "width": 9144000, "height": 500000, "element_type": "text", "text": "Solo"}]
    single_adj, single_ovf = resolve_collisions(single, SLIDE_HEIGHT, PAGE_WIDTH)
    print(f"Single element: adjusted={len(single_adj)}, overflow={len(single_ovf)}")

    wide = [{"left": 0, "top": 0, "width": 20000000, "height": 500000, "element_type": "text", "text": "Wider than slide"}]
    wide_adj, wide_ovf = resolve_collisions(wide, SLIDE_HEIGHT, PAGE_WIDTH)
    print(f"Wider than slide: adjusted={len(wide_adj)}, overflow={len(wide_ovf)}")

    print("\n" + "=" * 60)
    print("All tests completed.")
    print("=" * 60)


if __name__ == "__main__":
    _run_test()
