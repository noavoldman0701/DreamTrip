"""DreamTrip - a Streamlit travel budget planner.

Pages:
    Home    - search form: budget, travelers, dates, filters and limits
    Explore - matching destinations as cards, plus a map
    Compare - side-by-side cost table and chart for chosen destinations
    Budget  - full cost breakdown for one destination

Run from the project folder with:
    python -m streamlit run app.py
"""

from datetime import date, timedelta
from urllib.parse import urlencode

import pandas as pd
import plotly.express as px
import streamlit as st

import ui
from planner import CATEGORIES, DESTINATIONS, cheapest_trip, exchange_rates, search

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAGES = ["Home", "Explore", "Compare", "Budget"]

# Material icon for each page, used in the sidebar and the top menu.
PAGE_ICONS = {
    "Home": ":material/home:",
    "Explore": ":material/explore:",
    "Compare": ":material/balance:",
    "Budget": ":material/donut_large:",
}

CURRENCIES = ["ILS", "USD", "EUR"]

# Chart colors, one per cost category (matches the theme in .streamlit/config.toml).
CHART_COLORS = ["#B77C90", "#D7A5AD", "#C4AB90", "#A58A9B", "#E6C7B5"]

LODGING_TYPES = ["Hotel", "Apartment", "Hostel", "Resort"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def go_to(page_name):
    """Switch to another page. Used by the sidebar buttons."""
    st.session_state.page = page_name


def sync_top_menu():
    """Switch page when the top menu changes (ignore a click that clears it)."""
    if st.session_state.top_menu:
        st.session_state.page = st.session_state.top_menu


def money(value, currency):
    """Format an amount with its currency, e.g. 'ILS 6,000'."""
    return f"{currency} {value:,.0f}"


def cost_chart(result):
    """Build a donut chart of the cost per category for one destination."""
    fig = px.pie(
        names=list(result["costs"]),
        values=list(result["costs"].values()),
        hole=0.65,
        color_discrete_sequence=CHART_COLORS,
    )
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def booking_links(result, criteria):
    """Show buttons that open flight and accommodation searches for a destination."""
    flight_query = {
        "q": f"Flights Tel Aviv to {result['city']} "
             f"{criteria['start']} return {criteria['end']}"
    }
    st.link_button(
        "Search flights on Google",
        "https://www.google.com/search?" + urlencode(flight_query),
    )

    hotel_query = {
        "ss": f"{result['city']}, {result['country']}",
        "checkin": criteria["start"],
        "checkout": criteria["end"],
        "group_adults": criteria["travelers"],
        "no_rooms": criteria["rooms"],
    }
    st.link_button(
        "Search accommodation on Booking.com",
        "https://www.booking.com/searchresults.html?" + urlencode(hotel_query),
    )


def show_trip_summary(criteria):
    """Show a one-line summary of the current search under the page title."""
    st.caption(
        f"{criteria['travelers']} adults • {criteria['nights']} nights • "
        f"{criteria['start']} to {criteria['end']} • "
        f"Budget {money(criteria['budget'], criteria['currency'])}  \n"
        "Prices are sample estimates, not booking quotes. Flight schedule, baggage, "
        "airline, hotel rating and location are unverified preferences."
    )


def find_result(results, city):
    """Return the search result for the given city."""
    return next(result for result in results if result["city"] == city)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def show_home_page():
    """Show the hero and the search form, then save the criteria and results."""
    ui.hero()

    rates, source = exchange_rates()
    rates_missing = "ILS" not in rates

    with st.form("trip"):
        # --- Row 1: budget and travelers ------------------------------------
        ui.form_section("Budget & travelers")
        col_budget, col_currency, col_adults, col_rooms = st.columns([2, 1, 1, 1])
        with col_budget:
            budget = st.number_input(
                "Total budget", min_value=1.0, value=20000.0, step=500.0
            )
        with col_currency:
            currency = st.selectbox("Currency", CURRENCIES)
        with col_adults:
            travelers = st.number_input("Adults", 1, 12, 2)
        with col_rooms:
            rooms = st.number_input("Rooms", 1, 12, 1)

        # --- Row 2: dates and stay ------------------------------------------
        ui.form_section("Dates & stay")
        col_dates, col_mode, col_nights, col_lodging = st.columns([2, 1, 1, 1])
        with col_dates:
            dates = st.date_input(
                "Departure and return / flexible window",
                (date.today() + timedelta(days=14), date.today() + timedelta(days=21)),
                min_value=date.today(),
            )
        with col_mode:
            mode = st.selectbox("Date flexibility", ["Exact dates", "Flexible window"])
        with col_nights:
            flexible_nights = st.number_input(
                "Nights", 1, 30, 4, help="Used only with a flexible window."
            )
        with col_lodging:
            lodging = st.selectbox("Accommodation type", LODGING_TYPES)

        # --- Row 3: where ---------------------------------------------------
        ui.form_section("Where to")
        col_region, col_city, col_types = st.columns([1, 1, 2])
        with col_region:
            regions = sorted({d["region"] for d in DESTINATIONS})
            region = st.selectbox("Region", ["Anywhere"] + regions)
        with col_city:
            cities = sorted(d["city"] for d in DESTINATIONS)
            city = st.selectbox("Destination", ["Anywhere"] + cities)
        with col_types:
            all_types = sorted({t for d in DESTINATIONS for t in d["types"]})
            types = st.multiselect("Vacation types", all_types, placeholder="Any type")

        # --- Advanced filters -----------------------------------------------
        # Only the spending limits and the nightly price affect the estimate.
        # The rest are saved as preferences, because there is no live flight
        # or hotel data to check them against.
        with st.expander("Advanced filters"):
            st.caption(
                "Category limits are totals for all travelers. Zero means no separate limit."
            )
            limits = {}
            for col, category in zip(st.columns(len(CATEGORIES)), CATEGORIES):
                with col:
                    limits[category] = st.number_input(
                        category, min_value=0.0, value=0.0, step=100.0
                    )

            col_left, col_mid, col_right = st.columns(3)
            with col_left:
                st.selectbox("Departure airport", ["TLV (Tel Aviv)"])  # Only option for now.
                stops = st.selectbox("Flight stops", ["Any", "Direct only", "At most one stop"])
                baggage = st.selectbox("Baggage", ["Any", "Cabin bag", "Checked bag"])
            with col_mid:
                hours = st.multiselect(
                    "Preferred flight times", ["Morning", "Afternoon", "Evening", "Night"]
                )
                airlines = st.text_input("Preferred airlines (optional)")
            with col_right:
                stars = st.selectbox("Minimum hotel stars", ["Any", "3+", "4+", "5"])
                location = st.selectbox(
                    "Location", ["Any", "City center", "Near airport", "Beach"]
                )
                nightly = st.number_input(
                    "Max room price per night (0 = any)", min_value=0.0, value=0.0
                )

            # The exchange-rate service failed: let the user enter a rate by hand.
            manual_rate = 1.0
            if rates_missing:
                manual_rate = st.number_input(
                    "Manual exchange rate (ILS or EUR per 1 USD)",
                    min_value=0.01, value=1.0, step=0.01,
                )

        st.caption(source)
        submitted = st.form_submit_button(
            "Find My Trip", type="primary", icon=":material/flight_takeoff:",
            use_container_width=True,
        )

    if not submitted:
        return

    # --- Validate the input -------------------------------------------------
    if len(dates) != 2 or dates[1] <= dates[0]:
        st.error("Select a valid date range.")
        return

    if rooms > travelers:
        st.error("Rooms cannot exceed travelers.")
        return

    if mode == "Flexible window" and (dates[1] - dates[0]).days < flexible_nights:
        st.error("The date window is shorter than the trip.")
        return

    # --- Run the search -----------------------------------------------------
    rate = rates.get(currency, manual_rate)

    start = dates[0]
    if mode == "Exact dates":
        end = dates[1]
    else:
        # Flexible window: use the first possible departure date.
        end = start + timedelta(days=flexible_nights)

    criteria = {
        "currency": currency,
        "rate": rate,
        "budget": budget,
        "travelers": travelers,
        "rooms": rooms,
        "region": region,
        "city": city,
        "types": types,
        "start": start,
        "end": end,
        "nights": (end - start).days,
        "limits": limits,
        "lodging": lodging,
        "nightly": nightly,
        "preferences": {
            "stops": stops,
            "baggage": baggage,
            "hours": hours,
            "airlines": airlines,
            "stars": stars,
            "location": location,
        },
    }

    st.session_state.criteria = criteria
    st.session_state.results = search(criteria)

    results = st.session_state.results
    if results:
        st.success(f"Found {len(results)} estimated matches.")
        st.button(
            "View destinations", type="primary", icon=PAGE_ICONS["Explore"],
            on_click=go_to, args=("Explore",),
        )
    else:
        # No match: explain why and suggest what to change.
        cheapest = cheapest_trip(criteria)
        if cheapest is None:
            st.warning("No destinations match the selected region, destination and types.")
        else:
            st.warning(
                "No destinations fit your budget and limits. The cheapest match is "
                f"{cheapest['city']} at about {money(cheapest['total'], currency)}. "
                "Try a higher budget, fewer nights or travelers, a cheaper accommodation "
                "type, or remove the category and nightly limits."
            )
    st.warning(
        "Flight and hotel preferences are recorded but cannot be verified without "
        "live inventory. Flexible dates use the first possible departure; "
        "no live date optimization is performed."
    )


def show_explore_page(results, criteria):
    """Show matching destinations as cards (3 per row) and on a map."""
    currency = criteria["currency"]
    ui.page_header(
        "Explore Destinations",
        f"{len(results)} destinations found within your budget",
        "explore",
    )
    show_trip_summary(criteria)

    order = st.selectbox("Sort by", ["Lowest cost", "Highest cost", "Destination name"])
    if order == "Destination name":
        ordered = sorted(results, key=lambda r: r["city"])
    else:
        ordered = sorted(results, key=lambda r: r["total"], reverse=order == "Highest cost")

    # Show the cards in rows of 3.
    for i in range(0, len(ordered), 3):
        row = ordered[i:i + 3]
        for col, result in zip(st.columns(3), row):
            with col, st.container(border=True):
                st.subheader(f"{result['city']}, {result['country']}")
                st.caption(" / ".join(result["types"]))

                st.metric("Estimated total", money(result["total"], currency))
                # Share of the budget used (capped at 100%).
                st.progress(min(1, result["total"] / criteria["budget"]))

                st.plotly_chart(
                    cost_chart(result),
                    use_container_width=True,
                    key="pie" + result["city"],
                )
                remaining = criteria["budget"] - result["total"]
                st.caption("Remaining: " + money(remaining, currency))
                booking_links(result, criteria)

    st.subheader("Destination map")
    st.map(pd.DataFrame(ordered)[["lat", "lon"]])


def show_compare_page(results, criteria):
    """Compare up to 5 destinations in a table and a stacked bar chart."""
    ui.page_header(
        "Compare Destinations", "Compare costs, categories and budget usage", "compare"
    )
    show_trip_summary(criteria)

    cities = [r["city"] for r in results]
    chosen = st.multiselect(
        "Select destinations",
        cities,
        default=cities[:3],
        max_selections=5,
    )
    selected = [r for r in results if r["city"] in chosen]
    if not selected:
        return

    # Table: one column per destination, one row per category.
    table = pd.DataFrame({
        r["city"]: {
            **r["costs"],
            "Total": r["total"],
            "Remaining": criteria["budget"] - r["total"],
        }
        for r in selected
    })
    st.dataframe(table.style.format("{:,.0f}"), use_container_width=True)

    # Bar chart: each bar is a destination, split by category.
    chart_data = pd.DataFrame([
        {"Destination": r["city"], "Category": category, "Cost": cost}
        for r in selected
        for category, cost in r["costs"].items()
    ])
    fig = px.bar(
        chart_data,
        x="Destination",
        y="Cost",
        color="Category",
        color_discrete_sequence=CHART_COLORS,
    )
    st.plotly_chart(fig, use_container_width=True)


def show_budget_page(results, criteria):
    """Show the full cost breakdown for one chosen destination."""
    currency = criteria["currency"]
    ui.page_header(
        "Budget Breakdown", "Detailed cost breakdown for your selected destination", "budget"
    )
    show_trip_summary(criteria)

    city = st.selectbox("Destination", [r["city"] for r in results])
    result = find_result(results, city)

    # Summary numbers
    col_budget, col_cost, col_left = st.columns(3)
    col_budget.metric("Budget", money(criteria["budget"], currency))
    col_cost.metric("Estimated cost", money(result["total"], currency))
    col_left.metric("Remaining", money(criteria["budget"] - result["total"], currency))

    # Chart and table side by side
    col_chart, col_table = st.columns(2)

    with col_chart:
        st.plotly_chart(cost_chart(result), use_container_width=True)

    with col_table:
        rows = []
        for category, cost in result["costs"].items():
            limit = criteria["limits"][category]
            rows.append({
                "Category": category,
                "Estimated cost": money(cost, currency),
                "Limit": money(limit, currency) if limit else "None",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)

    booking_links(result, criteria)


# ---------------------------------------------------------------------------
# App layout and navigation
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="DreamTrip",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.load_styles()

# Keep the last search and the current page between reruns.
if "results" not in st.session_state:
    st.session_state.results = []
if "criteria" not in st.session_state:
    st.session_state.criteria = None
if "page" not in st.session_state:
    st.session_state.page = "Home"


# --- Sidebar menu -----------------------------------------------------------
ui.sidebar_logo()
for name in PAGES:
    st.sidebar.button(
        name,
        key=f"side_{name}",
        icon=PAGE_ICONS[name],
        type="primary" if st.session_state.page == name else "secondary",
        on_click=go_to,
        args=(name,),
        use_container_width=True,
    )
st.sidebar.divider()
st.sidebar.caption(
    "Travel cost estimates are illustrative. No live flight or hotel inventory is connected."
)
ui.sidebar_landmark()

# --- Top menu ---------------------------------------------------------------
# Both menus read and write the same st.session_state.page, so they always
# show the same page. The value is set before the widget is drawn.
st.session_state.top_menu = st.session_state.page
st.segmented_control(
    "Pages",
    PAGES,
    format_func=lambda name: f"{PAGE_ICONS[name]} {name}",
    key="top_menu",
    on_change=sync_top_menu,
    label_visibility="collapsed",
)

page = st.session_state.page

if page == "Home":
    show_home_page()
else:
    # Explore, Compare and Budget need a search from the Home page first.
    criteria = st.session_state.criteria
    results = st.session_state.results

    if not criteria:
        st.info("Start with a search on Home.")
        st.button("Go to search", icon=PAGE_ICONS["Home"], on_click=go_to, args=("Home",))
        st.stop()

    if not results:
        st.warning(
            "No destinations meet your estimated budget and selected filters. "
            "Adjust your search on Home."
        )
        st.button("Adjust search", icon=PAGE_ICONS["Home"], on_click=go_to, args=("Home",))
        st.stop()

    if page == "Explore":
        show_explore_page(results, criteria)
    elif page == "Compare":
        show_compare_page(results, criteria)
    else:
        show_budget_page(results, criteria)
