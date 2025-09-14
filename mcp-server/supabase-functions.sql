-- Supabase SQL Functions for Face Recognition
-- These functions need to be created in your Supabase database

-- Function to match faces using vector similarity
CREATE OR REPLACE FUNCTION match_faces(
    query_embedding vector(512),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    name varchar,
    relationship varchar,
    color varchar,
    face_embedding vector(512),
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        faces.id,
        faces.name,
        faces.relationship,
        faces.color,
        faces.face_embedding,
        1 - (faces.face_embedding <=> query_embedding) AS similarity
    FROM faces
    WHERE 1 - (faces.face_embedding <=> query_embedding) > match_threshold
    ORDER BY faces.face_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to add a new face with validation
CREATE OR REPLACE FUNCTION add_face(
    face_name varchar,
    face_relationship varchar,
    face_color varchar DEFAULT 'blue',
    face_embedding vector(512) DEFAULT NULL,
    face_image_url text DEFAULT NULL,
    face_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    name varchar,
    relationship varchar,
    color varchar,
    created_at timestamptz
)
LANGUAGE plpgsql
AS $$
DECLARE
    new_face_id uuid;
BEGIN
    -- Insert the new face
    INSERT INTO faces (name, relationship, color, face_embedding, image_url, user_id)
    VALUES (face_name, face_relationship, face_color, face_embedding, face_image_url, face_user_id)
    RETURNING faces.id INTO new_face_id;
    
    -- Return the created face
    RETURN QUERY
    SELECT faces.id, faces.name, faces.relationship, faces.color, faces.created_at
    FROM faces
    WHERE faces.id = new_face_id;
END;
$$;

-- Function to update face information
CREATE OR REPLACE FUNCTION update_face_info(
    face_id uuid,
    new_name varchar DEFAULT NULL,
    new_relationship varchar DEFAULT NULL,
    new_color varchar DEFAULT NULL,
    new_embedding vector(512) DEFAULT NULL,
    new_image_url text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    name varchar,
    relationship varchar,
    color varchar,
    updated_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Update only provided fields
    UPDATE faces
    SET
        name = COALESCE(new_name, faces.name),
        relationship = COALESCE(new_relationship, faces.relationship),
        color = COALESCE(new_color, faces.color),
        face_embedding = COALESCE(new_embedding, faces.face_embedding),
        image_url = COALESCE(new_image_url, faces.image_url),
        updated_at = NOW()
    WHERE faces.id = face_id;
    
    -- Return the updated face
    RETURN QUERY
    SELECT faces.id, faces.name, faces.relationship, faces.color, faces.updated_at
    FROM faces
    WHERE faces.id = face_id;
END;
$$;

-- Function to get face statistics
CREATE OR REPLACE FUNCTION get_face_stats(user_id_param uuid DEFAULT NULL)
RETURNS TABLE (
    total_faces bigint,
    unique_relationships bigint,
    most_common_relationship varchar,
    last_updated timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_faces,
        COUNT(DISTINCT relationship) as unique_relationships,
        (SELECT relationship FROM faces 
         WHERE (user_id_param IS NULL OR user_id = user_id_param)
         GROUP BY relationship 
         ORDER BY COUNT(*) DESC 
         LIMIT 1) as most_common_relationship,
        MAX(updated_at) as last_updated
    FROM faces
    WHERE (user_id_param IS NULL OR user_id = user_id_param);
END;
$$;
