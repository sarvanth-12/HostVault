from datetime import datetime, timezone
from app.extensions import db


class FileRecord(db.Model):
    __tablename__ = 'files'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename     = db.Column(db.String(512), nullable=False)
    object_name  = db.Column(db.String(512), nullable=False, unique=True)
    file_size    = db.Column(db.BigInteger, nullable=False, default=0)
    content_type = db.Column(db.String(255), nullable=True)
    uploaded_at  = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner = db.relationship('User', back_populates='files', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id':           self.id,
            'filename':     self.filename,
            'file_size':    self.file_size,
            'content_type': self.content_type,
            'uploaded_at':  self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class TrashRecord(db.Model):
    __tablename__ = 'trash'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename     = db.Column(db.String(512), nullable=False)
    object_name  = db.Column(db.String(512), nullable=False)
    file_size    = db.Column(db.BigInteger, nullable=False, default=0)
    content_type = db.Column(db.String(255), nullable=True)
    deleted_at   = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner = db.relationship('User', back_populates='trash', foreign_keys=[user_id])

    def days_until_expiry(self, retention_days=30):
        now = datetime.now(timezone.utc)
        deleted = self.deleted_at.replace(tzinfo=timezone.utc) if self.deleted_at.tzinfo is None else self.deleted_at
        elapsed = (now - deleted).days
        return max(0, retention_days - elapsed)

    def is_expired(self, retention_days=30):
        return self.days_until_expiry(retention_days) == 0

    def to_dict(self, retention_days=30):
        return {
            'id':           self.id,
            'filename':     self.filename,
            'file_size':    self.file_size,
            'content_type': self.content_type,
            'deleted_at':   self.deleted_at.isoformat() if self.deleted_at else None,
            'days_left':    self.days_until_expiry(retention_days),
            'expires_soon': self.days_until_expiry(retention_days) <= 3,
        }


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    detail     = db.Column(db.String(512), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id':         self.id,
            'event_type': self.event_type,
            'detail':     self.detail,
            'user_email': self.user.email if self.user else 'unknown',
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
