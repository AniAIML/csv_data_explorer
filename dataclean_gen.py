import streamlit as st
import pandas as pd
import numpy as np
import io

# ─────────────────────────────────────────────────────────────────
#  PAGE SETUP
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Cleaning App",
    page_icon="🧹",
    layout="wide"
)

st.title("🧹 General-Purpose Data Cleaning App")
st.caption("Upload any CSV and clean it step by step — missing values, wrong types, "
           "outliers, inconsistent categories, and duplicates.")
st.divider()

# ─────────────────────────────────────────────────────────────────
#  SIDEBAR – INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 How to Use This App")
    st.markdown("""
    1. **Upload** any CSV file
    2. **View** the raw data and its problems
    3. **Apply** each cleaning step — every step adapts to *your* columns
    4. **Download** the cleaned dataset
    """)
    st.divider()
    st.markdown("**What this app detects automatically:**")
    st.markdown("""
    - ❌ Missing values
    - ❌ Columns that are numbers stored as text
    - ❌ Outliers / out-of-range values (via IQR)
    - ❌ Inconsistent text categories (spacing, capitalisation)
    - ❌ Duplicate rows
    """)
    st.divider()
    st.markdown("**Settings**")
    numeric_detect_threshold = st.slider(
        "Min %% of non-null values that must look numeric to treat a column as numeric",
        min_value=50, max_value=100, value=90, step=5
    ) / 100
    iqr_multiplier = st.slider(
        "Outlier sensitivity (IQR multiplier — lower = stricter)",
        min_value=1.0, max_value=3.0, value=1.5, step=0.1
    )

# ─────────────────────────────────────────────────────────────────
#  FILE UPLOAD
# ─────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("📂 Upload a CSV file", type=["csv"])

if uploaded_file is None:
    st.info("👆 Please upload a CSV file to get started.")
    st.stop()

try:
    df_raw = pd.read_csv(uploaded_file)
except Exception as e:
    st.error(f"Could not read this file as CSV: {e}")
    st.stop()

if df_raw.empty:
    st.warning("The uploaded file has no rows.")
    st.stop()

df = df_raw.copy()

