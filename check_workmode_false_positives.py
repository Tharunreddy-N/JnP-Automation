"""
Check work mode false positives to understand the issue
"""
import json
import mysql.connector
import pysolr
from utils.connections import connections

def check_workmode_issue():
    """Check a few false positive jobs to understand work mode comparison issue"""
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
    
    # Get false positive job IDs
    with open('reports/verification_report_130_failures.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    false_positives = [fp for fp in report['false_positives'] if 'Work Mode' in fp.get('reported_msg', '')]
    
    print(f"Checking {len(false_positives)} work mode false positives...\n")
    
    for fp in false_positives[:5]:
        job_id = fp['id']
        print(f"{'='*80}")
        print(f"Job ID: {job_id} - {fp['title']}")
        print(f"{'='*80}")
        
        # Get DB data
        cursor.execute("SELECT id, is_remote FROM jobsnprofiles_2022.jnp_jobs WHERE id = %s", (job_id,))
        db_data = cursor.fetchone()
        
        # Get Solr data
        solr_results = solr.search(f"id:{job_id}", rows=1)
        if solr_results:
            solr_data = solr_results.docs[0]
            
            print(f"\nDB is_remote: {db_data['is_remote']} (Type: {type(db_data['is_remote'])})")
            print(f"Solr remote: {solr_data.get('remote')} (Type: {type(solr_data.get('remote'))})")
            print(f"Solr workmode: {solr_data.get('workmode')} (Type: {type(solr_data.get('workmode'))})")
            
            # Check what the test logic would do
            db_val = db_data['is_remote']
            db_val_normalized = None
            if db_val is not None and db_val != '':
                db_val_str = str(db_val).strip()
                if db_val_str in ['0', 'false', 'False', 'FALSE', 'not remote', 'onsite', 'on-site']:
                    db_val_normalized = '0'
                elif db_val_str in ['1', 'true', 'True', 'TRUE', 'remote']:
                    db_val_normalized = '1'
                elif db_val_str in ['2', 'hybrid', 'Hybrid', 'HYBRID']:
                    db_val_normalized = '2'
            
            solr_remote = solr_data.get('remote')
            solr_workmode = solr_data.get('workmode')
            solr_val_normalized = None
            
            # Check remote field first
            if solr_remote is not None:
                solr_remote_str = str(solr_remote).strip()
                if solr_remote_str in ['0', 'false', 'False', 'FALSE', 'not remote', 'onsite', 'on-site']:
                    solr_val_normalized = '0'
                elif solr_remote_str in ['1', 'true', 'True', 'TRUE', 'remote']:
                    solr_val_normalized = '1'
                elif solr_remote_str in ['2', 'hybrid', 'Hybrid', 'HYBRID']:
                    solr_val_normalized = '2'
            
            # Fallback to workmode if remote not available
            if solr_val_normalized is None and solr_workmode is not None:
                solr_workmode_str = str(solr_workmode).strip().lower()
                if solr_workmode_str in ['true', '1', 'remote']:
                    solr_val_normalized = '1'
                elif solr_workmode_str in ['false', '0', 'not remote', 'onsite']:
                    solr_val_normalized = '0'
            
            print(f"\nNormalized:")
            print(f"  DB: {db_val_normalized}")
            print(f"  Solr: {solr_val_normalized}")
            print(f"  Match: {db_val_normalized == solr_val_normalized}")
            print()
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_workmode_issue()
