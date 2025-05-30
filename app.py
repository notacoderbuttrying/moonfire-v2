import streamlit as st
import pandas as pd
import plotly.express as px
# Removed streamlit-aggrid dependency - using built-in table functionality
import requests
from datetime import datetime
import logging
from typing import Dict, Optional
import io
import os
from dotenv import load_dotenv
import time  # Add time import for delays
import json
from pathlib import Path
import hashlib

# Cache directory setup
cache_dir = Path(".cache")
if not cache_dir.exists():
    cache_dir.mkdir()

# Cache file for company data
cache_file = cache_dir / "company_cache.json"

# Load existing cache if it exists
company_cache = {}
if cache_file.exists():
    try:
        with open(cache_file, 'r') as f:
            company_cache = json.load(f)
    except json.JSONDecodeError:
        logger.warning("Cache file corrupted. Creating new cache.")
        company_cache = {}

# Page configuration must be first
st.set_page_config(
    page_title="Capital-Efficiency Radar",
    layout="wide"
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom theme
st.markdown("""
<style>
[data-testid="stMetric"] {
    background-color: #2b2b2b;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem;
    color: #fff;
}

[data-testid="stButton"] > button {
    background-color: #4CAF50;
    color: white;
}

[data-testid="stButton"] > button:hover {
    background-color: #45a049;
}

.st-aggrid-table {
    background-color: #2b2b2b;
    color: #fff;
}

.st-aggrid .ag-header-cell {
    background-color: #3b3b3b !important;
    color: #fff !important;
}

.st-aggrid .ag-cell {
    background-color: #2b2b2b !important;
    color: #fff !important;
}

.stDataFrame {
    background-color: #2b2b2b;
    color: #fff;
}

.stDataFrame table {
    background-color: #2b2b2b !important;
    color: #fff !important;
}

.stDataFrame th {
    background-color: #3b3b3b !important;
    color: #fff !important;
}

.stDataFrame td {
    background-color: #2b2b2b !important;
    color: #fff !important;
}
</style>
""", unsafe_allow_html=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if "df" not in st.session_state:
    st.session_state["df"] = pd.DataFrame(columns=[
        "Company Name",
        "Crunchbase UUID",
        "Country",
        "Employee Count",
        "Funding (USD)",
        "Founded Date",
        "Website",
        "Categories",
        "Tags",
        "Age (Years)",
        "Capital Efficiency Score"
    ])

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_company(info_id: str):
    """
    Return static OpenAI data instead of making API calls.
    """
    return {
        "logo": "https://images.crunchbase.com/image/upload/c_pad,h_45,w_45,f_auto,b_white,q_auto:eco,dpr_1/jjykwqqhsscreywea4gb",
        "name": "OpenAI",
        "tags": ["unicorn"],
        "founded": "2015-12-11",
        "website": "https://www.openai.com",
        "headline": "OpenAI creates artificial intelligence technologies to assist with tasks and provide support for human activities.",
        "location": [
            {"name": "San Francisco", "type": "city"},
            {"name": "California", "type": "region"},
            {"name": "United States", "type": "country"},
            {"name": "North America", "type": "continent"}
        ],
        "categories": [
            {"name": "Artificial Intelligence (AI)"},
            {"name": "Generative AI"},
            {"name": "Machine Learning"},
            {"name": "Natural Language Processing"},
            {"name": "SaaS"}
        ],
        "description": "OpenAI is an AI research and deployment company that conducts research and develops machine learning technologies. OpenAI works on projects that involve autonomous learning and task performance. It serves industries such as technology, healthcare, and education.",
        "company_type": "for profit",
        "phone_number": "(800) 217-3145",
        "employee_count": "1001-5000",
        "semrush_summary": {"semrush_global_rank": 31, "semrush_visits_latest_month": 1443825092},
        "social_networks": [
            {"url": "https://www.facebook.com/openai", "name": "facebook"},
            {"url": "https://www.linkedin.com/company/openai", "name": "linkedin"},
            {"url": "https://x.com/OpenAI", "name": "twitter"}
        ],
        "operating_status": "active",
        "funding_rounds_headline": {
            "funding_total": {"value": 61900120000, "currency": "USD", "value_usd": 61900120000},
            "num_funding_rounds": 11
        }
    }

def add_company(company_input: str):
    """Add a company to the DataFrame."""
    try:
        # Fetch company data (static for now)
        company_data = fetch_company(company_input)
        
        # Extract relevant data
        company_info = {
            "Name": company_data.get("name", "N/A"),
            "Location": ", ".join(loc["name"] for loc in company_data.get("location", [])),
            "Founded": company_data.get("founded", "N/A"),
            "Employee Count": company_data.get("employee_count", "N/A"),
            "Funding Total": f"${company_data['funding_rounds_headline']['funding_total']['value_usd'] / 1000000:.1f}M",
            "Tags": ", ".join(company_data.get("tags", [])),
            "Categories": ", ".join(cat["name"] for cat in company_data.get("categories", [])),
            "Website": company_data.get("website", "N/A")
        }
        
        # Display company card
        with st.expander(f" COMPANY CARD FOR {company_info['Name'].upper()}", expanded=True):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.image(company_data.get("logo", ""), width=100)
            
            with col2:
                st.markdown(f"""
                <div style='text-align: left; padding: 20px;'>
                    <h3>{company_info['Name']}</h3>
                    <p><strong>Location:</strong> {company_info['Location']}</p>
                    <p><strong>Founded:</strong> {company_info['Founded']}</p>
                    <p><strong>Employee Count:</strong> {company_info['Employee Count']}</p>
                    <p><strong>Funding Total:</strong> {company_info['Funding Total']}</p>
                    <p><strong>Tags:</strong> {company_info['Tags']}</p>
                    <p><strong>Categories:</strong> {company_info['Categories']}</p>
                    <p><strong>Website:</strong> <a href='{company_info['Website']}' target='_blank'>{company_info['Website']}</a></p>
                </div>
                """, unsafe_allow_html=True)
        
        # Calculate age in years
        age_years = 0
        if company_info["Founded"] != "N/A":
            try:
                founded_date = datetime.strptime(company_info["Founded"], "%Y-%m-%d")
                age_years = (datetime.now() - founded_date).days / 365
            except ValueError:
                pass
        
        # Calculate capital efficiency score
        cap_eff = 0
        if company_info["Funding Total"] != "N/A" and age_years > 0:
            cap_eff = float(company_info["Funding Total"].replace("$", "").replace("M", "")) * 1000000 / age_years
            
        # Create new row
        new_row = {
            "Company Name": company_info["Name"],
            "Crunchbase UUID": company_input if "-" in company_input else "N/A",
            "Country": company_info["Location"].split(", ")[-1],
            "Employee Count": company_info["Employee Count"],
            "Funding (USD)": float(company_info["Funding Total"].replace("$", "").replace("M", "")) * 1000000,
            "Founded Date": company_info["Founded"],
            "Website": company_info["Website"],
            "Categories": company_info["Categories"],
            "Tags": company_info["Tags"],
            "Age (Years)": age_years,
            "Capital Efficiency Score": cap_eff
        }
        
        # Add to DataFrame
        st.session_state["df"] = pd.concat(
            [st.session_state["df"], pd.DataFrame([new_row])],
            ignore_index=True
        )
        
        st.success(f"Successfully added {company_info['Name']}")
        update_visualizations()
    except Exception as e:
        st.error(f"Error displaying company: {str(e)}")

def update_visualizations():
    """Update the plot and table visualizations."""
    df = st.session_state["df"]
    
    if not df.empty:
        # Calculate metrics
        median_cap_eff = df["Capital Efficiency Score"].median()
        best_cap_eff = df.loc[df["Capital Efficiency Score"].idxmax()]
        oldest_company = df.loc[df["Age (Years)"].idxmax()]
        
        # Create metrics section
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Median $/Employee", f"${median_cap_eff:,.2f}")
            with col2:
                st.metric(
                    "Best $/Employee",
                    f"${best_cap_eff['Capital Efficiency Score']:,.2f}"
                    f"\n\n{best_cap_eff['Company Name']}"
                )
            with col3:
                st.metric(
                    "Oldest Company",
                    f"{oldest_company['Age (Years)']:.1f} years"
                    f"\n\n{oldest_company['Company Name']}"
                )
        
        # Create plot section
        with st.container():
            # Enhanced scatter plot
            fig = px.scatter(
                df,
                x="Age (Years)",
                y="Capital Efficiency Score",
                size="Funding (USD)",
                color="Country",
                hover_data={
                    "Company Name": True,
                    "Country": True,
                    "Funding (USD)": ":.2f",
                    "Employee Count": True,
                    "Capital Efficiency Score": ":.2f",
                    "Age (Years)": ":.1f"
                },
                title="Capital Efficiency Radar",
                labels={
                    "Age (Years)": "Company Age (Years)",
                    "Capital Efficiency Score": "$ per Employee",
                    "Funding (USD)": "Funding (USD)"
                }
            )
            
            # Add size scale reference
            fig.update_layout(
                autosize=True,
                margin=dict(l=0, r=0, t=30, b=0),
                hovermode="closest",
                showlegend=True,
                legend_title="Country"
            )
            
            # Add size scale reference
            fig.add_annotation(
                x=0.95,
                y=0.95,
                xref="paper",
                yref="paper",
                text="Size represents funding amount",
                showarrow=False,
                font=dict(size=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Create download and table section
        with st.container():
            # Download button
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name="radar.csv",
                mime="text/csv"
            )
            
            # Display table with Streamlit's built-in functionality
            st.dataframe(
                df.style.format({
                    "Capital Efficiency Score": "${:,.2f}",
                    "Funding (USD)": "${:,.2f}",
                    "Age (Years)": "{:.1f}"
                }),
                use_container_width=True
            )
    else:
        st.write("No companies added yet. Add companies using the sidebar.")

# Sidebar layout
with st.sidebar:
    st.title("Settings")

    company_input = st.text_input("Crunchbase UUID or Name")
    if st.button("Add Company"):
        add_company(company_input)

    st.sidebar.markdown("---")
    if st.sidebar.button("Add Test Companies"):
        test_companies = [
            {"name": "OpenAI", "uuid": "716f3613-036e-4814-9003-779526b58f0c"},
            {"name": "GitHub", "uuid": "6393c62a-4c5a-456a-9737-950356d72814"}
        ]
        for company in test_companies:
            add_company(company["uuid"])

# Main content
st.title("Capital-Efficiency Radar")
update_visualizations()
