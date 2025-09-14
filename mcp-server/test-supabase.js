#!/usr/bin/env node

// Simple Supabase connection test
// Run with: node test-supabase.js

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

console.log('🔍 Testing Supabase Connection...\n');

// Check environment variables
if (!supabaseUrl) {
  console.error('❌ SUPABASE_URL not found in environment variables');
  process.exit(1);
}

if (!supabaseKey) {
  console.error('❌ SUPABASE_SERVICE_ROLE_KEY not found in environment variables');
  process.exit(1);
}

console.log('✅ Environment variables found');
console.log(`📍 Supabase URL: ${supabaseUrl}`);
console.log(`🔑 Service Key: ${supabaseKey.substring(0, 20)}...`);

// Create Supabase client
const supabase = createClient(supabaseUrl, supabaseKey);

async function testConnection() {
  try {
    console.log('\n🧪 Testing basic connection...');
    
    // Test 1: Basic connection
    const { data, error } = await supabase.from('faces').select('count').limit(1);
    
    if (error) {
      console.error('❌ Basic connection failed:', error.message);
      return false;
    }
    
    console.log('✅ Basic connection successful');
    
    // Test 2: Check if faces table exists
    console.log('\n🧪 Testing faces table...');
    const { data: tableData, error: tableError } = await supabase
      .from('faces')
      .select('id')
      .limit(1);
    
    if (tableError) {
      console.error('❌ Faces table error:', tableError.message);
      console.log('💡 You may need to run the database schema setup');
      return false;
    }
    
    console.log('✅ Faces table accessible');
    
    // Test 3: Check vector extension
    console.log('\n🧪 Testing vector functions...');
    const { data: vectorData, error: vectorError } = await supabase
      .rpc('match_faces', {
        query_embedding: Array(512).fill(0), // Dummy vector
        match_threshold: 0.1,
        match_count: 1
      });
    
    if (vectorError) {
      console.error('❌ Vector functions error:', vectorError.message);
      console.log('💡 You may need to run the supabase-functions.sql setup');
      return false;
    }
    
    console.log('✅ Vector functions accessible');
    
    // Test 4: Insert a test record
    console.log('\n🧪 Testing insert operation...');
    const testFace = {
      name: 'Test User',
      relationship: 'test',
      color: 'blue',
      face_embedding: Array(512).fill(0.1) // Dummy embedding
    };
    
    const { data: insertData, error: insertError } = await supabase
      .from('faces')
      .insert([testFace])
      .select()
      .single();
    
    if (insertError) {
      console.error('❌ Insert test failed:', insertError.message);
      return false;
    }
    
    console.log('✅ Insert operation successful');
    console.log(`📝 Created test record with ID: ${insertData.id}`);
    
    // Test 5: Clean up test record
    console.log('\n🧪 Cleaning up test record...');
    const { error: deleteError } = await supabase
      .from('faces')
      .delete()
      .eq('id', insertData.id);
    
    if (deleteError) {
      console.error('❌ Delete test failed:', deleteError.message);
      return false;
    }
    
    console.log('✅ Delete operation successful');
    
    console.log('\n🎉 All tests passed! Supabase connection is working perfectly.');
    return true;
    
  } catch (error) {
    console.error('❌ Connection test failed:', error.message);
    return false;
  }
}

// Run the test
testConnection().then(success => {
  if (success) {
    console.log('\n✅ Supabase connection is ready for your MCP server!');
    process.exit(0);
  } else {
    console.log('\n❌ Supabase connection needs attention.');
    process.exit(1);
  }
});
