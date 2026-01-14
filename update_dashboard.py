
import os

file_path = r'c:\Users\Nityainc\OneDrive - Nitya Software Solutions Inc\Desktop\Automation_testing_pytest\logs\index.html'

new_css = """    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

        :root {
            --primary: #F97316; /* Orange 500 */
            --secondary: #F59E0B; /* Amber 500 */
            --accent: #EA580C; /* Orange 600 */
            --dark: #1C1917; /* Stone 900 */
            --light: #FFF7ED; /* Orange 50 */
            --card-bg: rgba(255, 255, 255, 0.65);
            --glass-border: rgba(255, 255, 255, 0.8);
            --text-primary: #1C1917;
            --text-secondary: #78350F;
            --success: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
        }
        
        body {
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #FFEDD5 0%, #FFF7ED 100%);
            min-height: 100vh;
            padding: 15px;
            position: relative;
            overflow-x: hidden;
            color: var(--text-primary);
        }

        /* Animated Bubble Background */
        .background-bubbles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
            pointer-events: none;
        }

        .bubble {
            position: absolute;
            border-radius: 50%;
            background: linear-gradient(135deg, rgba(249, 115, 22, 0.15), rgba(245, 158, 11, 0.15));
            filter: blur(40px);
            animation: floatBubble 20s infinite ease-in-out;
            opacity: 0.6;
        }

        .bubble:nth-child(1) { top: -10%; left: -10%; width: 600px; height: 600px; background: radial-gradient(circle, rgba(249, 115, 22, 0.2) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 25s; }
        .bubble:nth-child(2) { bottom: -10%; right: -10%; width: 500px; height: 500px; background: radial-gradient(circle, rgba(245, 158, 11, 0.2) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 30s; animation-delay: -5s; }
        .bubble:nth-child(3) { top: 40%; left: 40%; width: 300px; height: 300px; background: radial-gradient(circle, rgba(234, 88, 12, 0.15) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 20s; animation-delay: -10s; }
        .bubble:nth-child(4) { bottom: 20%; left: 10%; width: 200px; height: 200px; background: radial-gradient(circle, rgba(251, 146, 60, 0.2) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 18s; animation-delay: -8s; }

        @keyframes floatBubble {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(30px, -50px) scale(1.1); }
            66% { transform: translate(-20px, 20px) scale(0.95); }
        }
        
        .container {
            max-width: 1400px;
            width: calc(100% - 40px);
            margin: 0 auto;
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
            padding-top: 20px;
        }
        
        .back-btn-container {
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
        }
        
        @media (max-width: 1400px) {
            .container { width: calc(100% - 30px); padding-top: 15px; }
        }
        @media (max-width: 768px) {
            .container { width: calc(100% - 20px); padding-top: 15px; }
            .back-btn-container { top: 15px; left: 15px; }
        }
        
        .header {
            background: var(--card-bg);
            backdrop-filter: blur(25px) saturate(150%);
            -webkit-backdrop-filter: blur(25px) saturate(150%);
            border-radius: 24px;
            padding: 25px 35px;
            box-shadow: 
                0 20px 60px -10px rgba(249, 115, 22, 0.15),
                0 8px 24px -5px rgba(0, 0, 0, 0.05),
                inset 0 0 0 1px rgba(255, 255, 255, 0.6);
            border: 1px solid var(--glass-border);
            position: relative;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 25px;
        }
        
        .header-content {
            flex: 1;
            min-width: 0;
            padding-right: 15px;
        }
        
        .refresh-btn-wrapper {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 10px;
            flex-shrink: 0;
        }
        
        .header h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.2em;
            font-weight: 700;
            margin-bottom: 6px;
            background: linear-gradient(135deg, #9a3412 0%, #c2410c 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.2;
        }
        
        .header .subtitle {
            font-family: 'Outfit', sans-serif;
            color: var(--text-secondary);
            font-size: 1em;
            line-height: 1.4;
        }
        
        .header .last-updated {
            color: #b45309; /* Amber 700 */
            font-size: 0.85em;
            margin-top: 4px;
            opacity: 0.8;
        }
        
        /* Buttons */
        .back-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(10px);
            color: var(--accent);
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 4px 15px rgba(249, 115, 22, 0.15);
            font-family: 'Space Grotesk', sans-serif;
            transition: all 0.3s ease;
        }
        
        .back-btn:hover {
            transform: translateY(-2px);
            background: white;
            color: var(--primary);
            box-shadow: 0 8px 25px rgba(249, 115, 22, 0.25);
        }
        
        .back-btn svg { width: 20px; height: 20px; stroke: currentColor; }
        
        .refresh-btn {
            display: inline-block;
            padding: 10px 24px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            transition: all 0.3s ease;
            cursor: pointer;
            font-family: 'Space Grotesk', sans-serif;
            border: none;
            box-shadow: 0 4px 15px rgba(249, 115, 22, 0.3);
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(249, 115, 22, 0.4);
            filter: brightness(1.1);
        }
        
        .auto-refresh-indicator {
            display: inline-block;
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.5);
            color: var(--secondary);
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        
        .stat-card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px -5px rgba(249, 115, 22, 0.1);
            border: 1px solid var(--glass-border);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px -5px rgba(249, 115, 22, 0.2);
            background: rgba(255, 255, 255, 0.8);
        }
        
        .stat-card.total { border-bottom: 4px solid var(--primary); }
        .stat-card.passed { border-bottom: 4px solid var(--success); }
        .stat-card.failed { border-bottom: 4px solid var(--danger); }
        .stat-card.skipped { border-bottom: 4px solid var(--warning); }
        
        .stat-card .number {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 3em;
            font-weight: 700;
            margin-bottom: 5px;
            line-height: 1;
        }
        
        .stat-card.total .number { color: var(--primary); }
        .stat-card.passed .number { color: var(--success); }
        .stat-card.failed .number { color: var(--danger); }
        .stat-card.skipped .number { color: var(--warning); }
        
        .stat-card .label {
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 12px;
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(15px);
            padding: 8px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.6);
            flex-wrap: wrap;
        }
        
        .tab {
            padding: 10px 20px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 0.95em;
            font-weight: 600;
            color: var(--text-secondary);
            border-radius: 12px;
            transition: all 0.3s ease;
            font-family: 'Outfit', sans-serif;
        }
        
        .tab:hover {
            background: rgba(255, 255, 255, 0.6);
            color: var(--primary);
        }
        
        .tab.active {
            background: white;
            color: var(--primary);
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15);
            font-weight: 700;
        }
        
        /* Test List */
        .test-section {
            display: none;
            background: var(--card-bg);
            backdrop-filter: blur(25px);
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 15px 50px -10px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--glass-border);
            min-height: 500px;
            max-height: calc(100vh - 300px);
            overflow-y: auto;
        }
        
        .test-section.active { display: block; }
        
        .test-section h2 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.5em;
            color: var(--dark);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        
        .test-list { display: grid; gap: 12px; }
        
        .test-item {
            background: rgba(255, 255, 255, 0.7);
            border-radius: 16px;
            padding: 16px 20px;
            border: 1px solid rgba(255, 255, 255, 0.8);
            transition: all 0.2s ease;
            border-left: 5px solid transparent;
        }
        
        .test-item:hover {
            transform: translateX(5px);
            background: white;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
        }
        
        .test-item.pass { border-left-color: var(--success); }
        .test-item.fail { border-left-color: var(--danger); }
        .test-item.skip { border-left-color: var(--warning); }
        .test-item.not-run { border-left-color: #CBD5E1; opacity: 0.8; }
        
        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            margin-bottom: 5px;
        }
        
        .test-name {
            font-weight: 600;
            font-size: 1.05em;
            color: var(--text-primary);
        }
        
        .test-badge {
            padding: 5px 12px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.75em;
            text-transform: uppercase;
        }
        
        .test-badge.pass { background: rgba(16, 185, 129, 0.15); color: var(--success); }
        .test-badge.fail { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
        .test-badge.skip { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
        .test-badge.not-run { background: #E2E8F0; color: #64748B; }
        
        .test-source { font-size: 0.85em; color: var(--text-secondary); opacity: 0.8; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(249, 115, 22, 0.3); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(249, 115, 22, 0.5); }
        
        /* Screenshots */
        .screenshots { margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.05); }
        .screenshot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-top: 10px; }
        .screenshot-item img { width: 100%; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .screenshot-item img:hover { transform: scale(1.05); box-shadow: 0 8px 20px rgba(0,0,0,0.15); }
        
        /* Log Links */
        .log-link {
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.8);
            color: var(--accent);
            text-decoration: none;
            border-radius: 8px;
            font-size: 0.9em;
            font-weight: 600;
            border: 1px solid rgba(249, 115, 22, 0.2);
            transition: all 0.2s;
        }
        .log-link:hover { background: var(--accent); color: white; transform: translateY(-2px); }

        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 15px; }
            .header { padding: 20px; }
            .header h1 { font-size: 1.8em; }
        }
        @media (max-width: 480px) {
            .stats-grid { grid-template-columns: 1fr; }
            .tabs { flex-direction: column; }
        }
    </style>"""

bubbles_html = """    <div class="background-bubbles">
        <div class="bubble"></div>
        <div class="bubble"></div>
        <div class="bubble"></div>
        <div class="bubble"></div>
    </div>"""

# Read existing content
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Styles
start_style = content.find('<style>')
end_style = content.find('</style>')
if start_style != -1 and end_style != -1:
    pre_style = content[:start_style]
    post_style = content[end_style + 8:] 
    content = pre_style + new_css + post_style
else:
    print("ERROR: Could not find <style> tags")

# Inject Bubbles after <body>
body_tag_index = content.find('<body>')
if body_tag_index != -1:
    # Check if bubbles already exist to avoid duplication
    if 'class="background-bubbles"' not in content:
        pre_body = content[:body_tag_index + 6]
        post_body = content[body_tag_index + 6:]
        content = pre_body + "\n" + bubbles_html + post_body
    else:
        print("Bubbles already exist")
else:
    print("ERROR: Could not find <body> tag")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully wrote to file.")
print("--- First 500 chars of updated file ---")
print(content[:500])
