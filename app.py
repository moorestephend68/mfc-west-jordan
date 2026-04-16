import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Mobile-optimized view
st.set_page_config(page_title="Fleet Tracker", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING
try:
    # We "ping" the sheet by reading the Live_Status tab
    df_status = conn.read(worksheet="Live_Status", ttl=0)
    df_staff = conn.read(worksheet="Staff", ttl=0)
    df_routes = conn.read(worksheet="Routes", ttl=0)
    df_payroll = conn.read(worksheet="Payroll_Logs", ttl=0)
    
    st.sidebar.success("✅ Connected to Fleet Database")
    
except Exception as e:
    st.error("🚨 Connection Failed")
    st.write(f"Error details: {e}")
    st.info("Check 1: Is your Spreadsheet ID in Secrets correct?")
    st.info("Check 2: Is the sheet shared with 'Anyone with the link' as 'Editor'?")
    st.stop()

# 3. GET TRUCK ID FROM QR CODE
# URL: https://your-app.streamlit.app/?truck=Truck-01
truck_id = st.query_params.get("truck")

if truck_id:
    st.header(f"🚚 Vehicle: {truck_id}")
    
    # Filter for the specific truck scanned
    truck_data = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_data.empty:
        current_status = truck_data.iloc[0]['Status']
        
        # --- CASE A: TRUCK IS OFF (CHECK-IN) ---
        if current_status == "Red":
            st.subheader("Start Your Shift")
            with st.form("checkin"):
                name = st.selectbox("Select Your Name", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Current Mileage (Start)", min_value=0, step=1)
                
                if st.form_submit_button("Clock In", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # 1. Update the Map (Live_Status tab)
                        updated_df = df_status.copy()
                        idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                        updated_df.at[idx, 'Status'] = "Green"
                        updated_df.at[idx, 'Status_Color'] = "#00FF00"
                        updated_df.at[idx, 'Driver_Name'] = name
                        updated_df.at[idx, 'Route_Number'] = route
                        conn.update(worksheet="Live_Status", data=updated_df)
                        
                        # 2. Log to Payroll (Payroll_Logs tab)
                        new_log = pd.DataFrame([[
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                            truck_id, name, route, "Check-In", miles
                        ]])
                        conn.append(worksheet="Payroll_Logs", data=new_log)
                        
                        st.success(f"Shift Started! Have a safe trip, {name}.")
                        st.rerun()
                    else:
                        st.warning("Please pick your name and route.")

        # --- CASE B: TRUCK IS ON (CHECK-OUT) ---
        else:
            driver_on_shift = truck_data.iloc[0]['Driver_Name']
            st.subheader(f"End Shift: {driver_on_shift}")
            with st.form("checkout"):
                end_miles = st.number_input("Current Mileage (End)", min_value=0, step=1)
                
                if st.form_submit_button("Clock Out", use_container_width=True):
                    # 1. Update the Map back to Red
                    updated_df = df_status.copy()
                    idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_df.at[idx, 'Route_Number'] # Keep for the log
                    
                    updated_df.at[idx, 'Status'] = "Red"
                    updated_df.at[idx, 'Status_Color'] = "#FF0000"
                    updated_df.at[idx, 'Driver_Name'] = ""
                    updated_df.at[idx, 'Route_Number'] = ""
                    conn.update(worksheet="Live_Status", data=updated_df)
                    
                    # 2. Log to Payroll
                    new_log = pd.DataFrame([[
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        truck_id, driver_on_shift, prev_route, "Check-Out", end_miles
                    ]])
                    conn.append(worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended. Data logged for payroll!")
                    st.rerun()
    else:
        st.error(f"Truck ID '{truck_id}' not found in Live_Status list.")

# 4. PUBLIC DASHBOARD (Always Visible)
st.divider()
st.title("Live Fleet Status")
# Use the status colors for the pins
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

st.subheader("Current Assignments")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], hide_index=True, use_container_width=True)
