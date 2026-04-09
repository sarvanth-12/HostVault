from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.extensions import db
from app.models import User
from app.utils.decorators import login_required_api

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')


@profile_bp.get('')
@login_required_api
def get_profile():
    return jsonify({'user': current_user.to_dict(include_stats=True)}), 200


@profile_bp.put('')
@login_required_api
def update_profile():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'first_name' in data:
        current_user.first_name = data['first_name'].strip()
    if 'last_name' in data:
        current_user.last_name = data['last_name'].strip()

    if 'email' in data:
        new_email = data['email'].strip().lower()
        if new_email != current_user.email:
            if User.query.filter_by(email=new_email).first():
                return jsonify({'error': 'Email already in use'}), 409
            current_user.email = new_email

    if 'new_password' in data and data['new_password']:
        if current_user.password_hash and not current_user.check_password(data.get('current_password', '')):
            return jsonify({'error': 'Current password is incorrect'}), 400
        if len(data['new_password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        current_user.set_password(data['new_password'])

    db.session.commit()
    return jsonify({'message': 'Profile updated', 'user': current_user.to_dict(include_stats=True)}), 200
