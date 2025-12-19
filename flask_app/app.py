from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, session
from camera import RealTimePred, RegistrationCamera
import pandas as pd
import json
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production!

# Global camera instances (simple approach for POC)
# In production, handle per-user or session-based cameras
pred_camera = None
reg_camera = None

def get_pred_camera():
    global pred_camera
    if pred_camera is None:
        pred_camera = RealTimePred()
    return pred_camera

def get_reg_camera():
    global reg_camera
    if reg_camera is None:
        reg_camera = RegistrationCamera()
    return reg_camera

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Teacher-only decorator
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'Teacher':
            return render_template('error.html', 
                message='Access Denied', 
                detail='This page is only accessible to Teachers.'), 403
        return f(*args, **kwargs)
    return decorated_function

# Demo users (in production, use database with hashed passwords)
DEMO_USERS = {
    'teacher1': {'password': 'teacher123', 'role': 'Teacher'},
    'student1': {'password': 'student123', 'role': 'Student'},
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        print(f"Login attempt - Username: {username}, Password: {password}, Role: {role}")
        
        # Check hardcoded demo users first
        if username in DEMO_USERS:
            user = DEMO_USERS[username]
            print(f"Demo user found - Expected password: {user['password']}, Expected role: {user['role']}")
            if user['password'] == password and user['role'] == role:
                session['username'] = username
                session['role'] = role
                print(f"Login successful for demo user {username}")
                return redirect(url_for('index'))
        
        # Check MongoDB for student accounts
        if role == 'Student':
            from camera import student_accounts_collection
            student = student_accounts_collection.find_one({"username": username, "password": password})
            if student:
                session['username'] = username
                session['role'] = 'Student'
                print(f"Login successful for student {username}")
                return redirect(url_for('index'))
        
        # Check MongoDB for teacher accounts
        if role == 'Teacher':
            from camera import teacher_accounts_collection
            teacher = teacher_accounts_collection.find_one({"username": username, "password": password})
            if teacher:
                session['username'] = username
                session['role'] = 'Teacher'
                print(f"Login successful for teacher {username}")
                return redirect(url_for('index'))
        
        print("Login failed - Invalid credentials or role mismatch")
        return render_template('login.html', error='Invalid credentials or role mismatch')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/attendance')
@login_required
def attendance():
    return render_template('attendance.html')

@app.route('/register')
@teacher_required
def register():
    return render_template('register.html')

@app.route('/my_attendance')
@login_required
def my_attendance():
    # Students can view their own attendance
    return render_template('my_attendance.html')

@app.route('/dashboard')
@teacher_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/alerts')
@teacher_required
def alerts():
    return render_template('alerts.html')

def gen_pred(camera, lat, long):
    while True:
        frame = camera.get_frame(lat, long)
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def gen_reg(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed_pred')
def video_feed_pred():
    lat = request.args.get('lat', 0.0, type=float)
    long = request.args.get('long', 0.0, type=float)
    return Response(gen_pred(get_pred_camera(), lat, long),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_reg')
def video_feed_reg():
    return Response(gen_reg(get_reg_camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/submit_registration', methods=['POST'])
def submit_registration():
    name = request.form.get('name')
    role = request.form.get('role')
    username = request.form.get('username')
    password = request.form.get('password')
    
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image captured'})
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
        
    try:
        image_bytes = file.read()
        camera = get_reg_camera()
        
        # Generate a unique user_id
        import uuid
        user_id = str(uuid.uuid4())[:8].upper()
        if role == 'Student':
            user_id = f"STU-{user_id}"
        elif role == 'Teacher':
            user_id = f"TEA-{user_id}"
        else:
            user_id = f"USR-{user_id}"
            
        # Use the new register_user method with user_id
        result = camera.register_user(name, role, image_bytes, user_id=user_id)
        
        if result == True:
            # If student, also create account
            if role == 'Student' and username and password:
                from camera import student_accounts_collection
                student_accounts_collection.update_one(
                    {"username": username},
                    {"$set": {
                        "user_id": user_id,
                        "username": username,
                        "password": password,
                        "name": name,
                        "role": "Student",
                        "created_at": datetime.now()
                    }},
                    upsert=True
                )
                print(f"Student account created/updated for {username} (ID: {user_id})")
            
            # If teacher, also create account
            if role == 'Teacher' and username and password:
                from camera import teacher_accounts_collection
                teacher_accounts_collection.update_one(
                    {"username": username},
                    {"$set": {
                        "user_id": user_id,
                        "username": username,
                        "password": password,
                        "name": name,
                        "role": "Teacher",
                        "created_at": datetime.now()
                    }},
                    upsert=True
                )
                print(f"Teacher account created/updated for {username} (ID: {user_id})")
                
            return jsonify({'status': 'success', 'message': f'{name} registered successfully (ID: {user_id})'})
        elif result == 'name_false':
            return jsonify({'status': 'error', 'message': 'Name cannot be empty'})
        elif result == 'file_false':
            return jsonify({'status': 'error', 'message': 'No face detected in image'})
        else:
            return jsonify({'status': 'error', 'message': 'Unknown error'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image uploaded'})
    
    file = request.files['image']
    lat = request.form.get('lat', 0.0, type=float)
    long = request.form.get('long', 0.0, type=float)
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})

    try:
        image_bytes = file.read()
        camera = get_pred_camera()
        annotated_image, detected_people = camera.process_snapshot(image_bytes, lat, long)
        
        if annotated_image is None:
             return jsonify({'status': 'error', 'message': 'Failed to process image'})
             
        # Convert annotated image to base64 for display
        import base64
        image_b64 = base64.b64encode(annotated_image).decode('utf-8')
        
        if detected_people:
            msg = f"Attendance marked for: {', '.join(detected_people)}"
            status = 'success'
            # Send notification to each detected person
            for person in detected_people:
                send_notification(person, f"Your attendance has been marked successfully at {lat}, {long}", "success")
        else:
            msg = "No registered face detected"
            status = 'warning'
            # Send notification to current user about failure
            username = session.get('username')
            send_notification(username, "Attendance failed: No registered face detected", "warning")
            
        return jsonify({
            'status': status,
            'message': msg,
            'image': image_b64,
            'detected': detected_people
        })
        
    except Exception as e:
        print(f"Error in mark_attendance: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/stats')
def api_stats():
    # Fetch stats for dashboard
    try:
        from camera import users_collection, logs_collection
        from datetime import datetime
        
        # Total Students (Registered Users)
        total_students = users_collection.count_documents({})
        
        # Present Today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_str = str(today_start.date())
        present_today = logs_collection.count_documents({"timestamp": {"$regex": f"^{today_str}"}})
        
        # Anomalies (Mock for now)
        anomalies = 3 
        
        return jsonify({
            'total_students': total_students,
            'present_today': present_today,
            'anomalies': anomalies
        })
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({
            'total_students': 0,
            'present_today': 0,
            'anomalies': 0
        })

@app.route('/api/download_report')
def download_report():
    try:
        from camera import users_collection, logs_collection
        import io
        from flask import send_file
        
        # Fetch all logs
        logs = list(logs_collection.find({}, {"_id": 0}))
        
        if not logs:
            # Return empty CSV if no data
            output = io.StringIO()
            output.write("No attendance data available\n")
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode()),
                mimetype='text/csv',
                as_attachment=True,
                download_name='attendance_report.csv'
            )
        
        # Convert to DataFrame
        df = pd.DataFrame(logs)
        
        # Create CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'attendance_report_{pd.Timestamp.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_alerts')
@login_required
def get_alerts():
    try:
        from camera import alerts_collection
        from bson import json_util
        import json as json_lib
        
        alerts = list(alerts_collection.find({}))
        # Convert ObjectId to string for JSON serialization
        alerts_json = json_lib.loads(json_util.dumps(alerts))
        return jsonify(alerts_json)
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return jsonify([])

@app.route('/api/approve_alert', methods=['POST'])
@login_required
def approve_alert():
    try:
        from camera import alerts_collection, notifications_collection
        from datetime import datetime
        
        alert_id = request.json.get('alert_id')
        action = request.json.get('action')  # 'reviewed' or 'approved'
        
        username = session.get('username')
        role = session.get('role')
        
        # Only teachers can approve
        if role != 'Teacher':
            return jsonify({'error': 'Only teachers can approve alerts'}), 403
        
        # Update alert
        from bson.objectid import ObjectId
        result = alerts_collection.update_one(
            {'_id': ObjectId(alert_id)},
            {
                '$set': {
                    'status': action,
                    'reviewed_by': username,
                    'reviewed_at': str(datetime.now())
                }
            }
        )
        
        if result.modified_count > 0:
            # Notify the user involved in the alert
            alert_doc = alerts_collection.find_one({'_id': ObjectId(alert_id)})
            if alert_doc:
                send_notification(alert_doc.get('user'), f"Your alert '{alert_doc.get('type')}' has been {action} by {username}", "info")
            
            return jsonify({ 'success': True, 'message': f'Alert {action} by {username}'})
        else:
            return jsonify({'error': 'Alert not found'}), 404
            
    except Exception as e:
        print(f"Error approving alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/my_attendance')
@login_required
def api_my_attendance():
    try:
        from camera import logs_collection, student_accounts_collection
        
        username = session.get('username')
        
        # Find the student's real name from their account
        student = student_accounts_collection.find_one({"username": username})
        if not student:
            # Fallback for demo users or if account not found
            name_to_search = username
        else:
            name_to_search = student.get('name')
            
        print(f"Searching attendance for name: {name_to_search} (username: {username})")
        
        # Find logs for this name
        user_logs = list(logs_collection.find({"name": name_to_search}))
        
        # Calculate statistics
        total_days = 30  # Assume 30 days in month
        present_days = len(set([log['timestamp'].split()[0] for log in user_logs]))
        
        # Current month attendance
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_logs = [log for log in user_logs if log['timestamp'] >= str(month_start)]
        this_month_count = len(set([log['timestamp'].split()[0] for log in this_month_logs]))
        
        percentage = round((present_days / total_days) * 100, 1) if total_days > 0 else 0
        
        # Format logs for display
        formatted_logs = []
        for log in user_logs:
            formatted_logs.append({
                "timestamp": log.get('timestamp'),
                "lat": log.get('lat', 0),
                "long": log.get('long', 0)
            })
            
        return jsonify({
            'records': formatted_logs,
            'stats': {
                'total_days': total_days,
                'present_days': present_days,
                'percentage': percentage,
                'this_month': this_month_count
            }
        })
    except Exception as e:
        print(f"Error fetching attendance: {e}")
        return jsonify({'records': [], 'stats': {'total_days': 0, 'present_days': 0, 'percentage': 0, 'this_month': 0}})

# --- New Skill Andhra Pradesh Enhancements ---

def send_notification(username, message, type='info'):
    try:
        notifications_collection.insert_one({
            "username": username,
            "message": message,
            "type": type,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "read": False
        })
    except Exception as e:
        print(f"Error sending notification: {e}")

@app.route('/notifications')
@login_required
def notifications_page():
    return render_template('notifications.html')

@app.route('/api/get_notifications')
@login_required
def get_notifications():
    try:
        username = session.get('username')
        notifs = list(notifications_collection.find({"username": username}).sort("time", -1).limit(20))
        for n in notifs:
            n['_id'] = str(n['_id'])
        return jsonify(notifs)
    except Exception as e:
        return jsonify([])

@app.route('/api/sync_portal', methods=['POST'])
@login_required
@teacher_required
def sync_portal():
    try:
        # Simulate API call to iti.ap.gov.in
        import time
        time.sleep(2) # Simulate network latency
        
        username = session.get('username')
        send_notification(username, "Successfully synced attendance data with ITI Portal (iti.ap.gov.in)", "success")
        
        return jsonify({
            "status": "success",
            "message": "Attendance data successfully synchronized with Government ITI Portal."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
