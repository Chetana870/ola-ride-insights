"""Step 1: Load, explore, clean the OLA July 2024 dataset and save cleaned CSV."""
import pandas as pd

RAW = "/mnt/user-data/uploads/1794727776609_OLA_DataSet.xlsx"
OUT = "/mnt/user-data/outputs/ola_clean.csv"

# 'July' is the real data; Sheet1 is a scratch pivot, Sheet2 is vehicle -> icon URL
df = pd.read_excel(RAW, sheet_name="July")

# ---- 1. Basic checks ---------------------------------------------------
print(df.shape)
print(df.isna().sum())
print("duplicate Booking_IDs:", df["Booking_ID"].duplicated().sum())

# ---- 2. Standardise column names & text -------------------------------
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
df = df.rename(columns={
    "canceled_rides_by_customer": "cancel_reason_customer",
    "canceled_rides_by_driver": "cancel_reason_driver",
    "incomplete_rides": "is_incomplete",
    "incomplete_rides_reason": "incomplete_reason",
})
df = df.drop(columns=["time"])  # duplicates the timestamp inside 'date'
for c in df.select_dtypes(include=["object", "string"]).columns:
    df[c] = df[c].str.strip()

# ---- 3. Types -----------------------------------------------------------
# 'date' already carries the full timestamp
df["booking_datetime"] = pd.to_datetime(df["date"])
df["booking_date"] = df["booking_datetime"].dt.date
df = df.drop(columns=["date", "vehicle_images"])  # keep icon URLs in Sheet2 for Power BI

# ---- 4. Missing values: they are *structural*, not errors --------------
# Ratings / payment / TAT exist only when the ride was a Success.
# Reasons exist only for the matching cancellation / incomplete case.
# Keep them NULL (correct for SQL averages); only label the reason columns.
df["cancel_reason_customer"] = df["cancel_reason_customer"].fillna("Not Applicable")
df["cancel_reason_driver"] = df["cancel_reason_driver"].fillna("Not Applicable")
df["incomplete_reason"] = df["incomplete_reason"].fillna("Not Applicable")
# is_incomplete: NaN for non-success rows -> leave NULL

# ---- 5. Derived features -----------------------------------------------
dt = df["booking_datetime"].dt
df["hour"] = dt.hour
df["day_of_week"] = dt.day_name()
df["day"] = dt.day
df["time_of_day"] = pd.cut(
    df["hour"], bins=[-1, 5, 11, 16, 20, 23],
    labels=["Night", "Morning", "Afternoon", "Evening", "Late Night"])
df["is_success"] = (df["booking_status"] == "Success").astype(int)
df["is_completed"] = ((df["booking_status"] == "Success") & (df["is_incomplete"] == "No")).astype(int)

# ---- 6. Sanity assertions ----------------------------------------------
assert df["booking_id"].is_unique
assert df.loc[df.is_success == 0, "ride_distance"].eq(0).all()

df.to_csv(OUT, index=False)
print("saved", OUT, df.shape)
