import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]

# 2. DATA LOADING (Simplified for Testing)
def load_data():
    try:
        # We try to read using the NAME of the tab instead of the GID
        df = conn.read(spreadsheet=url, worksheet="Live_Status", ttl=0)
        
        # If this works, we know the connection is good!
        if df is not None:
            df['Vehicle_ID'] = df['Vehicle_ID'].astype(str).str.replace('.0', '', regex=False).str.strip()
            return df
        return "Empty Sheet"
    except Exception as e:
        return str(e)

result = load_data()

# If the result is a string, it's an error message
if isinstance(result, str):
    st.error("🚨 Connection still not active")
    st.write(f"Google says: {result}")
    if st.button("Force System Reboot"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# If we get here, it worked!
df_status = result
st.sidebar.success("✅ Secure Connection Active")

# 3. TRUCK SCANNER LOGIC
truck_id = st.query_params.get("truck")
if truck_id:
    truck_id = str(truck_id).strip()
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        status = str(truck_row.iloc[0]['Status']).strip().lower()
        
        if status in ["red", "", "nan"]:
            st.subheader(f"Clock-In: Vehicle {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Driver", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Odometer", min_value=0)
                if st.form_submit_button("Start Shift"):
                    if name != "Select" and route != "Select":
                        df_status.loc[df_status['Vehicle_ID'] == truck_id, ['Status', 'Status_Color', 'Driver_Name', 'Route_Number']] = ["Green", "#00FF00", name, route]
                        conn.update(spreadsheet=url, worksheet="Live_Status", data=df_status)
                        st.success("Success!")
                        st.rerun()
        else:
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: {truck_id} ({driver_now})")
            if st.button("End Shift"):
                df_status.loc[df_status['Vehicle_ID'] == truck_id, ['Status', 'Status_Color', 'Driver_Name', 'Route_Number']] = ["Red", "#FF0000", "", ""]
                conn.update(spreadsheet=url, worksheet="Live_Status", data=df_status)
                st.rerun()
    else:
        st.error(f"Vehicle '{truck_id}' not found.")

# 4. BIG MAP
st.divider()
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])
if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", height=600)
