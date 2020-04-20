# your_firestore.py

# Required imports
from firebase_admin import credentials, firestore, initialize_app

# Initialize Firestore DB
cred = credentials.Certificate('credentials/your-firebase-api-key.json')
default_app = initialize_app(cred)
db = firestore.client()
your_collection_ref = db.collect('your-collection-name')
# events_ref = db.collection('events')