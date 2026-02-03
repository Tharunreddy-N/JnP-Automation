#!/usr/bin/env python
"""Verify sample jobs from DB and Solr to check sync"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.connections import connections
import mysql.connector
import pysolr

# Get credentials
creds = connections()
if not creds:
    print("ERROR: Failed to get credentials")
    exit(1)

mysql_cred = creds.get('mysql_cred')
solr_cred = creds.get('solr_cred')

if not mysql_cred or not solr_cred:
    print("ERROR: Credentials not found")
    exit(1)

# Connect to DB
conn = mysql.connector.connect(
    host=mysql_cred['host'],
    user=mysql_cred['user'],
    password=mysql_cred['password'],
    database="jobsnprofiles_2022"
)
cursor = conn.cursor(dictionary=True)

# Connect to Solr - get URL from credentials
solr_url = solr_cred.get('url') or solr_cred.get('solr_url') or f"http://{solr_cred.get('host', 'localhost')}:{solr_cred.get('port', 8983)}/solr/{solr_cred.get('core', 'jobs')}"
solr_instance = pysolr.Solr(solr_url, timeout=10)

# Sample job IDs from failures
sample_job_ids = [6028929, 6024767, 6023661, 6023733, 6023233, 23400]

print("=" * 100)
print("VERIFYING SAMPLE JOBS - DB vs SOLR")
print("=" * 100)

for job_id in sample_job_ids:
    print(f"\n{'='*100}")
    print(f"Job ID: {job_id}")
    print(f"{'='*100}")
    
    # Get from DB
    query = "SELECT id, title, is_remote, company_name FROM jobsnprofiles_2022.jnp_jobs WHERE id = %s"
    cursor.execute(query, (job_id,))
    db_result = cursor.fetchone()
    
    if not db_result:
        print(f"  DB: Job not found in database")
        continue
    
    print(f"\nDB Data:")
    print(f"  ID: {db_result['id']}")
    print(f"  Title: {db_result['title']}")
    print(f"  is_remote: {db_result['is_remote']} ({'Not Remote' if db_result['is_remote'] == 0 else 'Remote' if db_result['is_remote'] == 1 else 'Hybrid' if db_result['is_remote'] == 2 else 'Unknown'})")
    print(f"  Company: {db_result['company_name']}")
    
    # Get from Solr
    try:
        solr_results = solr_instance.search(f"id:{job_id}", rows=1)
        if len(solr_results) > 0:
            solr_doc = solr_results.docs[0]
            print(f"\nSolr Data:")
            print(f"  ID: {solr_doc.get('id')}")
            print(f"  Title: {solr_doc.get('title', 'N/A')}")
            
            # Check remote field
            solr_remote = solr_doc.get('remote')
            print(f"  remote field: {solr_remote} ({type(solr_remote).__name__})")
            if solr_remote is not None:
                if isinstance(solr_remote, (int, float)):
                    remote_val = int(solr_remote)
                    remote_str = 'Not Remote' if remote_val == 0 else 'Remote' if remote_val == 1 else 'Hybrid' if remote_val == 2 else 'Unknown'
                    print(f"    -> Interpreted as: {remote_str}")
                elif isinstance(solr_remote, str):
                    remote_str = 'Not Remote' if solr_remote == '0' else 'Remote' if solr_remote == '1' else 'Hybrid' if solr_remote == '2' else 'Unknown'
                    print(f"    -> Interpreted as: {remote_str}")
            
            # Check workmode field
            solr_workmode = solr_doc.get('workmode')
            print(f"  workmode field: {solr_workmode} ({type(solr_workmode).__name__})")
            if solr_workmode is not None:
                if isinstance(solr_workmode, bool):
                    print(f"    -> Interpreted as: {'Remote' if solr_workmode else 'Not Remote'}")
                elif isinstance(solr_workmode, str):
                    print(f"    -> Interpreted as: {solr_workmode}")
            
            print(f"  Company: {solr_doc.get('company_name', 'N/A')}")
            
            # Compare
            print(f"\nComparison:")
            db_remote = db_result['is_remote']
            if solr_remote is not None:
                if isinstance(solr_remote, (int, float)):
                    solr_remote_val = int(solr_remote)
                elif isinstance(solr_remote, str):
                    solr_remote_val = int(solr_remote) if solr_remote.isdigit() else None
                else:
                    solr_remote_val = None
                
                if solr_remote_val is not None:
                    if db_remote == solr_remote_val:
                        print(f"  ✅ MATCH: DB={db_remote}, Solr remote={solr_remote_val}")
                    else:
                        print(f"  ❌ MISMATCH: DB={db_remote}, Solr remote={solr_remote_val}")
                else:
                    print(f"  ⚠️  Solr remote field value cannot be interpreted")
            else:
                print(f"  ⚠️  Solr remote field is missing")
        else:
            print(f"\nSolr: Job not found in Solr")
    except Exception as e:
        print(f"\nSolr Error: {e}")

cursor.close()
conn.close()

print(f"\n{'='*100}")
print("VERIFICATION COMPLETE")
print(f"{'='*100}")
