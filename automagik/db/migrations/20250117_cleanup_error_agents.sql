-- Clean up existing error agents
DELETE FROM agents WHERE name LIKE '%_error';

-- Add constraint to prevent agent names ending with '_error'
ALTER TABLE agents 
ADD CONSTRAINT check_agent_name_not_error 
CHECK (name NOT LIKE '%_error');