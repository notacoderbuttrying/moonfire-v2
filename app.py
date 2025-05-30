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
def fetch_company(info_id: str) -> Dict:
    """
    Fetch company information from Piloterr's Crunchbase API.
    
    Args:
        info_id: Either a UUID (with '-') or company name
    
    Returns:
        Dict containing company information
    """
    api_key = os.getenv("PILOTERR_API_KEY")
    if not api_key:
        raise ValueError("PILOTERR_API_KEY environment variable not set")
    
    base_url = "https://piloterr.com/api/v2/crunchbase/company/info"
    headers = {
        "x-api-key": api_key
    }
    
    if "-" in info_id:  # UUID
        params = {"id": info_id}
    else:  # Company name
        params = {"query": info_id}
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # If it's a company name search, take the first match
        if "-" not in info_id and isinstance(data, list):
            if not data:
                raise ValueError("No company found with that name")
            data = data[0]
            
        # Extract required fields with safe defaults
        return {
            "company": data.get("company", "Unknown"),
            "country": data.get("country", "Unknown"),
            "employee_min": int(data.get("employee_min", 0)),
            "funding_usd": float(data.get("funding_usd", 0)),
            "founded_on": data.get("founded_on", "Unknown"),
            "website": data.get("website", "Unknown"),
            "category_list": ", ".join(data.get("category_list", [])),
            "tags": ", ".join(data.get("tags", []))
        }
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing response: {e}")
        raise

def add_company(company_input: str):
    """Add a company to the DataFrame."""
    try:
        company_data = fetch_company(company_input)
        
        # Calculate derived metrics
        if company_data["founded_on"] != "Unknown":
            try:
                founded_date = datetime.strptime(company_data["founded_on"], "%Y-%m-%d")
                age_years = (datetime.now() - founded_date).days / 365
            except ValueError:
                age_years = 0
        else:
            age_years = 0
            
        if company_data["employee_min"] > 0:
            cap_eff = company_data["funding_usd"] / company_data["employee_min"]
        else:
            cap_eff = 0
            
        # Create new row
        new_row = {
            "Company Name": company_data["company"],
            "Crunchbase UUID": company_input if "-" in company_input else "N/A",
            "Country": company_data["country"],
            "Employee Count": company_data["employee_min"],
            "Funding (USD)": company_data["funding_usd"],
            "Founded Date": company_data["founded_on"],
            "Website": company_data["website"],
            "Categories": company_data["category_list"],
            "Tags": company_data["tags"],
            "Age (Years)": age_years,
            "Capital Efficiency Score": cap_eff
        }
        
        # Add to DataFrame if not already present
        df = st.session_state["df"]
        uuid = company_input if "-" in company_input else company_data.get("company", "")
        if uuid not in df["Crunchbase UUID"].values and uuid not in df["Company Name"].values:
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state["df"] = df
            st.success("Company added successfully!")
        else:
            st.warning("Company already exists in the database")
            
        # Update visualization
        update_visualizations()
        
    except Exception as e:
        st.error(f"Error adding company: {str(e)}")

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
    
    # Test UUIDs for demonstration
    test_uuids = {
        "OpenAI": "716f3613-036e-4814-9003-779526b58f0c",
        "GitHub": "6393c62a-4c5a-456a-9737-950356d72814"
    }
    if st.sidebar.button("Add Test Companies"):
        for name, uuid in test_uuids.items():
            add_company(uuid)

# Main content
st.title("Capital-Efficiency Radar")
update_visualizations()
