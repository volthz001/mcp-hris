# routes/notifications.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import firebase_admin
from firebase_admin import messaging, credentials

notif_bp = Blueprint('notifications', __name__)

# Init Firebase Admin sekali di app.py:
# cred = credentials.Certificate('firebase-service-account.json')
# firebase_admin.initialize_app(cred)

@notif_bp.route('/notifications/register-token', methods=['POST'])
@jwt_required()
def register_token():
    data = request.json
    mongo.db.fcm_tokens.update_one(
        {'user_id': data['user_id']},
        {'$set': {'fcm_token': data['fcm_token']}},
        upsert=True,
    )
    return jsonify({'status': 'ok'})


def send_push(user_id: str, title: str, body: str):
    doc = mongo.db.fcm_tokens.find_one({'user_id': user_id})
    if not doc:
        return
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=doc['fcm_token'],
    )
    messaging.send(message)
