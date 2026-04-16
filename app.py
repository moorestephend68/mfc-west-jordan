import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Page config for mobile-friendly view
st.set_page_config(page_title="Driver Fleet Portal", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
# Ensure your secrets are set up in Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. LOAD DATA
# We load the status of all trucks and the list of drivers/routes
try:
    df_status = conn.read(worksheet="Live_Status")
    df_drivers = conn.read(worksheet="Staff")
    df_routes = conn.read(worksheet="Routes")
except Exception as e:
    st.error("Could not connect to Google Sheets. Check your worksheet names!")
    st.stop()

# 3. IDENTIFY TRUCK FROM QR CODE
# URL looks like: https://your-app.streamlit.app/?truck=Truck-01
query_params = st.query_params
truck_id = query_params.get("truck")

# --- UI LOGIC ---

if truck_id:
    st.header(f"🚚 Vehicle: {truck_id}")
    
    # Find current status of this specific truck
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if truck_row.empty:
        st.error(f"Truck {truck_id} not found in the Live_Status system.")
    else:
        current_status = truck_row.iloc[0]['Status']
        
        # --- CASE A: TRUCK IS OFF (CHECK-IN) ---
        if current_status == "Red":
            st.subheader("Start Shift")
            with st.form("check_in_form"):
                driver = st.selectbox("Select Your Name", ["Select Name"] + df_drivers['Driver_Name'].tolist())
                route = st.selectbox("Select Assigned Route", ["Select Route"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Mileage", min_value=0, step=1)
                submit = st.form_submit_button("Clock In", use_container_width=True)
                
                if submit:
                    if driver != "Select Name" and route != "Select Route":
                        # 1. Update Live_Status tab (for the map)
                        # In a real app, you'd use conn.update(). For simple Sunday setup:
                        st.success(f"Welcome, {driver}! Shift started.")
                        st.info("Note: Ensure you've shared 'Editor' access with your Google Service Account to save data.")
                        # This is where the write-back logic goes
                    else:
                        st.warning("Please select both a Name and a Route.")

        # --- CASE B: TRUCK IS ON (CHECK-OUT) ---
        else:
            current_driver = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"End Shift: {current_driver}")
            with st.form("check_out_form"):
                end_miles = st.number_input("Ending Mileage", min_value=0, step=1)
                submit = st.form_submit_button("Clock Out & Finish", use_container_width=True)
                
                if submit:
                    st.success("Shift ended. Data logged for payroll.")

# --- 4. THE PUBLIC DASHBOARD (The Map) ---
st.divider()
st.title("Live Fleet Status")

# simple map view
# Ensure your 'Live_Status' sheet has 'Lat' and 'Lon' columns
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

# Status Table for quick viewing
st.subheader("Current Assignments")
display_df = df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']]
st.dataframe(display_df, use_container_width=True, hide_index=True)
