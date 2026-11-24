"""Core trip-planning logic for DreamTrip.

This module holds the destination data, fetches currency exchange rates
and calculates estimated trip costs. It has no Streamlit code, so it can
be tested and reused on its own.
"""

from functools import lru_cache

import requests

# Cost categories, in the order they are shown in the app.
CATEGORIES = [
    "Flights",
    "Accommodation",
    "Food & Drinks",
    "Transportation",
    "Activities",
]

# Price multiplier for each accommodation type, relative to a standard hotel.
LODGING_FACTORS = {
    "Hotel": 1.0,
    "Apartment": 0.85,
    "Hostel": 0.55,
    "Resort": 1.4,
}

EXCHANGE_RATES_URL = "https://api.frankfurter.dev/v1/latest"

# Destination data.
# All prices are illustrative USD values, not collected market prices:
#   flight     - round-trip ticket per adult
#   room       - one room for one night
#   food, transport, activities - per person per day
_DESTINATION_ROWS = [
    # city, country, region, lat, lon,
    # flight, room, food, transport, activities, vacation types
    ("Rome", "Italy", "Europe", 41.90, 12.49,
     340, 120, 45, 12, 25, "City,Shopping,Culinary"),
    ("Paris", "France", "Europe", 48.86, 2.35,
     460, 170, 55, 15, 35, "City,Shopping,Culinary"),
    ("London", "UK", "Europe", 51.51, -0.13,
     450, 180, 55, 18, 35, "City,Shopping"),
    ("Athens", "Greece", "Europe", 37.98, 23.73,
     240, 90, 35, 10, 20, "City,Beach,Culinary"),
    ("Budapest", "Hungary", "Europe", 47.50, 19.04,
     270, 75, 30, 9, 20, "City,Culinary"),
    ("Barcelona", "Spain", "Europe", 41.39, 2.17,
     380, 130, 45, 12, 25, "City,Beach,Culinary"),
    ("Vienna", "Austria", "Europe", 48.21, 16.37,
     320, 110, 40, 12, 25, "City,Culinary"),
    ("Innsbruck", "Austria", "Europe", 47.27, 11.39,
     450, 140, 45, 20, 65, "Ski,Nature"),
    ("Larnaca", "Cyprus", "Europe", 34.92, 33.63,
     160, 85, 35, 12, 20, "Beach,Nature"),
    ("Dubai", "UAE", "Asia", 25.20, 55.27,
     420, 130, 45, 20, 40, "City,Shopping,Beach"),
    ("Bangkok", "Thailand", "Asia", 13.76, 100.50,
     850, 65, 25, 10, 25, "City,Culinary,Shopping"),
    ("Tokyo", "Japan", "Asia", 35.68, 139.69,
     1050, 120, 40, 15, 30, "City,Shopping,Culinary"),
    ("New York", "USA", "North America", 40.71, -74.01,
     1100, 220, 65, 18, 40, "City,Shopping"),
    ("Toronto", "Canada", "North America", 43.65, -79.38,
     1000, 150, 50, 15, 30, "City,Nature"),
    ("Cape Town", "South Africa", "Africa", -33.92, 18.42,
     950, 100, 35, 15, 35, "Nature,Beach"),
    ("Marrakesh", "Morocco", "Africa", 31.63, -8.00,
     550, 75, 25, 10, 20, "City,Culinary"),
    ("Buenos Aires", "Argentina", "South America", -34.60, -58.38,
     1450, 85, 35, 10, 25, "City,Culinary"),
    ("Rio de Janeiro", "Brazil", "South America", -22.91, -43.17,
     1400, 100, 35, 12, 30, "Beach,Nature"),
    ("Sydney", "Australia", "Oceania", -33.87, 151.21,
     1600, 150, 55, 15, 35, "City,Beach,Nature"),
]

# Convert each row into a dictionary that the rest of the app works with.
DESTINATIONS = [
    {
        "city": city,
        "country": country,
        "region": region,
        "lat": lat,
        "lon": lon,
        "flight": flight,
        "room": room,
        "food": food,
        "transport": transport,
        "activities": activities,
        "types": types.split(","),
    }
    for (city, country, region, lat, lon,
         flight, room, food, transport, activities, types) in _DESTINATION_ROWS
]


