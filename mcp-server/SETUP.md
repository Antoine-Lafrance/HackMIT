# Facial Recognition MCP Server Setup Guide

## Prerequisites

1. **Supabase Project**: You need a Supabase project with the vector extension enabled
2. **Node.js**: Version 18 or higher
3. **Environment Variables**: Supabase credentials

## Setup Steps

### 1. Install Dependencies

```bash
cd mcp-server
npm install
```

### 2. Environment Configuration

Create a `.env` file in the `mcp-server` directory with your Supabase credentials:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

**Important**: Use the service role key (not the anon key) for server-side operations. The service role key has full access to your database and bypasses RLS policies.

### 3. Database Setup

Run the SQL scripts in your Supabase SQL editor:

1. First, run `database-schema.sql` to create the faces table and indexes
2. Then, run `supabase-functions.sql` to create the helper functions

### 4. Enable Vector Extension

In your Supabase SQL editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. Build and Run

```bash
npm run build
npm start
```

## Database Schema

The `faces` table includes:
- `id`: Unique identifier
- `name`: Person's name
- `relationship`: Relationship to the user (e.g., "daughter", "son", "caregiver")
- `color`: UI color for visualization
- `face_embedding`: Vector embedding for similarity search (512 dimensions)
- `image_url`: Optional reference to stored image
- `user_id`: Link to user account
- `created_at`, `updated_at`: Timestamps

## Available Operations

### 1. Identify Face
```json
{
  "name": "recognize_face",
  "arguments": {
    "image_data": "base64_encoded_image",
    "operation": "identify"
  }
}
```

### 2. Add New Face
```json
{
  "name": "recognize_face", 
  "arguments": {
    "image_data": "base64_encoded_image",
    "operation": "add_face",
    "name": "John Doe",
    "relationship": "son",
    "color": "blue"
  }
}
```

### 3. List All Faces
```json
{
  "name": "recognize_face",
  "arguments": {
    "image_data": "base64_encoded_image",
    "operation": "list_faces"
  }
}
```

## Architecture

```
User's Phone → Modal Agent → MCP Server → Face Recognition (CDN Models) → Supabase Database
                      ↓
                Face Recognition
                      ↓
              Vector Similarity Search
```

The MCP server processes camera input, loads AI models from CDN, generates face embeddings using face-api.js, and performs similarity searches against stored face embeddings in Supabase.

### **CDN Model Loading**
- Models are loaded directly from `https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights/`
- No need to download or host model files locally
- Models are cached after first load for faster subsequent use
- Includes: SSD MobileNet (face detection), Face Landmarks, Face Recognition

## Troubleshooting

1. **Models not loading**: Ensure you have internet connectivity for initial model downloads
2. **Supabase connection issues**: Verify your environment variables and database setup
3. **Vector extension**: Make sure the vector extension is enabled in your Supabase project
4. **Face detection issues**: Ensure images are clear and contain visible faces

## Next Steps

1. Set up your Supabase project with the provided schema
2. Configure environment variables
3. Test the server with sample images
4. Integrate with your Modal agent and React Native frontend
