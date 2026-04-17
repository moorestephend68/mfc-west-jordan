import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]

# 2. DATA LOADING (The "Sunday Stable" Version)
def load_fleet_data():
    try:
        # Load the sheets
        status = conn.read(spreadsheet=url, worksheet="Live_Status", ttl=0)
        staff = conn.read(spreadsheet=url, worksheet="1358717605", ttl=0)
        routes = conn.read(spreadsheet=url, worksheet="29737201", ttl=0)
        
        # Immediate Cleaning
        status['Vehicle_ID'] = status['Vehicle_ID'].astype(str).str.replace('.0', '', regex=False).str.strip()
        return status, staff, routes
    except Exception as e:
        return str(e)

# Run the loader
result = load_fleet_data()

# Error Handling
if isinstance(result, str):
    st.error("🔄 Connection Reset Required")
    st.info("Google is still verifying your new Service Account permissions.")
    if st.button("Retry Connection"):
        st.cache_data.clear()
        st.rerun()
    st.stop()
else:
    df_status, df_staff, df_routes = result
    st.sidebar.success("✅ Secure Connection Active")

# 3. SCANNER LOGIC
truck_id = st.query_params.get("truck")
if truck_id:
    truck_id = str(truck_id).strip()
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        # Use .iloc[0] to get the actual value, and force to string
        current_status = str(truck_row.iloc[0]['Status']).strip()
        
        # Check-In Logic
        if current_status.lower() in ["red", "", "nan"]:
            st.subheader(f"Clock-In: Vehicle {truck_id}")
            with st.form("checkin_form"):
                driver_name = st.selectbox("Select Driver", ["Select"] + df_staff['Driver_Name'].tolist())
                route_id = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Odometer", min_value=0)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if driver_name != "Select" and route_id != "Select":
                        # Update local dataframe
                        idx = df_status[df_status['Vehicle_ID'] == truck_id].index[0]
                        df_status.at[idx, 'Status'] = "Green"
                        df_status.at[idx, 'Status_Color'] = "#00FF00"
                        df_status.at[idx, 'Driver_Name'] = driver_name
                        df_status.at[idx, 'Route_Number'] = route_id
                        
                        # Write to Sheet - Using Tab Names
                        conn.update(spreadsheet=url, worksheet="Live_Status", data=df_status)
                        
                        # Log to Payroll
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_name, route_id, "Check-In", miles]])
                        conn.append(spreadsheet=url, worksheet="Payroll_Logs", data=new_log)
                        
                        st.success("Shift Started!")
                        st.rerun()
        
        # Check-Out Logic
        else:
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: Vehicle {truck_id} ({driver_now})")
            with st.form("checkout_form"):
                end_miles = st.number_input("Ending Odometer", min_value=0)
                if st.form_submit_button("End Shift", use_container_width=True):
                    idx = df_status[df_status['Vehicle_ID'] == truck_id].index[0]
                    prev_route = df_status.at[idx, 'Route_Number']
                    
                    df_status.at[idx, 'Status'] = "Red"
                    df_status.at[idx, 'Status_Color'] = "#FF0000"
                    df_status.at[idx, 'Driver_Name'] = ""
                    df_status.at[idx, 'Route_Number'] = ""
                    
                    conn.update(spreadsheet=url, worksheet="Live_Status", data=df_status)
                    
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_now, prev_route, "Check-Out", end_miles]])
                    conn.append(spreadsheet=url, worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended!")
                    st.rerun()
    else:
        st.error(f"Vehicle '{truck_id}' not found.")

# 4. MAP DISPLAY
st.divider()
st.subheader("Live Fleet Location")
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])

if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", size=20, height=600)
