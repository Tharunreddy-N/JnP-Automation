# Log Viewer API Server - 24/7 Setup Guide

## Overview
This setup ensures the Log Viewer API Server runs continuously 24/7 with automatic restart on failure.

## Quick Start Options

### Option 1: Manual Start (24/7 Mode)
**Double-click:** `START_API_NOW.bat`
- Starts server immediately with auto-restart
- Runs in background window
- Auto-restarts if server crashes
- Stops when you close the window

### Option 2: Install as Windows Service (Auto-start on Boot)
1. **Right-click** `INSTALL_API_SERVICE.bat`
2. Select **"Run as administrator"**
3. The service will:
   - Start automatically when Windows boots
   - Restart automatically if it crashes
   - Run continuously in background

### Option 3: Advanced 24/7 Script
**Double-click:** `START_LOG_VIEWER_API_24x7.bat`
- Full control with console output
- Shows restart messages
- Press Ctrl+C to stop

## Files Created

1. **START_LOG_VIEWER_API_24x7.bat**
   - Main 24/7 script with auto-restart loop
   - Monitors server and restarts on crash

2. **START_API_NOW.bat**
   - Quick start script
   - Launches 24/7 mode in background

3. **INSTALL_API_SERVICE.bat**
   - Installs as Windows Scheduled Task
   - Auto-starts on system boot
   - Requires Administrator privileges

4. **UNINSTALL_API_SERVICE.bat**
   - Removes the Windows service
   - Requires Administrator privileges

## Service Management Commands

### Start Service (if installed)
```cmd
schtasks /Run /TN "LogViewerAPIServer"
```

### Stop Service
```cmd
schtasks /End /TN "LogViewerAPIServer"
```

### Check Service Status
```cmd
schtasks /Query /TN "LogViewerAPIServer"
```

### Uninstall Service
```cmd
schtasks /Delete /TN "LogViewerAPIServer" /F
```

Or simply run: `UNINSTALL_API_SERVICE.bat` (as Administrator)

## Features

✅ **Auto-Restart**: Server automatically restarts if it crashes  
✅ **Port Check**: Detects if port 5001 is already in use  
✅ **Error Handling**: Graceful error handling and logging  
✅ **24/7 Operation**: Runs continuously without manual intervention  
✅ **Boot Start**: Can be configured to start on Windows boot  

## Server URL
- **Health Check**: http://127.0.0.1:5001/api/health
- **API Base**: http://127.0.0.1:5001/api

## Troubleshooting

### Server Not Starting
1. Check if port 5001 is already in use:
   ```cmd
   netstat -an | findstr ":5001"
   ```

2. Kill existing process:
   ```cmd
   taskkill /F /PID <process_id>
   ```

### Service Not Starting on Boot
1. Check if service is installed:
   ```cmd
   schtasks /Query /TN "LogViewerAPIServer"
   ```

2. Reinstall the service:
   - Run `INSTALL_API_SERVICE.bat` as Administrator

### Server Keeps Restarting
- Check the console output for error messages
- Verify Python and dependencies are installed correctly
- Check log files in the project directory

## Notes

- The server runs on port **5001** by default
- Server logs are displayed in the console window
- For production use, consider using a proper WSGI server (gunicorn, waitress)
- The current setup uses Flask's development server (suitable for local use)
