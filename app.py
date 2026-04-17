import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. SECURE CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]

# 2. THE "FORCE READ" FUNCTION
@st.cache_data(ttl=10) # Refresh every 10 seconds
def get_data_forcefully():
    try:
        # We bypass 'conn.read' and use the underlying client directly
        # This prevents the <Response [200]> error
        sheet = conn.client.open_by_key("1ib1MEFybGRteaZRJnyJ3UZAgk6mep5nsjws_uYfbwiw")
        
        # Load the three tabs
        ws_status = sheet.worksheet("Live_Status").get_all_records()
        ws_staff = sheet.worksheet("Staff_List").get_all_records() # Ensure this name is exact
        ws_routes = sheet.worksheet("Routes").get_all_records()     # Ensure this name is exact
        
        return pd.DataFrame(ws_status), pd.DataFrame(ws_staff), pd.DataFrame(ws_routes)
    except Exception as e:
        return str(e)

# RUN THE FORCE LOAD
result = get_data_forcefully()

if isinstance(result, str):
    st.error("🚨 Final Connection Hurdle")
    st.write(f"Technical Detail: {result}")
    st.info("If it says 'Worksheet not found', check your Tab Names in Google Sheets!")
    if st.button("Clear System Cache & Retry"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# Assign dataframes
df_status, df_staff, df_routes = result

# Clean IDs
df_status['Vehicle_ID'] = df_status['Vehicle_ID'].astype(str).str.replace('.0', '', regex=False).strip()

# 3. SCANNER LOGIC
truck_id = st.query_params.get("truck")
if truck_id:
    truck_id = str(truck_id).strip()
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        status = str(truck_row.iloc[0]['Status']).strip().lower()
        
        if status in ["red", "", "nan"]:
            st.subheader(f"Clock-In: Vehicle {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Driver", ["Select"] + df_staff.iloc[:, 0].tolist())
                route = st.selectbox("Route", ["Select"] + df_routes.iloc[:, 0].tolist())
                miles = st.number_input("Odometer", min_value=0)
                if st.form_submit_button("Start Shift"):
                    # Update Sheet
                    idx = df_status[df_status['Vehicle_ID'] == truck_id].index[0]
                    # Direct update to avoid the [200] error
                    sh = conn.client.open_by_key("1ib1MEFybGRteaZRJnyJ3UZAgk6mep5nsjws_uYfbwiw").worksheet("Live_Status")
                    sh.update_cell(idx + 2, 2, "Green") # Column B: Status
                    sh.update_cell(idx + 2, 3, "#00FF00") # Column C: Color
                    sh.update_cell(idx + 2, 4, name) # Column D: Driver
                    sh.update_cell(idx + 2, 5, route) # Column E: Route
                    
                    st.success("Success! Truck is now Green.")
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.subheader(f"Clock-Out: {truck_id}")
            if st.button("End Shift"):
                idx = df_status[df_status['Vehicle_ID'] == truck_id].index[0]
                sh = conn.client.open_by_key("1ib1MEFybGRteaZRJnyJ3UZAgk6mep5nsjws_uYfbwiw").worksheet("Live_Status")
                sh.update_cell(idx + 2, 2, "Red")
                sh.update_cell(idx + 2, 3, "#FF0000")
                sh.update_cell(idx + 2, 4, "")
                sh.update_cell(idx + 2, 5, "")
                st.cache_data.clear()
                st.rerun()

# 4. MAP
st.divider()
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])
if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", height=600)
