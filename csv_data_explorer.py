"""
📊 SMART SALES ANALYTICS DASHBOARD
====================================
Built on top of: CSV Data Explorer (Project 4)

Concepts used:
- File Upload & Validation
- Dataset Info / Summary Statistics
- KPI Cards
- Interactive Filters (Region, City, Category, Product, Rep, Payment, Delivery, Month)
- Sales / Customer / Product / Payment / Delivery / Profit Dashboards
- Correlation Heatmap
- Sortable / Searchable Data Table
- Multi-format Download (CSV, Excel, JSON)
- Light / Dark Theme Toggle
- Sidebar Navigation
"""

import io
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Smart Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def find_col(df, candidates):
    """Case/space/underscore-insensitive column matcher.
    Returns the actual column name in df that best matches one of the
    candidate names, or None if nothing matches."""
    if df is None:
        return None

    norm_map = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}

    for cand in candidates:
        key = cand.lower().replace(" ", "").replace("_", "")
        if key in norm_map:
            return norm_map[key]
    return None


def fmt_inr(value):
    """Format a number as an Indian Rupee currency string."""
    try:
        return f"₹{value:,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def safe_sum(df, col):
    return float(df[col].sum()) if col and col in df.columns else 0.0


def safe_mean(df, col):
    return float(df[col].mean()) if col and col in df.columns and len(df) else 0.0


def missing_col_notice(label):
    st.info(f"'{label}' column not found in this dataset — section skipped.")


def apply_theme(theme):
    """Very small CSS tweak to fake a dark theme (works without restart,
    unlike st.set_page_config which only accepts a fixed theme)."""
    if theme == "Dark":
        st.markdown(
            """
            <style>
            .stApp { background-color: #0e1117; color: #fafafa; }
            section[data-testid="stSidebar"] { background-color: #161a23; }
            </style>
            """,
            unsafe_allow_html=True,
        )


def pie_chart(labels, values, title):
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title(title)
    ax.axis("equal")
    st.pyplot(fig)


def corr_heatmap(df, cols, title="Correlation Heatmap"):
    corr = df[cols].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title(title)
    st.pyplot(fig)


