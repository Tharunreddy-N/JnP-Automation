# Test Log Viewer - 7 Day History Dashboard

## Overview
A comprehensive UI dashboard for viewing test execution logs with 7-day historical data. Shows pass/fail reports, runtime information, and allows downloading log files for each module.

## Features
- 📁 **Module Selection**: View BenchSale, Employer, and JobSeeker modules
- 📥 **Download Logs**: Download log files for each module with one click
- 🧪 **Test Case List**: View all test cases for each module
- 📊 **7-Day History**: See past 7 days of execution data for each test case
- ✅ **Pass/Fail Reports**: Visual indicators for test status
- ⏱️ **Runtime Data**: View execution time for each test run
- 📈 **Statistics Summary**: Quick overview of pass/fail/not-run counts

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   This will install Flask and Flask-CORS along with other dependencies.

2. **Create History Directory**:
   The system will automatically create `logs/history/` directory on first run.

## Usage

### Option 1: Start Complete System (Recommended)
Double-click `START_LOG_VIEWER.bat` - This will:
- Start the API server in the background
- Open the UI in your default browser
- Keep the server running until you press a key

### Option 2: Start Server Only
Double-click `START_LOG_VIEWER_SERVER_ONLY.bat` - This will:
- Start only the API server (useful for background service)
- You can manually open `log_viewer_ui.html` in your browser

### Option 3: Manual Start
1. Start the API server:
   ```bash
   python utils\log_history_api.py
   ```

2. Open `log_viewer_ui.html` in your browser

## How It Works

### Backend API (`utils/log_history_api.py`)
- Parses log files from `logs/` directory
- Extracts test execution data with dates and runtime
- Stores historical data in `logs/history/` as JSON files
- Provides REST API endpoints:
  - `GET /api/modules` - List all modules
  - `GET /api/modules/<module_id>/test-cases` - Get test cases for a module
  - `GET /api/modules/<module_id>/test-cases/<test_case>/history` - Get 7-day history
  - `GET /api/modules/<module_id>/download-log` - Download log file
  - `POST /api/modules/<module_id>/update` - Manually update historical data

### Frontend UI (`log_viewer_ui.html`)
- Modern, responsive web interface
- Left panel: Module selection and test case list
- Right panel: 7-day log history with statistics
- Auto-refreshes every 30 seconds
- Color-coded status indicators (green=pass, red=fail, gray=not run)

## Module Configuration

Modules are configured in `utils/log_history_api.py`:

```python
MODULES = {
    'benchsale': {
        'name': 'BenchSale',
        'log_file': 'logs/benchsale_admin.log',
        'test_files': [...]
    },
    'employer': {...},
    'jobseeker': {...}
}
```

## Data Storage

Historical data is stored in JSON format in `logs/history/`:
- `benchsale_history.json`
- `employer_history.json`
- `jobseeker_history.json`

Each file contains test case names as keys, with arrays of execution records:
```json
{
  "test_t1_01_home_page": [
    {
      "test_name": "test_t1_01_home_page",
      "status": "PASS",
      "date": "2026-01-19",
      "datetime": "2026-01-19T11:16:25",
      "running_time": "00:01:20.601"
    }
  ]
}
```

## Troubleshooting

### API Server Not Starting
- Check if port 5001 is available
- Ensure Flask is installed: `pip install flask flask-cors`
- Check Python path in batch files

### No Test Cases Showing
- Ensure log files exist in `logs/` directory
- Run tests first to generate log files
- Check API server is running and accessible

### Date Extraction Issues
- Log files should have "Start: YYYYMMDD HH:MM:SS" format
- If dates are incorrect, check log file format

### UI Not Loading
- Ensure API server is running on http://127.0.0.1:5001
- Check browser console for errors
- Verify CORS is enabled in API server

## API Endpoints

### Get Modules
```
GET http://127.0.0.1:5001/api/modules
```

### Get Test Cases
```
GET http://127.0.0.1:5001/api/modules/employer/test-cases
```

### Get 7-Day History
```
GET http://127.0.0.1:5001/api/modules/employer/test-cases/test_t1_01_home_page/history
```

### Download Log
```
GET http://127.0.0.1:5001/api/modules/employer/download-log
```

## Notes

- Historical data is automatically updated when you access test cases
- Only last 7 days of data is kept (older data is automatically removed)
- Log files are parsed on-demand to extract latest test results
- Test case names are extracted from both log files and test source files
