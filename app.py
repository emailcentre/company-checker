# company_checker.py - Complete Companies House Checker with FIXED API Key Issue
# Just run: streamlit run company_checker.py

import streamlit as st
import pandas as pd
import requests
import time
import base64
from datetime import datetime

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
    .stop-button {
        background-color: #DC2626 !important;
        color: white !important;
        border: 2px solid #B91C1C !important;
    }
    .stButton>button {
        width: 100%;
    }
    .test-box {
        padding: 1rem;
        background-color: #E0F2FE;
        border-radius: 0.5rem;
        border-left: 5px solid #0EA5E9;
        margin: 1rem 0;
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
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'api_key_valid' not in st.session_state:
    st.session_state.api_key_valid = None

# Main header
st.markdown('<h1 class="main-header">🏢 Companies House UK - Company Status Checker</h1>', unsafe_allow_html=True)

# STOP FUNCTION
def stop_processing():
    st.session_state.stop_processing = True
    st.warning("🛑 Stopping process...")

# TEST API KEY FUNCTION
def test_api_key(api_key):
    """Test if the API key is valid by making a simple search"""
    try:
        if not api_key:
            return False, "No API key provided"
        
        # Test with a well-known company
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {'q': 'BBC STUDIOS LIMITED', 'items_per_page': 1}
        
        response = requests.get(
            url, 
            params=params,
            auth=(api_key, ''),
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ API key is valid"
        elif response.status_code == 401:
            return False, "❌ Invalid API key - Unauthorized"
        elif response.status_code == 429:
            return False, "⚠️ Rate limit exceeded - try again later"
        else:
            return False, f"❌ API error (status {response.status_code})"
    
    except requests.exceptions.RequestException as e:
        return False, f"❌ Network error: {str(e)}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# SIMPLIFIED SEARCH FUNCTION - FIXED
def search_companies_house(company_name, api_key):
    """Search for a company on Companies House"""
    try:
        if not api_key:
            return {'error': 'API key is missing'}
        
        # Clean the company name
        search_term = str(company_name).strip()
        
        # Make the API call
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {
            'q': search_term,
            'items_per_page': 5  # Get more results for better matching
        }
        
        response = requests.get(
            url, 
            params=params,
            auth=(api_key, ''),
            timeout=10
        )
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                return {
                    'company_name': search_term,
                    'company_number': 'NOT FOUND',
                    'company_status': 'NOT FOUND',
                    'match_score': 0,
                    'total_matches_found': 0,
                    'error': 'No companies found'
                }
            
            # Return the first match
            first_match = items[0]
            return {
                'company_name': first_match.get('title', ''),
                'company_number': first_match.get('company_number', ''),
                'company_status': first_match.get('company_status', ''),
                'company_type': first_match.get('company_type', ''),
                'address': first_match.get('address_snippet', ''),
                'date_of_creation': first_match.get('date_of_creation', ''),
                'match_score': 95,  # High score for first match
                'total_matches_found': len(items)
            }
            
        elif response.status_code == 401:
            return {'error': 'Invalid API key - Unauthorized'}
        elif response.status_code == 429:
            return {'error': 'Rate limit exceeded'}
        else:
            return {'error': f'API error (status {response.status_code})'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

# PROCESS FUNCTION
def process_companies(df, column_name, api_key, debug_mode=False):
    """Process all companies with stop capability"""
    results = []
    total = len(df)
    
    if total == 0:
        return pd.DataFrame()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    stop_container = st.empty()
    
    # Display stop button
    with stop_container:
        st.button("🛑 Stop Processing", on_click=stop_processing, key="stop_button", 
                 type="secondary", use_container_width=True)
    
    for i, row in df.iterrows():
        if st.session_state.stop_processing:
            status_text.warning(f"🛑 Process stopped at row {i+1}/{total}")
            break
        
        company_name = str(row[column_name])
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Processing {i+1}/{total}: {company_name[:50]}...")
        
        # Search Companies House
        result = search_companies_house(company_name, api_key)
        
        # Debug output
        if debug_mode:
            with st.expander(f"Debug: {company_name[:30]}...", expanded=False):
                st.write(f"**Original:** {company_name}")
                st.write(f"**Result:** {result}")
        
        # Combine with original data
        result_row = row.to_dict()
        result_row.update({
            'ch_company_name': result.get('company_name', ''),
            'ch_company_number': result.get('company_number', ''),
            'ch_company_status': result.get('company_status', ''),
            'ch_company_type': result.get('company_type', ''),
            'ch_address': result.get('address', ''),
            'ch_date_of_creation': result.get('date_of_creation', ''),
            'ch_match_score': result.get('match_score', 0),
            'ch_error': result.get('error', ''),
            'ch_matches_found': result.get('total_matches_found', 0)
        })
        results.append(result_row)
        
        # Rate limiting for free API tier
        time.sleep(0.6)
    
    stop_container.empty()
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

# DOWNLOAD FUNCTION
def get_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV File</a>'
    return href

# SIDEBAR
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # API Key Section
    st.subheader("1. Enter & Test API Key")
    api_key = st.text_input(
        "Companies House API Key", 
        type="password",
        value=st.session_state.api_key,
        help="Get from https://developer.company-information.service.gov.uk/"
    )
    
    # Test API Button
    if st.button("🔍 Test API Key", type="secondary"):
        if api_key:
            with st.spinner("Testing API key..."):
                is_valid, message = test_api_key(api_key)
                st.session_state.api_key_valid = is_valid
                st.session_state.api_key = api_key
                
                if is_valid:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.warning("Please enter an API key first")
    
    # Show API status
    if st.session_state.api_key_valid is not None:
        if st.session_state.api_key_valid:
            st.markdown('<div class="test-box">✅ API Key is working</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="test-box">❌ API Key has issues</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Debug mode
    debug_mode = st.checkbox("🔧 Enable Debug Mode", 
                           help="Show detailed search information")
    
    st.markdown("---")
    
    # Emergency stop
    st.subheader("🛑 Emergency Stop")
    st.button("Force Stop All Processing", 
             on_click=stop_processing,
             help="Use if app becomes unresponsive",
             type="primary",
             use_container_width=True)
    
    st.markdown("---")
    
    # Instructions
    st.subheader("📋 Quick Test")
    st.markdown("""
    **Test with these names:**
    1. BBC STUDIOS LIMITED
    2. TESCO PLC  
    3. SAINSBURY'S SUPERMARKETS LTD
    """)

# MAIN CONTENT
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Step 1: Upload Your File")
    
    uploaded_file = st.file_uploader(
        "Choose CSV or Excel file",
        type=['csv', 'xlsx', 'xls']
    )
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File loaded! {len(df)} rows found")
            
            st.subheader("🔍 Step 2: Select Company Name Column")
            if len(df.columns) > 0:
                column_name = st.selectbox(
                    "Select column with company names",
                    options=df.columns.tolist(),
                    index=0
                )
                
                st.info(f"Selected: **{column_name}**")
                
                # Show first few names
                with st.expander("👀 First 5 Company Names"):
                    for i, name in enumerate(df[column_name].head(5).tolist()):
                        st.write(f"{i+1}. {name}")
            else:
                st.error("No columns found!")
                
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with col2:
    st.subheader("🚀 Step 3: Process Companies")
    
    # QUICK TEST BUTTON
    st.markdown("### Quick Test First")
    if st.button("🔬 Test with BBC STUDIOS LIMITED", type="secondary"):
        if not st.session_state.api_key:
            st.warning("Enter API key in sidebar first")
        else:
            with st.spinner("Testing with BBC STUDIOS LIMITED..."):
                result = search_companies_house("BBC STUDIOS LIMITED", st.session_state.api_key)
                if 'error' in result:
                    st.error(f"Test failed: {result['error']}")
                else:
                    st.success("✅ Test successful!")
                    st.write(f"**Found:** {result['company_name']}")
                    st.write(f"**Company Number:** {result['company_number']}")
                    st.write(f"**Status:** {result['company_status']}")
    
    st.markdown("---")
    
    if uploaded_file and 'df' in locals() and 'column_name' in locals():
        if not st.session_state.api_key:
            st.warning("⚠️ Enter your API key in the sidebar")
        else:
            if st.button("🔍 Start Checking All Companies", 
                        type="primary", 
                        use_container_width=True,
                        disabled=st.session_state.processing):
                
                st.session_state.stop_processing = False
                st.session_state.processing = True
                
                with st.spinner("Starting Companies House search..."):
                    try:
                        # Process companies
                        results_df = process_companies(df, column_name, 
                                                     st.session_state.api_key, 
                                                     debug_mode)
                        
                        st.session_state.results_df = results_df
                        st.session_state.processing = False
                        
                        if st.session_state.stop_processing:
                            st.warning(f"⚠️ Processing stopped early. {len(results_df)}/{len(df)} processed.")
                        else:
                            st.success(f"✅ Complete! {len(results_df)} companies processed.")
                        
                        # Show summary
                        st.subheader("📈 Results")
                        
                        if len(results_df) > 0:
                            found = len(results_df[results_df['ch_company_number'] != 'NOT FOUND'])
                            not_found = len(results_df) - found
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Found", found)
                            with col_b:
                                st.metric("Not Found", not_found)
                            
                            # Show results
                            with st.expander("📋 View Results"):
                                display_df = results_df[[column_name, 'ch_company_name', 'ch_company_status', 'ch_company_number']]
                                st.dataframe(display_df, use_container_width=True)
                            
                            # Download
                            if len(results_df) > 0:
                                st.subheader("📥 Download")
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = f"companies_house_results_{timestamp}.csv"
                                st.markdown(get_download_link(results_df, filename), unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.session_state.processing = False
    else:
        st.info("👈 Upload a file to begin")

# FOOTER
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Using official Companies House API • Get API key: <a href="https://developer.company-information.service.gov.uk/" target="_blank">developer.company-information.service.gov.uk</a></p>
</div>
""", unsafe_allow_html=True)

# Auto-reset stop flag
if not st.session_state.processing and st.session_state.stop_processing:
    st.session_state.stop_processing = False
