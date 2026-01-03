-- Restore categories with original colors
-- This script adds the categories that were used before the refactoring

INSERT INTO categories (user_id, name, color, created_at, updated_at)
VALUES 
    ('default_user', 'Groceries', '#7E57C2', NOW(), NOW()),           -- Purple (matches original #8B5CF6)
    ('default_user', 'Transport', '#26C6DA', NOW(), NOW()),            -- Cyan (matches original #06B6D4)
    ('default_user', 'Food & Dining', '#EC407A', NOW(), NOW()),        -- Pink (matches original #EC4899)
    ('default_user', 'Shopping', '#F9A825', NOW(), NOW()),             -- Amber (matches original #F59E0B)
    ('default_user', 'Entertainment', '#FF7043', NOW(), NOW()),        -- Orange (matches original #F97316)
    ('default_user', 'Utilities', '#5E35B1', NOW(), NOW()),            -- Indigo (matches original #6366F1)
    ('default_user', 'Technology Subscriptions', '#E74C3C', NOW(), NOW()), -- Red (matches original #EF4444)
    ('default_user', 'Telecommunications', '#2196F3', NOW(), NOW()),   -- Blue (matches original #3B82F6)
    ('default_user', 'Healthcare', '#43A047', NOW(), NOW()),           -- Emerald (matches original #10B981)
    ('default_user', 'Salary', '#4CAF50', NOW(), NOW()),               -- Green (matches original #34C759)
    ('default_user', 'Incoming Transfer', '#66BB6A', NOW(), NOW()),    -- Green (matches original #34C759)
    ('default_user', 'Outgoing Transfer', '#90CAF9', NOW(), NOW()),    -- Light blue/gray
    ('default_user', 'Other', '#90CAF9', NOW(), NOW())                 -- Gray (matches original #64748B)
ON CONFLICT (user_id, name) DO UPDATE
SET 
    color = EXCLUDED.color,
    updated_at = NOW();

