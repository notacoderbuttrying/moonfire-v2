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
def fetch_company(info_id: str, max_retries: int = 3, backoff_factor: float = 1.5) -> Dict:
    """
    Fetch company information from Piloterr's API with enhanced error handling and rate limiting.
    Uses caching to reduce API calls and provides better error messages.
    
    Args:
        info_id: Either a UUID (with '-') or company name
        max_retries: Maximum number of retries for failed requests
        backoff_factor: Factor by which to increase wait time between retries
    
    Returns:
        Dict containing company information
    """
    # Check cache first
    cache_key = hashlib.md5(info_id.encode()).hexdigest()
    if cache_key in company_cache:
        logger.info(f"Found company in cache: {info_id}")
        return company_cache[cache_key]
    
    api_key = os.getenv("PILOTERR_API_KEY")
    if not api_key:
        raise ValueError("PILOTERR_API_KEY environment variable not set")
    
    # Debug logging
    logger.info(f"Fetching company info for: {info_id}")
    logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:]}")  # Masked for security
    
    # Try different header formats
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Rate-Limit-Interval": "1s",  # Add rate limiting headers
        "X-Rate-Limit-Count": "1"
    }
    
    # Search endpoints ordered by priority
    search_urls = [
        f"https://piloterr.com/api/v2/search",  # Try more general search endpoint first
        f"https://piloterr.com/api/v2/crunchbase/search",
        f"https://piloterr.com/api/v2/crunchbase/company/search"
    ]
    
    # Company detail endpoints ordered by priority
    detail_urls = [
        f"https://piloterr.com/api/v2/company/{info_id}",
        f"https://piloterr.com/api/v2/crunchbase/company/{info_id}",
        f"https://piloterr.com/api/v2/crunchbase/{info_id}"
    ]
    
    def make_request(url: str, retry_count: int = 0, last_retry: bool = False) -> Optional[requests.Response]:
        """Make a request with retry logic. Returns None for 403 errors."""
        try:
            # Add a small delay between requests to avoid overwhelming the server
            if retry_count > 0:
                time.sleep(1)  # Wait 1 second between retries
            
            response = requests.get(url, headers=headers, params={"query": info_id})
            
            if response.status_code == 401:
                logger.error(f"401 Unauthorized response received. Headers: {headers}")
                raise ValueError("API key not authorized. Please check your API key in Streamlit Cloud secrets.")
            elif response.status_code == 403:
                logger.warning(f"403 Forbidden for endpoint {url}. Skipping this endpoint.")
                return None  # Skip forbidden endpoints
            elif response.status_code == 500:
                # Check if we've exceeded rate limits
                if "rate limit" in response.text.lower() or "too many requests" in response.text.lower():
                    wait_time = 5  # Wait 5 seconds for rate limit
                    logger.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    return make_request(url, retry_count + 1)
                
                # If we've exceeded max retries and this isn't the last retry, try next endpoint
                if retry_count >= max_retries and not last_retry:
                    logger.warning("Maximum retries reached. Trying next endpoint...")
                    return None
                
                # Otherwise, if we haven't exceeded max retries, wait and retry
                if retry_count < max_retries:
                    wait_time = backoff_factor ** retry_count
                    logger.warning(f"500 Server Error. Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    return make_request(url, retry_count + 1)
                else:
                    logger.error(f"500 Server Error received after {max_retries} retries. Response: {response.text}")
                    logger.error(f"Response headers: {response.headers}")
                    logger.error(f"Full URL: {response.url}")
                    
                    # Check if we should try a different endpoint
                    if not last_retry:
                        logger.warning("Trying next endpoint...")
                        return None  # Indicate we should try next endpoint
                    else:
                        raise ValueError("API server error. Please try again later or contact Piloterr support.")
            return response
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    try:
        successful_response = None
        
        if "-" in info_id:  # UUID
            # For UUIDs, try multiple endpoints in order
            for endpoint in detail_urls:
                try:
                    logger.info(f"Trying company details endpoint: {endpoint}")
                    response = make_request(endpoint)
                    if response is not None and response.status_code == 200:
                        successful_response = response
                        break
                except Exception as e:
                    logger.error(f"Failed to fetch from {endpoint}: {e}")
                    continue
            
            if successful_response is None:
                raise ValueError("Failed to fetch company details from any endpoint")
        else:  # Company name
            # Try each search endpoint in order
            for search_url in search_urls:
                try:
                    logger.info(f"Trying search endpoint: {search_url}")
                    response = make_request(search_url)
                    
                    if response is not None and response.status_code == 200:
                        successful_response = response
                        break
                    
                    logger.info(f"Search endpoint {search_url} failed with status {response.status_code if response else 'None'}")
                except Exception as e:
                    logger.error(f"Error with search endpoint {search_url}: {e}")
                    continue
        
        if successful_response is None:
            raise ValueError("No successful response from any endpoint")
            
        logger.info(f"API Request URL: {successful_response.url}")
        logger.info(f"API Response Status: {successful_response.status_code}")
        logger.info(f"API Response Headers: {successful_response.headers}")
        
        successful_response.raise_for_status()
        data = successful_response.json()
        
        if "-" not in info_id and isinstance(data, list):
            # For search results, take the first match
            if not data:
                raise ValueError("No company found with that name")
            data = data[0]
        
        # Extract required fields with safe defaults
        return {
            "company": data.get("name", "Unknown"),
            "country": data.get("country_code", "Unknown"),
            "employee_min": int(data.get("num_employees_min", 0)),
            "funding_usd": float(data.get("total_funding_usd", 0)),
            "founded_on": data.get("founded_on", "Unknown"),
            "website": data.get("website", "Unknown"),
            "category_list": ", ".join(data.get("categories", [])),
            "tags": ", ".join(data.get("tags", []))
        }
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise ValueError(f"Failed to fetch company data. Error: {str(e)}")
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise ValueError(f"Failed to fetch company data. Error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise ValueError(f"Failed to fetch company data. Error: {str(e)}")

def add_company(company_input: str):
    """Add a company to the DataFrame."""
    try:
        company_data = fetch_company(company_input)
        
        # Calculate age in years
        age_years = 0
        if company_data["founded_on"] != "Unknown":
            try:
                founded_date = datetime.strptime(company_data["founded_on"], "%Y-%m-%d")
                age_years = (datetime.now() - founded_date).days / 365
            except ValueError:
                pass
        
        # Calculate capital efficiency score
        cap_eff = 0
        if company_data["funding_usd"] > 0 and age_years > 0:
            cap_eff = company_data["funding_usd"] / age_years
            
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
        
        # Add to DataFrame
        st.session_state["df"] = pd.concat(
            [st.session_state["df"], pd.DataFrame([new_row])],
            ignore_index=True
        )
        
        st.success(f"Successfully added {company_data['company']}")
        update_visualizations()
    except ValueError as e:
        # Handle API-related errors with a more user-friendly message
        if "API" in str(e) or "server" in str(e).lower():
            st.error(f"API Error: {str(e)}\n\nThe API might be experiencing temporary issues. Please try again later or contact Piloterr support if the problem persists.")
        else:
            st.error(f"Error adding company: {str(e)}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")

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
