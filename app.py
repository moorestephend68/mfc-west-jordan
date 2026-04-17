import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT (Now uses the Service Account from Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]

# 2. LOAD DATA (Reading by GID)
try:
    df_status = conn.read(spreadsheet=url, worksheet="472708195", ttl=0)
    df_staff = conn.read(spreadsheet=url, worksheet="1358717605", ttl=0)
    df_routes = conn.read(spreadsheet=url, worksheet="29737201", ttl=0)
    
    # Clean ID formatting
    df_status['Vehicle_ID'] = df_status['Vehicle_ID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    st.sidebar.success("✅ Secure Connection Active")
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# 3. SCANNER LOGIC
truck_id = st.query_params.get("truck")
if truck_id:
    truck_id = str(truck_id).strip()
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        status = str(truck_row.iloc[0]['Status']).strip().lower()
        
        if status in ["red", "", "nan"]:
            with st.form("checkin"):
                st.subheader(f"Clock-In: {truck_id}")
                name = st.selectbox("Driver", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Odometer", min_value=0)
                if st.form_submit_button("Start Shift"):
                    if name != "Select" and route != "Select":
                        # Update Local Data
                        df_status.loc[df_status['Vehicle_ID'] == truck_id, ['Status', 'Status_Color', 'Driver_Name', 'Route_Number']] = ["Green", "#00FF00", name, route]
                        
                        # UPDATE SHEET (Works now because of Service Account!)
                        conn.update(spreadsheet=url, worksheet="Live_Status", data=df_status)
                        
                        # LOG PAYROLL
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(spreadsheet=url, worksheet="Payroll_Logs", data=new_log)
                        st.success("Shift Started!")
                        st.rerun()
        else:
            # Clock-out logic
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: {truck_id} ({driver_now})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Odometer", min_value=0)
                if st.form_submit_button("End Shift"):
                    df_status.loc[df_status['Vehicle_ID'] == truck_id, ['Status', 'Status_Color', 'Driver_Name', 'Route_Number']] = ["Red", "#FF0000", "", ""]
                    conn.update(spreadsheet=url, worksheet="Live_Status", data=df_status)
                    
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_now, "", "Check-Out", end_miles]])
                    conn.append(spreadsheet=url, worksheet="Payroll_Logs", data=new_log)
                    st.success("Shift Ended!")
                    st.rerun()

# 4. MAP
st.divider()
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])
if not map_df.empty:
    st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color", height=600)
