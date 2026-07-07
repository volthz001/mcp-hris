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
    """Get all notifications for current user"""
    user_id = get_jwt_identity()
    
    try:
        notifications = list(mongo.db.notifications.find(
            {'userId': user_id}
        ).sort('createdAt', -1))
        
        # Convert ObjectId to string
        for notif in notifications:
            notif['_id'] = str(notif['_id'])
            
        return jsonify({
            'success': True,
            'data': notifications,
            'count': len(notifications)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/<notification_id>/read', methods=['PATCH'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark notification as read"""
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
    """Mark all notifications as read for current user"""
    user_id = get_jwt_identity()
    
    try:
        mongo.db.notifications.update_many(
            {'userId': user_id},
            {'$set': {'isRead': True}}
        )
        
        return jsonify({
            'success': True,
            'message': 'All notifications marked as read'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """Delete a notification"""
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
    """Create notification (internal use)"""
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
        
        return jsonify({
            'success': True,
            'data': notification
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# routes/messages.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson.objectid import ObjectId
from extensions import mongo

messages_bp = Blueprint('messages', __name__, url_prefix='/api/messages')

@messages_bp.route('', methods=['GET'])
@jwt_required()
def get_messages():
    """Get messages with optional role filter"""
    user_id = get_jwt_identity()
    recipient_role = request.args.get('role')
    
    try:
        query = {}
        
        if recipient_role:
            query['recipientRole'] = recipient_role
        
        messages = list(mongo.db.messages.find(query).sort('createdAt', -1))
        
        # Convert ObjectId to string
        for msg in messages:
            msg['_id'] = str(msg['_id'])
        
        return jsonify({
            'success': True,
            'data': messages,
            'count': len(messages)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@messages_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    """Send message to a specific role"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        # Get sender info
        sender = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not sender:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        message = {
            'senderId': user_id,
            'senderName': data.get('senderName', sender.get('name')),
            'senderRole': data.get('senderRole', sender.get('role')),
            'recipientRole': data.get('recipientRole'),
            'messageText': data.get('messageText'),
            'isRead': False,
            'createdAt': datetime.utcnow()
        }
        
        result = mongo.db.messages.insert_one(message)
        message['_id'] = str(result.inserted_id)
        
        # Create notifications for users with recipient role
        recipients = mongo.db.users.find({'role': data.get('recipientRole')})
        
        for recipient in recipients:
            notification = {
                'userId': str(recipient['_id']),
                'title': f'Pesan dari {message["senderName"]}',
                'message': message['messageText'][:100],
                'type': 'message',
                'isRead': False,
                'senderId': user_id,
                'senderName': message['senderName'],
                'createdAt': datetime.utcnow()
            }
            mongo.db.notifications.insert_one(notification)
        
        return jsonify({
            'success': True,
            'data': message,
            'notificationsCreated': recipients.count()
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@messages_bp.route('/<message_id>/read', methods=['PATCH'])
@jwt_required()
def mark_message_read(message_id):
    """Mark message as read"""
    try:
        result = mongo.db.messages.update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'isRead': True}}
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'message': 'Message not found'}), 404
        
        return jsonify({'success': True, 'message': 'Message marked as read'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Update routes/users.py untuk add endpoints profile update
@users_bp.route('/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    """Update user profile"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        update_data = {}
        
        if 'name' in data:
            update_data['name'] = data['name']
        if 'email' in data:
            update_data['email'] = data['email']
        if 'phone' in data:
            update_data['phone'] = data['phone']
        if 'department' in data:
            update_data['department'] = data['department']
        if 'profileImage' in data:
            update_data['profileImage'] = data['profileImage']
        
        update_data['updatedAt'] = datetime.utcnow()
        
        result = mongo.db.users.find_one_and_update(
            {'_id': ObjectId(user_id)},
            {'$set': update_data},
            return_document=True
        )
        
        if not result:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Convert ObjectId to string
        result['_id'] = str(result['_id'])
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Profile updated successfully'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@users_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        from werkzeug.security import check_password_hash, generate_password_hash
        
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Verify old password
        if not check_password_hash(user['password'], data.get('oldPassword', '')):
            return jsonify({
                'success': False,
                'message': 'Password lama tidak sesuai'
            }), 400
        
        # Update with new password
        new_password_hash = generate_password_hash(data.get('newPassword', ''))
        
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'password': new_password_hash,
                'updatedAt': datetime.utcnow()
            }}
        )
        
        return jsonify({
            'success': True,
            'message': 'Password berhasil diubah'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Update routes/auth.py untuk add refresh endpoint
@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh JWT token"""
    data = request.get_json()
    refresh_token = data.get('refreshToken')
    
    try:
        # Verify refresh token
        decoded = JwtManager.decode_token(refresh_token)
        user_id = decoded.get('sub')
        
        # Check if refresh token still valid
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user or not user.get('refreshToken') == refresh_token:
            return jsonify({
                'success': False,
                'message': 'Invalid refresh token'
            }), 401
        
        # Generate new access token
        access_token = create_access_token(identity=user_id)
        
        return jsonify({
            'success': True,
            'token': access_token,
            'message': 'Token refreshed successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Token refresh failed'
        }), 401

# Update app.py untuk register blueprints