def to_excel_bytes(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return buffer.getvalue()


# ============================================================
# SIDEBAR: THEME + NAVIGATION
# ============================================================
st.sidebar.title("📊 Sales Dashboard")

theme = st.sidebar.radio("Theme", ["Light", "Dark"], horizontal=True)
apply_theme(theme)

st.sidebar.markdown("---")

PAGES = [
    "🏠 Home",
    "📁 Upload",
    "📊 Dashboard",
    "📈 Analytics",
    "👤 Customers",
    "📦 Products",
    "💳 Payments",
    "🚚 Delivery",
    "⬇ Download",
]
page = st.sidebar.radio("Navigate", PAGES)

st.title("📊 Smart Sales Analytics Dashboard")
st.write("Upload a CSV file to instantly explore, filter and visualize your sales data.")

# ============================================================
# SECTION 1: FILE UPLOAD
# ============================================================
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is None:
    st.info("Waiting for a CSV file to be uploaded...")
    st.stop()

try:
    df_raw = pd.read_csv(uploaded_file)
    st.success(f"✅ File uploaded successfully: **{uploaded_file.name}**")
    st.caption(
        f"Filename: {uploaded_file.name}  |  "
        f"File size: {uploaded_file.size / 1024:.2f} KB"
    )
except Exception as e:
    st.error(f"❌ Could not read this file as a CSV: {e}")
    st.stop()

if df_raw.empty:
    st.warning("The uploaded CSV has no rows.")
    st.stop()

# ------------------------------------------------------------
# Basic data cleaning
# ------------------------------------------------------------
df = df_raw.copy()
df.columns = [c.strip() for c in df.columns]
df = df.drop_duplicates()
for c in df.select_dtypes(include="object").columns:
    df[c] = df[c].astype(str).str.strip()

# ------------------------------------------------------------
# Column detection (flexible to different CSV schemas)
# ------------------------------------------------------------
region_col = find_col(df, ["Region"])
city_col = find_col(df, ["City"])
category_col = find_col(df, ["Product_Category", "Category", "ProductCategory"])
product_col = find_col(df, ["Product_Name", "Product", "ProductName"])
rep_col = find_col(df, ["Sales_Rep", "SalesRep", "Sales Representative", "Employee", "Salesperson"])
payment_col = find_col(df, ["Payment_Mode", "PaymentMode", "Payment Method", "Payment"])
delivery_col = find_col(df, ["Delivery_Status", "DeliveryStatus", "Status"])
date_col = find_col(df, ["Date", "Order_Date", "OrderDate"])
month_col = find_col(df, ["Month"])
customer_col = find_col(df, ["Customer_Name", "Customer", "CustomerName"])
sales_col = find_col(df, ["Total_Sales", "Sales", "Amount", "Revenue"])
profit_col = find_col(df, ["Profit"])
discount_col = find_col(df, ["Discount"])
price_col = find_col(df, ["Unit_Price", "Price", "UnitPrice"])
qty_col = find_col(df, ["Quantity", "Qty"])
order_col = find_col(df, ["Order_ID", "OrderID", "Order Id", "Invoice", "Invoice_No"])

# Derive Month from a date column if there's no explicit Month column
if month_col is None and date_col is not None:
    try:
        df["_Month"] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%b")
        month_col = "_Month"
    except Exception:
        pass

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(include="object").columns.tolist()
all_cols = df.columns.tolist()

# ============================================================
# SECTION 6: SIDEBAR FILTERS
# ============================================================
st.sidebar.markdown("---")
st.sidebar.header("🔎 Filters")

filtered_df = df.copy()


def sidebar_multiselect(label, col):
    global filtered_df
    if col and col in df.columns:
        options = sorted(df[col].dropna().unique().tolist())
        chosen = st.sidebar.multiselect(label, options, default=options)
        filtered_df = filtered_df[filtered_df[col].isin(chosen)]


sidebar_multiselect("Region", region_col)
sidebar_multiselect("City", city_col)
sidebar_multiselect("Product Category", category_col)
sidebar_multiselect("Product Name", product_col)
sidebar_multiselect("Sales Representative", rep_col)
sidebar_multiselect("Payment Mode", payment_col)
sidebar_multiselect("Delivery Status", delivery_col)
sidebar_multiselect("Month", month_col)

# Date range filter (Industry-level enhancement)
if date_col:
    try:
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
        min_d, max_d = parsed_dates.min(), parsed_dates.max()
        if pd.notna(min_d) and pd.notna(max_d):
            date_range = st.sidebar.date_input(
                "Date range", value=(min_d.date(), max_d.date())
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                mask = (parsed_dates.dt.date >= start) & (parsed_dates.dt.date <= end)
                filtered_df = filtered_df[mask.reindex(filtered_df.index, fill_value=True)]
    except Exception:
        pass

# Generic single-column filter (kept from the original explorer)
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Generic Filter (any column)")
if all_cols:
    generic_col = st.sidebar.selectbox("Filter by any column", ["(none)"] + all_cols)
    if generic_col != "(none)":
        vals = df[generic_col].dropna().unique().tolist()
        if len(vals) <= 30:
            chosen_vals = st.sidebar.multiselect(f"Values of '{generic_col}'", vals, default=vals)
            filtered_df = filtered_df[filtered_df[generic_col].isin(chosen_vals)]
        else:
            st.sidebar.caption("Too many unique values — generic filter skipped.")

if filtered_df.empty:
    st.warning("No rows match the current filters. Try widening your filter selection.")
    st.stop()


# ============================================================
# PAGE: HOME
# ============================================================
if page == "🏠 Home":
    st.subheader("Welcome")
    st.write(
        "Use the sidebar to navigate between the Dashboard, Analytics, "
        "Customers, Products, Payments, Delivery and Download sections. "
        "Filters in the sidebar apply across every page."
    )

    # ---------------- Section 2: Dataset Information ----------------
    st.subheader("📋 Dataset Information")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Numeric Columns", len(numeric_cols))
    c4.metric("Categorical Columns", len(categorical_cols))
    c5.metric("Missing Values", int(df.isna().sum().sum()))

    # ---------------- Section 3: Data Preview ----------------
    st.subheader("👀 Data Preview")
    tab1, tab2, tab3 = st.tabs(["First 10 rows", "Last 10 rows", "Random 10 rows"])
    with tab1:
        st.dataframe(df.head(10), use_container_width=True)
    with tab2:
        st.dataframe(df.tail(10), use_container_width=True)
    with tab3:
        st.dataframe(df.sample(min(10, len(df))), use_container_width=True)

    # ---------------- Section 4: Dataset Summary ----------------
    st.subheader("🧾 Dataset Summary")
    with st.expander("describe()"):
        st.write(df.describe(include="all"))
    with st.expander("info()"):
        buf = io.StringIO()
        df.info(buf=buf)
        st.text(buf.getvalue())
    with st.expander("Data types"):
        st.write(df.dtypes.astype(str))
    with st.expander("Missing values per column"):
        st.write(df.isna().sum())
    with st.expander("Duplicate rows"):
        st.write(f"Duplicate rows found and removed during cleaning: {df_raw.shape[0] - df.shape[0]}")


# ============================================================
# PAGE: UPLOAD (recap of Section 1 + 2)
# ============================================================
elif page == "📁 Upload":
    st.subheader("📁 File Upload Details")
    c1, c2 = st.columns(2)
    c1.metric("Filename", uploaded_file.name)
    c2.metric("File size (KB)", f"{uploaded_file.size / 1024:.2f}")

    st.subheader("📋 Dataset Information")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Numeric Columns", len(numeric_cols))
    c4.metric("Categorical Columns", len(categorical_cols))
    c5.metric("Missing Values", int(df.isna().sum().sum()))

    st.subheader("👀 Data Preview")
    tab1, tab2, tab3 = st.tabs(["First 10 rows", "Last 10 rows", "Random 10 rows"])
    with tab1:
        st.dataframe(df.head(10), use_container_width=True)
    with tab2:
        st.dataframe(df.tail(10), use_container_width=True)
    with tab3:
        st.dataframe(df.sample(min(10, len(df))), use_container_width=True)


# ============================================================
# PAGE: DASHBOARD (KPI cards + Sales Dashboard + Correlation + Table)
# ============================================================
elif page == "📊 Dashboard":

    # ---------------- Section 5: KPI Cards ----------------
    st.subheader("📌 KPI Cards")
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    total_orders = (
        filtered_df[order_col].nunique() if order_col else len(filtered_df)
    )
    k1.metric("Total Orders", f"{total_orders:,}")
    k2.metric("Total Sales", fmt_inr(safe_sum(filtered_df, sales_col)))
    k3.metric("Total Profit", fmt_inr(safe_sum(filtered_df, profit_col)))
    k4.metric("Avg Discount", f"{safe_mean(filtered_df, discount_col):.2f}")
    k5.metric("Avg Unit Price", fmt_inr(safe_mean(filtered_df, price_col)))
    k6.metric("Total Quantity Sold", f"{safe_sum(filtered_df, qty_col):,.0f}")

    st.markdown("---")

    # ---------------- Section 7: Sales Dashboard ----------------
    st.subheader("📈 Sales Dashboard")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("**1. Sales by Region**")
        if region_col and sales_col:
            st.bar_chart(filtered_df.groupby(region_col)[sales_col].sum())
        else:
            missing_col_notice("Region / Total_Sales")

    with colB:
        st.markdown("**2. Sales by City**")
        if city_col and sales_col:
            st.bar_chart(filtered_df.groupby(city_col)[sales_col].sum())
        else:
            missing_col_notice("City / Total_Sales")

    st.markdown("**3. Monthly Sales Trend**")
    if month_col and sales_col:
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        trend = filtered_df.groupby(month_col)[sales_col].sum()
        trend = trend.reindex([m for m in month_order if m in trend.index]).dropna() \
            if set(trend.index).issubset(set(month_order)) else trend
        st.line_chart(trend)

        # Industry enhancement: month-over-month growth %
        if len(trend) > 1:
            growth = trend.pct_change().fillna(0) * 100
            st.caption("Month-over-month sales growth %:")
            st.dataframe(growth.round(2).rename("Growth %"))
    else:
        missing_col_notice("Month / Total_Sales")

    colC, colD = st.columns(2)

    with colC:
        st.markdown("**4. Profit by Region**")
        if region_col and profit_col:
            st.bar_chart(filtered_df.groupby(region_col)[profit_col].sum())
        else:
            missing_col_notice("Region / Profit")

    with colD:
        st.markdown("**5. Quantity Sold by Category**")
        if category_col and qty_col:
            st.bar_chart(filtered_df.groupby(category_col)[qty_col].sum())
        else:
            missing_col_notice("Product_Category / Quantity")

    colE, colF = st.columns(2)

    with colE:
        st.markdown("**6. Sales by Product Category**")
        if category_col and sales_col:
            grp = filtered_df.groupby(category_col)[sales_col].sum()
            pie_chart(grp.index, grp.values, "Sales by Category")
        else:
            missing_col_notice("Product_Category / Total_Sales")

    with colF:
        st.markdown("**7. Sales by Product Name**")
        if product_col and sales_col:
            grp = filtered_df.groupby(product_col)[sales_col].sum().sort_values()
            fig, ax = plt.subplots(figsize=(6, max(3, len(grp) * 0.3)))
            ax.barh(grp.index.astype(str), grp.values, color="#4C78A8")
            ax.set_xlabel("Total Sales")
            st.pyplot(fig)
        else:
            missing_col_notice("Product_Name / Total_Sales")

    # Top N selector (Industry enhancement)
    st.markdown("---")
    top_n = st.slider("Top N selector (for products / customers / reps below)", 3, 20, 5)

    colG, colH, colI = st.columns(3)

    with colG:
        st.markdown(f"**8. Top {top_n} Products**")
        if product_col and sales_col:
            top_products = (
                filtered_df.groupby(product_col)[sales_col].sum()
                .sort_values(ascending=False).head(top_n)
            )
            st.dataframe(top_products.rename("Total Sales").apply(fmt_inr))
        else:
            missing_col_notice("Product_Name / Total_Sales")

    with colH:
        st.markdown(f"**9. Top {top_n} Customers**")
        if customer_col and sales_col:
            top_customers = (
                filtered_df.groupby(customer_col)[sales_col].sum()
                .sort_values(ascending=False).head(top_n)
            )
            st.dataframe(top_customers.rename("Total Sales").apply(fmt_inr))
        else:
            missing_col_notice("Customer_Name / Total_Sales")

    with colI:
        st.markdown(f"**10. Top {top_n} Sales Representatives**")
        if rep_col and sales_col:
            top_reps = (
                filtered_df.groupby(rep_col)[sales_col].sum()
                .sort_values(ascending=False).head(top_n)
            )
            st.dataframe(top_reps.rename("Total Sales").apply(fmt_inr))
        else:
            missing_col_notice("Sales_Rep / Total_Sales")


# ============================================================
# PAGE: ANALYTICS (Profit dashboard + Correlation + Outliers)
# ============================================================
elif page == "📈 Analytics":

    # ---------------- Section 12: Profit Dashboard ----------------
    st.subheader("💹 Profit Dashboard")
    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown("**Profit by Region**")
        if region_col and profit_col:
            st.bar_chart(filtered_df.groupby(region_col)[profit_col].sum())
        else:
            missing_col_notice("Region / Profit")

    with colB:
        st.markdown("**Profit by Category**")
        if category_col and profit_col:
            st.bar_chart(filtered_df.groupby(category_col)[profit_col].sum())
        else:
            missing_col_notice("Product_Category / Profit")

    with colC:
        st.markdown("**Profit by Product**")
        if product_col and profit_col:
            top_profit = (
                filtered_df.groupby(product_col)[profit_col].sum()
                .sort_values(ascending=False).head(10)
            )
            st.bar_chart(top_profit)
        else:
            missing_col_notice("Product_Name / Profit")

    # Profit margin % (Industry enhancement)
    if sales_col and profit_col and safe_sum(filtered_df, sales_col) != 0:
        margin = safe_sum(filtered_df, profit_col) / safe_sum(filtered_df, sales_col) * 100
        st.metric("Overall Profit Margin (%)", f"{margin:.2f}%")

    # Average order value (Industry enhancement)
    if sales_col and (order_col or True):
        n_orders = filtered_df[order_col].nunique() if order_col else len(filtered_df)
        if n_orders:
            aov = safe_sum(filtered_df, sales_col) / n_orders
            st.metric("Average Order Value", fmt_inr(aov))

    st.markdown("---")

    # ---------------- Section 13: Correlation Analysis ----------------
    st.subheader("🔗 Correlation Analysis")
    corr_candidates = [qty_col, price_col, sales_col, profit_col, discount_col]
    corr_cols = [c for c in corr_candidates if c and c in filtered_df.columns]
    if len(corr_cols) >= 2:
        corr_heatmap(filtered_df, corr_cols)
    else:
        st.info("Not enough numeric columns (Quantity, Unit Price, Sales, Profit, Discount) found for a correlation heatmap.")

    # Outlier detection (Industry enhancement)
    st.markdown("---")
    st.subheader("🚨 Outlier Detection")
    if sales_col:
        q1, q3 = filtered_df[sales_col].quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr
        outliers = filtered_df[filtered_df[sales_col] > upper]
        st.caption(f"Rows with unusually high '{sales_col}' (above {fmt_inr(upper)}):")
        st.dataframe(outliers, use_container_width=True)
    else:
        missing_col_notice("Total_Sales")


# ============================================================
# PAGE: CUSTOMERS (Section 8)
# ============================================================
elif page == "👤 Customers":
    st.subheader("👤 Customer Dashboard")

    if customer_col and sales_col:
        agg = {sales_col: "sum"}
        if order_col:
            agg[order_col] = "nunique"

        cust = filtered_df.groupby(customer_col).agg(agg).rename(
            columns={sales_col: "Total Sales", order_col: "Total Orders"} if order_col
            else {sales_col: "Total Sales"}
        )
        if order_col is None:
            cust["Total Orders"] = filtered_df.groupby(customer_col).size()

        cust["Average Order Value"] = cust["Total Sales"] / cust["Total Orders"].replace(0, np.nan)
        cust = cust.sort_values("Total Sales", ascending=False).reset_index()

        search_term = st.text_input("🔍 Search Customer", "")
        display_cust = cust
        if search_term:
            display_cust = cust[
                cust[customer_col].str.contains(search_term, case=False, na=False)
            ]

        show = display_cust.copy()
        show["Total Sales"] = show["Total Sales"].apply(fmt_inr)
        show["Average Order Value"] = show["Average Order Value"].apply(fmt_inr)
        st.dataframe(show, use_container_width=True)

        if search_term and not display_cust.empty:
            row = display_cust.iloc[0]
            st.success(
                f"**{row[customer_col]}** — Orders: {int(row['Total Orders'])}, "
                f"Total Sales: {fmt_inr(row['Total Sales'] if isinstance(row['Total Sales'], (int, float)) else cust.loc[cust[customer_col]==row[customer_col],'Total Sales'].values[0])}"
            )
    else:
        missing_col_notice("Customer_Name / Total_Sales")


# ============================================================
# PAGE: PRODUCTS (Section 9)
# ============================================================
elif page == "📦 Products":
    st.subheader("📦 Product Dashboard")

    if product_col:
        agg = {}
        if qty_col:
            agg[qty_col] = "sum"
        if sales_col:
            agg[sales_col] = "sum"
        if profit_col:
            agg[profit_col] = "sum"

        if agg:
            prod = filtered_df.groupby(product_col).agg(agg).reset_index()
            rename_map = {}
            if qty_col:
                rename_map[qty_col] = "Total Quantity Sold"
            if sales_col:
                rename_map[sales_col] = "Revenue"
            if profit_col:
                rename_map[profit_col] = "Profit"
            prod = prod.rename(columns=rename_map).sort_values(
                "Revenue" if "Revenue" in rename_map.values() else prod.columns[1],
                ascending=False,
            )

            show = prod.copy()
            if "Revenue" in show.columns:
                show["Revenue"] = show["Revenue"].apply(fmt_inr)
            if "Profit" in show.columns:
                show["Profit"] = show["Profit"].apply(fmt_inr)
            st.dataframe(show, use_container_width=True)
        else:
            missing_col_notice("Quantity / Total_Sales / Profit")
    else:
        missing_col_notice("Product_Name")


# ============================================================
# PAGE: PAYMENTS (Section 10)
# ============================================================
elif page == "💳 Payments":
    st.subheader("💳 Payment Dashboard")
    if payment_col:
        counts = filtered_df[payment_col].value_counts()
        pie_chart(counts.index, counts.values, "Payment Mode Split")
        st.dataframe(counts.rename("Transactions"))
    else:
        missing_col_notice("Payment_Mode")


# ============================================================
# PAGE: DELIVERY (Section 11)
# ============================================================
elif page == "🚚 Delivery":
    st.subheader("🚚 Delivery Dashboard")
    if delivery_col:
        counts = filtered_df[delivery_col].value_counts()
        pie_chart(counts.index, counts.values, "Delivery Status Split")
        st.dataframe(counts.rename("Orders"))
    else:
        missing_col_notice("Delivery_Status")


# ============================================================
# PAGE: DOWNLOAD (Section 14 + 15)
# ============================================================
elif page == "⬇ Download":

    # ---------------- Section 14: Data Table ----------------
    st.subheader("🗂️ Filtered Data Table")

    search = st.text_input("🔍 Search across all columns")
    table_df = filtered_df
    if search:
        mask = filtered_df.apply(
            lambda row: row.astype(str).str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        table_df = filtered_df[mask]

    sort_col = st.selectbox("Sort by column", ["(none)"] + all_cols)
    if sort_col != "(none)":
        ascending = st.checkbox("Ascending", value=True)
        table_df = table_df.sort_values(sort_col, ascending=ascending)

    page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
    total_rows = len(table_df)
    total_pages = max(1, (total_rows - 1) // page_size + 1)
    page_num = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    start = (page_num - 1) * page_size
    end = start + page_size

    st.caption(f"Showing rows {start + 1}-{min(end, total_rows)} of {total_rows}")
    st.dataframe(table_df.iloc[start:end], use_container_width=True)

    st.markdown("---")

    # ---------------- Section 15: Download ----------------
    st.subheader("⬇ Download Filtered Data")

    d1, d2, d3 = st.columns(3)

    with d1:
        st.download_button(
            "Download as CSV",
            filtered_df.to_csv(index=False),
            file_name="filtered_data.csv",
            mime="text/csv",
        )

    with d2:
        st.download_button(
            "Download as Excel",
            to_excel_bytes(filtered_df),
            file_name="filtered_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with d3:
        st.download_button(
            "Download as JSON",
            json.dumps(filtered_df.to_dict(orient="records"), default=str, indent=2),
            file_name="filtered_data.json",
            mime="application/json",
        )