# ─────────────────────────────────────────────────────────────────
#  STEP 0 – RAW DATA
# ─────────────────────────────────────────────────────────────────
st.header("Step 0 — Raw Data (as uploaded)")
st.markdown(f"**{df.shape[0]} rows × {df.shape[1]} columns**")
st.dataframe(df_raw, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Total Rows", df.shape[0])
col2.metric("Total Columns", df.shape[1])
col3.metric("Total Missing Values", int(df.isnull().sum().sum()))

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 1 – FIND MISSING VALUES
# ─────────────────────────────────────────────────────────────────
st.header("Step 1 — Find Missing Values")
st.markdown("""
**What is a missing value?**
A missing value means a cell has no data — shown as `NaN` (Not a Number) by Pandas.
We use `df.isnull().sum()` to count missing values in each column.
""")
st.code("df.isnull().sum()", language="python")

missing = df.isnull().sum().reset_index()
missing.columns = ["Column", "Missing Count"]
missing["% Missing"] = (missing["Missing Count"] / len(df) * 100).round(1)
missing["Has Missing?"] = missing["Missing Count"].apply(lambda x: "⚠️ Yes" if x > 0 else "✅ No")
st.dataframe(missing, use_container_width=True, hide_index=True)

if df.isnull().any(axis=1).any():
    st.markdown("**Rows containing at least one missing value:**")
    st.dataframe(df[df.isnull().any(axis=1)], use_container_width=True)
else:
    st.write("No missing values found. 🎉")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 2 – DETECT & FIX DATA TYPES (auto-detect numeric-looking columns)
# ─────────────────────────────────────────────────────────────────
st.header("Step 2 — Fix Data Types")
st.markdown("""
**Why does data type matter?**
Pandas reads every column from CSV as text unless it *clearly* looks like a number.
A column with even one stray value like `"abc"` gets stored as text for the whole column.

This app scans every column: if at least the chosen percentage of its non-empty values
can be converted to a number, the whole column is treated as numeric — and the few
invalid entries become `NaN` instead of crashing anything.
""")

st.code("""
for col in df.columns:
    converted = pd.to_numeric(df[col], errors='coerce')
    pct_numeric = converted.notna().mean()
    if pct_numeric >= threshold:
        df[col] = converted   # column becomes numeric; bad values become NaN
""", language="python")

numeric_cols = []
type_report = []
for col in df.columns:
    converted = pd.to_numeric(df[col], errors='coerce')
    non_null_original = df[col].notna().sum()
    pct_numeric = converted.notna().sum() / non_null_original if non_null_original > 0 else 0

    if pct_numeric >= numeric_detect_threshold:
        newly_invalid = int(((df[col].notna()) & (converted.isna())).sum())
        df[col] = converted
        numeric_cols.append(col)
        type_report.append([col, "Numeric", f"{pct_numeric*100:.0f}%", newly_invalid])
    else:
        type_report.append([col, "Text / Category", f"{pct_numeric*100:.0f}%", 0])

type_df = pd.DataFrame(type_report, columns=["Column", "Detected Type", "%% Numeric-looking", "Invalid values → NaN"])
st.dataframe(type_df, use_container_width=True, hide_index=True)
st.success(f"✅ Detected {len(numeric_cols)} numeric column(s): {', '.join(numeric_cols) if numeric_cols else '(none)'}")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 3 – FIX OUT-OF-RANGE VALUES (IQR-based outlier detection)
# ─────────────────────────────────────────────────────────────────
st.header("Step 3 — Fix Out-of-Range Values (Outliers)")
st.markdown(f"""
**What counts as out-of-range here?**
Since every dataset has different valid ranges, this app uses the
**IQR (Interquartile Range) method**: for each numeric column it computes the
25th and 75th percentiles, and flags any value that falls far outside that range
(using a multiplier of **{iqr_multiplier}**, adjustable in the sidebar) as an outlier.

Outliers are replaced with `NaN` so they can be handled like any other missing value.
""")

st.code("""
Q1 = df[col].quantile(0.25)
Q3 = df[col].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - multiplier * IQR
upper = Q3 + multiplier * IQR
df.loc[(df[col] < lower) | (df[col] > upper), col] = None
""", language="python")

outlier_report = []
outlier_mask_any = pd.Series(False, index=df.index)

if numeric_cols:
    for col in numeric_cols:
        col_data = df[col]
        if col_data.notna().sum() < 4:
            continue  # not enough data to compute a meaningful IQR
        Q1 = col_data.quantile(0.25)
        Q3 = col_data.quantile(0.75)
        IQR = Q3 - Q1
        if IQR == 0:
            continue
        lower = Q1 - iqr_multiplier * IQR
        upper = Q3 + iqr_multiplier * IQR
        mask = col_data.notna() & ((col_data < lower) | (col_data > upper))
        outlier_mask_any = outlier_mask_any | mask
        outlier_report.append([col, round(lower, 2), round(upper, 2), int(mask.sum())])
        df.loc[mask, col] = None

    if outlier_report:
        st.markdown("**Valid range used per column, and outliers found:**")
        st.dataframe(
            pd.DataFrame(outlier_report, columns=["Column", "Lower bound", "Upper bound", "Outliers found"]),
            use_container_width=True, hide_index=True
        )
        if outlier_mask_any.any():
            st.markdown("**Rows that had at least one outlier (values shown before removal):**")
            st.dataframe(df_raw.loc[outlier_mask_any], use_container_width=True)
        st.success("✅ Out-of-range values replaced with NaN.")
    else:
        st.write("No numeric columns had enough variation to flag outliers.")
else:
    st.write("No numeric columns detected — skipping outlier check.")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 4 – FIX INCONSISTENT CATEGORIES (text columns)
# ─────────────────────────────────────────────────────────────────
st.header("Step 4 — Fix Inconsistent Categories")
st.markdown("""
**What is an inconsistent category?**
The same category written in different ways — e.g. `Male`, `male`, `MALE `, are the
same thing but Pandas treats them as different values.

For every text column, this app strips extra whitespace and standardises capitalisation
(`Title Case`). You can also mark specific columns as **restricted categories** and set
which values are valid — anything else becomes `NaN`.
""")

text_cols = [c for c in df.columns if c not in numeric_cols]

st.code("""
df[col] = df[col].astype(str).str.strip().str.title()

# Optional: restrict to a known set of valid categories
df.loc[~df[col].isin(valid_values), col] = None
""", language="python")

if text_cols:
    for col in text_cols:
        # only touch columns that actually contain string-like data
        df[col] = df[col].where(df[col].isna(), df[col].astype(str).str.strip().str.title())
        df[col] = df[col].replace({"Nan": None, "None": None, "": None})

    restrict_col = st.selectbox(
        "Optional: pick a column to restrict to specific valid categories (e.g. Gender)",
        ["(none)"] + text_cols
    )

    if restrict_col != "(none)":
        st.markdown(f"**Values in `{restrict_col}` before restricting:**")
        st.dataframe(
            df[restrict_col].value_counts(dropna=False).reset_index().rename(
                columns={restrict_col: "Value", "count": "Count"}
            ),
            use_container_width=True, hide_index=True
        )
        options = sorted([v for v in df[restrict_col].dropna().unique()])
        valid_values = st.multiselect(
            f"Which values of `{restrict_col}` are valid? (unselected values become NaN)",
            options=options, default=options
        )
        df.loc[~df[restrict_col].isin(valid_values), restrict_col] = None

        st.markdown(f"**Values in `{restrict_col}` after restricting:**")
        st.dataframe(
            df[restrict_col].value_counts(dropna=False).reset_index().rename(
                columns={restrict_col: "Value", "count": "Count"}
            ),
            use_container_width=True, hide_index=True
        )

    st.success(f"✅ Standardised spacing/capitalisation for {len(text_cols)} text column(s).")
else:
    st.write("No text columns detected — skipping category cleanup.")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 5 – HANDLE REMAINING MISSING VALUES
# ─────────────────────────────────────────────────────────────────
st.header("Step 5 — Handle Remaining Missing Values")
st.markdown("""
After Steps 2–4, more `NaN`s may exist (from replacing bad data). Now decide how to
handle them.

- **Fill numeric columns with mean/median**, drop rows still missing key text columns
- **Drop any row** with a missing value
- **Drop columns** that are mostly empty, then fill/drop the rest
""")

missing_now = df.isnull().sum()
missing_now = missing_now[missing_now > 0]
if not missing_now.empty:
    st.markdown("**Columns still having missing values:**")
    st.dataframe(
        missing_now.reset_index().rename(columns={"index": "Column", 0: "Missing Count"}),
        use_container_width=True, hide_index=True
    )
else:
    st.write("No missing values remain. 🎉")

fill_method = st.radio(
    "How should remaining numeric NaNs be filled?",
    ["Mean", "Median", "Don't fill (leave as NaN)"],
    index=0, horizontal=True
)

key_cols = st.multiselect(
    "Which column(s) are essential — drop a row if any of these are missing?",
    options=list(df.columns),
    default=[c for c in text_cols if c] [:1]  # sensible default: first text column, e.g. an ID/Name
)

drop_all_na = st.checkbox("Instead, just drop ANY row with a missing value (overrides the above)")

st.code("""
# Fill numeric NaNs
for col in numeric_cols:
    df[col] = df[col].fillna(df[col].mean())   # or .median()

# Drop rows missing essential columns
df = df.dropna(subset=key_cols)

# OR: drop every row with any missing value
df = df.dropna()
""", language="python")

rows_before = len(df)

if drop_all_na:
    df = df.dropna()
else:
    if fill_method == "Mean":
        for col in numeric_cols:
            df[col] = df[col].fillna(round(df[col].mean(), 2)) if df[col].notna().any() else df[col]
    elif fill_method == "Median":
        for col in numeric_cols:
            df[col] = df[col].fillna(round(df[col].median(), 2)) if df[col].notna().any() else df[col]
    if key_cols:
        df = df.dropna(subset=key_cols)

st.success(f"✅ Done! Rows before: **{rows_before}**  →  Rows after: **{len(df)}**")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 6 – REMOVE DUPLICATE ROWS
# ─────────────────────────────────────────────────────────────────
st.header("Step 6 — Remove Duplicate Rows")
st.markdown("""
Duplicate rows (identical across every column) usually indicate a data entry or
export error. We use `df.duplicated()` to find and remove them.
""")
st.code("df = df.drop_duplicates()", language="python")

dupe_count = int(df.duplicated().sum())
if dupe_count > 0:
    st.markdown(f"**Found {dupe_count} duplicate row(s):**")
    st.dataframe(df[df.duplicated(keep=False)], use_container_width=True)
    df = df.drop_duplicates()
    st.success(f"✅ Removed {dupe_count} duplicate row(s).")
else:
    st.write("No exact duplicate rows found.")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  STEP 7 – RESET INDEX
# ─────────────────────────────────────────────────────────────────
st.header("Step 7 — Reset the Index")
st.markdown("""
After dropping rows, the row numbers (index) will have gaps like 0, 2, 5, 7…
`df.reset_index(drop=True)` renumbers them cleanly from 0.
""")
st.code("df = df.reset_index(drop=True)", language="python")
df = df.reset_index(drop=True)
st.success("✅ Index reset.")

st.divider()

# ─────────────────────────────────────────────────────────────────
#  FINAL – CLEAN DATASET
# ─────────────────────────────────────────────────────────────────
st.header("✅ Final Clean Dataset")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows (clean)", df.shape[0])
c2.metric("Columns", df.shape[1])
c3.metric("Missing Values", int(df.isnull().sum().sum()))
c4.metric("Rows removed", df_raw.shape[0] - df.shape[0])

st.dataframe(df, use_container_width=True)

st.markdown("### Before vs After Cleaning")
summary = pd.DataFrame({
    "Metric": [
        "Total Rows",
        "Missing Values",
        "Numeric Columns Detected",
        "Outliers Fixed",
        "Duplicate Rows Removed",
    ],
    "Before Cleaning": [
        df_raw.shape[0],
        int(df_raw.isnull().sum().sum()),
        "—",
        "—",
        "—",
    ],
    "After Cleaning": [
        df.shape[0],
        int(df.isnull().sum().sum()),
        f"{len(numeric_cols)} → {', '.join(numeric_cols) if numeric_cols else 'none'}",
        f"{int(outlier_mask_any.sum())} value(s) replaced" if numeric_cols else "n/a",
        f"{dupe_count} row(s) removed",
    ],
})
st.dataframe(summary, use_container_width=True, hide_index=True)

st.divider()

# ─────────────────────────────────────────────────────────────────
#  DOWNLOAD
# ─────────────────────────────────────────────────────────────────
st.subheader("⬇️ Download the Clean Dataset")

csv_buffer = io.StringIO()
df.to_csv(csv_buffer, index=False)
csv_bytes = csv_buffer.getvalue().encode()

out_name = uploaded_file.name.rsplit(".", 1)[0] + "_clean.csv"

st.download_button(
    label=f"⬇️ Download {out_name}",
    data=csv_bytes,
    file_name=out_name,
    mime="text/csv",
)

st.caption("General-Purpose Data Cleaning App  |  Streamlit + Pandas")