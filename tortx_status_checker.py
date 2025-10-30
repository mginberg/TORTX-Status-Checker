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
CLAIM_TYPE = "Personal Injury"

def get_lead_status(lead_id, source_id):
    """
    Call TortX API to get lead status
    """
    try:
        params = {
            "subscription-key": SUBSCRIPTION_KEY,
            "LeadId": lead_id,
            "SourceId": source_id,
            "ClaimType": CLAIM_TYPE
        }

        response = requests.post(API_URL, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # Adjust this based on actual API response structure
            return data.get("status", "Unknown")
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
        st.subheader("Data Preview")
        st.dataframe(df.head(), use_container_width=True)

        # Check if required columns exist
        # Column AR is index 43 (0-indexed), Column AJ is index 35
        columns_list = df.columns.tolist()

        # Convert column letters to indices
        # AR = column 44 (index 43), AJ = column 36 (index 35)
        # L = column 12 (index 11), M = column 13 (index 12)

        col_ar_idx = 43  # AR column
        col_aj_idx = 35  # AJ column
        col_l_idx = 11   # L column
        col_m_idx = 12   # M column

        if len(columns_list) > max(col_ar_idx, col_aj_idx, col_l_idx, col_m_idx):
            col_lead_id = columns_list[col_ar_idx]
            col_source_id = columns_list[col_aj_idx]
            col_l = columns_list[col_l_idx]
            col_m = columns_list[col_m_idx]

            st.info(f"Using columns: LeadId='{col_lead_id}', SourceId='{col_source_id}'")

            # Button to fetch statuses
            if st.button("🔄 Fetch Lead Statuses", type="primary"):
                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Initialize status column
                statuses = []

                # Process each row
                for idx, row in df.iterrows():
                    lead_id = row[col_lead_id]
                    source_id = row[col_source_id]

                    status_text.text(f"Processing row {idx + 1}/{len(df)} - LeadId: {lead_id}")

                    # Get status from API
                    status = get_lead_status(lead_id, source_id)
                    statuses.append(status)

                    # Update progress
                    progress_bar.progress((idx + 1) / len(df))

                    # Add small delay to avoid rate limiting
                    time.sleep(0.1)

                status_text.text("✅ All statuses fetched!")

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
            st.error("❌ The uploaded CSV doesn't have enough columns. Please check your file.")

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

else:
    st.info("👆 Please upload a CSV file to get started")

# Add footer
st.markdown("---")
st.markdown("💡 **Tip:** Make sure your CSV file contains the Zapier history with LeadId in column AR and SourceId in column AJ")
