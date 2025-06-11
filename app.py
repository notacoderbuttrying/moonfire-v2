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
            "tags": ["unicorn", "ai", "large language model", "enterprise"],
            "founded": "2015-12-11",
            "website": "https://www.openai.com",
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
                {"name": "Enterprise Software"}
            ],
            "description": "OpenAI is an AI research and deployment company focused on developing advanced AI systems.",
            "company_type": "for profit",
            "employee_count": "1001-5000",
            "funding_rounds_headline": {
                "funding_total": {"value_usd": 61900000000},
                "num_funding_rounds": 11
            },
            "operating_status": "active",
            "valuation": {"value_usd": 29000000000, "date": "2024-03-01"},
            "revenue": {"value_usd": 1000000000, "date": "2024-03-01"},
            "growth_rate": {"value": 1.5, "period": "annual"},
            "burn_rate": {"value_usd": 100000000, "period": "monthly"},
            "runway": {"months": 24, "date": "2024-03-01"},
            "unit_economics": {
                "gross_margin": 0.75,
                "customer_acquisition_cost": 100,
                "customer_lifetime_value": 5000
            },
            "market_size": {"total_addressable_market": 1000000000000, "serviceable_available_market": 500000000000}
        },
        "perplexity-ai-mock-uuid-001": { # Perplexity AI
            "uuid": "perplexity-ai-mock-uuid-001",
            "logo": "https://pbs.twimg.com/profile_images/1743001781703843840/G3ht02qE_400x400.jpg",
            "name": "Perplexity AI",
            "tags": ["ai search", "answer engine", "consumer"],
            "founded": "2022-08-01",
            "website": "https://www.perplexity.ai",
            "location": [
                {"name": "San Francisco", "type": "city"},
                {"name": "California", "type": "region"},
                {"name": "United States", "type": "country"},
                {"name": "North America", "type": "continent"}
            ],
            "categories": [
                {"name": "Artificial Intelligence (AI)"},
                {"name": "Search Engine"},
                {"name": "Conversational AI"},
                {"name": "Consumer Software"}
            ],
            "description": "Perplexity AI provides direct, accurate answers to questions using large language models.",
            "company_type": "for profit",
            "employee_count": "51-200",
            "funding_rounds_headline": {
                "funding_total": {"value_usd": 100000000},
                "num_funding_rounds": 2
            },
            "operating_status": "active",
            "valuation": {"value_usd": 1000000000, "date": "2024-03-01"},
            "revenue": {"value_usd": 10000000, "date": "2024-03-01"},
            "growth_rate": {"value": 2.5, "period": "annual"},
            "burn_rate": {"value_usd": 2000000, "period": "monthly"},
            "runway": {"months": 18, "date": "2024-03-01"},
            "unit_economics": {
                "gross_margin": 0.85,
                "customer_acquisition_cost": 50,
                "customer_lifetime_value": 2000
            },
            "market_size": {"total_addressable_market": 50000000000, "serviceable_available_market": 20000000000}
        },
        "anthropic-mock-uuid-002": { # Anthropic
            "uuid": "anthropic-mock-uuid-002",
            "logo": "https://pbs.twimg.com/profile_images/1636530473469095936/2UeSA05x_400x400.jpg",
            "name": "Anthropic",
            "tags": ["ai", "large language model", "ai safety", "enterprise"],
            "founded": "2021-01-01", # Approximate
            "website": "https://www.anthropic.com",
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
                {"name": "AI Safety"},
                {"name": "Enterprise Software"}
            ],
            "description": "Anthropic builds reliable, interpretable, and steerable AI systems.",
            "company_type": "for profit",
            "employee_count": "501-1000", # Estimated
            "funding_rounds_headline": {
                "funding_total": {"value_usd": 7300000000},
                "num_funding_rounds": 5
            },
            "operating_status": "active",
            "valuation": {"value_usd": 10000000000, "date": "2024-03-01"},
            "revenue": {"value_usd": 500000000, "date": "2024-03-01"},
            "growth_rate": {"value": 1.8, "period": "annual"},
            "burn_rate": {"value_usd": 50000000, "period": "monthly"},
            "runway": {"months": 20, "date": "2024-03-01"},
            "unit_economics": {
                "gross_margin": 0.70,
                "customer_acquisition_cost": 150,
                "customer_lifetime_value": 4000
            },
            "market_size": {"total_addressable_market": 800000000000, "serviceable_available_market": 400000000000}
        },
        "deepseek-ai-mock-uuid-001": { # Deepseek AI
            "uuid": "deepseek-ai-mock-uuid-001",
            "logo": "https://pbs.twimg.com/profile_images/1636530473469095936/2UeSA05x_400x400.jpg",
            "name": "Deepseek AI",
            "tags": ["ai", "large language model", "enterprise", "research"],
            "founded": "2022-01-01", # Estimated
            "website": "https://www.deepseek.ai",
            "location": [
                {"name": "Seoul", "type": "city"},
                {"name": "South Korea", "type": "country"},
                {"name": "Asia", "type": "continent"}
            ],
            "categories": [
                {"name": "Artificial Intelligence (AI)"},
                {"name": "Generative AI"},
                {"name": "Machine Learning"},
                {"name": "Enterprise Software"},
                {"name": "Research"}
            ],
            "description": "Deepseek AI develops advanced AI systems with a focus on large language models.",
            "company_type": "for profit",
            "employee_count": "201-500", # Estimated
            "funding_rounds_headline": {
                "funding_total": {"value_usd": 500000000},
                "num_funding_rounds": 3
            },
            "operating_status": "active",
            "valuation": {"value_usd": 2000000000, "date": "2024-03-01"},
            "revenue": {"value_usd": 100000000, "date": "2024-03-01"},
            "growth_rate": {"value": 2.0, "period": "annual"},
            "burn_rate": {"value_usd": 10000000, "period": "monthly"},
            "runway": {"months": 24, "date": "2024-03-01"},
            "unit_economics": {
                "gross_margin": 0.75,
                "customer_acquisition_cost": 120,
                "customer_lifetime_value": 3500
            },
            "market_size": {"total_addressable_market": 300000000000, "serviceable_available_market": 150000000000}
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
            "Website": company_data.get("website", "N/A"),
            "Valuation": f"${company_data.get('valuation', {}).get('value_usd', 0) / 1000000000:.1f}B",
            "Revenue": f"${company_data.get('revenue', {}).get('value_usd', 0) / 1000000:.1f}M",
            "Growth Rate": f"{company_data.get('growth_rate', {}).get('value', 0):.1f}x",
            "Burn Rate": f"${company_data.get('burn_rate', {}).get('value_usd', 0) / 1000000:.1f}M/mo",
            "Runway": f"{company_data.get('runway', {}).get('months', 0)} months",
            "Gross Margin": f"{company_data.get('unit_economics', {}).get('gross_margin', 0) * 100:.1f}%",
            "CAC": f"${company_data.get('unit_economics', {}).get('customer_acquisition_cost', 0)}",
            "LTV": f"${company_data.get('unit_economics', {}).get('customer_lifetime_value', 0)}",
            "TAM": f"${company_data.get('market_size', {}).get('total_addressable_market', 0) / 1000000000:.1f}B",
            "SAM": f"${company_data.get('market_size', {}).get('serviceable_available_market', 0) / 1000000000:.1f}B"
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
                    <p><strong>Valuation:</strong> {company_info['Valuation']}</p>
                    <p><strong>Revenue:</strong> {company_info['Revenue']}</p>
                    <p><strong>Growth Rate:</strong> {company_info['Growth Rate']}</p>
                    <p><strong>Burn Rate:</strong> {company_info['Burn Rate']}</p>
                    <p><strong>Runway:</strong> {company_info['Runway']}</p>
                    <p><strong>Gross Margin:</strong> {company_info['Gross Margin']}</p>
                    <p><strong>CAC:</strong> {company_info['CAC']}</p>
                    <p><strong>LTV:</strong> {company_info['LTV']}</p>
                    <p><strong>TAM:</strong> {company_info['TAM']}</p>
                    <p><strong>SAM:</strong> {company_info['SAM']}</p>
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
            "Capital Efficiency Score": float(company_info["Funding Total"].replace("$", "").replace("M", "")) * 1000000 / age_years,
            "Valuation (USD)": float(company_info["Valuation"].replace("$", "").replace("B", "")) * 1000000000,
            "Revenue (USD)": float(company_info["Revenue"].replace("$", "").replace("M", "")) * 1000000,
            "Growth Rate": float(company_info["Growth Rate"].replace("x", "")),
            "Burn Rate (USD)": float(company_info["Burn Rate"].replace("$", "").replace("M/mo", "")) * 1000000,
            "Runway (Months)": float(company_info["Runway"].replace(" months", "")),
            "Gross Margin": float(company_info["Gross Margin"].replace("%", "")) / 100,
            "CAC": float(company_info["CAC"].replace("$", "")),
            "LTV": float(company_info["LTV"].replace("$", "")),
            "TAM (USD)": float(company_info["TAM"].replace("$", "").replace("B", "")) * 1000000000,
            "SAM (USD)": float(company_info["SAM"].replace("$", "").replace("B", "")) * 1000000000
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


def remove_company(company_name_to_remove: str):
    """Remove a company from the DataFrame and cache."""
    global company_cache # Declare company_cache as global to modify it
    try:
        if company_name_to_remove in st.session_state.df["Company Name"].values:
            # Create a new DataFrame without the company
            new_df = st.session_state.df[st.session_state.df["Company Name"] != company_name_to_remove]
            
            # Update session state with new DataFrame
            st.session_state.df = new_df
            
            # Remove from cache
            cache_keys_to_delete = []
            for key, cached_data in list(company_cache.items()): # Iterate over a copy for safe deletion
                if isinstance(cached_data, dict) and cached_data.get("name") == company_name_to_remove:
                    cache_keys_to_delete.append(key)
            
            for key in cache_keys_to_delete:
                if key in company_cache:
                    del company_cache[key]
            
            # Save updated cache
            with open(cache_file, 'w') as f:
                json.dump(company_cache, f, indent=4)
            
            st.success(f"Successfully removed {company_name_to_remove}.")
            
            # Force a re-render by updating a dummy state variable
            if 'dummy_update' not in st.session_state:
                st.session_state.dummy_update = 0
            st.session_state.dummy_update += 1
        else:
            st.warning(f"{company_name_to_remove} not found in the current list.")
    except Exception as e:
        st.error(f"Error removing company: {str(e)}")

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
        total_valuation = st.session_state.df['Valuation (USD)'].sum()
        avg_age = st.session_state.df['Age (Years)'].mean()
        avg_cap_eff = st.session_state.df['Capital Efficiency Score'].mean()
        avg_growth = st.session_state.df['Growth Rate'].mean()
        avg_gross_margin = st.session_state.df['Gross Margin'].mean()
        avg_cac = st.session_state.df['CAC'].mean()
        avg_ltv = st.session_state.df['LTV'].mean()

        # Create metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", total_companies)
            st.metric("Avg Growth Rate", f"{avg_growth:.1f}x")
            st.metric("Avg Gross Margin", f"{avg_gross_margin*100:.1f}%")
        with col2:
            st.metric("Total Funding", f"${total_funding/1000000000:.1f}B")
            st.metric("Avg CAC", f"${avg_cac:.0f}")
            st.metric("Avg LTV", f"${avg_ltv:.0f}")
        with col3:
            st.metric("Total Valuation", f"${total_valuation/1000000000:.1f}B")
            st.metric("Avg Runway", f"{st.session_state.df['Runway (Months)'].mean():.1f} months")
            st.metric("Avg Burn Rate", f"${st.session_state.df['Burn Rate (USD)'].mean()/1000000:.1f}M/mo")
        with col4:
            st.metric("Average Age", f"{avg_age:.1f} years")
            st.metric("Avg TAM", f"${st.session_state.df['TAM (USD)'].mean()/1000000000:.1f}B")
            st.metric("Avg SAM", f"${st.session_state.df['SAM (USD)'].mean()/1000000000:.1f}B")

        # Create multiple plots for better comparison
        with st.expander("Interactive Visualizations", expanded=True):
            # Growth vs Valuation
            fig1 = px.scatter(
                st.session_state.df,
                x='Valuation (USD)',
                y='Growth Rate',
                size='Revenue (USD)',
                color='Company Name',
                hover_name='Company Name',
                log_x=True,
                size_max=60,
                title="Growth vs Valuation",
                labels={
                    "Valuation (USD)": "Company Valuation ($B)",
                    "Growth Rate": "Annual Growth Rate (x)",
                    "Revenue (USD)": "Annual Revenue ($M)"
                }
            )
            
            # Burn Rate vs Runway
            fig2 = px.scatter(
                st.session_state.df,
                x='Burn Rate (USD)',
                y='Runway (Months)',
                size='Employee Count',
                color='Company Name',
                hover_name='Company Name',
                log_x=True,
                size_max=60,
                title="Burn Rate vs Runway",
                labels={
                    "Burn Rate (USD)": "Monthly Burn Rate ($M)",
                    "Runway (Months)": "Runway (months)",
                    "Employee Count": "Employee Count"
                }
            )
            
            # LTV vs CAC
            fig3 = px.scatter(
                st.session_state.df,
                x='CAC',
                y='LTV',
                size='Gross Margin',
                color='Company Name',
                hover_name='Company Name',
                log_x=True,
                log_y=True,
                size_max=60,
                title="LTV vs CAC",
                labels={
                    "CAC": "Customer Acquisition Cost ($)",
                    "LTV": "Customer Lifetime Value ($)",
                    "Gross Margin": "Gross Margin"
                }
            )
            
            # Show plots in columns
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)

        # Create download and table section
        with st.container():
            # Download button
            csv_buffer = io.StringIO()
            st.session_state.df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name="vc_comparison.csv",
                mime="text/csv"
            )
            
            # Display table with Streamlit's built-in functionality
            st.dataframe(
                st.session_state.df.style.format({
                    "Capital Efficiency Score": "${:,.2f}",
                    "Funding (USD)": "${:,.2f}",
                    "Age (Years)": "{:.1f}",
                    "Valuation (USD)": "${:,.2f}",
                    "Revenue (USD)": "${:,.2f}",
                    "Growth Rate": "{:.1f}x",
                    "Burn Rate (USD)": "${:,.2f}",
                    "Runway (Months)": "{:.1f}",
                    "Gross Margin": "{:.1%}",
                    "CAC": "${:.0f}",
                    "LTV": "${:.0f}",
                    "TAM (USD)": "${:,.2f}",
                    "SAM (USD)": "${:,.2f}"
                }),
                use_container_width=True
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
with st.sidebar:
    st.title("Settings")

    # Sample companies section
    st.sidebar.subheader("Sample Companies")
    sample_companies = [
        {"name": "OpenAI", "uuid": "716f3613-036e-4814-9003-779526b58f0c"},
        {"name": "Perplexity AI", "uuid": "perplexity-ai-mock-uuid-001"},
        {"name": "Anthropic", "uuid": "anthropic-mock-uuid-002"},
        {"name": "Deepseek AI", "uuid": "deepseek-ai-mock-uuid-001"}
    ]
    
    for company in sample_companies:
        if st.sidebar.button(f"Add {company['name']}", key=f"add_{company['uuid']}"):
            add_company(company["uuid"])

    st.sidebar.markdown("---")
    
    # Add custom company
    company_input = st.text_input("Add Custom Company (Crunchbase UUID or Name)")
    if st.button("Add Custom Company"):
        add_company(company_input)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Manage Companies")
    if "df" in st.session_state and not st.session_state.df.empty:
        company_names = st.session_state.df["Company Name"].unique().tolist()
        if company_names: # Ensure there are companies to select
            company_to_remove = st.sidebar.selectbox(
                "Select company to remove",
                options=company_names,
                index=None, # No default selection
                placeholder="Choose a company...",
                key="remove_company_selectbox" # Unique key
            )
            if st.sidebar.button("Remove Selected Company"):
                if company_to_remove:
                    remove_company(company_to_remove)
                else:
                    st.sidebar.warning("Please select a company to remove.")
        else:
            st.sidebar.info("No companies available to remove.")
    else:
        st.sidebar.info("No companies added yet to manage.")

# Main content
st.title("Capital-Efficiency Radar")
update_visualizations()
