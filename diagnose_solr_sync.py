"""
Diagnostic script to understand why jobs are not found in Solr
This will help identify if it's a collection name issue, query issue, or sync delay
"""
import mysql.connector
import pysolr
from utils.connections import connections
import json

def diagnose_solr_sync_issue():
    """Diagnose why jobs are not found in Solr"""
    
    print("=" * 80)
    print("SOLR SYNC DIAGNOSTIC TOOL")
    print("=" * 80)
    
    # Get credentials
    creds = connections()
    if not creds:
        print("ERROR: Failed to retrieve credentials")
        return
    
    mysql_cred = creds.get('mysql_cred')
    solr_cred = creds.get('solr_cred')
    
    if not mysql_cred or not solr_cred:
        print("ERROR: Missing credentials")
        return
    
    # Connect to DB
    print("\n1. Connecting to MySQL database...")
    try:
        conn = mysql.connector.connect(
            host=mysql_cred['host'],
            user=mysql_cred['user'],
            password=mysql_cred['password'],
            database="jobsnprofiles_2022"
        )
        cursor = conn.cursor(dictionary=True)
        
        # Get a sample of recent jobs
        query = """
            SELECT id, company_name, title, statename, cityname, is_remote, joblink, ai_skills, slug, modified
            FROM jobsnprofiles_2022.jnp_jobs 
            WHERE modified >= NOW() - INTERVAL 1 DAY 
            ORDER BY modified DESC
            LIMIT 10;
        """
        cursor.execute(query)
        sample_jobs = cursor.fetchall()
        
        print(f"   [OK] Found {len(sample_jobs)} sample jobs from last 24 hours")
        if sample_jobs:
            print(f"   Sample Job IDs: {[job['id'] for job in sample_jobs[:5]]}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"   [ERROR] Database error: {e}")
        return
    
    # Test different Solr collections
    print("\n2. Testing Solr collections...")
    solr_collections = [
        "jnp_jobs_v6",      # Current collection in test
        "jnp_jobs_v4_1",    # Found in other code
        "jnp_jobs_v2",      # Found in other code
    ]
    
    solr_base_url = "https://solr.jobsnprofiles.com/solr"
    results_summary = {}
    
    for collection in solr_collections:
        print(f"\n   Testing collection: {collection}")
        try:
            solr_url = f"{solr_base_url}/{collection}/"
            solr = pysolr.Solr(
                solr_url,
                auth=(solr_cred['user'], solr_cred['password']),
                always_commit=False
            )
            
            # Test connection
            ping_result = solr.ping()
            print(f"      [OK] Connection successful")
            
            # Test with first sample job
            if sample_jobs:
                test_job_id = sample_jobs[0]['id']
                print(f"      Testing with Job ID: {test_job_id}")
                
                # Try different query formats
                queries_to_try = [
                    f"id:{test_job_id}",
                    f"id:\"{test_job_id}\"",
                    f"id:{test_job_id}*",
                ]
                
                found = False
                for query in queries_to_try:
                    try:
                        result = solr.search(query, rows=1)
                        if len(result) > 0:
                            print(f"      [FOUND] FOUND with query: {query}")
                            print(f"         Title: {result.docs[0].get('title', 'N/A')}")
                            print(f"         ID in Solr: {result.docs[0].get('id', 'N/A')}")
                            found = True
                            results_summary[collection] = {
                                'status': 'FOUND',
                                'query': query,
                                'sample_id': test_job_id
                            }
                            break
                    except Exception as e:
                        print(f"      [ERROR] Query '{query}' failed: {e}")
                
                if not found:
                    print(f"      [NOT FOUND] NOT FOUND with any query format")
                    results_summary[collection] = {
                        'status': 'NOT_FOUND',
                        'sample_id': test_job_id
                    }
                    
                    # Try a general search to see if collection has any data
                    try:
                        general_result = solr.search("*:*", rows=1)
                        if len(general_result) > 0:
                            print(f"      [INFO] Collection has data (found {len(general_result)} docs with general query)")
                            print(f"         Sample doc ID: {general_result.docs[0].get('id', 'N/A')}")
                        else:
                            print(f"      [WARNING] Collection appears empty")
                    except Exception as e:
                        print(f"      [ERROR] Cannot query collection: {e}")
            
        except Exception as e:
            print(f"      [ERROR] Connection failed: {e}")
            results_summary[collection] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(json.dumps(results_summary, indent=2))
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    found_collections = [c for c, r in results_summary.items() if r.get('status') == 'FOUND']
    if found_collections:
        print(f"[OK] Jobs found in: {', '.join(found_collections)}")
        print(f"  -> Update test to use: {found_collections[0]}")
    else:
        print("[ERROR] Jobs not found in any collection tested")
        print("  Possible reasons:")
        print("  1. Sync delay - Jobs may take time to appear in Solr")
        print("  2. Wrong collection name - Check with Solr admin")
        print("  3. Jobs are in a different collection not tested")
        print("  4. Jobs need to be manually synced to Solr")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    diagnose_solr_sync_issue()
