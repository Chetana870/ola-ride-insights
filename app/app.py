"""Ola Ride Insights - Streamlit app.

Reads from PostgreSQL (ola_db) when credentials are in .streamlit/secrets.toml,
otherwise falls back to data/ola_clean.csv so the app also runs when deployed.
"""
from pathlib import Path

import sqlite3
import warnings

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Ola Ride Insights", page_icon="🚖", layout="wide")

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / "ola_clean.csv"
SHOT_DIR = ROOT / "powerbi" / "screenshots"

# ---------------------------------------------------------------- queries
QUERIES = {
    "Q1. Retrieve all successful bookings": (
        "SELECT * FROM ola_rides WHERE booking_status = 'Success'", None),
    "Q2. Average ride distance per vehicle type": (
        """SELECT vehicle_type, ROUND(AVG(ride_distance), 2) AS avg_distance_km
           FROM ola_rides WHERE booking_status = 'Success'
           GROUP BY vehicle_type ORDER BY avg_distance_km DESC""",
        "vehicle_type"),
    "Q3. Total rides cancelled by customers": (
        """SELECT COUNT(*) AS cancelled_by_customers
           FROM ola_rides WHERE booking_status = 'Canceled by Customer'""", None),
    "Q4. Top 5 customers by number of rides": (
        """SELECT customer_id, COUNT(*) AS total_rides FROM ola_rides
           GROUP BY customer_id ORDER BY total_rides DESC, customer_id LIMIT 5""",
        "customer_id"),
    "Q5. Driver cancellations: personal & car related issues": (
        """SELECT COUNT(*) AS driver_cancel_personal_car FROM ola_rides
           WHERE booking_status = 'Canceled by Driver'
             AND cancel_reason_driver = 'Personal & Car related issue'""", None),
    "Q6. Max and min driver rating for Prime Sedan": (
        """SELECT MAX(driver_ratings) AS max_rating, MIN(driver_ratings) AS min_rating
           FROM ola_rides
           WHERE vehicle_type = 'Prime Sedan' AND driver_ratings IS NOT NULL""", None),
    "Q7. Rides paid via UPI": (
        "SELECT * FROM ola_rides WHERE payment_method = 'UPI'", None),
    "Q8. Average customer rating per vehicle type": (
        """SELECT vehicle_type, ROUND(AVG(customer_rating), 2) AS avg_customer_rating
           FROM ola_rides WHERE customer_rating IS NOT NULL
           GROUP BY vehicle_type ORDER BY avg_customer_rating DESC""",
        "vehicle_type"),
    "Q9. Total booking value of successful rides": (
        """SELECT SUM(booking_value) AS total_booking_value
           FROM ola_rides WHERE booking_status = 'Success'""", None),
    "Q10. Incomplete rides and the reason": (
        """SELECT booking_id, customer_id, vehicle_type, incomplete_reason
           FROM ola_rides WHERE is_incomplete = 'Yes'""", None),
}


# ---------------------------------------------------------------- data layer
warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")


@st.cache_resource
def get_connection():
    """PostgreSQL if configured and reachable, else in-memory SQLite loaded from the CSV."""
    try:
        import psycopg2  # may be missing or blocked on some machines -> fall back

        pg = st.secrets["postgres"]
        conn = psycopg2.connect(
            host=pg["host"], port=int(pg.get("port", 5432)), dbname=pg["database"],
            user=pg["user"], password=pg["password"], connect_timeout=5)
        conn.autocommit = True
        return conn, "PostgreSQL"
    except Exception:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        pd.read_csv(CSV_PATH).to_sql("ola_rides", conn, index=False)
        return conn, "CSV (SQLite)"


