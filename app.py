# company_checker.py - Companies House Checker with FIXED API Authentication
# Just run: streamlit run company_checker.py

import streamlit as st
import pandas as pd
import requests
import time
import base64
from datetime import datetime
import json

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
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'api_test_result' not in st.session_state:
    st.session_state.api_test_result = ""

# Main header
st.markdown('<h1 class="main-header">🏢 Companies House UK - Company Status Checker</h1>', unsafe_allow_html=True)

# STOP FUNCTION
def stop_processing():
    st.session_state.stop_processing = True

# TEST API KEY FUNCTION - CORRECT AUTHENTICATION
def test_api_key(api_key):
    """Test if the API key is valid"""
    try:
        if not api_key:
            return False, "❌ No API key provided"
        
        # Clean the API key (remove spaces, newlines)
        api_key = api_key.strip()
        
        # Make a simple test request
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {'q': 'BBC', 'items_per_page': 1}
        
        # CORRECT: Use HTTP Basic Auth with API key as username, empty password
        response = requests.get(
            url, 
            params=params,
            auth=(api_key, ''),  # THIS IS THE CORRECT FORMAT
            timeout=10
        )
        
        # Check response
        if response.status_code == 200:
            return True, "✅ API key is valid and working!"
        elif response.status_code == 400:
            return False, "❌ Bad request - Check API key format"
        elif response.status_code == 401:
            return False, "❌ Unauthorized - Invalid API key"
        elif response.status_code == 403:
            return False, "❌ Forbidden - API key doesn't have search permissions"
        elif response.status_code == 429:
            return False, "⚠️ Rate limit exceeded - Try again in an hour"
        else:
            return False, f"❌ HTTP Error {response.status_code}: {response.text[:100]}"
    
    except requests.exceptions.RequestException as e:
        return False, f"❌ Network error: {str(e)}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# SEARCH FUNCTION WITH CORRECT AUTH
def search_companies_house(company_name, api_key):
    """Search for a company on Companies House"""
    try:
        if not api_key:
            return {'error': 'API key is missing'}
        
        api_key = api_key.strip()
        search_term = str(company_name).strip()
        
        if not search_term:
            return {'error': 'Empty company name'}
        
        # Make the API call with CORRECT authentication
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {
            'q': search_term,
            'items_per_page': 5
        }
        
        headers = {
            'Accept': 'application/json'
        }
        
        response = requests.get(
            url, 
            params=params,
            auth=(api_key, ''),  # CORRECT AUTH
            headers=headers,
            timeout=15
        )
        
        # Log the response for debugging
        debug_info = {
            'status_code': response.status_code,
            'url': response.url
        }
        
        if response.status_code == 200:
            data = response.json()
            
            # Debug: Show raw response in debug mode
            if st.session_state.get('debug_mode', False):
                st.write(f"**Debug - Search for '{search_term}':**")
                st.json(data)
            
            items = data.get('items', [])
            total_results = data.get('total_results', 0)
            
            if total_results == 0 or not items:
                return {
                    'company_name': search_term,
                    'company_number': 'NOT FOUND',
                    'company_status': 'NOT FOUND',
                    'match_score': 0,
                    'total_matches': 0,
                    'api_debug': debug_info
                }
            
            # Get the best match (first item)
            company = items[0]
            
            return {
                'company_name': company.get('title', search_term),
                'company_number': company.get('company_number', ''),
                'company_status': company.get('company_status', ''),
                'company_type': company.get('company_type', ''),
                'address': company.get('address_snippet', ''),
                'date_of_creation': company.get('date_of_creation', ''),
                'match_score': 95,
                'total_matches': total_results,
                'api_debug': debug_info
            }
            
        else:
            return {
                'error': f'API Error {response.status_code}',
                'response_text': response.text[:200],
                'api_debug': debug_info
            }
    
    except requests.exceptions.Timeout:
        return {'error': 'Request timeout - API is slow or unresponsive'}
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

