"""
Run once to create all DB tables and a default admin user.
Usage: python scripts/init_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

with app.app_context():
    print('Creating database tables...')
    db.create_all()
    print('Tables created.')

    if not User.query.filter_by(role='admin').first():
        admin = User(
            first_name    = 'Admin',
            last_name     = 'User',
            email         = 'admin@privcloud.local',
            role          = 'admin',
            storage_quota = 100 * 1024 ** 3,
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print('\n✅ Default admin created:')
        print('   Email   : admin@privcloud.local')
        print('   Password: Admin@1234')
        print('   ⚠️  Change this password after first login!\n')
    else:
        print('Admin already exists, skipping.')

    print('✅ Database ready!')
