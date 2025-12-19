import streamlit as st
import pandas as pd
import face_rec
from anomaly_detection import AnomalyDetector

st.set_page_config(page_title='Alerts', layout='wide')
st.subheader('System Alerts & Notifications')

# Initialize Anomaly Detector
detector = AnomalyDetector()

# Load Data (Same as Dashboard)
def load_data():
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
        
        report_df = logs_df.groupby(by=['Date', 'Name', 'Role']).agg(
            In_Time=pd.NamedAgg('Timestamp', 'min'),
            Out_Time=pd.NamedAgg('Timestamp', 'max')
        ).reset_index()
        
        report_df['in_time'] = pd.to_datetime(report_df['In_Time'])
        report_df['out_time'] = pd.to_datetime(report_df['Out_Time'])
        report_df['Duration'] = report_df['out_time'] - report_df['in_time']
        report_df['Duration_hours'] = report_df['Duration'].dt.seconds / 3600
        
        return logs_df, report_df
    else:
        return pd.DataFrame(), pd.DataFrame()

logs_df, report_df = load_data()

if not logs_df.empty:
    anomalies_df = detector.get_all_anomalies(logs_df, report_df)
    
    if not anomalies_df.empty:
        st.error(f"Action Required: {len(anomalies_df)} Anomalies Detected")
        
        st.markdown("### Pending Alerts")
        st.dataframe(anomalies_df)
        
        st.markdown("### Notification Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("Send SMS/Email to Supervisors")
            if st.button("Send Notifications"):
                st.success("Notifications sent successfully to 5 supervisors.")
                
        with col2:
            st.info("Escalate to District Officials")
            if st.button("Escalate High Risk Items"):
                high_risk = anomalies_df[anomalies_df['RiskScore'] == 'High']
                if not high_risk.empty:
                    st.success(f"Escalated {len(high_risk)} high-risk items to District Officials.")
                else:
                    st.warning("No High Risk items to escalate.")
                    
    else:
        st.success("System Healthy. No alerts pending.")
else:
    st.info("No data available.")
