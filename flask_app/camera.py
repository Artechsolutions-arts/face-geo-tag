import numpy as np
import pandas as pd
import cv2
import pymongo
from insightface.app import FaceAnalysis
from sklearn.metrics import pairwise
import time
from datetime import datetime
import os

# Connect to MongoDB Client
# Default to localhost
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_client["face_attendance_db"]
users_collection = db["users"]
logs_collection = db["logs"]
alerts_collection = db["alerts"]
notifications_collection = db["notifications"]
student_accounts_collection = db["student_accounts"]
teacher_accounts_collection = db["teacher_accounts"]

# Initialize sample alerts if collection is empty
if alerts_collection.count_documents({}) == 0:
    sample_alerts = [
        {
            "type": "Multiple Check-in",
            "user": "Revanth",
            "description": "User 'Revanth' checked in 3 times in 5 mins",
            "risk_level": "Medium",
            "time": "2023-12-18 10:45:00",
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None
        },
        {
            "type": "Location Mismatch",
            "user": "Surya",
            "description": "User 'Surya' checked in 5km away",
            "risk_level": "High",
            "time": "2023-12-18 09:12:00",
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None
        }
    ]
    alerts_collection.insert_many(sample_alerts)

# Retrieve Data from database
def retrive_data(name):
    # In MongoDB, 'name' argument is unused as we query the collection directly
    # We fetch all users with embeddings
    cursor = users_collection.find({}, {"name": 1, "role": 1, "embedding": 1})
    
    data = []
    for doc in cursor:
        if "embedding" in doc:
            # Convert binary/list back to numpy array
            embedding = np.array(doc["embedding"], dtype=np.float32)
            data.append({
                "user_id": doc.get("user_id"),
                "Name": doc["name"],
                "Role": doc["role"],
                "facial_features": embedding
            })
            
    if not data:
        return pd.DataFrame(columns=['Name', 'Role', 'facial_features'])
        
    return pd.DataFrame(data)

# Configure face analysis
# Assuming running from root directory, so 'insightface_model' is accessible
faceapp = FaceAnalysis(name='buffalo_sc', root='insightface_model', providers=['CPUExecutionProvider'])
faceapp.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.5)

# ML Search Algorithm
def ml_search_algorithm(dataframe, feature_column, test_vector, name_role=['Name', 'Role'], thresh=0.5):
    if dataframe.empty:
        return 'Unknown', 'Unknown', None
        
    dataframe = dataframe.copy()
    X_list = dataframe[feature_column].tolist()
    x = np.asarray(X_list)
    
    similar = pairwise.cosine_similarity(x, test_vector.reshape(1, -1))
    similar_arr = np.array(similar).flatten()
    dataframe['cosine'] = similar_arr

    data_filter = dataframe.query(f'cosine >= {thresh}')
    if len(data_filter) > 0:
        data_filter.reset_index(drop=True, inplace=True)
        argmax = data_filter['cosine'].argmax()
        person_name, person_role = data_filter.loc[argmax][name_role]
        user_id = data_filter.loc[argmax].get('user_id')
    else:
        person_name = 'Unknown'
        person_role = 'Unknown'
        user_id = None
        
    return person_name, person_role, user_id

class RealTimePred:
    def __init__(self):
        self.logs = [] # List of dicts for MongoDB
        self.redis_face_db = retrive_data(name='academy:register')
        # self.camera = cv2.VideoCapture(0) # Removed for client-side capture
        self.waitTime = 30 # seconds
        self.setTime = time.time()

    # def __del__(self):
    #     self.camera.release()

    def reset_dict(self):
        self.logs = []
        
    def saveLogs_mongo(self):
        if not self.logs:
            return

        # Insert many documents
        try:
            logs_collection.insert_many(self.logs)
            print(f"Saved {len(self.logs)} logs to MongoDB")
        except Exception as e:
            print(f"Error saving logs to MongoDB: {e}")
                    
        self.reset_dict()     
        
    def get_frame(self, lat=0.0, long=0.0):
        # This method is likely unused in client-side flow but kept for compatibility
        return b''

    def process_snapshot(self, image_bytes, lat, long):
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return None, "Failed to decode image"

        # Optimization: Resize image if too large
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        current_time = str(datetime.now())
        results = faceapp.get(frame)
        
        detected_people = []
        
        for res in results:
            x1, y1, x2, y2 = res['bbox'].astype(int)
            embeddings = res['embedding']
            person_name, person_role, user_id = ml_search_algorithm(self.redis_face_db,
                                                        'facial_features',
                                                        test_vector=embeddings,
                                                        name_role=['Name', 'Role'],
                                                        thresh=0.5)
            if person_name == 'Unknown':
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)
                detected_people.append(person_name)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color)
            cv2.putText(frame, person_name, (x1, y1), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
            cv2.putText(frame, current_time, (x1, y2+10), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
            
            # Log data
            log_entry = {
                "user_id": user_id,
                "name": person_name,
                "role": person_role,
                "timestamp": current_time,
                "lat": lat,
                "long": long
            }
            self.logs.append(log_entry)

        # Save logs immediately for snapshots
        self.saveLogs_mongo()

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes(), detected_people

class RegistrationCamera:
    def __init__(self):
        # self.camera = cv2.VideoCapture(0)
        self.sample = 0
        self.embeddings = None

    # def __del__(self):
    #     self.camera.release()
        
    def get_frame(self):
        # Unused in client-side flow
        return b''

    def register_user(self, name, role, image_bytes, user_id=None):
        if not name or not name.strip():
            return 'name_false'
            
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return 'file_false'

        # Optimization: Resize image if too large
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

        # Get embedding
        results = faceapp.get(frame, max_num=1)
        if not results:
            return 'file_false'
            
        embedding = results[0]['embedding']
        
        try:
            # Convert to list for MongoDB
            embedding_list = embedding.astype(np.float32).tolist()
            
            user_doc = {
                "user_id": user_id,
                "name": name,
                "role": role,
                "embedding": embedding_list,
                "created_at": datetime.now()
            }
            
            # Update if user_id exists, otherwise update by name/role (legacy)
            if user_id:
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": user_doc},
                    upsert=True
                )
            else:
                users_collection.update_one(
                    {"name": name, "role": role},
                    {"$set": user_doc},
                    upsert=True
                )
            
            return True
        except Exception as e:
            print(f"Registration error: {e}")
            return False
