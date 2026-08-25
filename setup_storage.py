"""Setup Supabase Storage Bucket and RLS policies."""
from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # 1. Insert bucket into storage.buckets if not present
    db.session.execute(text("""
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('medical-reports', 'medical-reports', true)
        ON CONFLICT (id) DO UPDATE SET public = true;
    """))
    
    # 2. Add RLS policy to storage.objects to allow anon uploads & reads to medical-reports
    db.session.execute(text("""
        DO $$
        BEGIN
            DROP POLICY IF EXISTS "Public Access medical-reports select" ON storage.objects;
            CREATE POLICY "Public Access medical-reports select" ON storage.objects FOR SELECT USING (bucket_id = 'medical-reports');
            
            DROP POLICY IF EXISTS "Public Access medical-reports insert" ON storage.objects;
            CREATE POLICY "Public Access medical-reports insert" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'medical-reports');

            DROP POLICY IF EXISTS "Public Access medical-reports update" ON storage.objects;
            CREATE POLICY "Public Access medical-reports update" ON storage.objects FOR UPDATE USING (bucket_id = 'medical-reports');

            DROP POLICY IF EXISTS "Public Access medical-reports delete" ON storage.objects;
            CREATE POLICY "Public Access medical-reports delete" ON storage.objects FOR DELETE USING (bucket_id = 'medical-reports');
        END $$;
    """))
    db.session.commit()
    print("SUCCESS: Configured Supabase medical-reports bucket and RLS policies!")
