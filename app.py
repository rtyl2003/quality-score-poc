import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Product Quality Intelligence", layout="wide")

# ---------------------------
# Load JSON helpers
# ---------------------------
@st.cache_data
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def build_summary_path(use_case, tpnb):
    return os.path.join("summaries", use_case, f"{use_case}_{tpnb}.json")

def load_required_json(use_case, tpnb):
    path = build_summary_path(use_case, tpnb)
    if not os.path.exists(path):
        st.error(f"Missing file: {path}")
        st.stop()
    return load_json(path)

# ---------------------------
# TPNB Selection
# ---------------------------
default_tpnb = "050044027"
selected_tpnb = st.sidebar.text_input("Enter TPNB", value=default_tpnb).strip()

# ---------------------------
# Load Files
# ---------------------------
reviews = load_required_json("reviews", selected_tpnb)
complaints = load_required_json("complaints", selected_tpnb)
quality_panel = load_required_json("quality_panel", selected_tpnb)
pac = load_required_json("pac", selected_tpnb)

# ---------------------------
# Utility Functions
# ---------------------------
def avg_attribute_score(data):
    attributes = data.get("attributes_analysis", {}).get("attributes", [])
    if not attributes:
        return 0.0
    return sum(a.get("score", 0) for a in attributes) / len(attributes)

def get_reviews_score(data, sentiment_weight, rating_weight):
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

def render_action_plan(data):
    action_plan = data.get("action_plan", {})
    summary_items = action_plan.get("summary", [])
    recommendation_items = action_plan.get("recommendations", [])
    overall_items = data.get("overall_analysis", {}).get("action_plan", {}).get("items", [])

    st.subheader("Action Plan")

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

    overall_rating = data.get("overall_analysis", {}).get("overall_rating", {})
    dist = overall_rating.get("distribution", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Average Rating", round(overall_rating.get("mean", 0), 2))
    c2.metric("Review Count", overall_rating.get("count", 0))
    c3.metric("Sentiment Score", round(data.get("overall_analysis", {}).get("overall_sentiment", {}).get("score", 0) * 100, 1))

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
            "Related Attributes": ", ".join(item.get("related_attributes", []) or []),
            "Confidence": item.get("confidence", ""),
            "Timeline": item.get("timeline", ""),
            "Expected Impact": item.get("expected_impact", "")
        }
        for item in recommendations
    ])

    st.dataframe(df_recommendations, use_container_width=True)

# ---------------------------
# QCI Configuration
# ---------------------------
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

if abs(review_score_total_weight - 1.0) > 0.001:
    st.warning(
        f"Current review score weights sum to {review_score_total_weight:.2f}. "
        f"Review score is being normalized by total weight."
    )

st.sidebar.header("Quality Score Weights")

default_reviews_weight = 0.30
default_complaints_weight = 0.30
default_panel_weight = 0.20
default_pac_weight = 0.20

reviews_weight = st.sidebar.number_input("Reviews Weight", min_value=0.0, max_value=1.0, value=default_reviews_weight, step=0.05)
complaints_weight = st.sidebar.number_input("Complaints Weight", min_value=0.0, max_value=1.0, value=default_complaints_weight, step=0.05)
panel_weight = st.sidebar.number_input("Quality Panel Weight", min_value=0.0, max_value=1.0, value=default_panel_weight, step=0.05)
pac_weight = st.sidebar.number_input("PAC Weight", min_value=0.0, max_value=1.0, value=default_pac_weight, step=0.05)

total_weight = reviews_weight + complaints_weight + panel_weight + pac_weight

# ---------------------------
# Score Calculation
# ---------------------------
reviews_score, reviews_sentiment_score, reviews_avg_rating_score = get_reviews_score(
    reviews,
    review_sentiment_weight,
    review_rating_weight
)
complaints_score = complaints.get("overall_analysis", {}).get("overall_sentiment", {}).get("score", 0) * 100
panel_score = avg_attribute_score(quality_panel)
pac_score = avg_attribute_score(pac)

if total_weight == 0:
    QCI = 0.0
else:
    QCI = round(
        (
            reviews_weight * reviews_score +
            complaints_weight * complaints_score +
            panel_weight * panel_score +
            pac_weight * pac_score
        ) / total_weight,
        1
    )

# ---------------------------
# Header
# ---------------------------
product = reviews["product_info"]["product_name"]
brand = reviews["product_info"]["product_brand"]

st.title("📊 Product Quality Summary Dashboard")
st.subheader(f"{brand} – {product}")

if abs(total_weight - 1.0) > 0.001:
    st.warning(f"Current Quality score weights sum to {total_weight:.2f}. Quality score is being normalized by total weight.")

# ---------------------------
# Top KPIs
# ---------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Quality Score", QCI)
c2.metric("Reviews Score", round(reviews_score, 1))
c3.metric("Complaints Score", round(complaints_score, 1))
c4.metric("Panel Score", round(panel_score, 1))
c5.metric("PAC Score", round(pac_score, 1))

# ---------------------------
# Tabs
# ---------------------------
tab_overall, tab_reviews, tab_complaints, tab_panel, tab_pac = st.tabs(
    ["📊 Overall Summary", "⭐ Reviews", "🛑 Complaints", "🧪 Quality Panel", "🧠 PAC/CTH"]
)

# ============================
# OVERALL SUMMARY
# ============================
with tab_overall:
    st.header("Overall Quality Assessment")

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

    def extract(df, label):
        return pd.DataFrame([
            {"Source": label, "Attribute": a.get("attribute", ""), "Score": a.get("score", 0)}
            for a in df.get("attributes_analysis", {}).get("attributes", [])
        ])

    df_all = pd.concat([
        extract(reviews, "Reviews"),
        extract(complaints, "Complaints"),
        extract(quality_panel, "Panel"),
        extract(pac, "PAC")
    ])

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

# ============================
# REVIEWS
# ============================
with tab_reviews:
    st.header("Customer Reviews")
    st.write(reviews.get("overall_analysis", {}).get("summary", ""))

    c1, c2, c3 = st.columns(3)
    c1.metric("Reviews Score", reviews_score)
    c2.metric("Overall Sentiment Score", reviews_sentiment_score)
    c3.metric("Average Rating Score", reviews_avg_rating_score)

    render_action_plan(reviews)
    render_recommendations(reviews)
    render_attributes_analysis(reviews)
    render_reviews_rating_stats(reviews)

# ============================
# COMPLAINTS
# ============================
with tab_complaints:
    st.header("Customer Complaints")
    st.write(complaints.get("overall_analysis", {}).get("summary", ""))

    render_action_plan(complaints)
    render_attributes_analysis(complaints)

# ============================
# QUALITY PANEL
# ============================
with tab_panel:
    st.header("Quality Panel Evaluation")
    st.write(quality_panel.get("overall_analysis", {}).get("summary", ""))

    render_action_plan(quality_panel)
    render_attributes_analysis(quality_panel)

# ============================
# PAC
# ============================
with tab_pac:
    st.header("PAC – Consumer Acceptance Testing")
    st.write(pac.get("overall_analysis", {}).get("summary", ""))

    render_action_plan(pac)
    render_attributes_analysis(pac)