"""
Enhanced Test Logger - Robot Framework style logging
Provides clear, structured logging similar to Robot Framework
"""
import logging
import time
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, List


class TestLogger:
    """Enhanced logger with Robot Framework-style formatting"""
    
    def __init__(self, logger_name: str = 'benchsale_test'):
        self.logger = logging.getLogger(logger_name)
        self.test_stats = {
            'tests': [],
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None,
            'elapsed': 0
        }
        self.current_test = None
        self.keyword_stack = []
    
    def log_test_start(self, test_name: str, test_file: str = None):
        """Log test start with clear formatting"""
        self.current_test = {
            'name': test_name,
            'file': test_file,
            'start_time': time.time(),
            'status': 'RUNNING',
            'keywords': [],
            'messages': []
        }
        self.test_stats['total'] += 1
        
        self.logger.info("")
        self.logger.info("=" * 100)
        self.logger.info(f"TEST {test_name}")
        if test_file:
            self.logger.info(f"Full Name: {test_name}")
            self.logger.info(f"Source: {test_file}")
        start_time_str = datetime.now().strftime('%Y%m%d %H:%M:%S.%f')[:-3]
        self.logger.info(f"Start: {start_time_str}")
        self.logger.info("=" * 100)
    
    def log_test_end(self, test_name: str, status: str, message: str = None, elapsed: float = None):
        """Log test end with status and timing"""
        if self.current_test:
            end_time = time.time()
            start_time = self.current_test.get('start_time', end_time)
            elapsed_time = elapsed or (end_time - start_time)
            
            end_time_str = datetime.now().strftime('%Y%m%d %H:%M:%S.%f')[:-3]
            elapsed_str = self._format_elapsed(elapsed_time)
            
            self.logger.info("")
            self.logger.info(f"Full Name: {test_name}")
            self.logger.info(f"Start / End / Elapsed: {datetime.fromtimestamp(start_time).strftime('%Y%m%d %H:%M:%S.%f')[:-3]} / {end_time_str} / {elapsed_str}")
            
            status_upper = status.upper()
            self.logger.info(f"Status: {status_upper}")
            if message:
                self.logger.info(f"Message: {message}")
            
            # Update statistics
            self.current_test['status'] = status_upper
            self.current_test['elapsed'] = elapsed_time
            self.current_test['end_time'] = end_time
            
            if status_upper == 'PASS':
                self.test_stats['passed'] += 1
            elif status_upper == 'FAIL':
                self.test_stats['failed'] += 1
                if message:
                    self.current_test['error'] = message
            elif status_upper == 'SKIP':
                self.test_stats['skipped'] += 1
            
            self.test_stats['tests'].append(self.current_test.copy())
            self.current_test = None
    
    def log_keyword(self, keyword_name: str, args: List = None, elapsed: float = None, status: str = 'PASS'):
        """Log keyword execution with timing"""
        elapsed_str = self._format_elapsed(elapsed) if elapsed else "00:00:00.000"
        
        # Format args similar to Robot Framework
        if args:
            args_str = " " + ", ".join(str(a) for a in args)
        else:
            args_str = ""
        
        # Log in Robot Framework style: ELAPSEDKEYWORD KeywordName args
        self.logger.info(f"{elapsed_str}KEYWORD {keyword_name}{args_str}")
        
        if self.current_test:
            self.current_test['keywords'].append({
                'name': keyword_name,
                'args': args or [],
                'elapsed': elapsed or 0,
                'status': status
            })
    
    def log_keyword_start(self, keyword_name: str, args: List = None):
        """Start timing a keyword"""
        self.keyword_stack.append({
            'name': keyword_name,
            'args': args,
            'start_time': time.time()
        })
    
    def log_keyword_end(self, keyword_name: str, status: str = 'PASS', elapsed: float = None):
        """
        End timing a keyword.
        
        - If `elapsed` is provided, it will be used directly.
        - Otherwise elapsed is computed from the last `log_keyword_start`.
        """
        if self.keyword_stack:
            kw = self.keyword_stack.pop()
            elapsed_time = elapsed if elapsed is not None else (time.time() - kw['start_time'])
            self.log_keyword(kw['name'], kw.get('args'), elapsed_time, status)
        else:
            # Fallback: allow logging even if start wasn't recorded
            elapsed_time = elapsed if elapsed is not None else 0
            self.log_keyword(keyword_name, [], elapsed_time, status)
    
    def log_message(self, level: str, message: str, timestamp: bool = True):
        """Log a message with level"""
        if timestamp:
            time_str = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            # Robot Framework style: TIMESTAMP\tLEVEL\tMESSAGE
            self.logger.log(getattr(logging, level.upper(), logging.INFO), f"{time_str}\t{level.upper()}\t{message}")
        else:
            self.logger.log(getattr(logging, level.upper(), logging.INFO), message)
    
    def log_info(self, message: str):
        """Log info message"""
        self.log_message('INFO', message)
    
    def log_error(self, message: str):
        """Log error message"""
        self.log_message('ERROR', message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.log_message('WARNING', message)
    
    def log_suite_start(self, suite_name: str, source: str = None):
        """Log test suite start"""
        self.test_stats['start_time'] = time.time()
        start_time_str = datetime.now().strftime('%Y%m%d %H:%M:%S.%f')[:-3]
        
        self.logger.info("=" * 100)
        self.logger.info(f"SUITE {suite_name}")
        self.logger.info(f"Full Name: {suite_name}")
        if source:
            self.logger.info(f"Source: {source}")
        self.logger.info(f"Start: {start_time_str}")
        self.logger.info("=" * 100)
    
    def log_suite_end(self, suite_name: str):
        """Log test suite end with statistics"""
        end_time = time.time()
        start_time = self.test_stats.get('start_time')
        # Some runs load logging hooks after pytest_sessionstart; be defensive.
        if not start_time:
            start_time = end_time
        elapsed = end_time - start_time
        
        end_time_str = datetime.now().strftime('%Y%m%d %H:%M:%S.%f')[:-3]
        elapsed_str = self._format_elapsed(elapsed)
        
        self.logger.info("")
        self.logger.info("=" * 100)
        self.logger.info(f"Full Name: {suite_name}")
        self.logger.info(f"Start / End / Elapsed: {datetime.fromtimestamp(start_time).strftime('%Y%m%d %H:%M:%S.%f')[:-3]} / {end_time_str} / {elapsed_str}")
        self.logger.info(f"Status: {self.test_stats['total']} tests total, {self.test_stats['passed']} passed, {self.test_stats['failed']} failed, {self.test_stats['skipped']} skipped")
        self.logger.info("=" * 100)
        
        # Log test statistics table
        self.log_test_statistics()
    
    def log_test_statistics(self):
        """Log test statistics in table format"""
        self.logger.info("")
        self.logger.info("Test Statistics")
        self.logger.info("-" * 100)
        
        # Header
        header = f"{'Test':<60} {'Total':<8} {'Pass':<8} {'Fail':<8} {'Skip':<8} {'Elapsed':<15}"
        self.logger.info(header)
        self.logger.info("-" * 100)
        
        # Individual test stats
        for test in self.test_stats['tests']:
            elapsed_str = self._format_elapsed(test.get('elapsed', 0))
            status = test.get('status', 'UNKNOWN')
            pass_count = 1 if status == 'PASS' else 0
            fail_count = 1 if status == 'FAIL' else 0
            skip_count = 1 if status == 'SKIP' else 0
            
            row = f"{test['name']:<60} {1:<8} {pass_count:<8} {fail_count:<8} {skip_count:<8} {elapsed_str:<15}"
            self.logger.info(row)
        
        # Summary
        total_elapsed = sum(t.get('elapsed', 0) for t in self.test_stats['tests'])
        summary_elapsed = self._format_elapsed(total_elapsed)
        summary = f"{'All Tests':<60} {self.test_stats['total']:<8} {self.test_stats['passed']:<8} {self.test_stats['failed']:<8} {self.test_stats['skipped']:<8} {summary_elapsed:<15}"
        self.logger.info("-" * 100)
        self.logger.info(summary)
        self.logger.info("-" * 100)
    
    def _format_elapsed(self, seconds: float) -> str:
        """Format elapsed time as HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def get_statistics(self) -> Dict:
        """Get test statistics"""
        return self.test_stats.copy()


# Global test logger instance
_test_logger = None

def get_test_logger() -> TestLogger:
    """Get or create global test logger instance"""
    global _test_logger
    if _test_logger is None:
        _test_logger = TestLogger()
    return _test_logger


def log_keyword(keyword_name: str = None):
    """Decorator to log keyword execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_test_logger()
            kw_name = keyword_name or func.__name__
            logger.log_keyword_start(kw_name, list(args))
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log_keyword_end(kw_name, 'PASS')
                return result
            except Exception as e:
                logger.log_keyword_end(kw_name, 'FAIL')
                logger.log_error(f"{kw_name} failed: {str(e)}")
                raise
        return wrapper
    return decorator

