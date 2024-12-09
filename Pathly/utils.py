from dotenv import load_dotenv
import pyrebase
import os

load_dotenv()

fb_api_key = os.getenv('FIREBASE_API_KEY')
fb_db_url = os.getenv('FIREBASE_DB_URL')


FIREBASE_CONFIG = {
  'apiKey': fb_api_key,
  'authDomain': "firefly-sih.firebaseapp.com",
  'databaseURL': fb_db_url,
  'projectId': "firefly-sih",
  'storageBucket': "firefly-sih.firebasestorage.app",
  'messagingSenderId': "153569340026",
  'appId': "1:153569340026:web:502abe032d1489023b69c3",
  'measurementId': "G-TXYF53E28R"
}

firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
db = firebase.database()

def get_db():
    return db

def get_data(path):
    return db.child(path).get().val()

def set_data(path, data):
    db.child(path).set(data)

def update_data(path, data):
    db.child(path).update(data)

def delete_data(path):
    db.child(path).remove()

def get_nodeurl():
    return 'https://firefly-backend-sih24-153569340026.us-central1.run.app/'