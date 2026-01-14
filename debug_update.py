
import os

file_path = r'c:\Users\Nityainc\OneDrive - Nitya Software Solutions Inc\Desktop\Automation_testing_pytest\logs\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_style = content.find('<style>')
end_style = content.find('</style>')
body_start = content.find('<body>')

print(f"Start Style: {start_style}")
print(f"End Style: {end_style}")
print(f"Body Start: {body_start}")

if start_style == -1:
    print("Could not find <style>")
if end_style == -1:
    print("Could not find </style>")
if body_start == -1:
    print("Could not find <body>")
