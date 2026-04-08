from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import current_user
from io import BytesIO
from app.extensions import db, limiter
from app.models import FileRecord, TrashRecord, ActivityLog
from app.utils.decorators import login_required_api
from app.utils.minio_client import upload_file, download_file, delete_file
from app.security import sanitize_filename, is_allowed_file, MAX_FILE_SIZE

files_bp = Blueprint('files', __name__, url_prefix='/api/files')


def _log(event_type, detail):
    db.session.add(ActivityLog(
        user_id=current_user.id, event_type=event_type,
        detail=detail, ip_address=request.remote_addr
    ))


@files_bp.get('')
@login_required_api
def list_files():
    sort  = request.args.get('sort', 'date-d')
    query = request.args.get('q', '').strip()

    qs = FileRecord.query.filter_by(user_id=current_user.id)
    if query:
        qs = qs.filter(FileRecord.filename.ilike(f'%{query}%'))

    sort_map = {
        'date-d': FileRecord.uploaded_at.desc(),
        'date-a': FileRecord.uploaded_at.asc(),
        'name-a': FileRecord.filename.asc(),
        'name-d': FileRecord.filename.desc(),
        'size-d': FileRecord.file_size.desc(),
        'size-a': FileRecord.file_size.asc(),
    }
    qs = qs.order_by(sort_map.get(sort, FileRecord.uploaded_at.desc()))
    return jsonify({'files': [f.to_dict() for f in qs.all()]}), 200


@files_bp.post('/upload')
@login_required_api
@limiter.limit('100 per hour')
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file in request'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    # Sanitize filename — strip path traversal, bad chars, blocked extensions
    safe_name = sanitize_filename(file.filename)
    if not is_allowed_file(safe_name):
        return jsonify({'error': f'File type not allowed'}), 400

    # Check file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size == 0:
        return jsonify({'error': 'Cannot upload empty file'}), 400

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'File exceeds maximum allowed size (5 GB)'}), 413

    if current_user.storage_used + file_size > current_user.storage_quota:
        return jsonify({'error': 'Storage quota exceeded'}), 413

    content_type = file.content_type or 'application/octet-stream'

    try:
        object_name = upload_file(file.stream, safe_name, content_type, file_size)
    except Exception as e:
        current_app.logger.error(f'MinIO upload error: {e}')
        return jsonify({'error': 'Upload to storage failed'}), 500

    record = FileRecord(
        user_id=current_user.id, filename=safe_name,
        object_name=object_name, file_size=file_size, content_type=content_type,
    )
    db.session.add(record)
    current_user.storage_used += file_size
    _log('upload', f'Uploaded {safe_name} ({file_size} bytes)')
    db.session.commit()

    return jsonify({'message': 'Uploaded', 'file': record.to_dict()}), 201


@files_bp.get('/<int:file_id>/download')
@login_required_api
def download(file_id):
    record = FileRecord.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'error': 'File not found'}), 404

    try:
        data = download_file(record.object_name)
    except Exception as e:
        current_app.logger.error(f'MinIO download error: {e}')
        return jsonify({'error': 'Could not retrieve file'}), 500

    _log('download', f'Downloaded {record.filename}')
    db.session.commit()

    return send_file(
        BytesIO(data),
        download_name = record.filename,
        as_attachment = True,
        mimetype      = record.content_type or 'application/octet-stream',
    )


@files_bp.delete('/<int:file_id>')
@login_required_api
def soft_delete(file_id):
    record = FileRecord.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'error': 'File not found'}), 404

    trash = TrashRecord(
        user_id=current_user.id, filename=record.filename,
        object_name=record.object_name, file_size=record.file_size,
        content_type=record.content_type,
    )
    db.session.add(trash)
    db.session.delete(record)
    current_user.storage_used = max(0, current_user.storage_used - record.file_size)
    _log('delete', f'Moved {record.filename} to trash')
    db.session.commit()

    return jsonify({'message': 'Moved to trash'}), 200
