-- ==========================================
-- GATE ANPR SYSTEM - SUPABASE POSTGRES SCHEMA
-- ==========================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Uncomment if pg_cron is supported in your Supabase project
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. ENUMS
DO $$ BEGIN CREATE TYPE user_role AS ENUM ('admin', 'resident', 'guard'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE vehicle_type_enum AS ENUM ('car', 'bike', 'truck', 'other'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE vehicle_status_enum AS ENUM ('authorized', 'pending', 'denied'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE visitor_pass_status_enum AS ENUM ('active', 'expired', 'revoked', 'consumed'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE event_type_enum AS ENUM ('entry', 'exit'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE log_decision_enum AS ENUM ('authorized', 'visitor_allowed', 'pending', 'denied', 'blacklisted', 'unknown'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE log_source_enum AS ENUM ('camera', 'manual', 'api'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE alert_type_enum AS ENUM ('blacklisted_detected', 'unknown_vehicle', 'low_confidence_ocr', 'forced_entry', 'expired_visitor_attempt', 'repeat_denied_attempt'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE alert_severity_enum AS ENUM ('low', 'medium', 'high', 'critical'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE alert_status_enum AS ENUM ('open', 'acknowledged', 'resolved'); EXCEPTION WHEN duplicate_object THEN null; END $$;

-- 3. FUNCTIONS
-- Trigger Function for updated_at
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Plate Normalization Function
CREATE OR REPLACE FUNCTION normalize_plate(raw_plate text)
RETURNS text AS $$
BEGIN
    -- Uppercase, remove spaces, hyphens, and any special characters
    RETURN regexp_replace(upper(raw_plate), '[^A-Z0-9]', '', 'g');
END;
$$ language 'plpgsql' IMMUTABLE;

-- 4. TABLES

-- 4.1 profiles
CREATE TABLE IF NOT EXISTS profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name text,
    role user_role DEFAULT 'resident',
    apartment_number text,
    phone text,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE profiles IS 'Extended user profile data linked to Supabase Auth.';

-- 4.2 residents
CREATE TABLE IF NOT EXISTS residents (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id uuid REFERENCES profiles(id) ON DELETE CASCADE UNIQUE,
    tower text,
    flat_number text,
    occupancy_status text,
    emergency_contact text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 4.3 vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    resident_id uuid REFERENCES residents(id) ON DELETE SET NULL,
    plate_number text UNIQUE NOT NULL, -- Normalized plate
    plate_display text NOT NULL,       -- Original formatted plate
    vehicle_type vehicle_type_enum,
    color text,
    brand_model text,
    status vehicle_status_enum DEFAULT 'pending',
    is_blacklisted boolean DEFAULT false,
    blacklist_reason text,
    approved_by uuid REFERENCES profiles(id) ON DELETE SET NULL,
    approved_at timestamptz,
    notes text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 4.4 visitor_passes
CREATE TABLE IF NOT EXISTS visitor_passes (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    resident_id uuid REFERENCES residents(id) ON DELETE CASCADE,
    visitor_name text NOT NULL,
    visitor_phone text,
    vehicle_plate text, -- Expected normalized plate of visitor
    purpose text,
    valid_from timestamptz NOT NULL,
    valid_until timestamptz NOT NULL,
    allowed_entries int DEFAULT 1,
    used_entries int DEFAULT 0,
    status visitor_pass_status_enum DEFAULT 'active',
    qr_code_token text UNIQUE,
    approved_by uuid REFERENCES profiles(id) ON DELETE SET NULL,
    created_by uuid REFERENCES profiles(id) ON DELETE SET NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 4.5 entry_logs
CREATE TABLE IF NOT EXISTS entry_logs (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    gate_name text,
    event_type event_type_enum DEFAULT 'entry',
    plate_number_normalized text,
    plate_number_raw text,
    ocr_confidence numeric(5,2),
    source log_source_enum DEFAULT 'camera',
    vehicle_id uuid REFERENCES vehicles(id) ON DELETE SET NULL,
    resident_id uuid REFERENCES residents(id) ON DELETE SET NULL,
    visitor_pass_id uuid REFERENCES visitor_passes(id) ON DELETE SET NULL,
    decision log_decision_enum,
    reason text,
    snapshot_url text,
    scanned_at timestamptz DEFAULT now(),
    processed_at timestamptz DEFAULT now()
);

-- 4.6 alerts
CREATE TABLE IF NOT EXISTS alerts (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type alert_type_enum,
    severity alert_severity_enum,
    plate_number text,
    entry_log_id uuid REFERENCES entry_logs(id) ON DELETE CASCADE,
    message text,
    status alert_status_enum DEFAULT 'open',
    assigned_to uuid REFERENCES profiles(id) ON DELETE SET NULL,
    resolved_by uuid REFERENCES profiles(id) ON DELETE SET NULL,
    resolved_at timestamptz,
    meta jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 4.7 gate_devices (optional)
CREATE TABLE IF NOT EXISTS gate_devices (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name text,
    location text,
    api_key_hash text,
    is_active boolean DEFAULT true,
    last_seen_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 5. TRIGGERS
-- Auto-update timestamps
CREATE TRIGGER update_profiles_modtime BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
CREATE TRIGGER update_residents_modtime BEFORE UPDATE ON residents FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
CREATE TRIGGER update_vehicles_modtime BEFORE UPDATE ON vehicles FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
CREATE TRIGGER update_visitor_passes_modtime BEFORE UPDATE ON visitor_passes FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
CREATE TRIGGER update_alerts_modtime BEFORE UPDATE ON alerts FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
CREATE TRIGGER update_gate_devices_modtime BEFORE UPDATE ON gate_devices FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

-- Auto-normalize vehicle plate before insert/update
CREATE OR REPLACE FUNCTION set_normalized_plate()
RETURNS TRIGGER AS $$
BEGIN
    NEW.plate_number = normalize_plate(NEW.plate_number);
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_normalize_plate BEFORE INSERT OR UPDATE ON vehicles FOR EACH ROW EXECUTE PROCEDURE set_normalized_plate();

-- 6. INDEXES (Optimized for frequent queries)
CREATE INDEX IF NOT EXISTS idx_entry_logs_scanned_at ON entry_logs (scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_entry_logs_plate_norm ON entry_logs (plate_number_normalized);
CREATE INDEX IF NOT EXISTS idx_visitor_passes_dates_status ON visitor_passes (valid_from, valid_until, status);
CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON alerts (status, severity);
CREATE INDEX IF NOT EXISTS idx_vehicles_plate_num ON vehicles (plate_number);

-- 7. REALTIME PUBLICATION
-- Requires `supabase_realtime` publication to exist (Supabase defaults this)
BEGIN;
  DROP PUBLICATION IF EXISTS supabase_realtime;
  CREATE PUBLICATION supabase_realtime;
COMMIT;
ALTER PUBLICATION supabase_realtime ADD TABLE entry_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE visitor_passes;
ALTER PUBLICATION supabase_realtime ADD TABLE vehicles;

-- 8. CORE AUTOMATION: INGEST RPC
-- SECURITY DEFINER allows camera APIs (via Service Role / Anon) to safely log entries without admin auth, constrained by search_path.
CREATE OR REPLACE FUNCTION ingest_plate_scan(
    plate_raw text,
    ocr_confidence numeric,
    gate_name text,
    event_type text DEFAULT 'entry',
    source text DEFAULT 'camera',
    snapshot_url text DEFAULT NULL,
    scanned_at timestamptz DEFAULT now()
) RETURNS jsonb AS $$
DECLARE
    v_norm_plate text;
    v_vehicle record;
    v_visitor_pass record;
    v_decision log_decision_enum;
    v_reason text;
    v_resident_id uuid;
    v_vehicle_id uuid;
    v_pass_id uuid;
    v_log_id uuid;
    v_alert_created boolean := false;
    v_alert_type alert_type_enum;
    v_alert_severity alert_severity_enum;
    v_recent_denied_count int;
BEGIN
    -- 1. Normalize plate
    v_norm_plate := normalize_plate(plate_raw);

    -- 2. Find matching vehicle
    SELECT * INTO v_vehicle FROM vehicles WHERE plate_number = v_norm_plate LIMIT 1;
    
    IF FOUND THEN
        v_vehicle_id := v_vehicle.id;
        v_resident_id := v_vehicle.resident_id;
        
        -- 3. Check if blacklisted
        IF v_vehicle.is_blacklisted THEN
            v_decision := 'blacklisted';
            v_reason := COALESCE(v_vehicle.blacklist_reason, 'Vehicle is blacklisted');
            v_alert_type := 'blacklisted_detected';
            v_alert_severity := 'critical';
        -- 4. Check if authorized
        ELSIF v_vehicle.status = 'authorized' THEN
            v_decision := 'authorized';
            v_reason := 'Registered vehicle authorized';
        -- 5. Pending/Denied
        ELSIF v_vehicle.status = 'pending' THEN
            v_decision := 'pending';
            v_reason := 'Vehicle approval is pending';
        ELSIF v_vehicle.status = 'denied' THEN
            v_decision := 'denied';
            v_reason := 'Vehicle access is denied';
        END IF;
    ELSE
        -- 6. Check Active Visitor Pass (match exact normalized plate OR if plate is null meaning open pass)
        SELECT * INTO v_visitor_pass 
        FROM visitor_passes 
        WHERE status = 'active' 
          AND valid_from <= scanned_at 
          AND valid_until >= scanned_at 
          AND (vehicle_plate IS NULL OR normalize_plate(vehicle_plate) = v_norm_plate)
          AND used_entries < allowed_entries
        ORDER BY created_at DESC LIMIT 1;

        IF FOUND THEN
            v_pass_id := v_visitor_pass.id;
            v_resident_id := v_visitor_pass.resident_id;
            v_decision := 'visitor_allowed';
            v_reason := 'Valid visitor pass found';

            -- Update pass usage
            UPDATE visitor_passes 
            SET used_entries = used_entries + 1,
                status = CASE WHEN used_entries + 1 >= allowed_entries THEN 'consumed'::visitor_pass_status_enum ELSE 'active'::visitor_pass_status_enum END,
                updated_at = now()
            WHERE id = v_pass_id;
        ELSE
            -- 7. Unknown
            v_decision := 'unknown';
            v_reason := 'Plate not found in authorized vehicles or visitor passes';
            v_alert_type := 'unknown_vehicle';
            v_alert_severity := 'low';
        END IF;
    END IF;

    -- Duplicate/repeat denied logic (>= 3 times in 10 mins)
    IF v_decision IN ('unknown', 'denied') THEN
        SELECT count(*) INTO v_recent_denied_count
        FROM entry_logs
        WHERE plate_number_normalized = v_norm_plate
          AND decision IN ('unknown', 'denied')
          AND scanned_at >= (now() - interval '10 minutes');
          
        IF v_recent_denied_count >= 2 THEN -- 2 previous + 1 current = 3
            v_alert_type := 'repeat_denied_attempt';
            v_alert_severity := 'medium';
            v_reason := v_reason || ' (Repeated Attempt)';
        END IF;
    END IF;

    -- Low OCR confidence check (creates secondary alert if no critical alert is active)
    IF ocr_confidence < 70.0 AND v_alert_type IS NULL THEN
        v_alert_type := 'low_confidence_ocr';
        v_alert_severity := 'low';
    END IF;

    -- 8. Insert Log
    INSERT INTO entry_logs (
        gate_name, event_type, plate_number_normalized, plate_number_raw, 
        ocr_confidence, source, vehicle_id, resident_id, visitor_pass_id, 
        decision, reason, snapshot_url, scanned_at, processed_at
    ) VALUES (
        gate_name, event_type::event_type_enum, v_norm_plate, plate_raw, 
        ocr_confidence, source::log_source_enum, v_vehicle_id, v_resident_id, v_pass_id, 
        v_decision, v_reason, snapshot_url, scanned_at, now()
    ) RETURNING id INTO v_log_id;

    -- Create alert
    IF v_alert_type IS NOT NULL THEN
        INSERT INTO alerts (
            alert_type, severity, plate_number, entry_log_id, message
        ) VALUES (
            v_alert_type, v_alert_severity, v_norm_plate, v_log_id, v_reason
        );
        v_alert_created := true;
    END IF;

    -- 9. Return structured JSON payload
    RETURN jsonb_build_object(
        'decision', v_decision,
        'reason', v_reason,
        'vehicle_id', v_vehicle_id,
        'resident_id', v_resident_id,
        'visitor_pass_id', v_pass_id,
        'entry_log_id', v_log_id,
        'alert_created', v_alert_created
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Auto-expire visitor passes (Call via pg_cron or Edge Function)
CREATE OR REPLACE FUNCTION expire_visitor_passes() RETURNS void AS $$
BEGIN
    UPDATE visitor_passes
    SET status = 'expired'
    WHERE status = 'active' AND valid_until < now();
END;
$$ LANGUAGE plpgsql;

-- 9. ROW LEVEL SECURITY (RLS)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE residents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitor_passes ENABLE ROW LEVEL SECURITY;
ALTER TABLE entry_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE gate_devices ENABLE ROW LEVEL SECURITY;

-- Helper function
CREATE OR REPLACE FUNCTION get_my_role() RETURNS user_role AS $$
    SELECT role FROM profiles WHERE id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public;

-- Admin policies
CREATE POLICY admin_all_profiles ON profiles FOR ALL TO authenticated USING (get_my_role() = 'admin');
CREATE POLICY admin_all_residents ON residents FOR ALL TO authenticated USING (get_my_role() = 'admin');
CREATE POLICY admin_all_vehicles ON vehicles FOR ALL TO authenticated USING (get_my_role() = 'admin');
CREATE POLICY admin_all_visitor_passes ON visitor_passes FOR ALL TO authenticated USING (get_my_role() = 'admin');
CREATE POLICY admin_all_entry_logs ON entry_logs FOR ALL TO authenticated USING (get_my_role() = 'admin');
CREATE POLICY admin_all_alerts ON alerts FOR ALL TO authenticated USING (get_my_role() = 'admin');
CREATE POLICY admin_all_gate_devices ON gate_devices FOR ALL TO authenticated USING (get_my_role() = 'admin');

-- Resident policies
CREATE POLICY resident_read_own_profile ON profiles FOR SELECT TO authenticated USING (id = auth.uid());
CREATE POLICY resident_update_own_profile ON profiles FOR UPDATE TO authenticated USING (id = auth.uid());
CREATE POLICY resident_read_own_resident ON residents FOR SELECT TO authenticated USING (profile_id = auth.uid());

CREATE POLICY resident_read_own_vehicles ON vehicles FOR SELECT TO authenticated 
USING (resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()));
CREATE POLICY resident_insert_own_vehicles ON vehicles FOR INSERT TO authenticated 
WITH CHECK (resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()));
CREATE POLICY resident_update_own_vehicles ON vehicles FOR UPDATE TO authenticated 
USING (resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()))
WITH CHECK (is_blacklisted = false); 
CREATE POLICY resident_delete_own_vehicles ON vehicles FOR DELETE TO authenticated 
USING (resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()));

CREATE POLICY resident_crud_own_passes ON visitor_passes FOR ALL TO authenticated 
USING (resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()));

CREATE POLICY resident_read_own_logs ON entry_logs FOR SELECT TO authenticated 
USING (
    resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()) 
    OR vehicle_id IN (SELECT id FROM vehicles WHERE resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()))
);

CREATE POLICY resident_read_own_alerts ON alerts FOR SELECT TO authenticated
USING (
    entry_log_id IN (SELECT id FROM entry_logs WHERE resident_id IN (SELECT id FROM residents WHERE profile_id = auth.uid()))
);

-- Guard policies
CREATE POLICY guard_read_logs ON entry_logs FOR SELECT TO authenticated USING (get_my_role() = 'guard');
CREATE POLICY guard_insert_logs ON entry_logs FOR INSERT TO authenticated WITH CHECK (get_my_role() = 'guard');
CREATE POLICY guard_read_alerts ON alerts FOR SELECT TO authenticated USING (get_my_role() = 'guard');
CREATE POLICY guard_read_vehicles ON vehicles FOR SELECT TO authenticated USING (get_my_role() = 'guard');
CREATE POLICY guard_read_passes ON visitor_passes FOR SELECT TO authenticated USING (get_my_role() = 'guard');

-- 10. SEED DATA FOR TESTING 
-- (Note: In pure Supabase, profiles needs a matching auth.users row. We insert without profile linking here for testing pure DB logic)
DO $$
DECLARE
    res_id uuid := uuid_generate_v4();
    auth_car_id uuid := uuid_generate_v4();
    blacklisted_car_id uuid := uuid_generate_v4();
    pending_car_id uuid := uuid_generate_v4();
    pass_id uuid := uuid_generate_v4();
BEGIN
    INSERT INTO residents (id, tower, flat_number, occupancy_status)
    VALUES (res_id, 'A', '101', 'owner');

    -- Authorized Vehicle
    INSERT INTO vehicles (id, resident_id, plate_number, plate_display, status)
    VALUES (auth_car_id, res_id, 'MH12AB1234', 'MH 12 AB 1234', 'authorized');

    -- Blacklisted Vehicle
    INSERT INTO vehicles (id, resident_id, plate_number, plate_display, status, is_blacklisted, blacklist_reason)
    VALUES (blacklisted_car_id, res_id, 'KA01XYZ999', 'KA-01-XYZ-999', 'denied', true, 'Reckless driving');

    -- Pending Vehicle
    INSERT INTO vehicles (id, resident_id, plate_number, plate_display, status)
    VALUES (pending_car_id, res_id, 'DL8C8888', 'DL-8C-8888', 'pending');

    -- Active Visitor Pass
    INSERT INTO visitor_passes (id, resident_id, visitor_name, vehicle_plate, valid_from, valid_until, allowed_entries, used_entries, status)
    VALUES (pass_id, res_id, 'John Doe', 'HR26DK1111', now() - interval '1 hour', now() + interval '1 day', 2, 0, 'active');

    -- Expired Visitor Pass
    INSERT INTO visitor_passes (id, resident_id, visitor_name, vehicle_plate, valid_from, valid_until, allowed_entries, used_entries, status)
    VALUES (uuid_generate_v4(), res_id, 'Jane Smith', 'UP16ZZ0000', now() - interval '2 days', now() - interval '1 day', 1, 0, 'expired');
END $$;


-- ==========================================
-- 11. TEST CALLS FOR ingest_plate_scan
-- ==========================================
/*
-- Copy/paste these into the Supabase SQL editor to test the logic:

-- 1. Authorized Vehicle
SELECT ingest_plate_scan('mh 12 ab 1234', 95.5, 'Main Gate');

-- 2. Blacklisted Vehicle
SELECT ingest_plate_scan('KA01XYZ999', 92.0, 'Main Gate');

-- 3. Pending Vehicle
SELECT ingest_plate_scan('dl-8c-8888', 88.0, 'Main Gate');

-- 4. Valid Visitor (Consumes 1 entry out of 2)
SELECT ingest_plate_scan('hr26dk1111', 89.5, 'Main Gate');

-- 5. Valid Visitor (Second entry - consumes last entry, sets status to 'consumed')
SELECT ingest_plate_scan('hr26dk1111', 90.0, 'Main Gate');

-- 6. Expired Visitor (Will evaluate as Unknown)
SELECT ingest_plate_scan('up16zz0000', 85.0, 'Main Gate');

-- 7. Unknown Vehicle
SELECT ingest_plate_scan('UNKNOWN999', 91.0, 'Main Gate');

-- 8. Low OCR Confidence (Triggers low_confidence_ocr alert)
SELECT ingest_plate_scan('mh 12 ab 1234', 65.0, 'Main Gate');

-- 9. Repeat Denied / Unknown (Run 3 times to trigger 'repeat_denied_attempt' alert)
SELECT ingest_plate_scan('REPEAT999', 99.0, 'Main Gate');
SELECT ingest_plate_scan('REPEAT999', 99.0, 'Main Gate');
SELECT ingest_plate_scan('REPEAT999', 99.0, 'Main Gate');

-- 10. Manual Guard Entry
SELECT ingest_plate_scan('MH12AB1234', 100.0, 'Main Gate', 'entry', 'manual');

-- View Logs & Alerts after running:
SELECT * FROM entry_logs ORDER BY scanned_at DESC;
SELECT * FROM alerts ORDER BY created_at DESC;
*/
