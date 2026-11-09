-- ============================================================
-- OMNICARE AI — MEDICAL RECORDS ENHANCED SCHEMA MIGRATION
-- Supports Doctor Uploads, Built-in Consultation Notes, Prescriptions & Other Documents
-- ============================================================

-- 1. Extend medical_records table with optional audit and metadata columns
ALTER TABLE medical_records
    ADD COLUMN IF NOT EXISTS doctor_id UUID REFERENCES doctors(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS document_date DATE DEFAULT CURRENT_DATE,
    ADD COLUMN IF NOT EXISTS document_status VARCHAR(50) DEFAULT 'Active', -- 'Active', 'Draft', 'Archived'
    ADD COLUMN IF NOT EXISTS hospital_name TEXT,
    ADD COLUMN IF NOT EXISTS doctor_name TEXT,
    ADD COLUMN IF NOT EXISTS structured_data JSONB,
    ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 2. Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_medical_records_patient_id ON medical_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_medical_records_doctor_id ON medical_records(doctor_id);
CREATE INDEX IF NOT EXISTS idx_medical_records_record_type ON medical_records(record_type);
