import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Mobile-optimized view
st.set_page_config(page_title="Fleet Management Database", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING (Safety Version)
try:
    # We restrict columns to avoid "HTTP 400 Bad Request" on empty cells
    df_status = conn.read(worksheet="Live_Status", usecols=[0,1,2,3,4,5,6], ttl=0)
    df_staff = conn.read(worksheet="Staff", usecols=[0], ttl=0)
    df_routes = conn.read(worksheet="Routes", usecols=[0], ttl=0)
    df_payroll = conn.read(worksheet="Payroll_Logs", usecols=[0,1,2,3,4,5], ttl=0)
    
    st.sidebar.success("✅ Connected to Database")
    
except Exception as e:
    st.error("🚨 Connection Error")
    st.info("Check: Are your tabs named Live_Status, Staff, Routes, and Payroll_Logs?")
    st.warning(f"Technical Detail: {e}")
    st.stop()

# 3. APP HEADER
st.title("🚚 Fleet Management Database")
st.markdown(f"**Live Status:** {datetime.now().strftime('%A, %b %d')}")

# 4. TRUCK SCAN LOGIC (Using URL Parameter ?truck=Truck-01)
truck_id = st.query_params.get("truck")

if truck_id:
    st.divider()
    truck_data = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_data.empty:
        current_status = truck_data.iloc[0]['Status']
        
        # --- CHECK-IN FORM ---
        if current_status == "Red":
            st.subheader(f"Start Shift: {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Select Driver", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Odometer", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # Update Live Status tab
                        updated_df = df_status.copy()
                        idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                        updated_df.at[idx, 'Status'] = "Green"
                        updated_df.at[idx, 'Status_Color'] = "#00FF00"
                        updated_df.at[idx, 'Driver_Name'] = name
                        updated_df.at[idx, 'Route_Number'] = route
                        conn.update(worksheet="Live_Status", data=updated_df)
                        
                        # Log to Payroll tab
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(worksheet="Payroll_Logs", data=new_log)
                        
                        st.success(f"Shift Started for {name}!")
                        st.rerun()
                    else:
                        st.warning("Please select a name and route.")

        # --- CHECK-OUT FORM ---
        else:
            driver = truck_data.iloc[0]['Driver_Name']
            st.subheader(f"End Shift: {truck_id} ({driver})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Odometer", min_value=0, step=1)
                
                if st.form_submit_button("Complete Shift", use_container_width=True):
                    # Reset Live Status tab
                    updated_df = df_status.copy()
                    idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_df.at[idx, 'Route_Number']
                    
                    updated_df.at[idx, 'Status'] = "Red"
                    updated_df.at[idx, 'Status_Color'] = "#FF0000"
                    updated_df.at[idx, 'Driver_Name'] = ""
                    updated_df.at[idx, 'Route_Number'] = ""
                    conn.update(worksheet="Live_Status", data=updated_df)
                    
                    # Log to Payroll tab
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver, prev_route, "Check-Out", end_miles]])
                    conn.append(worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended. Data logged.")
                    st.rerun()
    else:
        st.error(f"Truck '{truck_id}' not found in database.")

# 5. DASHBOARD & MAP
st.divider()
st.subheader("Live Fleet Location")
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

st.subheader("Vehicle Assignments")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], hide_index=True, use_container_width=True)
