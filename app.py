import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Mobile-optimized view
st.set_page_config(page_title="Fleet Management Database", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
# This uses the ID you put in your "Secrets"
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING
# Note: These 'worksheet' names MUST match the tabs at the bottom of your sheet
try:
    df_status = conn.read(worksheet="Live_Status", ttl=0)
    df_staff = conn.read(worksheet="Staff", ttl=0)
    df_routes = conn.read(worksheet="Routes", ttl=0)
    df_payroll = conn.read(worksheet="Payroll_Logs", ttl=0)
    
    st.sidebar.success("Connected to: Fleet_Management_Database")
    
# 3. APP HEADER
st.title("🚚 Fleet Management Database")
st.markdown(f"**Current Date:** {datetime.now().strftime('%A, %b %d')}")

# 4. TRUCK SCAN LOGIC
truck_id = st.query_params.get("truck")

if truck_id:
    st.divider()
    truck_data = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_data.empty:
        current_status = truck_data.iloc[0]['Status']
        
        if current_status == "Red":
            st.subheader(f"Check-In: {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Driver Name", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Route ID", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Odometer Start", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # Update Live Status
                        updated_df = df_status.copy()
                        idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                        updated_df.at[idx, 'Status'] = "Green"
                        updated_df.at[idx, 'Status_Color'] = "#00FF00"
                        updated_df.at[idx, 'Driver_Name'] = name
                        updated_df.at[idx, 'Route_Number'] = route
                        conn.update(worksheet="Live_Status", data=updated_df)
                        
                        # Log to Payroll
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(worksheet="Payroll_Logs", data=new_log)
                        
                        st.success("Shift Started!")
                        st.rerun()
        else:
            driver = truck_data.iloc[0]['Driver_Name']
            st.subheader(f"Check-Out: {truck_id} ({driver})")
            with st.form("checkout"):
                end_miles = st.number_input("Odometer End", min_value=0, step=1)
                if st.form_submit_button("End Shift", use_container_width=True):
                    # Reset Live Status
                    updated_df = df_status.copy()
                    idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_df.at[idx, 'Route_Number']
                    
                    updated_df.at[idx, 'Status'] = "Red"
                    updated_df.at[idx, 'Status_Color'] = "#FF0000"
                    updated_df.at[idx, 'Driver_Name'] = ""
                    updated_df.at[idx, 'Route_Number'] = ""
                    conn.update(worksheet="Live_Status", data=updated_df)
                    
                    # Log to Payroll
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver, prev_route, "Check-Out", end_miles]])
                    conn.append(worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended!")
                    st.rerun()
    else:
        st.error(f"Vehicle {truck_id} not found.")

# 5. LIVE MAP & DATA
st.divider()
st.subheader("Live Fleet Map")
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

st.subheader("Vehicle Overview")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], hide_index=True, use_container_width=True)
