import streamlit as st
import json
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Product Quality Intelligence", layout="wide")

st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.8rem;
            padding-bottom: 0.8rem;
        }

        section[data-testid="stSidebar"] div[data-testid="stFileUploader"] small {
            display: none;
        }

        section[data-testid="stSidebar"] div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
            display: none;
        }

        section[data-testid="stSidebar"] div[data-testid="stFileUploader"] section button + div {
            display: none;
        }

        section[data-testid="stSidebar"] div[data-testid="stFileUploader"] > label {
            display: none;
        }

        section[data-testid="stSidebar"] div[data-testid="stFileUploader"] button {
            width: 100%;
            min-height: 2.2rem;
            padding: 0.25rem 0.5rem;
        }

        section[data-testid="stSidebar"] .upload-label {
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 0.1rem;
            margin-top: 0.2rem;
        }

        section[data-testid="stSidebar"] .status-box {
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 0.5rem;
            padding: 0.45rem 0.65rem;
            margin-top: 0.4rem;
            background: rgba(250, 250, 250, 0.6);
        }

        section[data-testid="stSidebar"] .status-row {
            font-size: 0.82rem;
            margin: 0.12rem 0;
            line-height: 1.2;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Load uploaded JSON helpers
# ---------------------------
def load_uploaded_json(uploaded_file, expected_use_case):
    if uploaded_file is None:
        return None

    try:
        data = json.load(uploaded_file)
    except Exception:
        st.sidebar.error(f"Could not read the uploaded JSON for '{expected_use_case}'.")
        return None

    actual_use_case = data.get("use_case")

    if actual_use_case != expected_use_case:
        st.sidebar.error(
            f"Uploaded file for '{expected_use_case}' has use_case='{actual_use_case}'. "
            f"Please upload the correct summary file."
        )
        return None

    return data

def render_upload_status_box(status_items):
    rows = []
    for label, data in status_items:
        if data is not None:
            rows.append(f"<div class='status-row'>🟢 <b>{label}</b></div>")
        else:
            rows.append(f"<div class='status-row'>🔴 <b>{label}</b></div>")

    st.sidebar.markdown(
        "<div class='status-box'>" + "".join(rows) + "</div>",
        unsafe_allow_html=True
    )

# ---------------------------
# Utility Functions
# ---------------------------
def avg_attribute_score(data):
    if not data:
        return None
    attributes = data.get("attributes_analysis", {}).get("attributes", [])
    if not attributes:
        return 0.0
    return sum(a.get("score", 0) for a in attributes) / len(attributes)

def get_reviews_score(data, sentiment_weight, rating_weight):
    if not data:
        return None, None, None

    sentiment_score = data.get("overall_analysis", {}).get("overall_sentiment", {}).get("score", 0) * 100
    rating_mean = data.get("overall_analysis", {}).get("overall_rating", {}).get("mean", 0)
    rating_score = (rating_mean / 5) * 100

    total_weight = sentiment_weight + rating_weight
    if total_weight == 0:
        combined_score = 0.0
    else:
        combined_score = (
            (sentiment_weight * sentiment_score) +
            (rating_weight * rating_score)
        ) / total_weight

    return round(combined_score, 1), round(sentiment_score, 1), round(rating_score, 1)

def format_metric_value(value):
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        return round(value, 1)
    return value

def render_no_data_message(label):
    st.info(f"No {label} summary uploaded or available.")

def render_action_plan(data):
    st.subheader("Action Plan")

    if not data:
        st.info("No action plan available.")
        return

    action_plan = data.get("action_plan", {})
    summary_items = action_plan.get("summary", [])
    recommendation_items = action_plan.get("recommendations", [])
    overall_items = data.get("overall_analysis", {}).get("action_plan", {}).get("items", [])

    if action_plan.get("rationale"):
        st.caption(action_plan["rationale"])
    elif data.get("overall_analysis", {}).get("action_plan", {}).get("rationale"):
        st.caption(data["overall_analysis"]["action_plan"]["rationale"])

    action_rows = []

    if summary_items:
        action_rows = [
            {
                "Item": item.get("item", ""),
                "Rationale": item.get("rationale", "")
            }
            for item in summary_items
        ]
    elif overall_items:
        action_rows = [
            {
                "Item": item.get("item", ""),
                "Rationale": item.get("rationale", "")
            }
            for item in overall_items
        ]
    elif recommendation_items:
        action_rows = [
            {
                "Item": item.get("recommendation", ""),
                "Rationale": item.get("rationale", ""),
                "Category": item.get("category", ""),
                "Priority": item.get("priority", ""),
                "Confidence": item.get("confidence", "")
            }
            for item in recommendation_items
        ]

    if action_rows:
        st.dataframe(pd.DataFrame(action_rows), use_container_width=True)
    else:
        st.info("No action plan available.")

def render_attributes_analysis(data):
    st.subheader("Attributes Analysis")

    if not data:
        st.info("No attributes analysis available.")
        return

    attributes = data.get("attributes_analysis", {}).get("attributes", [])
    if not attributes:
        st.info("No attributes analysis available.")
        return

    df_attr = pd.DataFrame([
        {
            "Attribute": a.get("attribute", ""),
            "Score": a.get("score", 0),
            "Sentiment": a.get("sentiment", ""),
            "Summary": a.get("summary_text", "")
        }
        for a in attributes
    ])

    st.plotly_chart(
        px.bar(df_attr, x="Attribute", y="Score", color="Sentiment", title="Attribute Scores"),
        use_container_width=True
    )
    st.dataframe(df_attr, use_container_width=True)

def render_reviews_rating_stats(data):
    st.subheader("Rating Stats")

    if not data:
        st.info("No rating stats available.")
        return

    overall_rating = data.get("overall_analysis", {}).get("overall_rating", {})
    dist = overall_rating.get("distribution", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Average Rating", round(overall_rating.get("mean", 0), 2))
    c2.metric("Review Count", overall_rating.get("count", 0))
    c3.metric(
        "Sentiment Score",
        round(data.get("overall_analysis", {}).get("overall_sentiment", {}).get("score", 0) * 100, 1)
    )

    if dist:
        df_dist = pd.DataFrame({"Rating": list(dist.keys()), "Count": list(dist.values())})
        df_dist["Rating"] = pd.to_numeric(df_dist["Rating"])
        df_dist = df_dist.sort_values("Rating")

        st.plotly_chart(
            px.bar(df_dist, x="Rating", y="Count", title="Review Rating Distribution"),
            use_container_width=True
        )

def render_recommendations(data):
    st.subheader("Recommendations")

    if not data:
        st.info("No recommendations available.")
        return

    recommendations = (
        data.get("overall_analysis", {}).get("recommendations", []) or
        data.get("action_plan", {}).get("recommendations", [])
    )

    if not recommendations:
        st.info("No recommendations available.")
        return

    df_recommendations = pd.DataFrame([
        {
            "Category": item.get("category", ""),
            "Priority": item.get("priority", ""),
            "Recommendation": item.get("recommendation", ""),
            "Rationale": item.get("rationale", ""),
            "Related Attributes": ", ".join(item.get("related_attributes", []) or []),
            "Confidence": item.get("confidence", ""),
            "Timeline": item.get("timeline", ""),
            "Expected Impact": item.get("expected_impact", "")
        }
        for item in recommendations
    ])

    st.dataframe(df_recommendations, use_container_width=True)

def extract_attributes(data, label):
    if not data:
        return pd.DataFrame(columns=["Source", "Attribute", "Score"])

    return pd.DataFrame([
        {
            "Source": label,
            "Attribute": a.get("attribute", ""),
            "Score": a.get("score", 0)
        }
        for a in data.get("attributes_analysis", {}).get("attributes", [])
    ])

# ---------------------------
# Sidebar Uploads
# ---------------------------
st.sidebar.header("Upload Summary Files")

col1, col2 = st.sidebar.columns(2)

with col1:
    st.markdown("<div class='upload-label'>Reviews</div>", unsafe_allow_html=True)
    reviews_file = st.file_uploader(
        "Reviews Summary JSON",
        type=["json"],
        key="reviews_file",
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<div class='upload-label'>Complaints</div>", unsafe_allow_html=True)
    complaints_file = st.file_uploader(
        "Complaints Summary JSON",
        type=["json"],
        key="complaints_file",
        label_visibility="collapsed"
    )

col3, col4 = st.sidebar.columns(2)

with col3:
    st.markdown("<div class='upload-label'>Quality Panel</div>", unsafe_allow_html=True)
    quality_panel_file = st.file_uploader(
        "Quality Panel Summary JSON",
        type=["json"],
        key="quality_panel_file",
        label_visibility="collapsed"
    )

with col4:
    st.markdown("<div class='upload-label'>PAC/CTH</div>", unsafe_allow_html=True)
    pac_file = st.file_uploader(
        "PAC/CTH Summary JSON",
        type=["json"],
        key="pac_file",
        label_visibility="collapsed"
    )

col5, col6 = st.sidebar.columns(2)

with col5:
    st.markdown("<div class='upload-label'>MQR</div>", unsafe_allow_html=True)
    mqr_file = st.file_uploader(
        "MQR Summary JSON",
        type=["json"],
        key="mqr_file",
        label_visibility="collapsed"
    )

with col6:
    st.markdown("<div class='upload-label'>QRPMU</div>", unsafe_allow_html=True)
    qrpmu_file = st.file_uploader(
        "QRPMU Summary JSON",
        type=["json"],
        key="qrpmu_file",
        label_visibility="collapsed"
    )

reviews = load_uploaded_json(reviews_file, "reviews")
complaints = load_uploaded_json(complaints_file, "complaints")
quality_panel = load_uploaded_json(quality_panel_file, "quality_panel")
pac = load_uploaded_json(pac_file, "pac")
mqr = load_uploaded_json(mqr_file, "mqr")
qrpmu = load_uploaded_json(qrpmu_file, "qrpmu")

st.sidebar.subheader("Upload Status")
render_upload_status_box([
    ("Reviews", reviews),
    ("Complaints", complaints),
    ("Quality Panel", quality_panel),
    ("PAC/CTH", pac),
    ("MQR", mqr),
    ("QRPMU", qrpmu)
])

if not any([reviews, complaints, quality_panel, pac, mqr, qrpmu]):
    st.title("📊 Product Quality Summary Dashboard")
    st.info("Upload one or more summary JSON files from the sidebar to view the dashboard.")
    st.stop()

# ---------------------------
# Sidebar Weights
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.header("Reviews Score Weights")

default_review_sentiment_weight = 0.50
default_review_rating_weight = 0.50

review_sentiment_weight = st.sidebar.number_input(
    "Review Sentiment Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_review_sentiment_weight,
    step=0.05
)
review_rating_weight = st.sidebar.number_input(
    "Average Rating Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_review_rating_weight,
    step=0.05
)

review_score_total_weight = review_sentiment_weight + review_rating_weight

st.sidebar.header("Quality Score Weights")

default_reviews_weight = 0.20
default_complaints_weight = 0.20
default_panel_weight = 0.15
default_pac_weight = 0.15
default_mqr_weight = 0.15
default_qrpmu_weight = 0.15

reviews_weight = st.sidebar.number_input(
    "Reviews Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_reviews_weight,
    step=0.05
)
complaints_weight = st.sidebar.number_input(
    "Complaints Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_complaints_weight,
    step=0.05
)
panel_weight = st.sidebar.number_input(
    "Quality Panel Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_panel_weight,
    step=0.05
)
pac_weight = st.sidebar.number_input(
    "PAC Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_pac_weight,
    step=0.05
)
mqr_weight = st.sidebar.number_input(
    "MQR Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_mqr_weight,
    step=0.05
)
qrpmu_weight = st.sidebar.number_input(
    "QRPMU Weight",
    min_value=0.0,
    max_value=1.0,
    value=default_qrpmu_weight,
    step=0.05
)

# ---------------------------
# Score Calculation
# ---------------------------
reviews_score, reviews_sentiment_score, reviews_avg_rating_score = get_reviews_score(
    reviews,
    review_sentiment_weight,
    review_rating_weight
)

complaints_score = (
    complaints.get("overall_analysis", {}).get("overall_sentiment", {}).get("score", 0) * 100
    if complaints else None
)
panel_score = avg_attribute_score(quality_panel)
pac_score = avg_attribute_score(pac)
mqr_score = avg_attribute_score(mqr)
qrpmu_score = (
    qrpmu.get("overall_analysis", {}).get("overall_sentiment", {}).get("score", 0) * 100
    if qrpmu else None
)

available_components = []
if reviews_score is not None:
    available_components.append((reviews_weight, reviews_score))
if complaints_score is not None:
    available_components.append((complaints_weight, complaints_score))
if panel_score is not None:
    available_components.append((panel_weight, panel_score))
if pac_score is not None:
    available_components.append((pac_weight, pac_score))
if mqr_score is not None:
    available_components.append((mqr_weight, mqr_score))
if qrpmu_score is not None:
    available_components.append((qrpmu_weight, qrpmu_score))

available_total_weight = sum(weight for weight, _ in available_components)

if available_total_weight == 0:
    QCI = None
else:
    QCI = round(
        sum(weight * score for weight, score in available_components) / available_total_weight,
        1
    )

# ---------------------------
# Header
# ---------------------------
base_product_info = (
    (reviews or {}).get("product_info") or
    (complaints or {}).get("product_info") or
    (quality_panel or {}).get("product_info") or
    (pac or {}).get("product_info") or
    (mqr or {}).get("product_info") or
    (qrpmu or {}).get("product_info") or
    {}
)

product = base_product_info.get("product_name", "Unknown Product")
brand = base_product_info.get("product_brand", "Unknown Brand")
tpnb = base_product_info.get("product_id", "N/A")

st.title("📊 Product Quality Summary Dashboard")
st.subheader(f"{brand} – {product}")
st.caption(f"TPNB: {tpnb}")

if reviews is not None and abs(review_score_total_weight - 1.0) > 0.001:
    st.warning(
        f"Current review score weights sum to {review_score_total_weight:.2f}. "
        f"Review score is being normalized by total weight."
    )

configured_total_weight = (
    reviews_weight +
    complaints_weight +
    panel_weight +
    pac_weight +
    mqr_weight +
    qrpmu_weight
)
if available_total_weight > 0 and abs(available_total_weight - 1.0) > 0.001:
    st.warning(
        f"Configured weights for available datapoints sum to {available_total_weight:.2f}. "
        f"Quality score is being normalized using only uploaded datapoints."
    )
elif configured_total_weight > 0 and available_total_weight == 0:
    st.warning("No valid uploaded datapoints available for Quality score calculation.")

# ---------------------------
# Top KPIs
# ---------------------------
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Quality Score", format_metric_value(QCI))
c2.metric("Reviews Score", format_metric_value(reviews_score))
c3.metric("Complaints Score", format_metric_value(complaints_score))
c4.metric("Panel Score", format_metric_value(panel_score))
c5.metric("PAC Score", format_metric_value(pac_score))
c6.metric("MQR Score", format_metric_value(mqr_score))
c7.metric("QRPMU Score", format_metric_value(qrpmu_score))

# ---------------------------
# Tabs
# ---------------------------
tab_overall, tab_reviews, tab_complaints, tab_panel, tab_pac, tab_mqr, tab_qrpmu = st.tabs(
    [
        "📊 Overall Summary",
        "⭐ Reviews",
        "🛑 Complaints",
        "🧪 Quality Panel",
        "🧠 PAC/CTH",
        "📋 MQR",
        "📦 QRPMU"
    ]
)

# ============================
# OVERALL SUMMARY
# ============================
with tab_overall:
    st.header("Overall Quality Assessment")

    if QCI is None:
        st.subheader("Quality Score: N/A")
        st.info("Quality score cannot be calculated yet. Upload one or more valid summary files.")
    else:
        qci_band = (
            "✅ High confidence" if QCI >= 80 else
            "⚠️ Watch" if QCI >= 60 else
            "❗ Risk" if QCI >= 40 else
            "🚨 Critical"
        )
        st.subheader(f"Quality Score: {QCI} — {qci_band}")

    st.markdown("""
    **What this means:**
    The Quality Score combines customer sentiment, expert evaluation,
    and large-sample quality testing into a single, interpretable metric.
    """)

    df_all = pd.concat([
        extract_attributes(reviews, "Reviews"),
        extract_attributes(complaints, "Complaints"),
        extract_attributes(quality_panel, "Panel"),
        extract_attributes(pac, "PAC"),
        extract_attributes(mqr, "MQR"),
        extract_attributes(qrpmu, "QRPMU")
    ], ignore_index=True)

    if not df_all.empty:
        st.plotly_chart(
            px.bar(
                df_all,
                x="Attribute",
                y="Score",
                color="Source",
                barmode="group",
                title="Attribute Scores Across All Signals"
            ),
            use_container_width=True
        )
    else:
        st.info("No attribute-level comparison data available across the uploaded summaries.")

# ============================
# REVIEWS
# ============================
with tab_reviews:
    st.header("Customer Reviews")

    if not reviews:
        render_no_data_message("reviews")
    else:
        st.write(reviews.get("overall_analysis", {}).get("summary", ""))

        c1, c2, c3 = st.columns(3)
        c1.metric("Reviews Score", format_metric_value(reviews_score))
        c2.metric("Overall Sentiment Score", format_metric_value(reviews_sentiment_score))
        c3.metric("Average Rating Score", format_metric_value(reviews_avg_rating_score))

        render_action_plan(reviews)
        render_recommendations(reviews)
        render_attributes_analysis(reviews)
        render_reviews_rating_stats(reviews)

# ============================
# COMPLAINTS
# ============================
with tab_complaints:
    st.header("Customer Complaints")

    if not complaints:
        render_no_data_message("complaints")
    else:
        st.write(complaints.get("overall_analysis", {}).get("summary", ""))

        render_action_plan(complaints)
        render_recommendations(complaints)
        render_attributes_analysis(complaints)

# ============================
# QUALITY PANEL
# ============================
with tab_panel:
    st.header("Quality Panel Evaluation")

    if not quality_panel:
        render_no_data_message("quality panel")
    else:
        st.write(quality_panel.get("overall_analysis", {}).get("summary", ""))

        render_action_plan(quality_panel)
        render_recommendations(quality_panel)
        render_attributes_analysis(quality_panel)

# ============================
# PAC
# ============================
with tab_pac:
    st.header("PAC – Consumer Acceptance Testing")

    if not pac:
        render_no_data_message("PAC/CTH")
    else:
        st.write(pac.get("overall_analysis", {}).get("summary", ""))

        render_action_plan(pac)
        render_recommendations(pac)
        render_attributes_analysis(pac)

# ============================
# MQR
# ============================
with tab_mqr:
    st.header("MQR Summary")

    if not mqr:
        render_no_data_message("MQR")
    else:
        st.write(mqr.get("overall_analysis", {}).get("summary", ""))

        render_action_plan(mqr)
        render_recommendations(mqr)
        render_attributes_analysis(mqr)

# ============================
# QRPMU
# ============================
with tab_qrpmu:
    st.header("QRPMU Summary")

    if not qrpmu:
        render_no_data_message("QRPMU")
    else:
        st.write(qrpmu.get("overall_analysis", {}).get("summary", ""))

        render_action_plan(qrpmu)
        render_recommendations(qrpmu)
        render_attributes_analysis(qrpmu)