import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY; // Use service role key for server-side operations

if (!supabaseUrl || !supabaseServiceKey) {
  throw new Error('Missing Supabase environment variables. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY');
}

export const supabase = createClient(supabaseUrl, supabaseServiceKey);

// Types for our database schema
export interface FaceRecord {
  id: string;
  name: string;
  relationship: string;
  color: string;
  face_embedding?: number[];
  image_url?: string;
  created_at: string;
  updated_at: string;
  user_id?: string;
}

export interface FaceInsert {
  name: string;
  relationship: string;
  color?: string;
  face_embedding?: number[];
  image_url?: string;
  user_id?: string;
}

export interface FaceUpdate {
  name?: string;
  relationship?: string;
  color?: string;
  face_embedding?: number[];
  image_url?: string;
}
