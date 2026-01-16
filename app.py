# company_checker.py - Complete Companies House Checker with Better Matching & Stop Button
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

# Main header
st.markdown('<h1 class="main-header">🏢 Companies House UK - Company Status Checker</h1>', unsafe_allow_html=True)

# STOP FUNCTION
def stop_processing():
    st.session_state.stop_processing = True
    st.warning("🛑 Stopping process...")

# IMPROVED SEARCH FUNCTION WITH BETTER MATCHING
def search_companies_house(company_name, api_key):
    """Search for a company on Companies House with intelligent matching"""
    try:
        original_name = str(company_name).strip()
        if not original_name:
            return {'error': 'Empty company name'}
        
        # Prepare multiple search variations
        search_variations = []
        
        # 1. Original name first
        search_variations.append(original_name)
        
        # 2. Remove common suffixes
        name_clean = original_name.upper()
        suffixes = ['LIMITED', 'LTD', 'LTD.', 'PLC', 'PLC.', 'LLP', 'LLP.', 
                   'LIMITED LIABILITY PARTNERSHIP', 'GROUP', 'HOLDINGS', 'HOLDING']
        
        for suffix in suffixes:
            if name_clean.endswith(' ' + suffix):
                name_clean = name_clean[:-(len(suffix)+1)].strip()
            elif name_clean.endswith(suffix):
                name_clean = name_clean[:-len(suffix)].strip()
        
        if name_clean != original_name.upper():
            search_variations.append(name_clean)
            search_variations.append(name_clean + " LIMITED")
            search_variations.append(name_clean + " LTD")
        
        # 3. Remove "THE " prefix
        if name_clean.startswith("THE "):
            without_the = name_clean[4:].strip()
            search_variations.append(without_the)
        
        # 4. Remove punctuation
        clean_no_punct = ''.join(c for c in name_clean if c.isalnum() or c == ' ')
        if clean_no_punct != name_clean:
            search_variations.append(clean_no_punct)
        
        # 5. Try abbreviated "&" vs "AND"
        if ' AND ' in clean_no_punct:
            search_variations.append(clean_no_punct.replace(' AND ', ' & '))
        if ' & ' in clean_no_punct:
            search_variations.append(clean_no_punct.replace(' & ', ' AND '))
        
        # Remove duplicates while preserving order
        seen = set()
        search_variations = [x for x in search_variations if not (x in seen or seen.add(x))]
        
        # Try each search variation
        best_match = None
        best_score = 0
        all_items = []
        search_term_used = ""
        
        for search_term in search_variations[:6]:  # Try first 6 variations
            url = "https://api.company-information.service.gov.uk/search/companies"
            params = {'q': search_term, 'items_per_page': 10}
            
            response = requests.get(url, params=params, auth=(api_key, ''), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                all_items.extend(items)
                
                # Score each result
                for item in items:
                    api_name = item.get('title', '').upper()
                    search_upper = original_name.upper()
                    
                    # Calculate match score
                    if api_name == search_upper:
                        score = 100
                    elif api_name in search_upper or search_upper in api_name:
                        score = 90
                    else:
                        # Clean both for comparison
                        api_clean = api_name
                        for suffix in suffixes:
                            api_clean = api_clean.replace(suffix, '')
                        api_clean = api_clean.strip()
                        
                        search_clean = search_upper
                        for suffix in suffixes:
                            search_clean = search_clean.replace(suffix, '')
                        search_clean = search_clean.strip()
                        
                        if api_clean == search_clean:
                            score = 85
                        elif (api_clean.startswith(search_clean[:min(10, len(search_clean))]) or 
                              search_clean.startswith(api_clean[:min(10, len(api_clean))])):
                            score = 75
                        else:
                            # Check word overlap
                            api_words = set(api_clean.split())
                            search_words = set(search_clean.split())
                            common_words = api_words.intersection(search_words)
                            if common_words:
                                score = 60 + len(common_words) * 5
                            else:
                                score = 50
                    
                    if score > best_score:
                        best_score = score
                        best_match = item
                        search_term_used = search_term
            
            if best_score >= 80:  # Good enough match found
                break
            
            time.sleep(0.2)  # Brief pause between API calls
        
        # Return results
        if best_match and best_score >= 65:  # Lower threshold to catch more matches
            return {
                'company_name': best_match.get('title', ''),
                'company_number': best_match.get('company_number', ''),
                'company_status': best_match.get('company_status', ''),
                'company_type': best_match.get('company_type', ''),
                'address': best_match.get('address_snippet', ''),
                'date_of_creation': best_match.get('date_of_creation', ''),
                'match_score': best_score,
                'search_term_used': search_term_used,
                'total_matches_found': len(all_items)
            }
        else:
            return {
                'company_name': original_name,
                'company_number': 'NOT FOUND',
                'company_status': 'NOT FOUND',
                'match_score': best_score,
                'search_term_used': search_term_used or 'All variations',
                'total_matches_found': len(all_items),
                'error': f'No good match found (best score: {best_score}%)'
            }
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Network error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

# PROCESS FUNCTION WITH STOP BUTTON
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
                st.write(f"**Search used:** {result.get('search_term_used', 'N/A')}")
                st.write(f"**Matches found:** {result.get('total_matches_found', 0)}")
                st.write(f"**Best match:** {result.get('company_name', 'None')}")
                st.write(f"**Match score:** {result.get('match_score', 0)}%")
                if 'error' in result:
                    st.write(f"**Error:** {result['error']}")
        
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
            'ch_search_used': result.get('search_term_used', ''),
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
    
    # API Key
    st.subheader("1. Enter API Key")
    api_key = st.text_input(
        "Companies House API Key", 
        type="password",
        value=st.session_state.api_key,
        help="Get from https://developer.company-information.service.gov.uk/"
    )
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("✅ API Key saved")
    
    st.markdown("---")
    
    # Debug mode
    debug_mode = st.checkbox("🔧 Enable Debug Mode", 
                           help="Show detailed search information for troubleshooting")
    
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
    st.subheader("📋 How to Use")
    st.markdown("""
    1. **Enter API key** above
    2. **Upload file** with company names
    3. **Select** correct name column
    4. **Click** 'Check Companies'
    5. **Download** results
    """)
    
    st.info("""
    **API Limits:** 
    - Free tier: 600 requests/day
    - Processing: ~2 seconds per company
    """)

# MAIN CONTENT
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Step 1: Upload Your File")
    
    uploaded_file = st.file_uploader(
        "Choose CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="File should contain at least one column with company names"
    )
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File loaded! {len(df)} rows found")
            
            with st.expander("📊 Preview First 10 Rows"):
                st.dataframe(df.head(10), use_container_width=True)
            
            st.subheader("🔍 Step 2: Select Company Name Column")
            if len(df.columns) > 0:
                column_name = st.selectbox(
                    "Select column containing company names",
                    options=df.columns.tolist(),
                    index=0
                )
                
                st.info(f"Selected: **{column_name}** - {df[column_name].nunique()} unique names")
                
                # Show sample names
                sample_names = df[column_name].dropna().head(10).tolist()
                with st.expander("👀 Sample Company Names"):
                    for i, name in enumerate(sample_names):
                        st.write(f"{i+1}. {name}")
            else:
                st.error("No columns found in the file!")
                
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with col2:
    st.subheader("🚀 Step 3: Process Companies")
    
    if uploaded_file and 'df' in locals() and 'column_name' in locals():
        if not st.session_state.api_key:
            st.warning("⚠️ Please enter your API key in the sidebar")
        else:
            # Reset stop flag when starting
            if st.button("🔍 Start Checking Companies", 
                        type="primary", 
                        use_container_width=True,
                        disabled=st.session_state.processing):
                
                st.session_state.stop_processing = False
                st.session_state.processing = True
                
                with st.spinner("Connecting to Companies House API..."):
                    try:
                        # Process companies
                        results_df = process_companies(df, column_name, 
                                                     st.session_state.api_key, 
                                                     debug_mode)
                        
                        st.session_state.results_df = results_df
                        st.session_state.processing = False
                        
                        if st.session_state.stop_processing:
                            st.warning(f"⚠️ Processing was stopped early.\n"
                                     f"**{len(results_df)} out of {len(df)}** companies were processed.")
                        else:
                            st.success(f"✅ Processing complete!\n"
                                     f"All **{len(results_df)}** companies processed successfully.")
                        
                        # Show summary statistics
                        st.subheader("📈 Results Summary")
                        
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            found = len(results_df[results_df['ch_company_number'] != 'NOT FOUND'])
                            st.metric("Companies Found", f"{found}/{len(results_df)}", 
                                    delta=f"{found/len(results_df)*100:.1f}%" if len(results_df) > 0 else "0%")
                        
                        with col_b:
                            active = len(results_df[results_df['ch_company_status'] == 'active'])
                            st.metric("Active Companies", active)
                        
                        with col_c:
                            if len(results_df) > 0 and 'ch_match_score' in results_df.columns:
                                avg_score = results_df['ch_match_score'].mean()
                                st.metric("Avg Match Score", f"{avg_score:.1f}%")
                        
                        # Show results table
                        with st.expander("📋 View All Results", expanded=True):
                            display_cols = [column_name, 'ch_company_name', 'ch_company_status', 
                                          'ch_company_number', 'ch_match_score']
                            display_cols = [c for c in display_cols if c in results_df.columns]
                            st.dataframe(results_df[display_cols], use_container_width=True, height=400)
                        
                        # Download section
                        if len(results_df) > 0:
                            st.subheader("📥 Step 4: Download Results")
                            
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"companies_house_results_{timestamp}.csv"
                            
                            st.markdown(get_download_link(results_df, filename), unsafe_allow_html=True)
                            
                            # Show match examples
                            if 'ch_match_score' in results_df.columns:
                                good_matches = results_df[results_df['ch_match_score'] >= 80].head(3)
                                if len(good_matches) > 0:
                                    with st.expander("🎯 Example Good Matches"):
                                        for _, row in good_matches.iterrows():
                                            st.markdown(f"""
                                            **Original:** {row[column_name]}  
                                            **Matched:** {row['ch_company_name']}  
                                            **Status:** {row['ch_company_status'].upper()}  
                                            **Company No:** {row['ch_company_number']}  
                                            **Match Score:** {row['ch_match_score']}%
                                            ---
                                            """)
                    
                    except Exception as e:
                        st.error(f"Processing error: {str(e)}")
                        st.session_state.processing = False
    else:
        st.info("👈 Please upload a CSV/Excel file with company names to begin")

# FOOTER
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>This tool uses the official Companies House API. Ensure compliance with their 
    <a href="https://developer.company-information.service.gov.uk/terms" target="_blank">terms of use</a>.</p>
    <p>Match scores below 70% may require manual verification.</p>
</div>
""", unsafe_allow_html=True)

# Auto-reset stop flag when not processing
if not st.session_state.processing and st.session_state.stop_processing:
    st.session_state.stop_processing = False

