"""
Check work mode failures to understand false positives
"""
import json
import mysql.connector
import pysolr
from utils.connections import connections

def check_workmode_failures():
    """Check work mode failures from the report"""
    creds = connections()
    mysql_cred = creds.get('mysql_cred')
    solr_cred = creds.get('solr_cred')
    
    conn = mysql.connector.connect(
        host=mysql_cred['host'],
        user=mysql_cred['user'],
        password=mysql_cred['password'],
        database="jobsnprofiles_2022"
    )
    cursor = conn.cursor(dictionary=True)
    
    solr_url = "https://solr.jobsnprofiles.com/solr/jnp_jobs_v6/"
    solr = pysolr.Solr(
        solr_url,
        auth=(solr_cred['user'], solr_cred['password']),
        always_commit=False
    )
    
    # Get work mode failures from report
    with open('reports/db_solr_sync_failures.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    workmode_failures = [f for f in report['failures'] if 'Work Mode' in f.get('msg', '')]
    
    print(f"Checking {len(workmode_failures)} work mode failures...\n")
    
    for idx, failure in enumerate(workmode_failures[:10], 1):
        job_id = failure['id']
        title = failure.get('db_title', failure.get('title', 'N/A'))
        print(f"{'='*80}")
        print(f"{idx}. Job ID: {job_id} - {title}")
        print(f"{'='*80}")
        
        # Get DB data
        cursor.execute("SELECT id, is_remote FROM jobsnprofiles_2022.jnp_jobs WHERE id = %s", (job_id,))
        db_data = cursor.fetchone()
        
        # Get Solr data
        solr_results = solr.search(f"id:{job_id}", rows=1)
        if not solr_results:
            print("NOT FOUND IN SOLR")
            continue
        
        solr_data = solr_results.docs[0]
        
        db_is_remote = db_data['is_remote']
        solr_remote = solr_data.get('remote')
        solr_workmode = solr_data.get('workmode')
        
        print(f"\nRAW VALUES:")
        print(f"  DB is_remote: {db_is_remote} (Type: {type(db_is_remote)})")
        print(f"  Solr remote: {solr_remote} (Type: {type(solr_remote)})")
        print(f"  Solr workmode: {solr_workmode} (Type: {type(solr_workmode)})")
        
        # Normalize like test does
        db_val_normalized = None
        if db_is_remote is not None and db_is_remote != '':
            db_val_str = str(db_is_remote).strip()
            if db_val_str in ['0', 'false', 'False', 'FALSE', 'not remote', 'onsite', 'on-site']:
                db_val_normalized = '0'
            elif db_val_str in ['1', 'true', 'True', 'TRUE', 'remote']:
                db_val_normalized = '1'
            elif db_val_str in ['2', 'hybrid', 'Hybrid', 'HYBRID']:
                db_val_normalized = '2'
        
        remote_normalized = None
        if solr_remote is not None:
            if isinstance(solr_remote, (int, float)):
                remote_str = str(int(solr_remote))
                if remote_str in ['0', '1', '2']:
                    remote_normalized = remote_str
            elif isinstance(solr_remote, str):
                remote_lower = str(solr_remote).strip().lower()
                if remote_lower in ['0', '1', '2']:
                    remote_normalized = remote_lower
        
        workmode_normalized = None
        if solr_workmode is not None:
            if isinstance(solr_workmode, (int, float)):
                workmode_str = str(int(solr_workmode))
                if workmode_str in ['0', '1', '2']:
                    workmode_normalized = workmode_str
            elif isinstance(solr_workmode, bool):
                workmode_normalized = '1' if solr_workmode else '0'
            elif isinstance(solr_workmode, str):
                workmode_lower = solr_workmode.lower().strip()
                if workmode_lower in ['0', '1', '2']:
                    workmode_normalized = workmode_lower
                elif workmode_lower in ['true', 'remote']:
                    workmode_normalized = '1'
                elif workmode_lower in ['false', 'not remote', 'onsite', 'on-site']:
                    workmode_normalized = '0'
                elif workmode_lower in ['hybrid']:
                    workmode_normalized = '2'
        
        print(f"\nNORMALIZED VALUES:")
        print(f"  DB: {db_val_normalized}")
        print(f"  Solr remote: {remote_normalized}")
        print(f"  Solr workmode: {workmode_normalized}")
        
        # Test logic: choose which to use
        solr_val_normalized = None
        solr_field_used = None
        
        if db_val_normalized is not None:
            # If workmode matches DB, use it (it's often more reliable)
            if workmode_normalized == db_val_normalized:
                solr_val_normalized = workmode_normalized
                solr_field_used = 'workmode'
                print(f"  [LOGIC] Using workmode (matches DB)")
            # Otherwise, use remote field (or workmode if remote not available)
            elif remote_normalized is not None:
                solr_val_normalized = remote_normalized
                solr_field_used = 'remote'
                print(f"  [LOGIC] Using remote field")
            elif workmode_normalized is not None:
                solr_val_normalized = workmode_normalized
                solr_field_used = 'workmode'
                print(f"  [LOGIC] Using workmode (remote not available)")
        
        print(f"\nFINAL COMPARISON:")
        print(f"  DB: {db_val_normalized}")
        print(f"  Solr (used): {solr_val_normalized} (from {solr_field_used})")
        print(f"  Match: {db_val_normalized == solr_val_normalized}")
        
        if db_val_normalized == solr_val_normalized:
            print(f"  [OK] Work mode MATCHES - this is a FALSE POSITIVE!")
        else:
            print(f"  [X] Work mode MISMATCH - this is a REAL ERROR")
        
        print()
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_workmode_failures()
