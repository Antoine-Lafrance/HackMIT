-- Facial Recognition Database Schema for Dementia Aid MCP Server
-- This schema supports face recognition with vector embeddings for similarity search

-- Enable the vector extension for Supabase (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the faces table to store face recognition data
CREATE TABLE IF NOT EXISTS faces (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    relationship VARCHAR(255) NOT NULL, -- e.g., "daughter", "son", "caregiver", "friend"
    color VARCHAR(50) DEFAULT 'blue', -- UI color for visualization
    face_embedding VECTOR(512), -- Face embedding vector (face-api.js uses 512 dimensions)
    image_url TEXT, -- Optional: URL to reference image
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID, -- Link to user account if needed
    
    -- Indexes for performance
    CONSTRAINT unique_name_per_user UNIQUE (name, user_id)
);

-- Create index for vector similarity search (using cosine similarity)
CREATE INDEX IF NOT EXISTS faces_embedding_idx ON faces 
USING ivfflat (face_embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create index for name searches
CREATE INDEX IF NOT EXISTS faces_name_idx ON faces (name);

-- Create index for relationship searches
CREATE INDEX IF NOT EXISTS faces_relationship_idx ON faces (relationship);

-- Create index for user_id
CREATE INDEX IF NOT EXISTS faces_user_id_idx ON faces (user_id);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_faces_updated_at 
    BEFORE UPDATE ON faces 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional)
-- INSERT INTO faces (name, relationship, color, face_embedding) VALUES
-- ('John Doe', 'son', 'blue', '[0.1, 0.2, 0.3, ...]'::vector),
-- ('Jane Smith', 'daughter', 'green', '[0.4, 0.5, 0.6, ...]'::vector);
