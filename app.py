import streamlit as st
import pandas as pd
import requests
import time
import base64
from datetime import datetime
import os

# Get API key from environment variable (Railway will set this)
COMPANIES_HOUSE_API_KEY = os.environ.get("COMPANIES_HOUSE_API_KEY", "")

# Page configuration
st.set_page_config(
    page_title="Companies House Checker",
    page_icon="🏢",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .api-box {
        padding: 1rem;
        background-color: #F0F9FF;
        border-radius: 0.5rem;
        border: 1px solid #0EA5E9;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'stop_processing' not in st.session_state:
    st.session_state.stop_processing = False
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Main header
st.markdown('<h1 class="main-header">🏢 Companies House UK - Company Status Checker</h1>', unsafe_allow_html=True)

# STOP FUNCTION
def stop_processing():
    st.session_state.stop_processing = True

# SIMPLE SEARCH FUNCTION
def search_companies_house(company_name):
    """Search for a company on Companies House"""
    try:
        if not COMPANIES_HOUSE_API_KEY:
            return {'error': 'API key not configured'}
        
        search_term = str(company_name).strip()
        
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {'q': search_term, 'items_per_page': 3}
        
        response = requests.get(
            url, 
            params=params,
            auth=(COMPANIES_HOUSE_API_KEY, ''),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            if items:
                company = items[0]
                return {
                    'company_name': company.get('title', ''),
                    'company_number': company.get('company_number', ''),
                    'company_status': company.get('company_status', ''),
                    'address': company.get('address_snippet', ''),
                    'match_score': 95
                }
            else:
                return {
                    'company_name': search_term,
                    'company_number': 'NOT FOUND',
                    'company_status': 'NOT FOUND'
                }
        else:
            return {'error': f'API Error {response.status_code}'}
    
    except Exception as e:
        return {'error': f'Error: {str(e)}'}

# PROCESS FUNCTION
def process_companies(df, column_name):
    """Process all companies"""
    results = []
    total = len(df)
    
    if total == 0:
        return pd.DataFrame()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, row in df.iterrows():
        if st.session_state.stop_processing:
            status_text.warning(f"🛑 Stopped at row {i+1}/{total}")
            break
        
        company_name = str(row[column_name])
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Processing {i+1}/{total}: {company_name[:40]}...")
        
        # Search Companies House
        result = search_companies_house(company_name)
        
        # Combine with original data
        result_row = row.to_dict()
        result_row.update({
            'ch_company_name': result.get('company_name', ''),
            'ch_company_number': result.get('company_number', ''),
            'ch_company_status': result.get('company_status', ''),
            'ch_address': result.get('address', ''),
            'ch_error': result.get('error', '')
        })
        results.append(result_row)
        
        time.sleep(0.7)  # Rate limiting
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

# DOWNLOAD FUNCTION
def get_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV</a>'
    return href

# SIDEBAR
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # API Status
    st.subheader("API Status")
    if COMPANIES_HOUSE_API_KEY:
        st.success("✅ API Key is configured")
        # Quick test
        if st.button("🔍 Test API Connection", type="secondary"):
            with st.spinner("Testing..."):
                result = search_companies_house("BBC STUDIOS LIMITED")
                if 'error' not in result:
                    st.success("✅ API is working!")
                    st.write(f"Found: {result.get('company_name')}")
                else:
                    st.error(f"Test failed: {result.get('error')}")
    else:
        st.error("❌ API Key missing")
        st.info("""
        Add your API key in Railway:
        1. Go to your project on Railway
        2. Click "Variables" tab
        3. Add: COMPANIES_HOUSE_API_KEY = your-key-here
        """)
    
    st.markdown("---")
    
    # Emergency stop
    st.subheader("🛑 Emergency Stop")
    st.button("Stop Processing", on_click=stop_processing, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📋 How to Use")
    st.markdown("""
    1. **Upload** CSV/Excel file
    2. **Select** company name column
    3. **Click** 'Process Companies'
    4. **Download** results
    """)

# MAIN CONTENT
st.subheader("📤 Upload Your File")
uploaded_file = st.file_uploader("Choose CSV or Excel", type=['csv', 'xlsx', 'xls'])

if uploaded_file:
    try:
        # Read file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ Loaded {len(df)} rows")
        
        # Select column
        column_name = st.selectbox(
            "Select column with company names:",
            options=df.columns.tolist(),
            index=0
        )
        
        # Preview
        with st.expander("👁️ Preview First 5 Rows"):
            st.dataframe(df[[column_name]].head(), use_container_width=True)
        
        # Process button
        if st.button("▶️ Process All Companies", type="primary", use_container_width=True):
            if not COMPANIES_HOUSE_API_KEY:
                st.error("❌ API key not configured. Please add it in Railway Variables.")
            else:
                st.session_state.stop_processing = False
                st.session_state.processing = True
                
                # Process
                with st.spinner(f"Processing {len(df)} companies..."):
                    results_df = process_companies(df, column_name)
                    st.session_state.results_df = results_df
                
                # Show results
                if len(results_df) > 0:
                    st.success(f"✅ Processed {len(results_df)} companies")
                    
                    # Statistics
                    found = len(results_df[results_df['ch_company_number'] != 'NOT FOUND'])
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Companies Found", found)
                    with col2:
                        st.metric("Not Found", len(results_df) - found)
                    
                    # Show table
                    with st.expander("📋 View Results", expanded=True):
                        st.dataframe(results_df, use_container_width=True, height=400)
                    
                    # Download
                    st.subheader("📥 Download Results")
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                    filename = f"companies_house_results_{timestamp}.csv"
                    st.markdown(get_download_link(results_df, filename), unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"Error: {str(e)}")

# FOOTER
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>Deployed on Railway.app • Using Companies House API • Free tier: 600 requests/day</p>
</div>
""", unsafe_allow_html=True)

