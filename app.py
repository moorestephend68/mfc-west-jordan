import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Fleet Management", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ID = "1ib1MEFybGRteaZRJnyJ3UZAgk6mep5nsjws_uYfbwiw"

# 2. DATA LOADER (GID ONLY)
@st.cache_data(ttl=10)
def get_fleet_data():
    try:
        # Access gspread client via internal _client
        client = conn.client._client 
        sh = client.open_by_key(SHEET_ID)
        
        # Pull data using GIDs
        ws_status = sh.get_worksheet_by_id(472708195).get_all_records()
        ws_staff = sh.get_worksheet_by_id(1358717605).get_all_records()
        ws_routes = sh.get_worksheet_by_id(29737201).get_all_records()
        
        return pd.DataFrame(ws_status), pd.DataFrame(staff_staff), pd.DataFrame(ws_routes)
    except Exception as e:
        return f"Error connecting to GIDs: {str(e)}"

# RUN LOADER
load_result = get_fleet_data()

if isinstance(load_result, str):
    st.error("🚨 Sheet Access Error")
    st.write(f"Technical Detail: {load_result}")
    if st.button("Clear Cache & Retry"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

df_status, df_staff, df_routes = load_result

# 3. DATA CLEANING
df_status['Vehicle_ID'] = df_status['Vehicle_ID'].astype(str).str.replace('.0', '', regex=False).str.strip()

# 4. TRUCK SCANNER LOGIC
truck_id = st.query_params.get("truck")

if truck_id:
    truck_id = str(truck_id).strip()
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        current_status = str(truck_row.iloc[0].get('Status', '')).strip().lower()
        
        # --- CLOCK-IN ---
        if current_status in ["red", "", "nan"]:
            st.subheader(f"Clock-In: Vehicle {truck_id}")
            with st.form("checkin"):
                driver_name = st.selectbox("Select Driver", ["Select"] + df_staff.iloc[:, 0].astype(str).tolist())
                route_id = st.selectbox("Select Route", ["Select"] + df_routes.iloc[:, 0].astype(str).tolist())
                miles = st.number_input("Starting Odometer", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if driver_name != "Select" and route_id != "Select":
                        idx = df_status[df_status['Vehicle_ID'] == truck_id].index[0] + 2
                        sh = conn.client._client.open_by_key(SHEET_ID)
                        
                        # Update Live_Status (GID: 472708195)
                        ws = sh.get_worksheet_by_id(472708195)
                        ws.update_cell(idx, 2, "Green")
                        ws.update_cell(idx, 3, "#00FF00")
                        ws.update_cell(idx, 4, driver_name)
                        ws.update_cell(idx, 5, route_id)
                        
                        # Update Payroll_Logs (GID: 1732762001)
                        log_ws = sh.get_worksheet_by_id(1732762001)
                        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_name, route_id, "Check-In", miles])
                        
                        st.success(f"Shift Started for {driver_name}!")
                        st.cache_data.clear()
                        st.rerun()

        # --- CLOCK-OUT ---
        else:
            driver_now = truck_row.iloc[0].get('Driver_Name', 'Unknown')
            st.subheader(f"Clock-Out: Vehicle {truck_id} ({driver_now})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Odometer", min_value=0, step=1)
                if st.form_submit_button("End Shift", use_container_width=True):
                    idx = df_status[df_status['Vehicle_ID'] == truck_id].index[0] + 2
                    sh = conn.client._client.open_by_key(SHEET_ID)
                    
                    # Reset Live_Status (GID: 472708195)
                    ws = sh.get_worksheet_by_id(472708195)
                    ws.update_cell(idx, 2, "Red")
                    ws.update_cell(idx, 3, "#FF0000")
                    ws.update_cell(idx, 4, "")
                    ws.update_cell(idx, 5, "")
                    
                    # Log Payroll (GID: 1732762001)
                    log_ws = sh.get_worksheet_by_id(1732762001)
                    log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_now, "", "Check-Out", end_miles])
                    
                    st.success("Shift Ended. Logged successfully.")
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.error(f"Vehicle '{truck_id}' not found.")

# 5. DASHBOARD MAP
st.divider()
st.title("🚚 Fleet Dashboard")

map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])

if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", size=20, height=600)
