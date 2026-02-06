"""
Verify actual data in DB and Solr for failed jobs
This script checks if we're comparing the correct data
"""
import mysql.connector
import pysolr
from utils.connections import connections
import json

def verify_job_data(job_ids):
    """Verify actual data in DB and Solr for given job IDs"""
    creds = connections()
    if not creds:
        print("ERROR: Failed to retrieve credentials")
        return
    
    # Connect to MySQL
    mysql_cred = creds.get('mysql_cred')
    conn = mysql.connector.connect(
        host=mysql_cred['host'],
        user=mysql_cred['user'],
        password=mysql_cred['password'],
        database="jobsnprofiles_2022"
    )
    cursor = conn.cursor(dictionary=True)
    
    # Connect to Solr
    solr_cred = creds.get('solr_cred')
    solr_url = "https://solr.jobsnprofiles.com/solr/jnp_jobs_v6/"
    solr = pysolr.Solr(
        solr_url,
        auth=(solr_cred['user'], solr_cred['password']),
        always_commit=False
    )
    
    print("="*100)
    print("VERIFYING ACTUAL DATA IN DB vs SOLR")
    print("="*100)
    
    for job_id in job_ids:
        print(f"\n{'='*100}")
        print(f"JOB ID: {job_id}")
        print(f"{'='*100}")
        
        # Get data from DB
        db_query = """
            SELECT id, company_name, title, statename, cityname, is_remote, joblink, ai_skills, slug, modified
            FROM jobsnprofiles_2022.jnp_jobs 
            WHERE id = %s
        """
        cursor.execute(db_query, (job_id,))
        db_result = cursor.fetchone()
        
        if not db_result:
            print(f"[ERROR] Job ID {job_id} NOT FOUND in DB")
            continue
        
        print(f"\n[DATABASE DATA]")
        print(f"   ID: {db_result['id']}")
        print(f"   Title: {db_result['title']}")
        print(f"   Company: {db_result.get('company_name', 'N/A')}")
        print(f"   State: {db_result.get('statename', 'N/A')}")
        print(f"   City: {db_result.get('cityname', 'N/A')}")
        print(f"   is_remote: {db_result.get('is_remote', 'N/A')} (Type: {type(db_result.get('is_remote'))})")
        print(f"   joblink: {db_result.get('joblink', 'N/A')}")
        print(f"   ai_skills (RAW): {repr(db_result.get('ai_skills', 'N/A'))}")
        print(f"   ai_skills (String): {str(db_result.get('ai_skills', 'N/A'))}")
        print(f"   Modified: {db_result.get('modified', 'N/A')}")
        
        # Get data from Solr
        solr_query = f"id:{job_id}"
        solr_results = solr.search(solr_query, rows=1)
        
        if len(solr_results) == 0:
            print(f"\n[ERROR] Job ID {job_id} NOT FOUND in Solr")
            continue
        
        solr_doc = solr_results.docs[0]
        print(f"\n[SOLR DATA]")
        print(f"   ID: {solr_doc.get('id', 'N/A')}")
        print(f"   Title: {solr_doc.get('title', 'N/A')} (Type: {type(solr_doc.get('title'))})")
        if isinstance(solr_doc.get('title'), list):
            print(f"   Title (first): {solr_doc.get('title')[0] if solr_doc.get('title') else 'N/A'}")
        print(f"   Company: {solr_doc.get('company_name', 'N/A')} (Type: {type(solr_doc.get('company_name'))})")
        print(f"   State: {solr_doc.get('state_name', 'N/A')} (Type: {type(solr_doc.get('state_name'))})")
        print(f"   City: {solr_doc.get('city_name', 'N/A')} (Type: {type(solr_doc.get('city_name'))})")
        print(f"   remote: {solr_doc.get('remote', 'N/A')} (Type: {type(solr_doc.get('remote'))})")
        print(f"   workmode: {solr_doc.get('workmode', 'N/A')} (Type: {type(solr_doc.get('workmode'))})")
        print(f"   joblink: {solr_doc.get('joblink', 'N/A')} (Type: {type(solr_doc.get('joblink'))})")
        print(f"   ai_skills (RAW): {repr(solr_doc.get('ai_skills', 'N/A'))}")
        print(f"   ai_skills (Type): {type(solr_doc.get('ai_skills'))}")
        if isinstance(solr_doc.get('ai_skills'), list):
            print(f"   ai_skills (List): {solr_doc.get('ai_skills')}")
            print(f"   ai_skills (Joined): {','.join(str(s) for s in solr_doc.get('ai_skills', []))}")
        else:
            print(f"   ai_skills (String): {str(solr_doc.get('ai_skills', 'N/A'))}")
        
        # Compare AI Skills
        print(f"\n[AI SKILLS COMPARISON]")
        db_skills = db_result.get('ai_skills', '')
        solr_skills = solr_doc.get('ai_skills', '')
        
        # Normalize DB skills
        if db_skills:
            if isinstance(db_skills, str):
                db_skills_list = [s.strip() for s in db_skills.split(',') if s.strip()]
            else:
                db_skills_list = [str(db_skills)]
        else:
            db_skills_list = []
        
        # Normalize Solr skills
        if solr_skills:
            if isinstance(solr_skills, list):
                solr_skills_list = [str(s).strip() for s in solr_skills if s]
            else:
                solr_skills_list = [str(solr_skills).strip()]
        else:
            solr_skills_list = []
        
        print(f"   DB Skills ({len(db_skills_list)}): {db_skills_list[:10]}{'...' if len(db_skills_list) > 10 else ''}")
        print(f"   Solr Skills ({len(solr_skills_list)}): {solr_skills_list[:10]}{'...' if len(solr_skills_list) > 10 else ''}")
        
        # Check overlap
        db_set = set(s.lower().strip() for s in db_skills_list)
        solr_set = set(s.lower().strip() for s in solr_skills_list)
        common = db_set & solr_set
        only_db = db_set - solr_set
        only_solr = solr_set - db_set
        
        print(f"\n   Common Skills: {len(common)}")
        if common:
            print(f"      {list(common)[:10]}{'...' if len(common) > 10 else ''}")
        print(f"   Only in DB: {len(only_db)}")
        if only_db:
            print(f"      {list(only_db)[:10]}{'...' if len(only_db) > 10 else ''}")
        print(f"   Only in Solr: {len(only_solr)}")
        if only_solr:
            print(f"      {list(only_solr)[:10]}{'...' if len(only_solr) > 10 else ''}")
        
        # Work Mode Comparison
        print(f"\n[WORK MODE COMPARISON]")
        db_remote = db_result.get('is_remote', '')
        solr_remote = solr_doc.get('remote', 'N/A')
        solr_workmode = solr_doc.get('workmode', 'N/A')
        print(f"   DB is_remote: {db_remote} (Type: {type(db_remote)})")
        print(f"   Solr remote: {solr_remote} (Type: {type(solr_remote)})")
        print(f"   Solr workmode: {solr_workmode} (Type: {type(solr_workmode)})")
    
    cursor.close()
    conn.close()
    print(f"\n{'='*100}")
    print("VERIFICATION COMPLETE")
    print("="*100)

if __name__ == "__main__":
    # Get failed job IDs from the report
    try:
        with open('reports/db_solr_sync_failures.json', 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        failures = report.get('failures', [])
        if not failures:
            print("No failures found in report. Checking first 5 from history...")
            with open('logs/history/jobseeker_history.json', 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            db_solr_test = history.get('test_t1_09_db_solr_sync_verification', [])
            if db_solr_test:
                latest = db_solr_test[0]
                error_jobs = latest.get('error_jobs', [])
                job_ids = [job['id'] for job in error_jobs[:5]]
            else:
                print("No test data found in history")
                job_ids = []
        else:
            job_ids = [f['id'] for f in failures[:5]]
        
        if job_ids:
            print(f"Checking {len(job_ids)} failed jobs...")
            verify_job_data(job_ids)
        else:
            print("No job IDs to verify")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
