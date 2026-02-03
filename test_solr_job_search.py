"""
Corrected Solr Job Search Test
Fixes the issue: searching by 'remote' instead of 'id'
"""
import pysolr
import mysql.connector
import json
import sys
import os

# Add utils to path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from utils.connections import connections

def test_solr_job_search():
    """Test searching for jobs in Solr by ID"""
    
    print("=" * 80)
    print("SOLR JOB SEARCH TEST")
    print("=" * 80)
    
    # Get credentials
    print("\n1. Getting credentials...")
    try:
        cred_json = connections()
        if not cred_json:
            print("ERROR: Failed to get credentials")
            return
        
        solr_cred = cred_json.get('solr_cred')
        mysql_cred = cred_json.get('mysql_cred')
        
        if not solr_cred:
            print("ERROR: Solr credentials not found")
            return
        if not mysql_cred:
            print("ERROR: MySQL credentials not found")
            return
            
        print("   ✓ Credentials retrieved")
    except Exception as e:
        print(f"   ✗ Error getting credentials: {e}")
        return
    
    # Connect to Solr
    print("\n2. Connecting to Solr...")
    try:
        solr_url = "https://solr.jobsnprofiles.com/solr/jnp_jobs_v6/"
        solr = pysolr.Solr(
            solr_url,
            auth=(solr_cred['user'], solr_cred['password']),
            always_commit=False
        )
        
        # Test connection
        ping_result = solr.ping()
        print(f"   ✓ Connected to Solr: {solr_url}")
    except Exception as e:
        print(f"   ✗ Failed to connect to Solr: {e}")
        return
    
    # Get sample job IDs from database
    print("\n3. Getting sample job IDs from database...")
    try:
        conn = mysql.connector.connect(
            host=mysql_cred['host'],
            user=mysql_cred['user'],
            password=mysql_cred['password'],
            database="jobsnprofiles_2022"
        )
        cursor = conn.cursor(dictionary=True)
        
        # Get jobs modified in last day (same query as test)
        query = """
            SELECT id, company_name, title, statename, cityname, is_remote, joblink, ai_skills, slug 
            FROM jobsnprofiles_2022.jnp_jobs 
            WHERE modified >= NOW() - INTERVAL 1 DAY 
            GROUP BY title, company_name, id
            LIMIT 10;
        """
        cursor.execute(query)
        db_jobs = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not db_jobs:
            print("   ⚠ No jobs found in database (modified in last 24 hours)")
            return
        
        print(f"   ✓ Found {len(db_jobs)} jobs in database")
        job_ids = [job['id'] for job in db_jobs[:5]]  # Test first 5
        print(f"   Testing with Job IDs: {job_ids}")
        
    except Exception as e:
        print(f"   ✗ Database error: {e}")
        return
    
    # Test searching by ID (CORRECT METHOD)
    print("\n4. Testing Solr search by ID (CORRECT METHOD)...")
    print("-" * 80)
    
    found_count = 0
    not_found_count = 0
    
    for job_id in job_ids:
        try:
            # CORRECT: Search by ID
            query = f"id:{job_id}"
            results = solr.search(query, rows=1)
            
            if len(results) > 0:
                found_count += 1
                doc = results.docs[0]
                print(f"\n   ✓ Job ID {job_id} FOUND in Solr")
                print(f"      Title: {doc.get('title', 'N/A')}")
                print(f"      ID in Solr: {doc.get('id', 'N/A')}")
                print(f"      Company: {doc.get('company_name', 'N/A')}")
            else:
                not_found_count += 1
                print(f"\n   ✗ Job ID {job_id} NOT FOUND in Solr")
                
                # Try alternative query formats
                alt_queries = [
                    f'id:"{job_id}"',
                    f'id:{job_id}*',
                ]
                
                for alt_query in alt_queries:
                    try:
                        alt_results = solr.search(alt_query, rows=1)
                        if len(alt_results) > 0:
                            print(f"      ⚠ But found with query: {alt_query}")
                            break
                    except:
                        pass
                        
        except Exception as e:
            print(f"\n   ✗ Error searching for Job ID {job_id}: {e}")
            not_found_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Jobs Tested: {len(job_ids)}")
    print(f"Found in Solr: {found_count}")
    print(f"Not Found in Solr: {not_found_count}")
    print(f"Success Rate: {(found_count/len(job_ids)*100):.2f}%")
    
    if not_found_count > 0:
        print("\n⚠️  ISSUE DETECTED:")
        print("   Some jobs are not found in Solr. Possible reasons:")
        print("   1. Jobs haven't been synced to Solr yet (sync delay)")
        print("   2. Wrong Solr collection (currently using: jnp_jobs_v6)")
        print("   3. Sync process is not running")
        print("   4. Jobs are in a different Solr collection")
    
    print("\n" + "=" * 80)
    
    # Show the CORRECTED code
    print("\n" + "=" * 80)
    print("CORRECTED CODE EXAMPLE")
    print("=" * 80)
    print("""
# ❌ WRONG (your original code):
results = solr_v4.search(f"remote:{2}")  # This searches by 'remote' field, not job ID!

# ✅ CORRECT:
job_ids = ["5840137", "5995257"]  # Your job IDs
for job_id in job_ids:
    results = solr_v4.search(f"id:{job_id}")  # Search by 'id' field
    if len(results) > 0:
        print(f"Job ID {job_id} exists in Solr")
        for doc in results:
            print(doc)
    else:
        print(f"Job ID {job_id} not found in Solr")
    """)

if __name__ == "__main__":
    test_solr_job_search()
