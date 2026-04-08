import uuid, os
from flask import current_app
from minio import Minio
from minio.error import S3Error


def get_minio():
    return Minio(
        endpoint   = current_app.config['MINIO_ENDPOINT'],
        access_key = current_app.config['MINIO_ACCESS_KEY'],
        secret_key = current_app.config['MINIO_SECRET_KEY'],
        secure     = current_app.config['MINIO_SECURE'],
        region     = current_app.config.get('MINIO_REGION', 'us-east-005'),  # ← ADDED
    )

def ensure_bucket():
    # Backblaze buckets must be created via dashboard, not API
    # This just verifies the bucket exists
    client = get_minio()
    bucket = current_app.config['MINIO_BUCKET']
    if not client.bucket_exists(bucket):
        raise Exception(f"Bucket '{bucket}' not found. Please create it in Backblaze dashboard.")

def upload_file(file_stream, filename, content_type, file_size):
    client = get_minio()  # ← removed ensure_bucket() call
    bucket = current_app.config['MINIO_BUCKET']
    ext = os.path.splitext(filename)[1]
    object_name = f"{uuid.uuid4().hex}{ext}"
    client.put_object(bucket, object_name, file_stream, file_size,
                      content_type=content_type or 'application/octet-stream')
    return object_name

def download_file(object_name):
    client = get_minio()
    bucket = current_app.config['MINIO_BUCKET']
    response = client.get_object(bucket, object_name)
    data = response.read()
    response.close()
    response.release_conn()
    return data

def delete_file(object_name):
    client = get_minio()
    bucket = current_app.config['MINIO_BUCKET']
    try:
        client.remove_object(bucket, object_name)
    except S3Error as e:
        current_app.logger.warning(f'Backblaze delete warning: {e}')

def get_cluster_stats():
    client = get_minio()
    bucket = current_app.config['MINIO_BUCKET']
    try:
        objects = list(client.list_objects(bucket, recursive=True))
        return {
            'total_objects': len(objects),
            'total_size':    sum(o.size or 0 for o in objects),
            'bucket':        bucket,
            'endpoint':      current_app.config['MINIO_ENDPOINT'],
        }
    except S3Error as e:
        return {'error': str(e)}