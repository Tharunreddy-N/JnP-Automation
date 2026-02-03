"""
CORRECTED Solr Search Code
The issue: You were searching by 'remote' field instead of 'id' field
"""

import pysolr
from utils.connections import connections

# Get credentials
cred_json = connections()

# Connect to Solr
solr_v4 = pysolr.Solr(
    "https://solr.jobsnprofiles.com/solr/jnp_jobs_v6/",
    auth=(cred_json['solr_cred']['user'], cred_json['solr_cred']['password']),
    always_commit=False  # Changed from True - no need to commit on read
)

# Get job IDs from database (your correct query)
import mysql.connector
mysql_cred = cred_json['mysql_cred']

conn = mysql.connector.connect(
    host=mysql_cred['host'],
    user=mysql_cred['user'],
    password=mysql_cred['password'],
    database="jobsnprofiles_2022"
)
cursor = conn.cursor(dictionary=True)

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

# Extract job IDs
job_ids = [job['id'] for job in db_jobs]
print(f"Testing {len(job_ids)} job IDs: {job_ids[:5]}...")

# CORRECTED: Search by ID (not by remote)
try:
    found_count = 0
    not_found_count = 0
    
    for job_id in job_ids:
        # ✅ CORRECT: Search by 'id' field
        results = solr_v4.search(f"id:{job_id}", rows=1)
        
        if len(results) > 0:
            found_count += 1
            doc = results.docs[0]
            print(f"\n[FOUND] Job ID {job_id} FOUND in Solr")
            print(f"  Title: {doc.get('title', 'N/A')}")
            print(f"  Company: {doc.get('company_name', 'N/A')}")
        else:
            not_found_count += 1
            print(f"\n[NOT FOUND] Job ID {job_id} NOT FOUND in Solr")
            
            # Try alternative query formats
            alt_queries = [
                f'id:"{job_id}"',  # Quoted format
                f'id:{job_id}*',   # Wildcard
            ]
            
            for alt_query in alt_queries:
                try:
                    alt_results = solr_v4.search(alt_query, rows=1)
                    if len(alt_results) > 0:
                        print(f"  [WARNING] But found with alternative query: {alt_query}")
                        found_count += 1
                        not_found_count -= 1
                        break
                except:
                    pass
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: Found {found_count}/{len(job_ids)} jobs in Solr")
    print(f"Success Rate: {(found_count/len(job_ids)*100):.2f}%")
    
    if not_found_count > 0:
        print(f"\n[WARNING] {not_found_count} jobs not found. Possible reasons:")
        print("   1. Jobs haven't synced to Solr yet (sync delay)")
        print("   2. Wrong Solr collection (check if jobs are in v4_1 or v2)")
        print("   3. Sync process is not running")
    
except Exception as e:
    print(f"Error querying Solr: {e}")
