"""
HTML Log Viewer Generator
Creates a simple redirect page to the new 7-day history viewer (no verbose log data)
"""
import os
from datetime import datetime
from pathlib import Path
from html import escape


def generate_html_log_viewer(log_file_path, output_html_path=None):
    """Generate a simple redirect page to the new 7-day history viewer (no verbose log data)."""
    if output_html_path is None:
        log_dir = os.path.dirname(log_file_path)
        log_filename = os.path.basename(log_file_path)
        output_html_path = os.path.join(log_dir, log_filename.replace('.log', '.html'))
    
    # Determine module ID from log file name
    log_basename = os.path.basename(log_file_path).lower()
    module_id = None
    if 'benchsale_admin' in log_basename:
        module_id = 'benchsale_admin'
    elif 'benchsale_recruiter' in log_basename:
        module_id = 'benchsale_recruiter'
    elif 'benchsale_test' in log_basename:
        module_id = 'benchsale_test'
    elif 'employer' in log_basename:
        module_id = 'employer'
    elif 'jobseeker' in log_basename:
        module_id = 'jobseeker'
    
    # Create simple redirect page - no verbose log data, just redirect to new clean viewer
    log_basename_display = escape(os.path.basename(log_file_path))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Simple redirect page - no verbose data
    if module_id:
        redirect_url = f"../log_viewer_ui.html?module={module_id}&hideModules=true"
    else:
        redirect_url = "../log_viewer_ui.html"
    
    html_template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="refresh" content="0; url=__REDIRECT_URL__" />
  <title>Redirecting to Log Viewer...</title>
  <style>
    * { box-sizing: border-box; }
    html, body { 
      height: 100%; 
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
    .redirect-container {
      text-align: center;
      padding: 40px;
    }
    .spinner {
      border: 4px solid rgba(255,255,255,0.3);
      border-top: 4px solid white;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
      margin: 0 auto 20px;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    h1 {
      margin: 0 0 10px 0;
      font-size: 24px;
    }
    p {
      margin: 0;
      opacity: 0.9;
      font-size: 16px;
    }
    a {
      color: white;
      text-decoration: underline;
      margin-top: 20px;
      display: inline-block;
    }
  </style>
  <script>
    // Immediate redirect
    window.location.href = '__REDIRECT_URL__';
  </script>
</head>
<body>
  <div class="redirect-container">
    <div class="spinner"></div>
    <h1>Redirecting to Log Viewer...</h1>
    <p>You will be redirected to the 7-day history viewer.</p>
    <a href="__REDIRECT_URL__">Click here if you are not redirected</a>
  </div>
</body>
</html>
"""
    
    html_content = (
        html_template
        .replace("__REDIRECT_URL__", redirect_url)
    )
    
    # Write HTML file
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_html_path


def generate_all_log_viewers():
    """Generate HTML redirect pages for all log files"""
    log_dir = Path(__file__).parent.parent / 'logs'
    html_files = []
    
    if log_dir.exists():
        # Prioritize main log file (benchsale_test.log)
        main_log = log_dir / 'benchsale_test.log'
        if main_log.exists():
            html_file = generate_html_log_viewer(str(main_log))
            html_files.append(html_file)
            print(f"Generated redirect page: {html_file}")
        
        # Then process other log files
        for log_file in sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True):
            if log_file.name != 'benchsale_test.log':
                html_file = generate_html_log_viewer(str(log_file))
                html_files.append(html_file)
                print(f"Generated redirect page: {html_file}")
    
    return html_files


if __name__ == '__main__':
    # Generate redirect pages for all logs
    generate_all_log_viewers()
