import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder

# Page configuration
st.set_page_config(
    page_title="Capital-Efficiency Radar",
    layout="wide"
)

# Initialize session state
if "df" not in st.session_state:
    st.session_state["df"] = pd.DataFrame(columns=["Company Name", "Crunchbase UUID", "Capital Efficiency Score"])

if "api_key" not in st.session_state:
    st.session_state["api_key"] = ""

# Sidebar layout
with st.sidebar:
    st.title("Settings")
    
    api_key = st.text_input(
        "Piloterr API Key",
        type="password",
        value=st.session_state.get("api_key", "")
    )
    st.session_state["api_key"] = api_key
    
    company_input = st.text_input("Crunchbase UUID or Name")
    if st.button("Add Company"):
        # TODO: Implement company addition logic
        pass

# Main content
st.title("Capital-Efficiency Radar")

# Plotly scatter plot placeholder
st.plotly_chart(px.scatter())

# Ag-Grid table placeholder
df = st.session_state["df"]
if not df.empty:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination()
    gb.configure_default_column(editable=False)
    grid_options = gb.build()
    AgGrid(df, gridOptions=grid_options)
else:
    st.write("No companies added yet. Add companies using the sidebar.")
