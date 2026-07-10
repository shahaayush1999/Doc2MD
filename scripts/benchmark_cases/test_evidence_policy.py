from __future__ import annotations

import unittest

from scripts.benchmark_cases.common import (
    evidence_policy_violations,
    extract_evidence_signals,
    finalize_fact_regions,
    leaf,
    table_leaves,
)


class EvidencePolicyCompletenessTest(unittest.TestCase):
    def test_table_binding_accepts_literal_source_value_alias(self) -> None:
        leaves = table_leaves(
            "audit",
            ["Event", "Timestamp"],
            [["Monitor verification", "12 May 2026 16:42"]],
            scored_bindings={("Monitor verification", "Timestamp")},
            value_aliases={("Monitor verification", "Timestamp"): ["12 May 16:42"]},
        )

        timestamp = next(item for item in leaves if item["id"].endswith(".timestamp"))

        self.assertIn("12 May 2026 16:42", timestamp["evidencePolicy"]["value"])
        self.assertIn("12 May 16:42", timestamp["evidencePolicy"]["value"])

    def test_full_date_and_literal_yearless_source_form_are_equivalent_alternatives(self) -> None:
        expectation = "Monitor verification occurred on 12 May 2026 at 16:42."
        policy = {
            "type": "table_binding",
            "row": ["Monitor verification"],
            "column": ["Timestamp"],
            "value": ["12 May 2026 16:42", "12 May 16:42"],
        }

        self.assertEqual(evidence_policy_violations(expectation, policy), [])

    def test_yearless_date_without_a_full_date_alternative_is_incomplete(self) -> None:
        expectation = "Monitor verification occurred on 12 May 2026 at 16:42."
        policy = {
            "type": "table_binding",
            "row": ["Monitor verification"],
            "column": ["Timestamp"],
            "value": ["12 May 16:42"],
        }

        missing = {(item.signal.kind, item.signal.value) for item in evidence_policy_violations(expectation, policy)}
        self.assertIn(("date", "12 May 2026"), missing)

    def test_closed_world_table_keys_expand_to_the_full_gold_table(self) -> None:
        regions = [
            {
                "id": "register",
                "goldSection": "Register",
                "closedWorld": {"scope": "table_rows", "keys": ["E-01", "E-03"]},
                "leaves": [
                    {
                        "id": "e01.state",
                        "expectation": "E-01 State is OPEN.",
                        "evidencePolicy": {
                            "type": "table_binding",
                            "row": ["E-01"],
                            "column": ["State"],
                            "value": ["OPEN"],
                        },
                    },
                    {
                        "id": "e03.owner",
                        "expectation": "E-03 Owner is LS.",
                        "evidencePolicy": {
                            "type": "table_binding",
                            "row": ["E-03"],
                            "column": ["Owner"],
                            "value": ["LS"],
                        },
                    },
                ],
            }
        ]
        gold = (
            "# Fixture\n\n## Register\n\n"
            "| Exception | State | Owner |\n| --- | --- | --- |\n"
            "| E-01 | OPEN | AK |\n| E-02 | CLOSED | IP |\n| E-03 | WATCH | LS |\n"
        )

        finalize_fact_regions(regions, gold)

        self.assertEqual(regions[0]["closedWorld"]["keys"], ["E-01", "E-02", "E-03"])

    def test_extracts_every_high_signal_value_unit_identifier_and_qualifier(self) -> None:
        expectation = (
            "PFOA uses 13C8-PFOA, RT 4.41 min, range 0.25-80 ng/L, "
            "and LOD/LOQ 0.08/0.25 ng/L."
        )

        signals = {(signal.kind, signal.value) for signal in extract_evidence_signals(expectation)}

        for expected in {
            ("identifier", "PFOA"),
            ("identifier", "13C8-PFOA"),
            ("identifier", "RT"),
            ("scalar", "4.41"),
            ("unit", "min"),
            ("scalar", "0.25"),
            ("scalar", "80"),
            ("unit", "ng/L"),
            ("identifier", "LOD/LOQ"),
            ("scalar", "0.08"),
        }:
            self.assertIn(expected, signals)

    def test_explicit_policy_must_guarantee_every_expected_signal(self) -> None:
        expectation = "PFOA has response ratio 0.077 at 1 ng/L."
        policy = {"type": "lexical", "allOf": [["PFOA"], ["0.077"], ["ng/L"]]}

        missing = {(item.signal.kind, item.signal.value) for item in evidence_policy_violations(expectation, policy)}

        self.assertIn(("scalar", "1"), missing)

    def test_one_of_several_required_values_is_not_complete(self) -> None:
        expectation = "Recoveries are 96.0% and 98.0%."
        policy = {"type": "lexical", "allOf": [["96.0%", "98.0%"], ["recoveries"]]}

        missing = {(item.signal.kind, item.signal.value) for item in evidence_policy_violations(expectation, policy)}

        self.assertIn(("scalar", "96.0"), missing)
        self.assertIn(("scalar", "98.0"), missing)

    def test_equivalent_formatting_alternatives_remain_complete(self) -> None:
        expectation = "The level is 1 ng/L."
        policy = {
            "type": "lexical",
            "allOf": [["1 ng/L", "1ng/L"], ["level"]],
        }

        self.assertEqual(evidence_policy_violations(expectation, policy), [])

    def test_separate_groups_require_both_values(self) -> None:
        expectation = "Recoveries are 96.0% and 98.0%."
        policy = {
            "type": "lexical",
            "allOf": [["96.0%"], ["98.0%"], ["recoveries"]],
        }

        self.assertEqual(evidence_policy_violations(expectation, policy), [])

    def test_same_polarity_paraphrases_pass_but_opposite_polarity_fails(self) -> None:
        expectation = "The exception is open."
        faithful = {"type": "lexical", "allOf": [["unresolved", "outstanding"]]}
        opposite = {"type": "lexical", "allOf": [["resolved", "closed"]]}

        self.assertEqual(evidence_policy_violations(expectation, faithful), [])
        missing = evidence_policy_violations(expectation, opposite)
        self.assertEqual([(item.signal.kind, item.signal.value) for item in missing], [("qualifier", "open")])

    def test_comma_separated_identifiers_are_not_treated_as_number_format_aliases(self) -> None:
        expectation = "For 01,02,04, Decision is Release."
        policy = {
            "type": "table_binding",
            "row": ["01,02,04"],
            "column": ["Decision"],
            "value": ["Release"],
        }

        self.assertEqual(evidence_policy_violations(expectation, policy), [])

    def test_auto_policy_never_drops_a_gold_unsupported_signal(self) -> None:
        item = leaf("curve", "PFOA has response ratio 0.077 at 1 ng/L.")
        regions = [{"id": "r", "goldSection": "Curve", "leaves": [item]}]
        gold = "# Fixture\n\n## Curve\n\nPFOA response ratio is 0.077.\n"

        with self.assertRaisesRegex(ValueError, r"curve.*1"):
            finalize_fact_regions(regions, gold)

    def test_auto_policy_keeps_more_than_four_required_signals(self) -> None:
        expectation = "PFOA values are 1, 2, 3, 4, and 5 ng/L."
        item = leaf("series", expectation)
        regions = [{"id": "r", "goldSection": "Series", "leaves": [item]}]
        gold = f"# Fixture\n\n## Series\n\n{expectation}\n"

        finalize_fact_regions(regions, gold)

        self.assertEqual(evidence_policy_violations(expectation, item["evidencePolicy"]), [])
        self.assertGreater(len(item["evidencePolicy"]["allOf"]), 4)


if __name__ == "__main__":
    unittest.main()
