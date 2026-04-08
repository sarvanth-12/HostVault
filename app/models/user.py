from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    first_name    = db.Column(db.String(80), nullable=False)
    last_name     = db.Column(db.String(80), nullable=False)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role          = db.Column(db.String(20), default='user')
    is_active     = db.Column(db.Boolean, default=True)
    storage_quota = db.Column(db.BigInteger, default=10 * 1024 ** 3)
    storage_used  = db.Column(db.BigInteger, default=0)
    google_id     = db.Column(db.String(255), unique=True, nullable=True)
    avatar_url    = db.Column(db.String(512), nullable=True)
    created_at    = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login    = db.Column(db.DateTime(timezone=True), nullable=True)

    files = db.relationship('FileRecord', back_populates='owner',
                            foreign_keys='FileRecord.user_id',
                            lazy='dynamic', cascade='all, delete-orphan')
    trash = db.relationship('TrashRecord', back_populates='owner',
                            foreign_keys='TrashRecord.user_id',
                            lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def get_id(self):
        return str(self.id)

    def to_dict(self, include_stats=False):
        data = {
            'id':         self.id,
            'first_name': self.first_name,
            'last_name':  self.last_name,
            'full_name':  f'{self.first_name} {self.last_name}',
            'email':      self.email,
            'role':       self.role,
            'is_active':  self.is_active,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        if include_stats:
            data.update({
                'storage_used':  self.storage_used,
                'storage_quota': self.storage_quota,
                'storage_pct':   round(self.storage_used / self.storage_quota * 100, 1)
                                 if self.storage_quota else 0,
                'file_count':    self.files.count(),
                'trash_count':   self.trash.count(),
            })
        return data
