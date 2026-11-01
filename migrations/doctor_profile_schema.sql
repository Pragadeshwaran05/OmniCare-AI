-- ============================================================
-- OMNICARE AI — DOCTOR PROFILE DATABASE SCHEMA MIGRATION
-- Adds professional attributes, working schedule, and credentials
-- ============================================================

-- 1. Extend doctors table with profile fields
ALTER TABLE doctors
    ADD COLUMN IF NOT EXISTS profile_photo_path TEXT,
    ADD COLUMN IF NOT EXISTS profile_photo_url TEXT,
    ADD COLUMN IF NOT EXISTS qualification TEXT DEFAULT 'MBBS',
    ADD COLUMN IF NOT EXISTS department TEXT DEFAULT 'General Medicine',
    ADD COLUMN IF NOT EXISTS experience_years INTEGER DEFAULT 5,
    ADD COLUMN IF NOT EXISTS professional_bio TEXT DEFAULT 'A dedicated physician with experience in patient care, chronic disease management, and preventive healthcare.',
    ADD COLUMN IF NOT EXISTS consultation_days JSONB DEFAULT '["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]'::jsonb,
    ADD COLUMN IF NOT EXISTS consultation_start_time TEXT DEFAULT '09:00',
    ADD COLUMN IF NOT EXISTS consultation_end_time TEXT DEFAULT '17:00',
    ADD COLUMN IF NOT EXISTS consultation_mode TEXT DEFAULT 'both',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 2. Create doctor_documents table for credential verification
CREATE TABLE IF NOT EXISTS doctor_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL, -- 'medical_registration', 'mbbs_degree', 'postgraduate_degree', 'experience_certificate', 'other'
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    file_size_formatted VARCHAR(50),
    file_path TEXT NOT NULL,
    file_url TEXT,
    mime_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'Verified', -- 'Verified', 'Pending Verification', 'Active'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_doctor_documents_doctor_id ON doctor_documents(doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctor_documents_type ON doctor_documents(document_type);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE doctor_documents ENABLE ROW LEVEL SECURITY;

-- 5. Policies: Doctors can only manage their own documents
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'doctor_documents' AND policyname = 'doctors_manage_own_documents'
    ) THEN
        CREATE POLICY doctors_manage_own_documents ON doctor_documents
            FOR ALL
            USING (auth.uid() = doctor_id)
            WITH CHECK (auth.uid() = doctor_id);
    END IF;
END $$;
