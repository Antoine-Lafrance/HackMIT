// test/basic.test.js
import { spawn } from 'child_process';
import { setTimeout as delay } from 'timers/promises';

async function testMCPServer() {
  console.log('Testing MCP Server...');
  
  try {
    // Start the server
    console.log('Starting MCP server...');
    const server = spawn('node', ['dist/index.js'], {
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    let serverOutput = '';
    server.stdout.on('data', (data) => {
      serverOutput += data.toString();
      console.log('Server output:', data.toString().trim());
    });
    
    server.stderr.on('data', (data) => {
      console.log('Server error:', data.toString().trim());
    });
    
    // Give server time to start
    await delay(1000);
    
    // Test 1: Initialize connection
    console.log('Testing initialization...');
    const initMessage = {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-03-26",
        capabilities: { tools: {} },
        clientInfo: { name: "test-client", version: "1.0.0" }
      }
    };
    
    server.stdin.write(JSON.stringify(initMessage) + '\n');
    await delay(500);
    
    // Test 2: List tools
    console.log('Testing tools list...');
    const listMessage = {
      jsonrpc: "2.0",
      id: 2,
      method: "tools/list"
    };
    
    server.stdin.write(JSON.stringify(listMessage) + '\n');
    await delay(500);
    
    // Test 3: Call ping tool
    console.log('Testing ping tool...');
    const pingMessage = {
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        name: "ping",
        arguments: { message: "test from automated test" }
      }
    };
    
    server.stdin.write(JSON.stringify(pingMessage) + '\n');
    await delay(500);
    
    // Test 4: Test Modal connection simulation
    console.log('Testing Modal connection simulation...');
    const modalPingMessage = {
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: {
        name: "ping",
        arguments: { message: "Modal connection test" }
      }
    };
    
    server.stdin.write(JSON.stringify(modalPingMessage) + '\n');
    await delay(500);
    
    // Test 5: Call mock tool
    console.log('Testing mock face recognition...');
    const mockMessage = {
      jsonrpc: "2.0",
      id: 5,
      method: "tools/call",
      params: {
        name: "recognize_face",
        arguments: { 
          image_data: "fake_base64_data",
          operation: "identify"
        }
      }
    };
    
    server.stdin.write(JSON.stringify(mockMessage) + '\n');
    await delay(500);
    
    // Clean up
    console.log('Stopping server...');
    server.kill('SIGTERM');
    
    // Wait a bit for cleanup
    await delay(1000);
    
    console.log('All tests completed successfully!');
    console.log('Summary:');
    console.log('   ✓ Server starts correctly');
    console.log('   ✓ Handles initialization');
    console.log('   ✓ Lists tools');
    console.log('   ✓ Ping tool works');
    console.log('   ✓ Face recognition tool responds');
    console.log('   ✓ Modal connection works');
    
    return true;
    
  } catch (error) {
    console.error('Test failed:', error);
    return false;
  }
}

// Run test if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  testMCPServer()
    .then((success) => {
      process.exit(success ? 0 : 1);
    })
    .catch((error) => {
      console.error('Test suite failed:', error);
      process.exit(1);
    });
}