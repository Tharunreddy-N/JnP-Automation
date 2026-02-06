"""
Verify all 130 failed jobs to check if errors are real or false positives
"""
import json
import mysql.connector
import pysolr
from utils.connections import connections
from urllib.parse import urlparse
from collections import defaultdict

def _normalize_skills_list(skills_input):
    """Normalize skills list for comparison"""
    if not skills_input:
        return set()
    
    if isinstance(skills_input, str):
        skills_list = [s.strip() for s in skills_input.split(',') if s.strip()]
    elif isinstance(skills_input, list):
        skills_list = [str(s).strip() for s in skills_input if s]
    else:
        skills_list = [str(skills_input).strip()]
    
    # Normalize: lowercase, remove extra spaces
    normalized = set()
    for skill in skills_list:
        normalized.add(skill.lower().strip())
    
    return normalized

def _skills_match(db_skills, solr_skills):
    """Check if skills match with 70% overlap threshold"""
    db_set = _normalize_skills_list(db_skills)
    solr_set = _normalize_skills_list(solr_skills)
    
    if not db_set and not solr_set:
        return True
    
    if not db_set or not solr_set:
        return False
    
    common = db_set & solr_set
    max_len = max(len(db_set), len(solr_set))
    overlap_pct = (len(common) / max_len * 100) if max_len > 0 else 0
    
    return overlap_pct >= 70

