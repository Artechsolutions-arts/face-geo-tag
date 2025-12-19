import streamlit as st
import pandas as pd
import face_rec
from anomaly_detection import AnomalyDetector
import plotly.express as px

st.set_page_config(page_title='Dashboard', layout='wide')
st.subheader('Real-Time Attendance Dashboard')

# Initialize Anomaly Detector
detector = AnomalyDetector()

# Load Data
def load_data():
    # Registered Users
    try:
        redis_face_db = face_rec.retrive_data(name='academy:register')
    except:
        redis_face_db = pd.DataFrame(columns=['Name', 'Role'])
        
    # Logs
    name = 'attendance:logs'
    logs_list = face_rec.r.lrange(name, start=0, end=-1)
    
    if logs_list:
        convert_byte_to_string = lambda x: x.decode('utf-8')
        logs_list_string = list(map(convert_byte_to_string, logs_list))
        split_string = lambda x: x.split('@')
        logs_nested_list = list(map(split_string, logs_list_string))
        
        processed_logs = []
        for log in logs_nested_list:
            if len(log) == 3:
                processed_logs.append(log + [None, None])
            elif len(log) == 5:
                processed_logs.append(log)
            else:
                continue
                
        logs_df = pd.DataFrame(processed_logs, columns=['Name', 'Role', 'Timestamp', 'Lat', 'Long'])
        logs_df['Timestamp'] = pd.to_datetime(logs_df['Timestamp'])
        logs_df['Date'] = logs_df['Timestamp'].dt.date
        
        # Calculate Report DF for duration
        report_df = logs_df.groupby(by=['Date', 'Name', 'Role']).agg(
            In_Time=pd.NamedAgg('Timestamp', 'min'),
            Out_Time=pd.NamedAgg('Timestamp', 'max')
        ).reset_index()
        
        report_df['in_time'] = pd.to_datetime(report_df['In_Time'])
        report_df['out_time'] = pd.to_datetime(report_df['Out_Time'])
        report_df['Duration'] = report_df['out_time'] - report_df['in_time']
        report_df['Duration_hours'] = report_df['Duration'].dt.seconds / 3600
        
        return redis_face_db, logs_df, report_df
    else:
        return redis_face_db, pd.DataFrame(), pd.DataFrame()

redis_face_db, logs_df, report_df = load_data()

# Tabs
tab1, tab2, tab3 = st.tabs(['Overview', 'Supervisor View', 'Anomalies'])

with tab1:
    st.markdown("### System Overview")
    col1, col2, col3 = st.columns(3)
    
    total_students = len(redis_face_db[redis_face_db['Role'] == 'Student'])
    
    if not logs_df.empty:
        today = pd.Timestamp.now().date()
        present_today = logs_df[logs_df['Date'] == today]['Name'].nunique()
        
        # Anomalies
        anomalies_df = detector.get_all_anomalies(logs_df, report_df)
        total_anomalies = len(anomalies_df)
    else:
        present_today = 0
        total_anomalies = 0
        anomalies_df = pd.DataFrame()

    col1.metric("Total Students", total_students)
    col2.metric("Present Today", present_today)
    col3.metric("Anomalies Detected", total_anomalies, delta_color="inverse")
    
    if not logs_df.empty:
        st.markdown("#### Attendance Trend")
        daily_counts = logs_df.groupby('Date')['Name'].nunique().reset_index()
        fig = px.bar(daily_counts, x='Date', y='Name', title='Daily Attendance')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### Supervisor View")
    if not logs_df.empty:
        roles = logs_df['Role'].unique()
        selected_role = st.selectbox("Filter by Role", roles)
        
        filtered_logs = logs_df[logs_df['Role'] == selected_role]
        st.dataframe(filtered_logs)
        
        st.markdown("#### Location Map (Last Check-in)")
        # Get last location for each person
        last_loc = filtered_logs.sort_values('Timestamp').groupby('Name').last().reset_index()
        
        # Filter out rows with no location
        map_data = last_loc.dropna(subset=['Lat', 'Long'])
        if not map_data.empty:
            # Convert to float
            map_data['lat'] = map_data['Lat'].astype(float)
            map_data['lon'] = map_data['Long'].astype(float)
            st.map(map_data)
        else:
            st.info("No location data available for map.")

with tab3:
    st.markdown("### Anomaly Detection")
    if not anomalies_df.empty:
        st.warning(f"Detected {len(anomalies_df)} anomalies.")
        
        # Filter by Risk Score
        risk_filter = st.multiselect("Filter by Risk Score", options=['High', 'Medium', 'Low'], default=['High', 'Medium'])
        
        if risk_filter:
            filtered_anomalies = anomalies_df[anomalies_df['RiskScore'].isin(risk_filter)]
            st.dataframe(filtered_anomalies)
        else:
            st.dataframe(anomalies_df)
            
    else:
        st.success("No anomalies detected.")
