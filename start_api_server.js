// Simple Node.js script to start Python API server
// This can be called from browser if Node.js is available
const { spawn } = require('child_process');
const path = require('path');

const scriptPath = path.join(__dirname, 'utils', 'log_history_api.py');
const pythonProcess = spawn('python', [scriptPath], {
    detached: true,
    stdio: 'ignore'
});

pythonProcess.unref();
console.log('API server started');
