# src/migrate_db.py
from src.main import app
from src.extensions import db
from sqlalchemy import text

def migrate_database():
    with app.app_context():
        try:
            # Check if period_type column exists
            result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='reliability_metric' AND column_name='period_type'"))
            if not result.fetchone():
                # Add the period_type column
                db.session.execute(text("ALTER TABLE reliability_metric ADD COLUMN period_type VARCHAR(10) DEFAULT 'daily'"))
                
                # Update existing records to have 'daily' as period_type
                db.session.execute(text("UPDATE reliability_metric SET period_type = 'daily' WHERE period_type IS NULL"))
                
                # Make the column NOT NULL
                db.session.execute(text("ALTER TABLE reliability_metric ALTER COLUMN period_type SET NOT NULL"))
                
                # Add unique constraint
                db.session.execute(text("ALTER TABLE reliability_metric ADD CONSTRAINT _date_period_type_uc UNIQUE (date, period_type)"))
                
                db.session.commit()
                print("Database migration completed successfully!")
            else:
                print("period_type column already exists.")
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_database()