# PROCESS FUNCTION
def process_companies(df, column_name, api_key):
    """Process all companies"""
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
            status_text.warning(f"🛑 Stopped at row {i+1}/{total}")
            break
        
        company_name = str(row[column_name])
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Processing {i+1}/{total}: {company_name[:40]}...")
        
        # Search Companies House
        result = search_companies_house(company_name, api_key)
        
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
            'ch_total_matches': result.get('total_matches', 0)
        })
        results.append(result_row)
        
        # Rate limiting
        time.sleep(0.7)
    
    stop_container.empty()
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
    
    # API Key Section
    st.markdown('<div class="api-box">', unsafe_allow_html=True)
    st.subheader("1. API Key Setup")
    
    # Important note
    st.info("""
    **Get your FREE API key from:**
    [developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk/)
    
    Click "Get started" → "Create an account" → "Get a free API key"
    """)
    
    # API Key input
    api_key = st.text_area(
        "Paste your API key here:",
        value=st.session_state.api_key,
        height=100,
        help="Paste the full API key from Companies House"
    )
    
    # Format help
    with st.expander("📝 API Key Format Help"):
        st.markdown("""
        Your API key should look like:
        ```
        abc123de-f456-789g-h012-i3456789jkl0
        ```
        
        **Correct Format:** 32 characters with hyphens
        **Wrong Format:** Don't add "Basic " or "Bearer " prefix
        """)
    
    # Test button
    if st.button("🔐 Test This API Key", type="primary", use_container_width=True):
        if api_key:
            st.session_state.api_key = api_key.strip()
            with st.spinner("Testing API key..."):
                is_valid, message = test_api_key(st.session_state.api_key)
                st.session_state.api_test_result = message
                
                if is_valid:
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.warning("Please paste your API key first")
    
    # Show test result
    if st.session_state.api_test_result:
        st.write(st.session_state.api_test_result)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Debug mode
    debug_mode = st.checkbox("🔍 Enable Debug Mode", 
                           value=False,
                           key='debug_mode',
                           help="Show raw API responses")
    
    st.markdown("---")
    
    # Instructions
    st.subheader("🚀 Quick Start")
    st.markdown("""
    1. **Get API key** from link above
    2. **Paste & Test** the key
    3. **Upload** your CSV/Excel file
    4. **Select** company name column
    5. **Process** companies
    """)

# MAIN CONTENT
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Step 2: Upload Your File")
    
    uploaded_file = st.file_uploader(
        "Drag & drop CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="File must contain company names in one column"
    )
    
    if uploaded_file:
        try:
            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Loaded {len(df)} rows")
            
            # Select column
            st.subheader("🔍 Step 3: Select Column")
            column_name = st.selectbox(
                "Which column has company names?",
                options=df.columns.tolist(),
                index=0
            )
            
            # Preview
            with st.expander("👁️ Preview Data"):
                st.dataframe(df[[column_name]].head(10), use_container_width=True)
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    st.subheader("🚀 Step 4: Process Companies")
    
    if not st.session_state.api_key:
        st.warning("""
        ⚠️ **API Key Required**
        
        1. Get free key from: [Companies House Developer Portal](https://developer.company-information.service.gov.uk/)
        2. Paste in sidebar
        3. Click "Test This API Key"
        """)
    elif uploaded_file and 'df' in locals() and 'column_name' in locals():
        # Process button
        if st.button("▶️ Start Processing", 
                    type="primary", 
                    use_container_width=True,
                    disabled=st.session_state.processing):
            
            st.session_state.stop_processing = False
            st.session_state.processing = True
            
            # Process
            try:
                results_df = process_companies(df, column_name, st.session_state.api_key)
                st.session_state.results_df = results_df
                st.session_state.processing = False
                
                # Show results
                st.success(f"✅ Processed {len(results_df)} companies")
                
                # Statistics
                if len(results_df) > 0:
                    found = len(results_df[results_df['ch_company_number'] != 'NOT FOUND'])
                    not_found = len(results_df) - found
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("✅ Found", found, delta=f"{found/len(results_df)*100:.0f}%")
                    with col_b:
                        st.metric("❌ Not Found", not_found)
                    
                    # Show table
                    with st.expander("📋 View All Results", expanded=True):
                        cols_to_show = [column_name, 'ch_company_name', 'ch_company_status', 'ch_company_number']
                        cols_to_show = [c for c in cols_to_show if c in results_df.columns]
                        st.dataframe(results_df[cols_to_show], use_container_width=True, height=300)
                    
                    # Download
                    st.subheader("📥 Download Results")
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                    filename = f"companies_house_results_{timestamp}.csv"
                    st.markdown(get_download_link(results_df, filename), unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Processing error: {str(e)}")
                st.session_state.processing = False
    else:
        st.info("👈 Upload a file to begin processing")

# TROUBLESHOOTING SECTION
with st.expander("🛠️ Troubleshooting Common Issues", expanded=False):
    st.markdown("""
    ### **400 Bad Request Error**
    
    **Cause:** Wrong API key format or authentication method
    
    **Solution:**
    1. Get a **new API key** from [Companies House](https://developer.company-information.service.gov.uk/)
    2. **Don't modify** the key - paste it exactly as shown
    3. Key format should be: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
    
    ### **Test Your API Key Manually**
    
    You can test your API key directly using this curl command:
    ```bash
    curl "https://api.company-information.service.gov.uk/search/companies?q=BBC" \
      -u "YOUR_API_KEY:"
    ```
    
    ### **Still Having Issues?**
    
    1. **Clear browser cache** and restart the app
    2. **Try a different browser** (Chrome/Firefox)
    3. **Contact Companies House support** if key doesn't work
    """)

# FOOTER
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>Using official Companies House API • 
    <a href="https://developer.company-information.service.gov.uk/" target="_blank">Get your free API key</a> • 
    Rate limit: 600 requests/day free tier</p>
</div>
""", unsafe_allow_html=True)

# Reset stop flag
if not st.session_state.processing and st.session_state.stop_processing:
    st.session_state.stop_processing = False

