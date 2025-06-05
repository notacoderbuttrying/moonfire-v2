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
import copy # For deep copying mock data

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
def fetch_company(info_id: str) -> Optional[Dict]:
    """
    Return mock company data for OpenAI or Perplexity AI.
    Simulates an API call for proof-of-concept.
    """
    MOCK_COMPANY_DATA = {
        "716f3613-036e-4814-9003-779526b58f0c": { # OpenAI
            "uuid": "716f3613-036e-4814-9003-779526b58f0c",
            "logo": "https://images.crunchbase.com/image/upload/c_pad,h_45,w_45,f_auto,b_white,q_auto:eco,dpr_1/jjykwqqhsscreywea4gb",
            "name": "OpenAI",
            "tags": ["unicorn", "ai", "large language model"],
            "founded": "2015-12-11",
            "website": "https://www.openai.com",
            "headline": "OpenAI creates artificial intelligence technologies.",
            "location": [
                {"name": "San Francisco", "type": "city"},
                {"name": "California", "type": "region"},
                {"name": "United States", "type": "country"},
                {"name": "North America", "type": "continent"}
            ],
            "categories": [
                {"name": "Artificial Intelligence (AI)"},
                {"name": "Generative AI"},
                {"name": "Machine Learning"}
            ],
            "description": "OpenAI is an AI research and deployment company.",
            "company_type": "for profit",
            "employee_count": "1001-5000",
            "funding_rounds_headline": {
                "funding_total": {"value_usd": 61900000000},
                "num_funding_rounds": 11
            },
            "operating_status": "active",
        },
        "perplexity-ai-mock-uuid-001": { # Perplexity AI
            "uuid": "perplexity-ai-mock-uuid-001",
            "logo": "https://pbs.twimg.com/profile_images/1743001781703843840/G3ht02qE_400x400.jpg",
            "name": "Perplexity AI",
            "tags": ["ai search", "answer engine"],
            "founded": "2022-08-01",
            "website": "https://www.perplexity.ai",
            "headline": "Perplexity AI is an AI-powered answer engine.",
            "location": [
                {"name": "San Francisco", "type": "city"},
                {"name": "California", "type": "region"},
                {"name": "United States", "type": "country"},
                {"name": "North America", "type": "continent"}
            ],
            "categories": [
                {"name": "Artificial Intelligence (AI)"},
                {"name": "Search Engine"},
                {"name": "Conversational AI"}
            ],
            "description": "Perplexity AI provides direct, accurate answers to questions using large language models.",
            "company_type": "for profit",
            "employee_count": "51-200",
            "funding_rounds_headline": {
                "funding_total": {"value_usd": 100000000}, # Approx $100M
                "num_funding_rounds": 2
            },
            "operating_status": "active",
        }
    }

    # Try to find by UUID
    if info_id in MOCK_COMPANY_DATA:
        return copy.deepcopy(MOCK_COMPANY_DATA[info_id])

    # Try to find by name (case-insensitive)
    for company_uuid, company_data in MOCK_COMPANY_DATA.items():
        if company_data.get("name", "").lower() == info_id.lower():
            return copy.deepcopy(company_data)

    logger.info(f"Mock data not found for {info_id}. You can add it to MOCK_COMPANY_DATA in fetch_company.")
    return None

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
        
        # Add to DataFrame in session state
        if "df" not in st.session_state:
            st.session_state.df = pd.DataFrame()
        
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])],
            ignore_index=True
        )
        
        st.success(f"Successfully added {company_info['Name']}")
        
    except Exception as e:
        st.error(f"Error displaying company: {str(e)}")

def update_visualizations():
    """Update the plot and table visualizations."""
    try:
        if "df" not in st.session_state:
            st.session_state.df = pd.DataFrame()
            st.info("No companies added yet. Add a company to see data.")
            return

        if st.session_state.df.empty:
            st.info("No companies added yet. Add a company to see data.")
            return

        # Calculate statistics
        total_companies = len(st.session_state.df)
        total_funding = st.session_state.df['Funding (USD)'].sum()
        avg_age = st.session_state.df['Age (Years)'].mean()
        avg_cap_eff = st.session_state.df['Capital Efficiency Score'].mean()

        # Create metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", total_companies)
        with col2:
            st.metric("Total Funding", f"${total_funding/1000000:.1f}M")
        with col3:
            st.metric("Average Age", f"{avg_age:.1f} years")
        with col4:
            st.metric("Avg Capital Efficiency", f"${avg_cap_eff/1000000:.1f}M/year")

        # Create plot
        fig = px.scatter(
            st.session_state.df,
            x='Age (Years)',
            y='Capital Efficiency Score',
            size='Funding (USD)',
            color='Employee Count',
            hover_name='Company Name',
            log_x=True,
            size_max=60,
            title="Capital Efficiency Radar",
            labels={
                "Age (Years)": "Company Age (Years)",
                "Capital Efficiency Score": "Capital Efficiency Score ($/Year)",
                "Employee Count": "Employee Count",
                "Funding (USD)": "Total Funding (USD)"
            }
        )
        
        # Use st.session_state to prevent duplicate element IDs
        if 'plot_container' not in st.session_state:
            st.session_state.plot_container = st.container()
        
        with st.session_state.plot_container:
            
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
            st.session_state.df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name="radar.csv",
                mime="text/csv"
            )
            
            # Display table with Streamlit's built-in functionality
            st.dataframe(
                st.session_state.df.style.format({
                    "Capital Efficiency Score": "${:,.2f}",
                    "Funding (USD)": "${:,.2f}",
                    "Age (Years)": "{:.1f}"
                }),
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Error updating visualizations: {str(e)}")
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
            {"name": "Perplexity AI", "uuid": "perplexity-ai-mock-uuid-001"}
        ]
        for company in test_companies:
            add_company(company["uuid"])

# Main content
st.title("Capital-Efficiency Radar")
update_visualizations()
