from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from heapq import heappop, heappush
from math import exp, log
from typing import DefaultDict, Dict, Iterable, List, Mapping, Sequence, Set, Tuple


@dataclass(frozen=True)
class Signal:
    origin: str
    target: str
    timestamp: datetime
    reliability: float
    signal_type: str
    tags: Tuple[str, ...] = ()


@dataclass
class EntityAssessment:
    entity: str
    suspicion_score: float
    centrality_score: float
    anomaly_score: float
    total_score: float
    supporting_tags: Tuple[str, ...] = ()


@dataclass
class AnalysisResult:
    assessments: List[EntityAssessment]
    exposure_paths: Dict[str, List[str]]
    graph_weights: Dict[str, Dict[str, float]]


class StrategicSignalFusionEngine:
    def __init__(self, signals: Sequence[Signal]):
        self.signals = list(signals)

    def analyze(self, watchlist: Iterable[str]) -> AnalysisResult:
        graph = self._build_graph()
        watchlist_set = set(watchlist)
        suspicion = self._calculate_suspicion()
        centrality = self._calculate_centrality(graph)
        anomalies = self._calculate_anomalies()
        tags = self._supporting_tags()
        paths = self._exposure_paths(graph, watchlist_set)
        graph_entities = set(graph) | {
            target
            for targets in graph.values()
            for target in targets
        }

        entities = graph_entities | set(suspicion) | set(anomalies) | set(tags) | watchlist_set
        assessments = []
        for entity in sorted(entities):
            total = (
                suspicion.get(entity, 0.0) * 0.5
                + centrality.get(entity, 0.0) * 0.3
                + anomalies.get(entity, 0.0) * 0.2
                + (0.15 if entity in watchlist_set else 0.0)
            )
            assessments.append(
                EntityAssessment(
                    entity=entity,
                    suspicion_score=round(suspicion.get(entity, 0.0), 4),
                    centrality_score=round(centrality.get(entity, 0.0), 4),
                    anomaly_score=round(anomalies.get(entity, 0.0), 4),
                    total_score=round(min(total, 1.0), 4),
                    supporting_tags=tuple(sorted(tags.get(entity, ()))),
                )
            )

        assessments.sort(key=lambda item: (-item.total_score, item.entity))
        rounded_graph = {
            source: {target: round(weight, 4) for target, weight in edges.items()}
            for source, edges in graph.items()
        }
        return AnalysisResult(assessments=assessments, exposure_paths=paths, graph_weights=rounded_graph)

    def _build_graph(self) -> DefaultDict[str, Dict[str, float]]:
        graph: DefaultDict[str, Dict[str, float]] = defaultdict(dict)
        for signal in self.signals:
            increment = signal.reliability * self._signal_multiplier(signal.signal_type)
            graph[signal.origin][signal.target] = graph[signal.origin].get(signal.target, 0.0) + increment
            graph.setdefault(signal.target, {})
        return graph

    def _calculate_suspicion(self) -> Dict[str, float]:
        evidence: DefaultDict[str, float] = defaultdict(float)
        for signal in self.signals:
            base = signal.reliability * self._signal_multiplier(signal.signal_type)
            tag_bonus = sum(self._tag_weight(tag) for tag in signal.tags)
            evidence[signal.origin] += base * 0.4
            evidence[signal.target] += base + tag_bonus

        suspicion = {}
        for entity, score in evidence.items():
            log_odds = -1.15 + score
            suspicion[entity] = 1.0 / (1.0 + exp(-log_odds))
        return suspicion

    def _calculate_centrality(self, graph: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
        inbound: DefaultDict[str, float] = defaultdict(float)
        outbound: DefaultDict[str, float] = defaultdict(float)
        for source, targets in graph.items():
            outbound[source] += sum(targets.values())
            for target, weight in targets.items():
                inbound[target] += weight

        entities = set(inbound) | set(outbound) | set(graph)
        max_total = max((inbound[e] + outbound[e] for e in entities), default=1.0)
        return {entity: (inbound[entity] + outbound[entity]) / max_total for entity in entities}

    def _calculate_anomalies(self) -> Dict[str, float]:
        activity: DefaultDict[str, List[datetime]] = defaultdict(list)
        for signal in self.signals:
            activity[signal.target].append(signal.timestamp)

        anomalies = {}
        for entity, timestamps in activity.items():
            ordered = sorted(timestamps)
            if len(ordered) < 3:
                anomalies[entity] = min(len(ordered) * 0.15, 0.3)
                continue

            total_span = max((ordered[-1] - ordered[0]).total_seconds(), 1.0)
            expected_gap = total_span / (len(ordered) - 1)
            recent_gap = max((ordered[-1] - ordered[-2]).total_seconds(), 1.0)
            burst = max(log((expected_gap + 1.0) / recent_gap), 0.0)
            anomalies[entity] = min(burst / 4.0 + min(len(ordered) / 20.0, 0.25), 1.0)
        return anomalies

    def _supporting_tags(self) -> Dict[str, Set[str]]:
        tags: DefaultDict[str, Set[str]] = defaultdict(set)
        for signal in self.signals:
            if signal.tags:
                tags[signal.target].update(signal.tags)
        return tags

    def _exposure_paths(
        self, graph: Mapping[str, Mapping[str, float]], watchlist: Set[str]
    ) -> Dict[str, List[str]]:
        reverse_graph: DefaultDict[str, List[Tuple[str, float]]] = defaultdict(list)
        for source, targets in graph.items():
            for target, weight in targets.items():
                reverse_graph[target].append((source, weight))

        paths: Dict[str, List[str]] = {}
        best_candidates: Dict[str, Tuple[int, float, str, str]] = {}
        frontier: List[Tuple[int, float, str, str, str]] = []

        for watched in sorted(watchlist):
            candidate = (0, 0.0, watched, "")
            best_candidates[watched] = candidate
            heappush(frontier, (0, 0.0, watched, "", watched))

        while frontier:
            hop_count, neg_strength, terminal_watch, next_hop, current = heappop(frontier)
            if best_candidates.get(current) != (hop_count, neg_strength, terminal_watch, next_hop):
                continue

            for predecessor, weight in reverse_graph.get(current, ()):
                candidate = (hop_count + 1, neg_strength - weight, terminal_watch, current)
                if candidate < best_candidates.get(predecessor, (float("inf"), float("inf"), "\uffff", "\uffff")):
                    best_candidates[predecessor] = candidate
                    heappush(frontier, (*candidate, predecessor))

        for entity in best_candidates:
            if entity not in watchlist:
                current = entity
                path = [current]
                while current not in watchlist:
                    current = best_candidates[current][3]
                    path.append(current)
                paths[entity] = path
        return paths

    @staticmethod
    def _signal_multiplier(signal_type: str) -> float:
        return {
            "financial_transfer": 1.35,
            "co_travel": 1.2,
            "encrypted_contact": 1.4,
            "facility_access": 1.1,
            "procurement": 1.15,
        }.get(signal_type, 1.0)

    @staticmethod
    def _tag_weight(tag: str) -> float:
        return {
            "shell_company": 0.5,
            "dual_use": 0.35,
            "sanctioned_route": 0.45,
            "spoofed_identity": 0.55,
            "unusual_hour": 0.2,
        }.get(tag, 0.1)


def build_demo_result() -> AnalysisResult:
    signals = [
        Signal("atlas_holdings", "black_orchid", datetime(2026, 8, 1, 10, 0), 0.92, "financial_transfer", ("shell_company",)),
        Signal("black_orchid", "helios_node", datetime(2026, 8, 2, 8, 15), 0.88, "encrypted_contact", ("spoofed_identity",)),
        Signal("meridian_logistics", "helios_node", datetime(2026, 8, 3, 22, 5), 0.83, "procurement", ("dual_use", "unusual_hour")),
        Signal("helios_node", "watchtower", datetime(2026, 8, 4, 9, 30), 0.9, "facility_access"),
        Signal("atlas_holdings", "watchtower", datetime(2026, 8, 4, 9, 45), 0.74, "co_travel"),
        Signal("meridian_logistics", "watchtower", datetime(2026, 8, 4, 9, 46), 0.79, "co_travel", ("sanctioned_route",)),
        Signal("black_orchid", "watchtower", datetime(2026, 8, 4, 9, 47), 0.93, "facility_access"),
    ]
    engine = StrategicSignalFusionEngine(signals)
    return engine.analyze(watchlist={"watchtower"})


def _format_result(result: AnalysisResult) -> str:
    lines = ["Top assessments:"]
    for assessment in result.assessments[:5]:
        lines.append(
            f"- {assessment.entity}: total={assessment.total_score} "
            f"(suspicion={assessment.suspicion_score}, centrality={assessment.centrality_score}, "
            f"anomaly={assessment.anomaly_score}, tags={','.join(assessment.supporting_tags) or 'none'})"
        )

    lines.append("")
    lines.append("Exposure paths:")
    for entity, path in sorted(result.exposure_paths.items()):
        lines.append(f"- {entity}: {' -> '.join(path)}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(_format_result(build_demo_result()))
