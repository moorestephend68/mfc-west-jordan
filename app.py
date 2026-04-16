import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)
# We store the ID in a variable to use for WRITING
sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]

# 2. DATA LOADING & CLEANING
try:
    # Use GIDs for Reading
    df_status = conn.read(spreadsheet=sheet_url, ttl=0, worksheet="472708195")
    df_staff = conn.read(spreadsheet=sheet_url, ttl=0, worksheet="1358717605")
    df_routes = conn.read(spreadsheet=sheet_url, ttl=0, worksheet="29737201")
    df_payroll = conn.read(spreadsheet=sheet_url, ttl=0, worksheet="1732762001")
    
    # Clean Columns for matching
    text_cols = ['Vehicle_ID', 'Status', 'Status_Color', 'Driver_Name', 'Route_Number']
    for col in text_cols:
        if col in df_status.columns:
            df_status[col] = df_status[col].astype(str).str.replace('.0', '', regex=False).replace(['nan', 'None', ''], '')
    
    st.sidebar.success("✅ Connected")
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

# 3. APP HEADER
st.title("🚚 Fleet Management Database")

# 4. TRUCK SCANNER LOGIC
truck_id = st.query_params.get("truck")

if truck_id:
    truck_id = str(truck_id).strip()
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        current_status = str(truck_row.iloc[0]['Status']).strip().lower()
        
        # --- CLOCK-IN FORM ---
        if current_status in ["red", "", "nan"]:
            st.subheader(f"Clock-In: Vehicle {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Select Driver", ["Select"] + df_staff['Driver_Name'].astype(str).tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].astype(str).tolist())
                miles = st.number_input("Starting Odometer", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # Logic Update
                        df_status.loc[df_status['Vehicle_ID'] == truck_id, ['Status', 'Status_Color', 'Driver_Name', 'Route_Number']] = ["Green", "#00FF00", name, route]
                        
                        # EXPLICIT WRITE (Bypasses UnsupportedOperationError)
                        conn.update(spreadsheet=sheet_url, worksheet="Live_Status", data=df_status)
                        
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(spreadsheet=sheet_url, worksheet="Payroll_Logs", data=new_log)
                        
                        st.success("Shift Started!")
                        st.rerun()
        
        # --- CLOCK-OUT FORM ---
        else:
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: Vehicle {truck_id} ({driver_now})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Odometer", min_value=0, step=1)
                if st.form_submit_button("End Shift", use_container_width=True):
                    prev_route = truck_row.iloc[0]['Route_Number']
                    df_status.loc[df_status['Vehicle_ID'] == truck_id, ['Status', 'Status_Color', 'Driver_Name', 'Route_Number']] = ["Red", "#FF0000", "", ""]
                    
                    conn.update(spreadsheet=sheet_url, worksheet="Live_Status", data=df_status)
                    
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_now, prev_route, "Check-Out", end_miles]])
                    conn.append(spreadsheet=sheet_url, worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended!")
                    st.rerun()
    else:
        st.error(f"Vehicle '{truck_id}' not found.")

# 5. PUBLIC DASHBOARD (Map)
st.divider()
st.subheader("Live Fleet Location")
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])

if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", size=20, height=600)
