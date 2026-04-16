import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Fleet Management", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING (Using your specific GIDs for stability)
try:
    # We use the GIDs you provided to ensure we hit the right tabs regardless of naming issues
    df_status = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="472708195")
    df_staff = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="1358717605")
    df_routes = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="29737201")
    df_payroll = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0, worksheet="1732762001")
    
    st.sidebar.success("✅ Database Connected")
except Exception as e:
    st.error("🚨 Connection Error")
    st.write(f"Technical Detail: {e}")
    st.stop()

# 3. APP HEADER
st.title("🚚 Fleet Management Database")

# 4. TRUCK SCANNER LOGIC
# This looks for ?truck=Truck-01 in the URL
truck_id = st.query_params.get("truck")

if truck_id:
    st.divider()
    # Find the specific truck row
    truck_row = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_row.empty:
        current_status = truck_row.iloc[0]['Status']
        
        # --- CLOCK-IN ---
        if current_status == "Red":
            st.subheader(f"Clock-In: {truck_id}")
            with st.form("checkin"):
                name = st.selectbox("Select Driver", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Odometer", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # Update Live_Status
                        updated_status = df_status.copy()
                        idx = updated_status[updated_status['Vehicle_ID'] == truck_id].index[0]
                        updated_status.at[idx, 'Status'] = "Green"
                        updated_status.at[idx, 'Status_Color'] = "#00FF00"
                        updated_status.at[idx, 'Driver_Name'] = name
                        updated_status.at[idx, 'Route_Number'] = route
                        conn.update(worksheet="472708195", data=updated_status)
                        
                        # Log to Payroll
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(worksheet="1732762001", data=new_log)
                        
                        st.success(f"Shift Started for {name}!")
                        st.rerun()
                    else:
                        st.warning("Please select a name and route.")

        # --- CLOCK-OUT ---
        else:
            driver_now = truck_row.iloc[0]['Driver_Name']
            st.subheader(f"Clock-Out: {truck_id} ({driver_now})")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Odometer", min_value=0, step=1)
                
                if st.form_submit_button("End Shift", use_container_width=True):
                    # Reset Live_Status
                    updated_status = df_status.copy()
                    idx = updated_status[updated_status['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_status.at[idx, 'Route_Number']
                    
                    updated_status.at[idx, 'Status'] = "Red"
                    updated_status.at[idx, 'Status_Color'] = "#FF0000"
                    updated_status.at[idx, 'Driver_Name'] = ""
                    updated_status.at[idx, 'Route_Number'] = ""
                    conn.update(worksheet="472708195", data=updated_status)
                    
                    # Log to Payroll
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_now, prev_route, "Check-Out", end_miles]])
                    conn.append(worksheet="1732762001", data=new_log)
                    
                    st.success("Shift Ended. Logged successfully!")
                    st.rerun()
    else:
        st.error(f"Vehicle '{truck_id}' not found.")

# 5. PUBLIC DASHBOARD & MAP
st.divider()
st.subheader("Live Fleet Location")

# CLEAN DATA FOR MAP: This prevents the crash you saw earlier
map_df = df_status.copy()
map_df['Lat'] = pd.to_numeric(map_df['Lat'], errors='coerce')
map_df['Lon'] = pd.to_numeric(map_df['Lon'], errors='coerce')
map_df = map_df.dropna(subset=['Lat', 'Lon'])

if not map_df.empty:
    try:
        # Drawing pins based on West Jordan coordinates in your sheet
        st.map(map_df, latitude="Lat", longitude="Lon", color="Status_Color")
    except Exception as map_err:
        st.info("Map is loading coordinates...")
else:
    st.warning("📍 No valid coordinates found. Please add Lat/Lon numbers to your Live_Status tab.")

st.subheader("Vehicle Overview")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], 
             hide_index=True, use_container_width=True)
