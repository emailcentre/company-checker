# company_checker.py - Complete Companies House Checker Web App
# Just run: streamlit run company_checker.py

import streamlit as st
import pandas as pd
import requests
import time
import os
from io import BytesIO
import base64
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Companies House Checker",
    page_icon="🏢",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #D1FAE5;
        border-radius: 0.5rem;
        border-left: 5px solid #10B981;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #FEF3C7;
        border-radius: 0.5rem;
        border-left: 5px solid #F59E0B;
        margin: 1rem 0;
    }
    .company-card {
        padding: 1rem;
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">🏢 Companies House UK - Company Status Checker</h1>', unsafe_allow_html=True)

# Initialize session state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# Sidebar for API key and instructions
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # API Key input
    st.subheader("1. Enter API Key")
    api_key = st.text_input(
        "Companies House API Key", 
        type="password",
        help="Get your API key from https://developer.company-information.service.gov.uk/",
        value=st.session_state.api_key
    )
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("✅ API Key saved")
    
    st.markdown("---")
    
    st.subheader("📋 How to Use")
    st.markdown("""
    1. **Enter API key** (get one free from Companies House)
    2. **Upload CSV/Excel** file with company names
    3. **Select** the column containing company names
    4. **Click** 'Check Companies'
    5. **Download** results
    """)
    
    st.markdown("---")
    st.subheader("📝 File Format")
    st.markdown("""
    Your file should contain at least one column with company names.
    
    **Example CSV:**
    ```
    Company Name
    BBC Studios Ltd
    Tesco PLC
    ```
    """)
    
    st.markdown("---")
    st.info("""
    **Note:** 
    - Free API tier: 600 requests/day
    - Processing time: ~2 seconds per company
    """)

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Step 1: Upload Your File")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload your file containing company names"
    )
    
    if uploaded_file:
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File loaded successfully! Found {len(df)} rows")
            
            # Show preview
            with st.expander("📊 Preview your data"):
                st.dataframe(df.head(), use_container_width=True)
            
            # Column selection
            st.subheader("🔍 Step 2: Select Company Name Column")
            column_name = st.selectbox(
                "Select the column containing company names",
                options=df.columns.tolist()
            )
            
            if column_name:
                st.info(f"Selected column: **{column_name}**")
                
                # Show unique names
                unique_names = df[column_name].dropna().unique()
                st.write(f"Found {len(unique_names)} unique company names")
                
                with st.expander("👀 See company names to check"):
                    for i, name in enumerate(unique_names[:20]):
                        st.write(f"{i+1}. {name}")
                    if len(unique_names) > 20:
                        st.write(f"... and {len(unique_names) - 20} more")

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# Companies House API functions
def search_companies_house(company_name, api_key):
    """Search for a company on Companies House"""
    try:
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {'q': company_name, 'items_per_page': 1}
        
        response = requests.get(
            url, 
            params=params,
            auth=(api_key, '')
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                company = data['items'][0]
                return {
                    'company_name': company.get('title', ''),
                    'company_number': company.get('company_number', ''),
                    'company_status': company.get('company_status', ''),
                    'company_type': company.get('company_type', ''),
                    'address': company.get('address_snippet', ''),
                    'date_of_creation': company.get('date_of_creation', ''),
                    'match_score': 100 if company['title'].lower() == company_name.lower() else 80
                }
        elif response.status_code == 401:
            return {'error': 'Invalid API key'}
        elif response.status_code == 429:
            return {'error': 'Rate limit exceeded'}
        
        return {'company_name': company_name, 'company_number': 'Not found', 'company_status': 'Not found'}
    
    except Exception as e:
        return {'error': str(e)}

def process_companies(df, column_name, api_key):
    """Process all companies in the dataframe"""
    results = []
    total = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, row in df.iterrows():
        company_name = str(row[column_name])
        
        # Update progress
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Processing {i+1}/{total}: {company_name[:50]}...")
        
        # Search Companies House
        result = search_companies_house(company_name, api_key)
        
        # Combine original row with results
        result_row = row.to_dict()
        result_row.update({
            'ch_company_name': result.get('company_name', ''),
            'ch_company_number': result.get('company_number', ''),
            'ch_company_status': result.get('company_status', ''),
            'ch_company_type': result.get('company_type', ''),
            'ch_address': result.get('address', ''),
            'ch_date_of_creation': result.get('date_of_creation', ''),
            'ch_match_score': result.get('match_score', 0),
            'ch_error': result.get('error', '')
        })
        
        results.append(result_row)
        
        # Rate limiting (2 requests per second for free tier)
        time.sleep(0.5)
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

# Download link function
def get_download_link(df, filename):
    """Generate a download link for the dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV File</a>'
    return href

# Process button
with col2:
    st.subheader("🚀 Step 3: Process Companies")
    
    if uploaded_file and 'df' in locals() and 'column_name' in locals():
        if not st.session_state.api_key:
            st.warning("⚠️ Please enter your API key in the sidebar first")
        else:
            if st.button("🔍 Check All Companies", type="primary", use_container_width=True):
                st.session_state.processing = True
                
                with st.spinner("Processing companies with Companies House API..."):
                    try:
                        # Process companies
                        results_df = process_companies(df, column_name, st.session_state.api_key)
                        st.session_state.results_df = results_df
                        
                        st.success(f"✅ Processed {len(results_df)} companies successfully!")
                        
                        # Show summary
                        st.subheader("📈 Results Summary")
                        
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            found = len(results_df[results_df['ch_company_number'] != 'Not found'])
                            st.metric("Companies Found", f"{found}/{len(results_df)}")
                        
                        with col_b:
                            active = len(results_df[results_df['ch_company_status'] == 'active'])
                            st.metric("Active Companies", active)
                        
                        with col_c:
                            avg_score = results_df['ch_match_score'].mean()
                            st.metric("Average Match Score", f"{avg_score:.1f}%")
                        
                        # Show results table
                        with st.expander("📋 View Detailed Results", expanded=True):
                            display_cols = [column_name, 'ch_company_name', 'ch_company_status', 
                                          'ch_company_number', 'ch_address', 'ch_match_score']
                            display_df = results_df[display_cols]
                            st.dataframe(display_df, use_container_width=True)
                        
                        # Download section
                        st.subheader("📥 Step 4: Download Results")
                        
                        # Generate timestamp for filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"companies_house_results_{timestamp}.csv"
                        
                        # Create download link
                        st.markdown(get_download_link(results_df, filename), unsafe_allow_html=True)
                        
                        # Show sample results
                        with st.expander("🎯 See Sample Matches"):
                            for i, row in results_df.head(3).iterrows():
                                if row['ch_company_number'] != 'Not found':
                                    st.markdown(f"""
                                    <div class="company-card">
                                    <strong>Original:</strong> {row[column_name]}<br>
                                    <strong>Matched:</strong> {row['ch_company_name']}<br>
                                    <strong>Status:</strong> <span style="color:{'green' if row['ch_company_status'] == 'active' else 'orange'}">
                                    {row['ch_company_status'].upper()}</span><br>
                                    <strong>Company No:</strong> {row['ch_company_number']}
                                    </div>
                                    """, unsafe_allow_html=True)
                    
                    except Exception as e:
                        st.error(f"Error processing companies: {str(e)}")
                        st.info("Please check your API key and try again")
                
                st.session_state.processing = False
    else:
        st.info("👈 Please upload a file and select a column to begin")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>This tool uses the official Companies House API. 
    Ensure you comply with their <a href="https://developer.company-information.service.gov.uk/terms" target="_blank">terms of use</a>.</p>
    <p>Made with ❤️ for UK businesses</p>
</div>
""", unsafe_allow_html=True)