def verify_all_failures():
    """Verify all failed jobs from JSON report"""
    # Load failures from JSON
    with open('reports/db_solr_sync_failures.json', 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    failures = report_data.get('failures', [])
    print(f"Total failures to verify: {len(failures)}")
    print("="*100)
    
    # Get credentials
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
    
    # Statistics
    stats = {
        'total': len(failures),
        'real_errors': 0,
        'false_positives': 0,
        'not_found_in_solr': 0,
        'not_found_in_db': 0,
        'error_types': defaultdict(int)
    }
    
    real_errors = []
    false_positives = []
    
    print(f"\nVerifying {len(failures)} failed jobs...\n")
    
    for idx, failure in enumerate(failures, 1):
        job_id = failure.get('id')
        reported_msg = failure.get('msg', '')
        
        if idx % 10 == 0:
            print(f"Progress: {idx}/{len(failures)} jobs verified...")
        
        # Get DB data
        db_query = """
            SELECT id, company_name, title, statename, cityname, is_remote, joblink, ai_skills, slug, modified
            FROM jobsnprofiles_2022.jnp_jobs 
            WHERE id = %s
        """
        cursor.execute(db_query, (job_id,))
        db_data = cursor.fetchone()
        
        if not db_data:
            stats['not_found_in_db'] += 1
            false_positives.append({
                'id': job_id,
                'reason': 'Not found in DB',
                'reported_msg': reported_msg
            })
            continue
        
        # Get Solr data
        solr_query = f"id:{job_id}"
        try:
            solr_results = solr.search(solr_query, rows=1)
            if len(solr_results) == 0:
                stats['not_found_in_solr'] += 1
                false_positives.append({
                    'id': job_id,
                    'reason': 'Not found in Solr',
                    'reported_msg': reported_msg
                })
                continue
            solr_data = solr_results.docs[0]
        except Exception as e:
            stats['not_found_in_solr'] += 1
            false_positives.append({
                'id': job_id,
                'reason': f'Solr query error: {str(e)}',
                'reported_msg': reported_msg
            })
            continue
        
        # Verify each reported mismatch
        mismatches = failure.get('mismatches', [])
        verified_errors = []
        is_false_positive = True
        
        for mismatch in mismatches:
            if 'Job Link' in mismatch and 'Different domains' in mismatch:
                # Verify job link mismatch
                db_joblink = db_data.get('joblink', '')
                solr_joblink = solr_data.get('joblink', '')
                
                if db_joblink and solr_joblink:
                    db_parsed = urlparse(db_joblink if '://' in db_joblink else f'https://{db_joblink}')
                    solr_parsed = urlparse(solr_joblink if '://' in solr_joblink else f'https://{solr_joblink}')
                    db_domain = db_parsed.netloc.lower().replace('www.', '')
                    solr_domain = solr_parsed.netloc.lower().replace('www.', '')
                    
                    if db_domain != solr_domain:
                        verified_errors.append(f"Job Link: Different domains (DB={db_domain}, Solr={solr_domain})")
                        is_false_positive = False
                        stats['error_types']['joblink_domain'] += 1
                
            elif 'ai_skills' in mismatch.lower():
                # Verify AI skills mismatch
                db_skills = db_data.get('ai_skills', '')
                solr_skills = solr_data.get('ai_skills', [])
                
                if not _skills_match(db_skills, solr_skills):
                    # Real mismatch - calculate overlap
                    db_set = _normalize_skills_list(db_skills)
                    solr_set = _normalize_skills_list(solr_skills)
                    common = db_set & solr_set
                    max_len = max(len(db_set), len(solr_set))
                    overlap_pct = (len(common) / max_len * 100) if max_len > 0 else 0
                    
                    verified_errors.append(f"ai_skills: Overlap {overlap_pct:.1f}% (below 70% threshold)")
                    is_false_positive = False
                    stats['error_types']['ai_skills'] += 1
                else:
                    # False positive - skills actually match
                    verified_errors.append(f"ai_skills: FALSE POSITIVE (skills actually match)")
            
            elif 'Cityname' in mismatch or 'Statename' in mismatch:
                # Verify location mismatch
                field = 'cityname' if 'Cityname' in mismatch else 'statename'
                solr_field = 'city_name' if field == 'cityname' else 'state_name'
                
                db_val = db_data.get(field, '')
                solr_val = solr_data.get(solr_field, '')
                
                if isinstance(solr_val, list) and solr_val:
                    solr_val = solr_val[0]
                
                db_normalized = str(db_val).lower().strip() if db_val else ''
                solr_normalized = str(solr_val).lower().strip() if solr_val else ''
                
                if db_normalized != solr_normalized:
                    verified_errors.append(f"{field}: DB='{db_val}' ≠ Solr='{solr_val}'")
                    is_false_positive = False
                    stats['error_types'][field] += 1
                else:
                    verified_errors.append(f"{field}: FALSE POSITIVE (values match)")
            
            elif 'Company' in mismatch or 'Title' in mismatch:
                # Verify company/title mismatch
                field = 'company_name' if 'Company' in mismatch else 'title'
                db_val = db_data.get(field, '')
                solr_val = solr_data.get(field, '')
                
                if isinstance(solr_val, list) and solr_val:
                    solr_val = solr_val[0]
                
                db_normalized = str(db_val).lower().strip() if db_val else ''
                solr_normalized = str(solr_val).lower().strip() if solr_val else ''
                
                if db_normalized != solr_normalized:
                    verified_errors.append(f"{field}: DB='{db_val}' ≠ Solr='{solr_val}'")
                    is_false_positive = False
                    stats['error_types'][field] += 1
                else:
                    verified_errors.append(f"{field}: FALSE POSITIVE (values match)")
        
        # Categorize result
        if is_false_positive:
            stats['false_positives'] += 1
            false_positives.append({
                'id': job_id,
                'title': db_data.get('title', 'N/A'),
                'reason': 'All mismatches are false positives',
                'reported_msg': reported_msg,
                'verified_errors': verified_errors
            })
        else:
            stats['real_errors'] += 1
            real_errors.append({
                'id': job_id,
                'title': db_data.get('title', 'N/A'),
                'reported_msg': reported_msg,
                'verified_errors': verified_errors
            })
    
    cursor.close()
    conn.close()
    
    # Print summary
    print("\n" + "="*100)
    print("VERIFICATION SUMMARY")
    print("="*100)
    print(f"Total failures checked: {stats['total']}")
    print(f"Real errors: {stats['real_errors']} ({stats['real_errors']/stats['total']*100:.1f}%)")
    print(f"False positives: {stats['false_positives']} ({stats['false_positives']/stats['total']*100:.1f}%)")
    print(f"Not found in DB: {stats['not_found_in_db']}")
    print(f"Not found in Solr: {stats['not_found_in_solr']}")
    print(f"\nError Types Breakdown:")
    for error_type, count in sorted(stats['error_types'].items()):
        print(f"  {error_type}: {count}")
    
    # Save detailed report
    report = {
        'summary': stats,
        'real_errors': real_errors,
        'false_positives': false_positives
    }
    
    with open('reports/verification_report_130_failures.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to: reports/verification_report_130_failures.json")
    
    # Print sample real errors
    if real_errors:
        print(f"\n{'='*100}")
        print(f"SAMPLE REAL ERRORS (first 5):")
        print("="*100)
        for error in real_errors[:5]:
            print(f"\nJob ID: {error['id']}")
            print(f"Title: {error['title']}")
            errors_str = ', '.join(error['verified_errors']).encode('utf-8', errors='replace').decode('utf-8')
            print(f"Verified Errors: {errors_str}")
    
    # Print sample false positives
    if false_positives:
        print(f"\n{'='*100}")
        print(f"SAMPLE FALSE POSITIVES (first 5):")
        print("="*100)
        for fp in false_positives[:5]:
            print(f"\nJob ID: {fp['id']}")
            print(f"Title: {fp.get('title', 'N/A')}")
            reason_str = fp['reason'].encode('utf-8', errors='replace').decode('utf-8')
            print(f"Reason: {reason_str}")

if __name__ == "__main__":
    verify_all_failures()
