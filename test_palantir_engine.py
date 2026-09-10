import unittest
from datetime import datetime

from palantir_engine import Signal, StrategicSignalFusionEngine, build_demo_result


class StrategicSignalFusionEngineTests(unittest.TestCase):
    def test_demo_prioritizes_watchtower_network(self) -> None:
        result = build_demo_result()
        self.assertEqual(
            [assessment.entity for assessment in result.assessments[:5]],
            ["watchtower", "helios_node", "black_orchid", "atlas_holdings", "meridian_logistics"],
        )
        self.assertGreater(result.graph_weights["black_orchid"]["watchtower"], 1.0)
        self.assertEqual(
            result.exposure_paths,
            {
                "atlas_holdings": ["atlas_holdings", "watchtower"],
                "black_orchid": ["black_orchid", "watchtower"],
                "helios_node": ["helios_node", "watchtower"],
                "meridian_logistics": ["meridian_logistics", "watchtower"],
            },
        )

    def test_exposure_paths_lead_back_to_watchlist(self) -> None:
        signals = [
            Signal("alpha", "beta", datetime(2026, 8, 1, 10, 0), 0.8, "financial_transfer"),
            Signal("beta", "gamma", datetime(2026, 8, 1, 11, 0), 0.9, "encrypted_contact"),
            Signal("gamma", "omega", datetime(2026, 8, 1, 12, 0), 0.85, "facility_access"),
        ]
        result = StrategicSignalFusionEngine(signals).analyze(watchlist={"omega"})
        self.assertEqual(result.exposure_paths["alpha"], ["alpha", "beta", "gamma", "omega"])
        self.assertEqual(result.exposure_paths["beta"], ["beta", "gamma", "omega"])

    def test_risk_increases_with_compounding_signals(self) -> None:
        signals = [
            Signal("source_a", "target", datetime(2026, 8, 1, 10, 0), 0.95, "financial_transfer", ("shell_company",)),
            Signal("source_b", "target", datetime(2026, 8, 1, 10, 5), 0.9, "encrypted_contact", ("spoofed_identity",)),
            Signal("source_c", "other", datetime(2026, 8, 1, 10, 10), 0.3, "facility_access"),
        ]
        result = StrategicSignalFusionEngine(signals).analyze(watchlist=set())
        by_entity = {assessment.entity: assessment for assessment in result.assessments}
        self.assertGreater(by_entity["target"].suspicion_score, by_entity["other"].suspicion_score)
        self.assertGreater(by_entity["target"].total_score, by_entity["other"].total_score)
        self.assertEqual(result.assessments[0].entity, "target")

    def test_exposure_paths_prefer_shortest_then_strongest_route(self) -> None:
        signals = [
            Signal("alpha", "beta", datetime(2026, 8, 1, 9, 0), 0.4, "facility_access"),
            Signal("beta", "omega", datetime(2026, 8, 1, 9, 5), 0.4, "facility_access"),
            Signal("alpha", "delta", datetime(2026, 8, 1, 9, 10), 0.95, "financial_transfer"),
            Signal("delta", "omega", datetime(2026, 8, 1, 9, 15), 0.95, "financial_transfer"),
            Signal("alpha", "epsilon", datetime(2026, 8, 1, 9, 20), 0.99, "encrypted_contact"),
            Signal("epsilon", "zeta", datetime(2026, 8, 1, 9, 25), 0.99, "encrypted_contact"),
            Signal("zeta", "omega", datetime(2026, 8, 1, 9, 30), 0.99, "encrypted_contact"),
        ]
        result = StrategicSignalFusionEngine(signals).analyze(watchlist={"omega"})
        self.assertEqual(result.exposure_paths["alpha"], ["alpha", "delta", "omega"])
        self.assertEqual(result.exposure_paths["epsilon"], ["epsilon", "zeta", "omega"])


if __name__ == "__main__":
    unittest.main()
