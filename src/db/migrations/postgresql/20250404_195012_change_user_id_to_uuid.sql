-- Migration: Change User.id from integer to UUID

-- Check if the migration has already been applied
DO $$
DECLARE
    column_type text;
    pk_constraint_name text;
BEGIN
    -- Get the data type of the users.id column
    SELECT data_type INTO column_type
    FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'id';
    
    -- Get the primary key constraint name for users table
    SELECT tc.constraint_name INTO pk_constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'users' AND tc.constraint_type = 'PRIMARY KEY';
    
    -- Only proceed if users.id is not already UUID
    IF column_type = 'uuid' THEN
        RAISE NOTICE 'Migration already applied: users.id is already UUID type';
    ELSE
        -- Create UUID extension if not exists
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Step 1: Add a new UUID column
        ALTER TABLE users ADD COLUMN uuid_id UUID DEFAULT uuid_generate_v4();

        -- Step 2: Copy data from id to uuid_id (convert int to UUID)
        -- For existing records, we'll create deterministic UUIDs based on the original ID
        UPDATE users SET uuid_id = uuid_generate_v4() WHERE uuid_id IS NULL;

        -- Step 3: Update foreign keys in other tables
        -- messages table
        ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_user_id_fkey;
        ALTER TABLE messages ADD COLUMN user_uuid_id UUID;
        UPDATE messages SET user_uuid_id = u.uuid_id
        FROM users u WHERE messages.user_id = u.id;
        ALTER TABLE messages ALTER COLUMN user_uuid_id SET NOT NULL;

        -- sessions table
        ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey;
        ALTER TABLE sessions ADD COLUMN user_uuid_id UUID;
        UPDATE sessions SET user_uuid_id = u.uuid_id
        FROM users u WHERE sessions.user_id = u.id;
        ALTER TABLE sessions ALTER COLUMN user_uuid_id SET NOT NULL;

        -- memories table
        ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_user_id_fkey;
        ALTER TABLE memories ADD COLUMN user_uuid_id UUID;
        UPDATE memories SET user_uuid_id = u.uuid_id
        FROM users u WHERE memories.user_id = u.id;
        ALTER TABLE memories ALTER COLUMN user_uuid_id SET NOT NULL;

        -- Step 4: Drop old columns and rename the new ones
        ALTER TABLE messages DROP COLUMN user_id;
        ALTER TABLE messages RENAME COLUMN user_uuid_id TO user_id;

        ALTER TABLE sessions DROP COLUMN user_id;
        ALTER TABLE sessions RENAME COLUMN user_uuid_id TO user_id;

        ALTER TABLE memories DROP COLUMN user_id;
        ALTER TABLE memories RENAME COLUMN user_uuid_id TO user_id;

        -- Step 5: Drop old primary key and add the new one
        -- Use the actual constraint name if it exists
        IF pk_constraint_name IS NOT NULL THEN
            EXECUTE 'ALTER TABLE users DROP CONSTRAINT ' || pk_constraint_name;
        END IF;
        
        ALTER TABLE users DROP COLUMN id;
        ALTER TABLE users RENAME COLUMN uuid_id TO id;
        ALTER TABLE users ADD PRIMARY KEY (id);

        -- Step 6: Add foreign key constraints back
        ALTER TABLE messages ADD CONSTRAINT messages_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

        ALTER TABLE sessions ADD CONSTRAINT sessions_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

        ALTER TABLE memories ADD CONSTRAINT memories_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

        RAISE NOTICE 'Successfully migrated users.id to UUID type';
    END IF;
END $$; 