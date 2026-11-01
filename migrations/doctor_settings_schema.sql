-- ============================================================
-- OMNICARE AI — DOCTOR SETTINGS DATABASE SCHEMA
-- Persists doctor application preferences, security, & notifications
-- ============================================================

-- 1. Extend doctors table with settings & status fields
ALTER TABLE doctors
    ADD COLUMN IF NOT EXISTS theme VARCHAR(20) DEFAULT 'light',
    ADD COLUMN IF NOT EXISTS sidebar_mode VARCHAR(20) DEFAULT 'expanded',
    ADD COLUMN IF NOT EXISTS notify_access_requests BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS notify_access_expiry BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS notify_system_updates BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS account_status VARCHAR(20) DEFAULT 'active';

-- 2. Create separate doctor_settings table for modular isolation
CREATE TABLE IF NOT EXISTS doctor_settings (
    doctor_id UUID PRIMARY KEY REFERENCES doctors(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'light',
    sidebar_mode VARCHAR(20) DEFAULT 'expanded',
    notify_access_requests BOOLEAN DEFAULT TRUE,
    notify_access_expiry BOOLEAN DEFAULT TRUE,
    notify_system_updates BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE doctor_settings ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policy
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'doctor_settings' AND policyname = 'doctors_manage_own_settings'
    ) THEN
        CREATE POLICY doctors_manage_own_settings ON doctor_settings
            FOR ALL
            USING (auth.uid() = doctor_id)
            WITH CHECK (auth.uid() = doctor_id);
    END IF;
END $$;
