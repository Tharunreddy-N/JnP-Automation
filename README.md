# BenchSale Automation Testing with pytest

This project contains pytest-based automation tests for BenchSale functionality, converted from Robot Framework test cases.

## Project Structure

```
Automation_testing_pytest/
├── conftest.py                 # Pytest configuration and fixtures
├── pytest.ini                  # Pytest configuration file
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── tests/                      # Test files directory
│   ├── __init__.py
│   ├── test_benchsale_admin.py # Admin test cases (T1.01-T1.13)
│   └── test_benchsale_recruiter.py  # Recruiter test cases (T2.01-T2.02)
└── reports/                    # Test reports (generated)
```

## Setup Instructions

1. **Install Python** (3.8 or higher)

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Update configuration:**
   - Edit `conftest.py` to update credentials and URLs if needed
   - Update file paths for test data (e.g., resume files)

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test case:
```bash
pytest -m T1.01
```

### Run by marker:
```bash
pytest -m admin          # Run all admin tests
pytest -m recruiter      # Run all recruiter tests
```

### Run with HTML report:
```bash
# HTML Report (automatically generated)
pytest --html=reports/report.html --self-contained-html

# JSON Report (automatically generated)
pytest --json-report --json-report-file=reports/report.json

# View logs
# Logs are automatically generated in logs/ directory
# Each test run creates a timestamped log file: logs/benchsale_test_YYYYMMDD_HHMMSS.log
```

### Run in parallel:
```bash
pytest -n auto
```

## Test Cases

### Admin Test Cases (T1.xx)

- **T1.01** - Verification of 'Favourite' button under Companies in BenchSale
- **T1.02** - Verification of adding recruiter in BenchSale
- **T1.03** - Verification of adding Candidates in BenchSale
- **T1.04** - Verification of allocating candidate under recruiter
- **T1.05** - Verification of Sources
- **T1.08** - Verification of inactivating and activating recruiter
- **T1.09** - Verification of inactivating and activating candidate
- **T1.10** - Deleting a recruiter
- **T1.11** - Deleting a candidate
- **T1.12** - Allocate candidate under recruiter and verify in Recruiter profile
- **T1.13** - Verification of candidates in submission Job flow

### Recruiter Test Cases (T2.xx)

- **T2.01** - Dashboard verification (Recruiter active/inactive)
- **T2.02** - Verification of inactivating and activating candidates

### API Test Cases (T3.xx)

- **T3.01** - API Monitoring and Runtime Measurement Test

## Features

- **Runtime Measurement**: Each test measures execution time
- **Network Connectivity Check**: Verifies network before running tests
- **Page Load Time Measurement**: Tracks page load performance
- **Error Handling**: Robust error handling with retries
- **HTML Reports**: Generates detailed HTML test reports
- **Comprehensive Logging**: Robot Framework-like detailed logging
  - Timestamped log files in `logs/` directory
  - Console output with timestamps
  - Test execution summary in `reports/test_summary.txt`
  - JSON report in `reports/report.json`
  - HTML report in `reports/report.html`

## Configuration

### Credentials (in conftest.py):
- BenchSale Admin credentials
- BenchSale Recruiter credentials
- CRM Admin credentials

### URLs:
- Base URL: https://jobsnprofiles.com/
- BenchSale URL: https://bs.jobsnprofiles.com/
- CRM Admin URL: https://admin.jobsnprofiles.com/

## Logging and Reports

The test suite generates comprehensive logs and reports similar to Robot Framework:

### Log Files
- **Location**: `logs/` directory
- **Format**: `benchsale_test_YYYYMMDD_HHMMSS.log`
- **Content**: 
  - Detailed test execution logs with timestamps
  - Step-by-step test actions
  - Error messages and stack traces
  - Runtime measurements
  - Network connectivity checks

### Report Files
- **HTML Report**: `reports/report.html` - Visual test results
- **JSON Report**: `reports/report.json` - Machine-readable results
- **Summary**: `reports/test_summary.txt` - Text summary with runtime stats

### Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General test execution information
- **WARNING**: Non-critical issues
- **ERROR**: Test failures and errors

### Example Log Output
```
2024-01-15 10:30:45 [    INFO] conftest.py:89 - conftest: ⏱️ Started runtime measurement for: T1.01_Favourite_Button_Test
2024-01-15 10:30:45 [    INFO] conftest.py:120 - conftest: 🌐 Checking network connectivity to: https://www.google.com
2024-01-15 10:30:46 [    INFO] conftest.py:123 - conftest: 🌐 Network connectivity check: ✅ Connected (Status: 200)
2024-01-15 10:30:50 [    INFO] conftest.py:188 - conftest: ✅ Logged in to BenchSale Admin successfully
```

## Notes

- Tests use Chrome browser (configured in conftest.py)
- ChromeDriver is automatically managed by webdriver-manager
- Tests include runtime monitoring and performance measurement
- All tests follow the same structure as Robot Framework tests for consistency
- Log files are automatically created in `logs/` directory
- Reports are generated in `reports/` directory

## Troubleshooting

1. **ChromeDriver issues**: webdriver-manager should handle this automatically
2. **Timeout errors**: Increase timeout values in conftest.py if needed
3. **Element not found**: Check if selectors match current UI
4. **Network issues**: Verify network connectivity and URLs

## Contributing

When adding new test cases:
1. Follow the existing test structure
2. Use appropriate markers (T1.xx, T2.xx, etc.)
3. Include runtime measurement
4. Add proper documentation
5. Handle errors gracefully

