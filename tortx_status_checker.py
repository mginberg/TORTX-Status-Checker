import streamlit as st
import pandas as pd
import requests
import time
from io import BytesIO

# Set page config
st.set_page_config(page_title="TortX Status Checker", page_icon="📞", layout="wide")

# App title
st.title("📞 TortX Lead Status Checker")
st.markdown("Upload your Zapier history CSV to check lead statuses from TortX API")

# API Configuration
API_URL = "https://api.tortx.law/external/intake/status"
SUBSCRIPTION_KEY = "df7fbbbf94544018a06bf01f4400fb43"

def get_lead_status(lead_id, source_id, claim_type="Personal Injury"):
    """
    Call TortX API to get lead status with subscription-key in HEADER
    """
    # Skip if either value is empty/null
    if pd.isna(lead_id) or pd.isna(source_id) or str(lead_id).strip() == "" or str(source_id).strip() == "":
        return "Missing Data"
    
    try:
        # Put subscription-key in HEADER (not in URL params!)
        headers = {
            "subscription-key": SUBSCRIPTION_KEY
        }
        
        # Only LeadId, SourceId, and ClaimType go in params
        params = {
            "LeadId": str(lead_id).strip(),
            "SourceId": str(source_id).strip(),
            "ClaimType": claim_type
        }
        
        response = requests.post(API_URL, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Try different possible field names
                status = data.get("status") or data.get("Status") or data.get("statusDescription") or str(data)
                return status if status else "Success"
            except:
                return f"Success ({response.text[:50]})"
        else:
            return f"Error: {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

# File uploader
uploaded_file = st.file_uploader("Upload Zapier History CSV", type=['csv'])

if uploaded_file is not None:
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        st.success(f"✅ File uploaded successfully! Found {len(df)} rows")
        
        # Show preview of data
        with st.expander("📋 Data Preview", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
        
        # Check if required columns exist
        columns_list = df.columns.tolist()
        
        # Convert column letters to indices (0-based)
        col_l_idx = 11   # L column
        col_m_idx = 12   # M column
        col_ak_idx = 36  # AK column (SourceId)
        col_at_idx = 45  # AT column (LeadId)
        
        if len(columns_list) > max(col_l_idx, col_m_idx, col_ak_idx, col_at_idx):
            col_l = columns_list[col_l_idx]
            col_m = columns_list[col_m_idx]
            col_source_id = columns_list[col_ak_idx]
            col_lead_id = columns_list[col_at_idx]
            
            st.info(f"✅ Using columns: **LeadId (AT)**='{col_lead_id}', **SourceId (AK)**='{col_source_id}'")
            
            # Show sample data from these columns
            with st.expander("🔍 Sample Data from Target Columns", expanded=False):
                sample_df = df[[col_l, col_m, col_source_id, col_lead_id]].head(5)
                st.dataframe(sample_df, use_container_width=True)
            
            # Add claim type selector
            claim_type = st.selectbox(
                "Select Claim Type:",
                ["Personal Injury", "Property Damage", "Other"],
                index=0
            )
            
            # Button to fetch statuses
            if st.button("🔄 Fetch Lead Statuses", type="primary"):
                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Initialize status column
                statuses = []
                error_count = 0
                
                # Process each row
                total_rows = len(df)
                for idx, row in df.iterrows():
                    lead_id = row[col_lead_id]
                    source_id = row[col_source_id]
                    
                    status_text.text(f"Processing row {idx + 1}/{total_rows} - LeadId: {lead_id}")
                    
                    # Get status from API
                    status = get_lead_status(lead_id, source_id, claim_type)
                    statuses.append(status)
                    
                    if "Error" in str(status):
                        error_count += 1
                    
                    # Update progress
                    progress_bar.progress((idx + 1) / total_rows)
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.2)
                
                if error_count == total_rows:
                    status_text.error("⚠️ All requests failed! Check API credentials.")
                elif error_count > 0:
                    status_text.warning(f"⚠️ Complete with {error_count} errors.")
                else:
                    status_text.success("✅ All statuses fetched successfully!")
                
                # Create output dataframe with only columns L, M, and Status
                output_df = pd.DataFrame({
                    col_l: df[col_l],
                    col_m: df[col_m],
                    'TortX_Status': statuses
                })
                
                # Display results
                st.subheader("Results")
                st.dataframe(output_df, use_container_width=True)
                
                # Download button
                csv_buffer = BytesIO()
                output_df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                st.download_button(
                    label="📥 Download Report",
                    data=csv_buffer,
                    file_name="tortx_status_report.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                # Show status summary
                st.subheader("Status Summary")
                status_counts = output_df['TortX_Status'].value_counts()
                st.bar_chart(status_counts)
                
        else:
            st.error(f"❌ The uploaded CSV doesn't have enough columns. Found {len(columns_list)} columns, need at least 46.")
            st.info(f"Please make sure your CSV has columns L, M, AK (SourceId), and AT (LeadId)")
            
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    st.info("👆 Please upload a CSV file to get started")
    
    # Instructions
    st.markdown("---")
    st.markdown("""
    ### 📖 How to Use
    
    1. **Export your Zapier history** as a CSV file
    2. **Upload it** using the file picker above
    3. **Select the claim type** (default: Personal Injury)
    4. **Click "Fetch Lead Statuses"** to process all leads
    5. **Download the report** with the status column added
    
    ### 📊 Required Columns
    
    - **Column AK**: SourceId
    - **Column AT**: LeadId
    - **Column L**: Will be included in report
    - **Column M**: Will be included in report
    """)

# Add footer
st.markdown("---")
st.markdown("💡 **Tip:** Subscription key is sent in header for security")
