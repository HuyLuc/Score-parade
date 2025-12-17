-- ============================================
-- Score Parade Database Initialization
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Sessions table - Lưu thông tin phiên chấm điểm
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) UNIQUE NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'testing', -- 'testing' or 'practising'
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'completed', 'cancelled'
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    total_frames INTEGER DEFAULT 0,
    video_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Persons table - Lưu thông tin từng người trong session
-- ============================================
CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL, -- Track ID từ tracker
    score DECIMAL(5,2) DEFAULT 100.00,
    total_errors INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'stopped', 'completed'
    first_frame INTEGER,
    last_frame INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(session_id, person_id)
);

-- ============================================
-- Errors table - Lưu chi tiết từng lỗi
-- ============================================
CREATE TABLE IF NOT EXISTS errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL,
    error_type VARCHAR(50) NOT NULL, -- 'arm_angle', 'leg_angle', 'head_angle', etc.
    severity DECIMAL(5,2) NOT NULL,
    deduction DECIMAL(5,2) NOT NULL,
    message TEXT,
    frame_number INTEGER,
    timestamp_sec DECIMAL(10,3),
    is_sequence BOOLEAN DEFAULT FALSE,
    sequence_length INTEGER,
    start_frame INTEGER,
    end_frame INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Golden Templates table - Lưu thông tin template chuẩn
-- ============================================
CREATE TABLE IF NOT EXISTS golden_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    video_path VARCHAR(500),
    skeleton_path VARCHAR(500),
    profile_path VARCHAR(500),
    camera_angle VARCHAR(50) DEFAULT 'front',
    total_frames INTEGER,
    fps DECIMAL(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Config table - Lưu cấu hình hệ thống
-- ============================================
CREATE TABLE IF NOT EXISTS configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Indexes for better query performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_persons_session_id ON persons(session_id);
CREATE INDEX IF NOT EXISTS idx_persons_person_id ON persons(person_id);

CREATE INDEX IF NOT EXISTS idx_errors_session_id ON errors(session_id);
CREATE INDEX IF NOT EXISTS idx_errors_person_id ON errors(person_id);
CREATE INDEX IF NOT EXISTS idx_errors_error_type ON errors(error_type);
CREATE INDEX IF NOT EXISTS idx_errors_frame_number ON errors(frame_number);

-- ============================================
-- Insert default config values
-- ============================================
INSERT INTO configs (key, value, description) VALUES
    ('scoring_config', '{
        "initial_score": 100,
        "fail_thresholds": {
            "testing": 60.0,
            "practising": 0.0,
            "default": 50.0
        },
        "multi_person_enabled": true,
        "error_weights": {
            "arm_angle": 1.0,
            "leg_angle": 1.0,
            "arm_height": 0.8,
            "leg_height": 0.8,
            "head_angle": 1.0,
            "torso_stability": 0.8,
            "rhythm": 1.0,
            "distance": 0.8,
            "speed": 0.8
        }
    }', 'Cấu hình chấm điểm'),
    
    ('multi_person_config', '{
        "enabled": true,
        "tracking_method": "bytetrack",
        "max_persons": 5,
        "max_disappeared": 60,
        "iou_threshold": 0.25
    }', 'Cấu hình theo dõi nhiều người'),
    
    ('error_thresholds', '{
        "arm_angle": 50.0,
        "leg_angle": 45.0,
        "arm_height": 50.0,
        "leg_height": 45.0,
        "head_angle": 30.0,
        "torso_stability": 0.85,
        "rhythm": 0.15,
        "distance": 50.0,
        "speed": 80.0
    }', 'Ngưỡng sai lệch cho từng loại lỗi')
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- Function to update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- Triggers for auto-updating updated_at
-- ============================================
DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_persons_updated_at ON persons;
CREATE TRIGGER update_persons_updated_at
    BEFORE UPDATE ON persons
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_golden_templates_updated_at ON golden_templates;
CREATE TRIGGER update_golden_templates_updated_at
    BEFORE UPDATE ON golden_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_configs_updated_at ON configs;
CREATE TRIGGER update_configs_updated_at
    BEFORE UPDATE ON configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Grant permissions (if needed)
-- ============================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scoreuser;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scoreuser;

COMMENT ON TABLE sessions IS 'Bảng lưu thông tin các phiên chấm điểm';
COMMENT ON TABLE persons IS 'Bảng lưu thông tin từng người trong mỗi phiên';
COMMENT ON TABLE errors IS 'Bảng lưu chi tiết các lỗi phát hiện được';
COMMENT ON TABLE golden_templates IS 'Bảng lưu thông tin các template chuẩn';
COMMENT ON TABLE configs IS 'Bảng lưu cấu hình hệ thống';

