-- Fix camera stream_name values to match go2rtc aliases exactly
-- Run: docker exec -i cctv_postgres psql -U postgres -d cctv_db < backend/scripts/fix_camera_stream_names.sql

BEGIN;

-- Remove all cameras with wrong stream_name (RTSP URLs instead of go2rtc aliases)
DELETE FROM stream_sessions;
DELETE FROM cameras;

-- Insert all 6 cameras matching go2rtc.yaml stream names exactly
INSERT INTO cameras (id, branch_id, name, stream_name, rtsp_channel, status, enabled, created_at) VALUES
  (gen_random_uuid(), '11797127-3529-4c7c-bded-b331d501c75c', 'SIG Kendal - Office Lt1', 'sig-kendal-office-lt1', '102', 'active', true, NOW()),
  (gen_random_uuid(), '11797127-3529-4c7c-bded-b331d501c75c', 'SIG Kendal - Gudang 01',  'sig-kendal-gudang-01',  '202', 'active', true, NOW()),
  (gen_random_uuid(), '11797127-3529-4c7c-bded-b331d501c75c', 'SIG Kendal - Lobby',      'sig-kendal-lobby',      '302', 'active', true, NOW()),
  (gen_random_uuid(), '11797127-3529-4c7c-bded-b331d501c75c', 'SIG Kendal - Parking',    'sig-kendal-parking',    '402', 'active', true, NOW()),
  (gen_random_uuid(), '11797127-3529-4c7c-bded-b331d501c75c', 'SIG Kendal - Entrance',   'sig-kendal-entrance',   '502', 'active', true, NOW()),
  (gen_random_uuid(), '11797127-3529-4c7c-bded-b331d501c75c', 'Test Cam 01',             'cam01',                 '102', 'active', true, NOW());

COMMIT;

-- Verify
SELECT id, name, stream_name, enabled FROM cameras ORDER BY name;
