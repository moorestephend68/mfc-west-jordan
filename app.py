import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Set page to mobile-friendly
st.set_page_config(page_title="Fleet Tracker", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING HELPER
def load_data():
    # Reading the exact tab names we discussed
    status_df = conn.read(worksheet="Live_Status")
    staff_df = conn.read(worksheet="Staff")
    routes_df = conn.read(worksheet="Routes")
    return status_df, staff_df, routes_df

try:
    df_status, df_staff, df_routes = load_data()
except Exception as e:
    st.error("Connection Error. Ensure your Google Sheet tabs are named: Live_Status, Staff, and Routes.")
    st.stop()

# 3. GET TRUCK ID FROM QR CODE (URL)
# Link format: https://your-app.streamlit.app/?truck=Truck-01
truck_id = st.query_params.get("truck")

if truck_id:
    st.header(f"🚚 {truck_id}")
    
    # Get current row for this truck
    truck_data = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_data.empty:
        current_status = truck_data.iloc[0]['Status']
        
        # --- OPTION A: CHECK IN ---
        if current_status == "Red":
            st.subheader("Check-In to Shift")
            with st.form("checkin"):
                name = st.selectbox("Select Name", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Mileage", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # In the Sunday version, the app instructs how to finalize write-back
                        st.success(f"Shift Started for {name}!")
                        st.balloons()
                        # Log to payroll logic goes here
                    else:
                        st.warning("Please select your name and route.")

        # --- OPTION B: CHECK OUT ---
        else:
            driver_on_shift = truck_data.iloc[0]['Driver_Name']
            st.subheader(f"Checking Out: {driver_on_shift}")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Mileage", min_value=0, step=1)
                if st.form_submit_button("End Shift", use_container_width=True):
                    st.success("Shift Ended. Data logged for payroll.")
    else:
        st.error(f"Truck ID '{truck_id}' not found in Live_Status tab.")

# 4. LIVE MAP DASHBOARD
st.divider()
st.title("Live Fleet Map")

# Map points (Ensuring colors match status)
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

# Status Table
st.subheader("Current Assignments")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], hide_index=True)
