from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from app.extensions import db
from app.models import FileRecord, TrashRecord, ActivityLog
from app.utils.decorators import login_required_api
from app.utils.minio_client import delete_file

trash_bp = Blueprint('trash', __name__, url_prefix='/api/trash')


def _log(event_type, detail):
    db.session.add(ActivityLog(
        user_id=current_user.id, event_type=event_type,
        detail=detail, ip_address=request.remote_addr
    ))


@trash_bp.get('')
@login_required_api
def list_trash():
    retention = current_app.config['TRASH_RETENTION_DAYS']
    items = TrashRecord.query.filter_by(user_id=current_user.id)\
                .order_by(TrashRecord.deleted_at.desc()).all()
    return jsonify({'trash': [t.to_dict(retention) for t in items], 'retention_days': retention}), 200


@trash_bp.post('/<int:trash_id>/restore')
@login_required_api
def restore(trash_id):
    retention = current_app.config['TRASH_RETENTION_DAYS']
    item = TrashRecord.query.filter_by(id=trash_id, user_id=current_user.id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if item.is_expired(retention):
        return jsonify({'error': 'File has expired and was purged'}), 410
    if current_user.storage_used + item.file_size > current_user.storage_quota:
        return jsonify({'error': 'Not enough storage quota'}), 413

    restored = FileRecord(
        user_id=current_user.id, filename=item.filename,
        object_name=item.object_name, file_size=item.file_size,
        content_type=item.content_type, uploaded_at=datetime.now(timezone.utc),
    )
    db.session.add(restored)
    db.session.delete(item)
    current_user.storage_used += item.file_size
    _log('restore', f'Restored {item.filename}')
    db.session.commit()
    return jsonify({'message': 'File restored', 'file': restored.to_dict()}), 200


@trash_bp.delete('/<int:trash_id>')
@login_required_api
def permanent_delete(trash_id):
    item = TrashRecord.query.filter_by(id=trash_id, user_id=current_user.id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    try:
        delete_file(item.object_name)
    except Exception as e:
        current_app.logger.warning(f'MinIO perm-delete warning: {e}')
    _log('perm_delete', f'Permanently deleted {item.filename}')
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Permanently deleted'}), 200
