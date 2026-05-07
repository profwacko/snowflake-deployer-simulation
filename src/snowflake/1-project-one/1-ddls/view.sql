CREATE OR REPLACE VIEW project_one_active AS
SELECT id, name, created_at
FROM project_one
WHERE created_at >= DATEADD(day, -30, CURRENT_TIMESTAMP);