@st.cache_data(show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    conn, _ = get_connection()
    return pd.read_sql_query(sql, conn)


@st.cache_data(show_spinner="Loading data...")
def load_rides() -> pd.DataFrame:
    df = run_query("SELECT * FROM ola_rides")
    df["booking_date"] = pd.to_datetime(df["booking_date"]).dt.date
    return df


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🚖 Ola Ride Insights")
page = st.sidebar.radio("Go to", ["SQL Insights", "Ride Explorer", "Power BI Dashboard"])
st.sidebar.caption(f"Data source: {get_connection()[1]}")


# ---------------------------------------------------------------- page 1
if page == "SQL Insights":
    st.title("SQL Insights")
    choice = st.selectbox("Choose a question", list(QUERIES))
    sql, chart_index = QUERIES[choice]
    sql = "\n".join(line.strip() for line in sql.strip().splitlines())
    with st.expander("Show SQL", expanded=True):
        st.code(sql, language="sql")
    result = run_query(sql)
    st.caption(f"{len(result):,} row(s)")
    if len(result) == 1 and len(result.columns) <= 2 and chart_index is None:
        cols = st.columns(len(result.columns))
        for col, name in zip(cols, result.columns):
            col.metric(name.replace("_", " ").title(), f"{result.iloc[0][name]:,}")
    else:
        st.dataframe(result.head(1000), use_container_width=True, hide_index=True)
        if len(result) > 1000:
            st.caption("Showing the first 1,000 rows.")
    if chart_index:
        st.bar_chart(result.set_index(chart_index))


# ---------------------------------------------------------------- page 2
elif page == "Ride Explorer":
    st.title("Ride Explorer")
    df = load_rides()

    with st.sidebar:
        st.header("Filters")
        vehicles = st.multiselect("Vehicle type", sorted(df["vehicle_type"].unique()))
        statuses = st.multiselect("Booking status", sorted(df["booking_status"].unique()))
        payments = st.multiselect("Payment method",
                                  sorted(df["payment_method"].dropna().unique()))
        dmin, dmax = df["booking_date"].min(), df["booking_date"].max()
        date_range = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
        search = st.text_input("Search Booking ID / Customer ID")

    f = df
    if vehicles:
        f = f[f["vehicle_type"].isin(vehicles)]
    if statuses:
        f = f[f["booking_status"].isin(statuses)]
    if payments:
        f = f[f["payment_method"].isin(payments)]
    if len(date_range) == 2:
        f = f[(f["booking_date"] >= date_range[0]) & (f["booking_date"] <= date_range[1])]
    if search.strip():
        s = search.strip().upper()
        f = f[f["booking_id"].str.upper().str.contains(s, regex=False)
              | f["customer_id"].str.upper().str.contains(s, regex=False)]

    ok = f[f["booking_status"] == "Success"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rides", f"{len(f):,}")
    c2.metric("Success rate", f"{len(ok) / len(f):.1%}" if len(f) else "-")
    c3.metric("Revenue (successful)", f"₹{ok['booking_value'].sum():,.0f}")
    c4.metric("Avg distance (km)", f"{ok['ride_distance'].mean():.1f}" if len(ok) else "-")

    left, right = st.columns(2)
    left.subheader("Rides by status")
    left.bar_chart(f["booking_status"].value_counts())
    right.subheader("Rides per day")
    right.line_chart(f.groupby("booking_date").size())

    st.subheader("Matching rides")
    st.dataframe(f.drop(columns=["booking_datetime"]).head(1000),
                 use_container_width=True, hide_index=True)
    st.caption("Showing the first 1,000 matching rows.")
    st.download_button("Download filtered data (CSV)", f.to_csv(index=False).encode(),
                       "ola_filtered.csv", "text/csv")


# ---------------------------------------------------------------- page 3
else:
    st.title("Power BI Dashboard")
    try:
        url = st.secrets["powerbi_url"]
    except Exception:
        url = ""
    if url:
        components.iframe(url, height=720, scrolling=False)
    else:
        order = ["overall", "vehicle", "revenue", "cancellation", "rating"]
        shots = sorted(SHOT_DIR.glob("*.png")) if SHOT_DIR.exists() else []
        shots.sort(key=lambda p: next((i for i, k in enumerate(order) if k in p.stem.lower()), 99))
        if shots:
            st.caption("Dashboard pages (screenshots from Power BI Desktop)")
            tabs = st.tabs([p.stem.replace("_screenshot", "").replace("_", " ").title()
                            for p in shots])
            for tab, shot in zip(tabs, shots):
                with tab:
                    st.image(str(shot), use_container_width=True)
        else:
            st.warning("Put your dashboard screenshots in `powerbi/screenshots/`.")
