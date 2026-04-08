from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from app.extensions import db
from app.models import User, FileRecord, TrashRecord, ActivityLog
from app.utils.decorators import admin_required
from app.utils.minio_client import get_cluster_stats, download_file, delete_file

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# ── Users ─────────────────────────────────────────────────────
@admin_bp.get('/users')
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict(include_stats=True) for u in users]}), 200


@admin_bp.put('/users/<int:user_id>')
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    if 'role' in data and data['role'] in ('user', 'admin'):
        user.role = data['role']
    if 'storage_quota' in data:
        user.storage_quota = int(data['storage_quota'])
    db.session.commit()
    return jsonify({'message': 'User updated', 'user': user.to_dict(include_stats=True)}), 200


@admin_bp.delete('/users/<int:user_id>')
@admin_required
def delete_user(user_id):
    from flask_login import current_user
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    # Delete all user files from MinIO
    for f in user.files:
        try:
            delete_file(f.object_name)
        except Exception:
            pass
    for t in user.trash:
        try:
            delete_file(t.object_name)
        except Exception:
            pass
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200


# ── User Files (admin can view/download/delete any user's files) ──
@admin_bp.get('/users/<int:user_id>/files')
@admin_required
def user_files(user_id):
    user = User.query.get_or_404(user_id)
    files = FileRecord.query.filter_by(user_id=user_id)\
                .order_by(FileRecord.uploaded_at.desc()).all()
    trash = TrashRecord.query.filter_by(user_id=user_id)\
                .order_by(TrashRecord.deleted_at.desc()).all()
    return jsonify({
        'user':  user.to_dict(include_stats=True),
        'files': [f.to_dict() for f in files],
        'trash': [t.to_dict() for t in trash],
    }), 200


@admin_bp.get('/files/<int:file_id>/download')
@admin_required
def admin_download_file(file_id):
    record = FileRecord.query.get_or_404(file_id)
    try:
        data = download_file(record.object_name)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return send_file(
        BytesIO(data),
        download_name=record.filename,
        as_attachment=True,
        mimetype=record.content_type or 'application/octet-stream',
    )


@admin_bp.delete('/files/<int:file_id>')
@admin_required
def admin_delete_file(file_id):
    record = FileRecord.query.get_or_404(file_id)
    user = User.query.get(record.user_id)
    try:
        delete_file(record.object_name)
    except Exception:
        pass
    if user:
        user.storage_used = max(0, user.storage_used - record.file_size)
    db.session.add(ActivityLog(
        user_id=record.user_id, event_type='admin_delete',
        detail=f'Admin deleted {record.filename}',
        ip_address=request.remote_addr
    ))
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'File deleted'}), 200


# ── Storage ───────────────────────────────────────────────────
@admin_bp.get('/storage')
@admin_required
def storage_stats():
    minio_stats      = get_cluster_stats()
    total_db_size    = db.session.query(db.func.sum(FileRecord.file_size)).scalar() or 0
    total_trash_size = db.session.query(db.func.sum(TrashRecord.file_size)).scalar() or 0
    total_users      = User.query.count()
    active_users     = User.query.filter_by(is_active=True).count()
    total_files      = FileRecord.query.count()
    return jsonify({
        'total_db_files_size': total_db_size,
        'total_trash_size':    total_trash_size,
        'total_users':         total_users,
        'active_users':        active_users,
        'total_files':         total_files,
        'minio':               minio_stats,
    }), 200


# ── Logs ──────────────────────────────────────────────────────
@admin_bp.get('/logs')
@admin_required
def activity_logs():
    page       = request.args.get('page', 1, type=int)
    per_page   = request.args.get('per_page', 100, type=int)
    event_type = request.args.get('type', None)
    user_id    = request.args.get('user_id', None, type=int)
    qs = ActivityLog.query.order_by(ActivityLog.created_at.desc())
    if event_type:
        qs = qs.filter_by(event_type=event_type)
    if user_id:
        qs = qs.filter_by(user_id=user_id)
    paginated = qs.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'logs':  [l.to_dict() for l in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'page':  page,
    }), 200


# ── Health ────────────────────────────────────────────────────
@admin_bp.get('/health')
@admin_required
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except Exception:
        db_ok = False
    minio_stats = get_cluster_stats()
    minio_ok = 'error' not in minio_stats
    return jsonify({
        'database': {'status': 'ok' if db_ok else 'error'},
        'minio':    {'status': 'ok' if minio_ok else 'error', **minio_stats},
        'overall':  'ok' if (db_ok and minio_ok) else 'degraded',
    }), 200 if (db_ok and minio_ok) else 503
