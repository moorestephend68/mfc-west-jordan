import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Mobile-friendly settings
st.set_page_config(page_title="Fleet Tracker", layout="centered")

# 1. CONNECT TO GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. LOAD DATA (Individually to avoid total crash)
try:
    df_status = conn.read(worksheet="Live_Status", ttl=0)
    df_staff = conn.read(worksheet="Staff", ttl=0)
    df_routes = conn.read(worksheet="Routes", ttl=0)
except Exception as e:
    st.error("Connection Error: Streamlit cannot find your tabs. Check names: Live_Status, Staff, Routes")
    st.info("Make sure your Google Sheet is shared as 'Anyone with the link can EDIT'")
    st.stop()

# 3. GET TRUCK ID FROM QR CODE
# URL: https://your-app.streamlit.app/?truck=Truck-01
truck_id = st.query_params.get("truck")

if truck_id:
    st.header(f"🚚 {truck_id}")
    
    # Filter for the specific truck
    truck_data = df_status[df_status['Vehicle_ID'] == truck_id]
    
    if not truck_data.empty:
        current_status = truck_data.iloc[0]['Status']
        
        if current_status == "Red":
            # --- CHECK IN FORM ---
            st.subheader("Start Shift")
            with st.form("checkin"):
                name = st.selectbox("Select Name", ["Select"] + df_staff['Driver_Name'].tolist())
                route = st.selectbox("Select Route", ["Select"] + df_routes['Route_ID'].tolist())
                miles = st.number_input("Starting Mileage", min_value=0, step=1)
                
                if st.form_submit_button("Start Shift", use_container_width=True):
                    if name != "Select" and route != "Select":
                        # Logic to update Google Sheets
                        updated_df = df_status.copy()
                        idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                        updated_df.at[idx, 'Status'] = "Green"
                        updated_df.at[idx, 'Status_Color'] = "#00FF00"
                        updated_df.at[idx, 'Driver_Name'] = name
                        updated_df.at[idx, 'Route_Number'] = route
                        
                        # Update the Sheet
                        conn.update(worksheet="Live_Status", data=updated_df)
                        
                        # Log for Payroll
                        new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, name, route, "Check-In", miles]])
                        conn.append(worksheet="Payroll_Logs", data=new_log)
                        
                        st.success(f"Shift Started! Stay safe, {name}.")
                        st.rerun()
                    else:
                        st.warning("Please select your Name and Route.")

        else:
            # --- CHECK OUT FORM ---
            driver_on_shift = truck_data.iloc[0]['Driver_Name']
            st.subheader(f"End Shift: {driver_on_shift}")
            with st.form("checkout"):
                end_miles = st.number_input("Ending Mileage", min_value=0, step=1)
                if st.form_submit_button("Clock Out", use_container_width=True):
                    # Logic to update Google Sheets back to Red
                    updated_df = df_status.copy()
                    idx = updated_df[updated_df['Vehicle_ID'] == truck_id].index[0]
                    prev_route = updated_df.at[idx, 'Route_Number']
                    
                    updated_df.at[idx, 'Status'] = "Red"
                    updated_df.at[idx, 'Status_Color'] = "#FF0000"
                    updated_df.at[idx, 'Driver_Name'] = ""
                    updated_df.at[idx, 'Route_Number'] = ""
                    
                    conn.update(worksheet="Live_Status", data=updated_df)
                    
                    # Log for Payroll
                    new_log = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), truck_id, driver_on_shift, prev_route, "Check-Out", end_miles]])
                    conn.append(worksheet="Payroll_Logs", data=new_log)
                    
                    st.success("Shift Ended. See you next time!")
                    st.rerun()
    else:
        st.error(f"Truck ID '{truck_id}' not found in the list.")

# 4. DASHBOARD (Always Visible)
st.divider()
st.title("Live Fleet Map")
st.map(df_status, latitude="Lat", longitude="Lon", color="Status_Color")

st.subheader("Current Assignments")
st.dataframe(df_status[['Vehicle_ID', 'Status', 'Driver_Name', 'Route_Number']], hide_index=True, use_container_width=True)
