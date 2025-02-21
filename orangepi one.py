import serial
import mysql.connector
from datetime import datetime
import logging
import time
import requests


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize serial communication
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)

# MySQL database connection
db = mysql.connector.connect(
    host="192.168.43.52",
    user="capstone",
    password="Ricof#30",
    database="capstone2"
)
cursor = db.cursor()

# Initialize previous water level
previous_water_level = None

# Function to get current date and time
def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_all_contacts():
    """Fetch all contacts from the database."""
    cursor.execute("SELECT phone_number FROM contacts WHERE status = 1")
    contacts = cursor.fetchall()
    return [contact[0] for contact in contacts]  # Return a list of phone numbers

def send_sms(message, phone_number):
    api_key = 'ef0a9cf7d5bf8f4b43bbdac91a2f1276'  # Replace with your Semaphore API key
    url = 'https://api.semaphore.co/api/v4/messages'

    # Prepare the parameters for the API request
    parameters = {
        'apikey': api_key,
        'number': phone_number,
        'message': message,
        'sendername': 'EuperAdmin'
    }

    try:
        response = requests.post(url, data=parameters)

        if response.status_code == 200:
            logging.info("Message sent successfully.")
        else:
            logging.error(f"Message failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error sending SMS: {e}")

# Function to send data to CI4
def send_to_ci4(data):
    url = 'https://elogtech.online/sensor-data'  # Replace with your actual URL
    try:
        response = requests.post(url, data=data, verify=False)
        if response.status_code == 200:
            logging.info("Data sent to CI4 successfully.")
        else:
            logging.error(f"Failed to send data to CI4 with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error sending data to CI4: {e}")

while True:
    if ser.in_waiting > 0:
        data = ser.readline().decode('utf-8').strip()
        logging.info(f"Raw data received: {repr(data)}")  # Log raw data for debugging

        if data and len(data) > 1:
            try:
                if data.startswith('WL:'):
                    water_level = float(data.split(':')[1].strip())
                    logging.info(f"Received water level: {water_level} meter/s")
                    send_to_ci4({'water_level': water_level})

                elif data.startswith('RF:'):
                    try:
                        duration = int(data.split(':')[1].strip())
                        send_to_ci4({'rainfall_duration': duration})
                    except ValueError:
                        logging.warning(f"Failed to parse rainfall duration from: {data}")

                elif data.startswith('UL:'):
                    ultrasonic_status = data.split(':')[1].strip()
                    send_to_ci4({'ultrasonic_status': ultrasonic_status})

                elif data.startswith('RS (Analog):'):
                    rain_sensor_status = data.split(':')[1].strip()
                    send_to_ci4({'rain_status': rain_sensor_status})

                elif data.startswith('MS:'):
                    message = data.split(':', 1)[1].strip()
                    contacts = get_all_contacts() 
                    for contact in contacts:
                        send_sms(message, contact)
                    send_to_ci4({'message': message})

            except (ValueError, IndexError) as e:
                logging.warning(f"Error processing data: {data} | {e}")

    time.sleep(0)
