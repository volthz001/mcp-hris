# routes/notifications.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson.objectid import ObjectId
from extensions import mongo

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    try:
        notifications = list(mongo.db.notifications.find(
            {'userId': user_id}
        ).sort('createdAt', -1))
        for notif in notifications:
            notif['_id'] = str(notif['_id'])
        return jsonify({'success': True, 'data': notifications, 'count': len(notifications)}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/<notification_id>/read', methods=['PATCH'])
@jwt_required()
def mark_notification_read(notification_id):
    user_id = get_jwt_identity()
    try:
        result = mongo.db.notifications.update_one(
            {'_id': ObjectId(notification_id), 'userId': user_id},
            {'$set': {'isRead': True}}
        )
        if result.matched_count == 0:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404
        return jsonify({'success': True, 'message': 'Notification marked as read'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_read():
    user_id = get_jwt_identity()
    try:
        mongo.db.notifications.update_many(
            {'userId': user_id},
            {'$set': {'isRead': True}}
        )
        return jsonify({'success': True, 'message': 'All notifications marked as read'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    user_id = get_jwt_identity()
    try:
        result = mongo.db.notifications.delete_one(
            {'_id': ObjectId(notification_id), 'userId': user_id}
        )
        if result.deleted_count == 0:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404
        return jsonify({'success': True, 'message': 'Notification deleted'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('', methods=['POST'])
@jwt_required()
def create_notification():
    user_id = get_jwt_identity()
    data = request.get_json()
    try:
        notification = {
            'userId': data.get('userId'),
            'title': data.get('title'),
            'message': data.get('message'),
            'type': data.get('type', 'alert'),
            'isRead': False,
            'senderId': user_id,
            'senderName': data.get('senderName'),
            'createdAt': datetime.utcnow()
        }
        result = mongo.db.notifications.insert_one(notification)
        notification['_id'] = str(result.inserted_id)
        return jsonify({'success': True, 'data': notification}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
