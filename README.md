# Capital-Efficiency Radar

A Streamlit application for analyzing company capital efficiency metrics using Crunchbase data.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Piloterr API key:
   - Create a `.env` file in the root directory
   - Add your API key:
   ```
   PILOTERR_API_KEY=a3f7439e-d753-44d3-a34a-d0b6f0a0a9c8
   ```

3. Run the application:
```bash
streamlit run app.py
```

## Features

- Interactive scatter plot showing company age vs capital efficiency
- Metrics dashboard with key insights
- Downloadable company data
- Dark mode theme
- Test data for demonstration

## Usage

1. Enter your Piloterr API key in the sidebar
2. Add companies using their Crunchbase UUID or name
3. Use the "Add Test Companies" button to add OpenAI and GitHub for demonstration
4. Explore the interactive visualizations and metrics

## Security Note

Never commit your API keys to version control. Always use environment variables or secure secrets management.
