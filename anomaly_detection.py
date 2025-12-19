import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class AnomalyDetector:
    def __init__(self):
        pass

    def detect_multiple_checkins(self, logs_df, time_window_minutes=5):
        """
        Detects if a user has checked in multiple times within a short window.
        """
        anomalies = []
        if logs_df.empty:
            return pd.DataFrame()

        # Ensure timestamp is datetime
        logs_df['Timestamp'] = pd.to_datetime(logs_df['Timestamp'])
        
        # Sort by Name and Timestamp
        logs_df = logs_df.sort_values(by=['Name', 'Timestamp'])
        
        # Calculate time difference between consecutive check-ins for the same user
        logs_df['TimeDiff'] = logs_df.groupby('Name')['Timestamp'].diff()
        
        # Filter for short intervals
        short_intervals = logs_df[logs_df['TimeDiff'] < timedelta(minutes=time_window_minutes)]
        
        if not short_intervals.empty:
            for index, row in short_intervals.iterrows():
                anomalies.append({
                    'Name': row['Name'],
                    'Role': row['Role'],
                    'Type': 'Multiple Check-ins',
                    'Details': f"Check-in within {row['TimeDiff'].seconds // 60} mins of previous",
                    'Timestamp': row['Timestamp'],
                    'RiskScore': 'Medium'
                })
                
        return pd.DataFrame(anomalies)

    def detect_short_duration(self, report_df, min_duration_hours=4):
        """
        Detects if the total duration for the day is less than the expected minimum.
        """
        anomalies = []
        if report_df.empty:
            return pd.DataFrame()

        # Check duration
        short_duration = report_df[report_df['Duration_hours'] < min_duration_hours]
        
        if not short_duration.empty:
            for index, row in short_duration.iterrows():
                anomalies.append({
                    'Name': row['Name'],
                    'Role': row['Role'],
                    'Type': 'Short Duration',
                    'Details': f"Total duration: {row['Duration_hours']} hours",
                    'Timestamp': row['Date'], # Using Date as timestamp
                    'RiskScore': 'High'
                })
                
        return pd.DataFrame(anomalies)

    def detect_location_mismatch(self, logs_df, expected_lat, expected_long, threshold_km=1.0):
        """
        Detects if check-ins are far from the expected location.
        Simple Haversine formula or approximation.
        """
        anomalies = []
        if logs_df.empty:
            return pd.DataFrame()
            
        # Check if lat/long columns exist
        if 'Lat' not in logs_df.columns or 'Long' not in logs_df.columns:
            return pd.DataFrame()

        # Simple Euclidean distance approximation for POC (1 deg lat ~ 111km)
        # For more accuracy, use Haversine
        
        for index, row in logs_df.iterrows():
            try:
                lat = float(row['Lat'])
                long = float(row['Long'])
                
                # Approx distance
                dist = np.sqrt((lat - expected_lat)**2 + (long - expected_long)**2) * 111
                
                if dist > threshold_km:
                    anomalies.append({
                        'Name': row['Name'],
                        'Role': row['Role'],
                        'Type': 'Location Mismatch',
                        'Details': f"Distance: {dist:.2f} km from site",
                        'Timestamp': row['Timestamp'],
                        'RiskScore': 'High'
                    })
            except ValueError:
                continue # Skip invalid lat/long
                
        return pd.DataFrame(anomalies)

    def get_all_anomalies(self, logs_df, report_df, expected_location=None):
        """
        Aggregates all anomalies.
        """
        all_anomalies = []
        
        # 1. Multiple Check-ins
        df1 = self.detect_multiple_checkins(logs_df)
        if not df1.empty:
            all_anomalies.append(df1)
            
        # 2. Short Duration
        df2 = self.detect_short_duration(report_df)
        if not df2.empty:
            all_anomalies.append(df2)
            
        # 3. Location Mismatch
        if expected_location:
            df3 = self.detect_location_mismatch(logs_df, expected_location['lat'], expected_location['long'])
            if not df3.empty:
                all_anomalies.append(df3)
                
        if all_anomalies:
            return pd.concat(all_anomalies, ignore_index=True)
        else:
            return pd.DataFrame(columns=['Name', 'Role', 'Type', 'Details', 'Timestamp', 'RiskScore'])