@lru_cache(maxsize=1)
def exchange_rates():
    """Fetch USD exchange rates for ILS and EUR from the Frankfurter API.

    The result is cached, so the API is called only once per app run.

    Returns:
        A tuple (rates, message):
        - rates: dict mapping a currency code to its value per 1 USD.
          Always contains "USD". Contains "ILS" and "EUR" only if the
          request succeeded.
        - message: a short note about the source of the rates, shown
          to the user.
    """
    try:
        response = requests.get(
            EXCHANGE_RATES_URL,
            params={"base": "USD", "symbols": "ILS,EUR"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        rates = {"USD": 1}
        for code, value in data["rates"].items():
            rates[code] = float(value)

        message = (
            f"Exchange rates: Frankfurter, reference date {data['date']} "
            "(not booking rates)."
        )
        return rates, message

    except (requests.RequestException, ValueError, KeyError, TypeError):
        # No network, a bad response or an unexpected format:
        # fall back to USD only and let the user enter a manual rate.
        return (
            {"USD": 1},
            "Exchange rates unavailable. USD or a manually entered rate may be used.",
        )


def estimate(destination, criteria):
    """Estimate the full trip cost for one destination.

    Args:
        destination: one item from DESTINATIONS.
        criteria: the user's search settings. Uses the keys
            "nights", "travelers", "rooms", "rate" and "lodging".

    Returns:
        A copy of the destination with three extra keys:
        - "costs": dict of cost per category (in the chosen currency)
        - "total": sum of all categories
        - "nightly": price of one room for one night
    """
    nights = criteria["nights"]
    travelers = criteria["travelers"]
    rooms = criteria["rooms"]
    rate = criteria["rate"]

    # A trip of N nights has N + 1 days of food, transport and activities.
    days = nights + 1

    nightly = destination["room"] * LODGING_FACTORS[criteria["lodging"]] * rate

    costs = {
        "Flights": destination["flight"] * travelers * rate,
        "Accommodation": nightly * nights * rooms,
        "Food & Drinks": destination["food"] * days * travelers * rate,
        "Transportation": destination["transport"] * days * travelers * rate,
        "Activities": destination["activities"] * days * travelers * rate,
    }

    return {
        **destination,
        "costs": costs,
        "total": sum(costs.values()),
        "nightly": nightly,
    }


def _matches_filters(destination, criteria):
    """Check the region, city and vacation-type filters for one destination."""
    if criteria["region"] != "Anywhere" and destination["region"] != criteria["region"]:
        return False

    if criteria["city"] != "Anywhere" and destination["city"] != criteria["city"]:
        return False

    # If vacation types were chosen, the destination must have at least one of them.
    if criteria["types"] and not set(criteria["types"]) & set(destination["types"]):
        return False

    return True


def _fits_budget(result, criteria):
    """Check the total budget, the nightly room limit and the category limits.

    A limit of 0 means "no limit".
    """
    if result["total"] > criteria["budget"]:
        return False

    if criteria["nightly"] and result["nightly"] > criteria["nightly"]:
        return False

    for category, limit in criteria["limits"].items():
        if limit and result["costs"][category] > limit:
            return False

    return True


def search(criteria):
    """Find every destination that matches the user's criteria.

    Args:
        criteria: the user's search settings (see the Home page in app.py).

    Returns:
        A list of estimate() results, sorted from cheapest to most expensive.
    """
    results = []

    for destination in DESTINATIONS:
        if not _matches_filters(destination, criteria):
            continue

        result = estimate(destination, criteria)
        if _fits_budget(result, criteria):
            results.append(result)

    return sorted(results, key=lambda result: result["total"])


def cheapest_trip(criteria):
    """Return the cheapest destination that matches the filters, ignoring all budgets.

    Used to tell the user how much budget they need when search() finds nothing.
    Returns None if no destination matches the region, city and type filters.
    """
    matching = [
        estimate(destination, criteria)
        for destination in DESTINATIONS
        if _matches_filters(destination, criteria)
    ]
    return min(matching, key=lambda result: result["total"], default=None)
