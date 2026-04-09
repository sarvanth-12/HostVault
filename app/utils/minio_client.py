import uuid, os
from flask import current_app
from minio import Minio
from minio.error import S3Error


def get_minio():
    return Minio(
        endpoint   = current_app.config['S3_ENDPOINT'],
        access_key = current_app.config['S3_ACCESS_KEY'],
        secret_key = current_app.config['S3_SECRET_KEY'],
        secure     = current_app.config['S3_SECURE'],
    )

def ensure_bucket():
    client = get_minio()
    bucket = current_app.config['S3_BUCKET']
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

def upload_file(file_stream, filename, content_type, file_size):
    ensure_bucket()
    client = get_minio()
    bucket = current_app.config['S3_BUCKET']
    ext = os.path.splitext(filename)[1]
    object_name = f"{uuid.uuid4().hex}{ext}"
    client.put_object(bucket, object_name, file_stream, file_size,
                      content_type=content_type or 'application/octet-stream')
    return object_name

def download_file(object_name):
    client = get_minio()
    bucket = current_app.config['S3_BUCKET']
    response = client.get_object(bucket, object_name)
    data = response.read()
    response.close()
    response.release_conn()
    return data

def delete_file(object_name):
    client = get_minio()
    bucket = current_app.config['S3_BUCKET']
    try:
        client.remove_object(bucket, object_name)
    except S3Error as e:
        current_app.logger.warning(f'S3 delete warning: {e}')

def get_cluster_stats():
    client = get_minio()
    bucket = current_app.config['S3_BUCKET']
    try:
        objects = list(client.list_objects(bucket, recursive=True))
        return {
            'total_objects': len(objects),
            'total_size':    sum(o.size or 0 for o in objects),
            'bucket':        bucket,
            'endpoint':      current_app.config['S3_ENDPOINT'],
        }
    except S3Error as e:
        return {'error': str(e)}
