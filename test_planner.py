"""Unit tests for planner.py.

Run from the project folder with:
    python -m unittest test_planner.py
"""

import unittest

from planner import CATEGORIES, DESTINATIONS, cheapest_trip, estimate, search


class PlannerTests(unittest.TestCase):
    """Tests for the cost estimate and the destination search."""

    def setUp(self):
        """Create default search criteria: 2 adults, 3 nights, one hotel room, USD."""
        self.criteria = {
            "nights": 3,
            "travelers": 2,
            "rooms": 1,
            "rate": 1,
            "lodging": "Hotel",
            "budget": 10000,
            "region": "Anywhere",
            "city": "Anywhere",
            "types": [],
            "nightly": 0,
            "limits": dict.fromkeys(CATEGORIES, 0),
        }

    def test_total_is_sum_of_categories(self):
        """The total equals the sum of all categories, and flights are per adult."""
        result = estimate(DESTINATIONS[0], self.criteria)  # Rome

        self.assertEqual(result["total"], sum(result["costs"].values()))
        self.assertEqual(result["costs"]["Flights"], 680)  # 340 USD x 2 adults

    def test_budget_too_low_returns_nothing(self):
        """A tiny budget leaves no matching destinations."""
        self.criteria["budget"] = 1

        self.assertEqual(search(self.criteria), [])

    def test_region_filter(self):
        """Filtering by region returns only destinations from that region."""
        self.criteria["region"] = "Europe"
        results = search(self.criteria)

        self.assertTrue(all(result["region"] == "Europe" for result in results))

    def test_category_limit(self):
        """A very low category limit filters out every destination."""
        self.criteria["limits"]["Flights"] = 1

        self.assertEqual(search(self.criteria), [])

    def test_cheapest_trip_ignores_budget(self):
        """cheapest_trip still finds a destination when the budget is too low."""
        self.criteria["budget"] = 1
        cheapest = cheapest_trip(self.criteria)

        self.assertIsNotNone(cheapest)
        all_totals = [estimate(d, self.criteria)["total"] for d in DESTINATIONS]
        self.assertEqual(cheapest["total"], min(all_totals))


if __name__ == "__main__":
    unittest.main()
