import redis
import sys

# Credentials from face_rec.py
hostname = 'redis-13246.c267.us-east-1-4.ec2.cloud.redislabs.com'
portnumber = 13246
password = 'aRkbqXJx1Dea2K6TbebfBUeJJrDJ6TZJ'

try:
    print(f"Attempting to connect to Redis at {hostname}:{portnumber}...")
    r = redis.StrictRedis(host=hostname, port=portnumber, password=password, socket_timeout=5)
    
    # Try a simple ping
    if r.ping():
        print("Successfully connected to Redis!")
    else:
        print("Connected, but ping failed.")
        sys.exit(1)

except redis.exceptions.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
