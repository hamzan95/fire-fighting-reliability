# src/migrate_db.py
import os
from src.main import create_app
from src.extensions import db
from sqlalchemy import text

def migrate_database():
    app = create_app()
    with app.app_context():
        try:
            print("Starting database migration...")
            
            # Check if period_type column exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='reliability_metric' AND column_name='period_type'
            """))
            
            if not result.fetchone():
                print("Adding period_type column...")
                
                # Add the period_type column with default value
                db.session.execute(text("""
                    ALTER TABLE reliability_metric 
                    ADD COLUMN period_type VARCHAR(10) DEFAULT 'daily'
                """))
                
                # Update existing records to have 'daily' as period_type
                db.session.execute(text("""
                    UPDATE reliability_metric 
                    SET period_type = 'daily' 
                    WHERE period_type IS NULL
                """))
                
                # Make the column NOT NULL
                db.session.execute(text("""
                    ALTER TABLE reliability_metric 
                    ALTER COLUMN period_type SET NOT NULL
                """))
                
                # Add unique constraint (drop existing if any, then add new one)
                try:
                    db.session.execute(text("""
                        ALTER TABLE reliability_metric 
                        DROP CONSTRAINT IF EXISTS _date_period_type_uc
                    """))
                except:
                    pass  # Constraint might not exist
                
                db.session.execute(text("""
                    ALTER TABLE reliability_metric 
                    ADD CONSTRAINT _date_period_type_uc UNIQUE (date, period_type)
                """))
                
                db.session.commit()
                print("✅ Database migration completed successfully!")
                print("✅ Added period_type column")
                print("✅ Updated existing records")
                print("✅ Added unique constraint")
            else:
                print("✅ period_type column already exists. No migration needed.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            raise e

if __name__ == "__main__":
    migrate_database()

