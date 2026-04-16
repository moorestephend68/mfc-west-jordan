import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING
try:
    df_status = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="472708195")
    df_staff = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="1358717605")
    df_routes = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="29737201")
    df_payroll = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="1732762001")
    
    # FORCE VEHICLE_ID TO BE TEXT (This fixes the 'Not Found' error)
    df_status['Vehicle_ID'] = df_status['Vehicle_ID'].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    st.sidebar.success("✅ Database Connected")
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

# 3. APP HEADER
st.title("🚚 Fleet Management Database")

# 4. TRUCK SCANNER LOGIC
truck_id = st.query_params.get("truck")

if truck_id:
    # Force the scanned ID to be a clean string as well
    truck_id = str(truck_id).strip()
    
    st.divider()
    # Search for the truck
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        current_status = truck_row.iloc[0]['Status']
        
        # --- CLOCK-IN FORM ---
        if current_status == "Red":
            st.subheader(f"Clock-In: Vehicle {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Select Driver", ["Select"] + df_staff['Driver_Name'].astype(str).tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].astype(str).tolist())
                miles = st.number_input("Starting Odometer", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        updated_status = df_status.copy()
                        idx = updated_status[updated_status['Vehicle_ID'] == truck_id].index[0]
                        updated_status.at[idx, 'Status'] = "Green"
                        updated_status.at[idx, 'Status_Color'] = "#00FF00"
                        updated_status.at[idx, 'Driver_Name'] = name
                        updated_status.at[idx, 'Route_Number'] = route
                        conn.update(worksheet="472708195", data=updated_status)
                        
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(worksheet="1732762001", data=new_log)
                        st.success("Shift Started!")
                        st.rerun()
                    else:
                        st.warning("Please select a name and route.")

        # --- CLOCK-OUT FORM ---
        else:
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: Vehicle {truck_id} ({driver_now})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Odometer", min_value=0, step=1)
                
                if st.form_submit_button("End Shift", use_container_width=True):
                    updated_status = df_status.copy()
                    idx = updated_status[updated_status['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_status.at[idx, 'Route_Number']
                    
                    updated_status.at[idx, 'Status'] = "Red"
                    updated_status.at[idx, 'Status_Color'] = "#FF0000"
                    updated_status.at[idx, 'Driver_Name'] = ""
                    updated_status.at[idx, 'Route_Number'] = ""
                    conn.update(worksheet="472708195", data=updated_status)
                    
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_now, prev_route, "Check-Out", end_miles]])
                    conn.append(worksheet="1732762001", data=new_log)
                    st.success("Shift Ended!")
                    st.rerun()
    else:
        st.error(f"Vehicle '{truck_id}' not found in the sheet.")
        st.info("Check your 'Vehicle_ID' column for typos or extra spaces.")

# 5. DASHBOARD & MAP
st.divider()
st.subheader("Live Fleet Location")
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])

if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", size=20, height=600)
