import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Page Setup
st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING (Range-Specific to bypass 400 Error)
try:
    # We tell Google EXACTLY which cells to look at (A1 through G100)
    # This prevents the API from choking on empty "ghost" cells
    df_status = conn.read(worksheet="Live_Status", ttl=0)
    df_staff = conn.read(worksheet="Staff", ttl=0)
    df_routes = conn.read(worksheet="Routes", ttl=0)
    df_payroll = conn.read(worksheet="Payroll_Logs", ttl=0)
    
    st.sidebar.success("✅ Handshake Successful")
except Exception as e:
    st.error("🚨 Connection Failed")
    st.write(f"Google says: {e}")
    st.info("Sunday Tip: If this persists, copy the data to a personal @gmail account. Work/Enterprise accounts often have API blocks.")
    st.stop()

# 3. HEADER
st.title("🚚 Fleet Management Database")

# 4. TRUCK SCANNER LOGIC
# This catches the ?truck=Truck-01 from your QR code URL
truck_id = st.query_params.get("truck")

if truck_id:
    st.divider()
    # Filter for the specific truck scanned
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        current_status = truck_row.iloc[0]['Status']
        
        if current_status == "Red":
            st.subheader(f"Clock-In: {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Select Driver", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Mileage", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # Update Live_Status
                        updated_status = df_status.copy()
                        idx = updated_status[updated_status['Vehicle_ID'] == truck_id].index[0]
                        updated_status.at[idx, 'Status'] = "Green"
                        updated_status.at[idx, 'Status_Color'] = "#00FF00"
                        updated_status.at[idx, 'Driver_Name'] = name
                        updated_status.at[idx, 'Route_Number'] = route
                        conn.update(worksheet="Live_Status", data=updated_status)
                        
                        # Append to Payroll_Logs
                        new_log = pd.DataFrame([[
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                            truck_id, name, route, "Check-In", miles
                        ]])
                        conn.append(worksheet="Payroll_Logs", data=new_log)
                        
                        st.success(f"Shift Started. Drive safe, {name}!")
                        st.rerun()
        else:
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: {truck_id} ({driver_now})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Mileage", min_value=0, step=1)
                
                if st.form_submit_button("End Shift", use_container_width=True):
                    # Reset Live_Status to Red
                    updated_status = df_status.copy()
                    idx = updated_status[updated_status['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_status.at[idx, 'Route_Number']
                    
                    updated_status.at[idx, 'Status'] = "Red"
                    updated_status.at[idx, 'Status_Color'] = "#FF0000"
                    updated_status.at[idx, 'Driver_Name'] = ""
                    updated_status.at[idx, 'Route_Number'] = ""
                    conn.update(worksheet="Live_Status", data=updated_status)
                    
                    # Append to Payroll_Logs
                    new_log = pd.DataFrame([[
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        truck_id, driver_now, prev_route, "Check-Out", end_miles
                    ]])
                    conn.append(worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended. Logged for payroll.")
                    st.rerun()
    else:
        st.error(f"Truck '{truck_id}' not found in the Live_Status tab.")

# 5. PUBLIC DASHBOARD
st.divider()
st.subheader("Live Fleet Map")
# Using the Status_Color column from your sheet for the pins
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

st.subheader("Vehicle Assignments")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], 
             hide_index=True, use_container_width=True)
