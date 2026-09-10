import unittest
from datetime import datetime

from palantir_engine import Signal, StrategicSignalFusionEngine, build_demo_result


class StrategicSignalFusionEngineTests(unittest.TestCase):
    def test_demo_prioritizes_watchtower_network(self) -> None:
        result = build_demo_result()
        self.assertEqual(
            [assessment.entity for assessment in result.assessments[:5]],
            ["fulfillment_hub", "relay_cluster", "harbor_buffer", "northstar_supply", "vector_parts"],
        )
        self.assertGreater(result.graph_weights["harbor_buffer"]["fulfillment_hub"], 1.0)
        self.assertEqual(
            result.exposure_paths,
            {
                "harbor_buffer": ["harbor_buffer", "fulfillment_hub"],
                "northstar_supply": ["northstar_supply", "fulfillment_hub"],
                "relay_cluster": ["relay_cluster", "fulfillment_hub"],
                "vector_parts": ["vector_parts", "fulfillment_hub"],
            },
        )

    def test_exposure_paths_lead_back_to_watchlist(self) -> None:
        signals = [
            Signal("alpha", "beta", datetime(2026, 8, 1, 10, 0), 0.8, "supplier_payment"),
            Signal("beta", "gamma", datetime(2026, 8, 1, 11, 0), 0.9, "inventory_sync"),
            Signal("gamma", "omega", datetime(2026, 8, 1, 12, 0), 0.85, "dock_access"),
        ]
        result = StrategicSignalFusionEngine(signals).analyze(watchlist={"omega"})
        self.assertEqual(result.exposure_paths["alpha"], ["alpha", "beta", "gamma", "omega"])
        self.assertEqual(result.exposure_paths["beta"], ["beta", "gamma", "omega"])

    def test_risk_increases_with_compounding_signals(self) -> None:
        signals = [
            Signal("source_a", "target", datetime(2026, 8, 1, 10, 0), 0.95, "supplier_payment", ("single_source",)),
            Signal("source_b", "target", datetime(2026, 8, 1, 10, 5), 0.9, "inventory_sync", ("identity_mismatch",)),
            Signal("source_c", "other", datetime(2026, 8, 1, 10, 10), 0.3, "dock_access"),
        ]
        result = StrategicSignalFusionEngine(signals).analyze(watchlist=set())
        by_entity = {assessment.entity: assessment for assessment in result.assessments}
        self.assertGreater(by_entity["target"].suspicion_score, by_entity["other"].suspicion_score)
        self.assertGreater(by_entity["target"].total_score, by_entity["other"].total_score)
        self.assertEqual(result.assessments[0].entity, "target")

    def test_exposure_paths_prefer_shortest_then_strongest_route(self) -> None:
        signals = [
            Signal("alpha", "beta", datetime(2026, 8, 1, 9, 0), 0.4, "dock_access"),
            Signal("beta", "omega", datetime(2026, 8, 1, 9, 5), 0.4, "dock_access"),
            Signal("alpha", "delta", datetime(2026, 8, 1, 9, 10), 0.95, "supplier_payment"),
            Signal("delta", "omega", datetime(2026, 8, 1, 9, 15), 0.95, "supplier_payment"),
            Signal("alpha", "gamma", datetime(2026, 8, 1, 9, 20), 0.99, "inventory_sync"),
            Signal("gamma", "omega", datetime(2026, 8, 1, 9, 25), 0.01, "inventory_sync"),
        ]
        result = StrategicSignalFusionEngine(signals).analyze(watchlist={"omega"})
        self.assertEqual(result.exposure_paths["alpha"], ["alpha", "delta", "omega"])
        self.assertEqual(result.exposure_paths["gamma"], ["gamma", "omega"])


if __name__ == "__main__":
    unittest.main()
