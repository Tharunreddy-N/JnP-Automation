"""
Verify DB vs Solr data for specific job IDs.
Supports explicit IDs or reading from the failures report.
"""
import json
import mysql.connector
import pysolr
from utils.connections import connections
from urllib.parse import urlparse
import argparse
from pathlib import Path

def _normalize_skills_list(skills_input):
    """Normalize skills list for comparison - same as test"""
    if not skills_input:
        return set()
    
    if isinstance(skills_input, str):
        skills_list = [s.strip() for s in skills_input.split(',') if s.strip()]
    elif isinstance(skills_input, list):
        skills_list = [str(s).strip() for s in skills_input if s]
    else:
        skills_list = [str(skills_input).strip()]
    
    normalized = set()
    for skill in skills_list:
        normalized.add(skill.lower().strip())
    
    return normalized

def _skills_match(db_skills, solr_skills):
    """Check if skills match with 70% overlap threshold - same as test"""
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

def _normalize_workmode(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        val_str = str(int(val))
        return val_str if val_str in ['0', '1', '2'] else None
    if isinstance(val, bool):
        return '1' if val else '0'
    if isinstance(val, str):
        val_lower = val.strip().lower()
        if val_lower in ['0', '1', '2']:
            return val_lower
        if val_lower in ['true', 'remote']:
            return '1'
        if val_lower in ['false', 'not remote', 'onsite', 'on-site']:
            return '0'
        if val_lower in ['hybrid']:
            return '2'
    return None


def _load_ids_from_report(report_path: Path, limit: int | None):
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")
    with report_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    failures = payload.get("failures", [])
    ids = [int(item.get("id")) for item in failures if item.get("id")]
    if limit:
        return ids[:limit]
    return ids


def verify_sample_jobs(job_ids):
    """Verify DB vs Solr data for given job IDs"""
    
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
    
    for job_id in job_ids:
        print(f"\n{'='*100}")
        print(f"VERIFYING JOB ID: {job_id}")
        print(f"{'='*100}")
        
        # Get DB data
        cursor.execute("""
            SELECT id, company_name, title, statename, cityname, is_remote, joblink, ai_skills, slug, modified
            FROM jobsnprofiles_2022.jnp_jobs 
            WHERE id = %s
        """, (job_id,))
        db_data = cursor.fetchone()
        
        if not db_data:
            print(f"NOT FOUND IN DB")
            continue
        
        # Get Solr data
        solr_results = solr.search(f"id:{job_id}", rows=1)
        if not solr_results:
            print(f"NOT FOUND IN SOLR")
            continue
        
        solr_data = solr_results.docs[0]
        
        print(f"\n[0. BASIC FIELDS]")
        print(f"   DB Title: {db_data.get('title')}")
        print(f"   Solr Title: {solr_data.get('title')}")
        print(f"   DB Company: {db_data.get('company_name')}")
        print(f"   Solr Company: {solr_data.get('company_name')}")
        print(f"   DB State: {db_data.get('statename')}")
        print(f"   Solr State: {solr_data.get('state_name')}")
        print(f"   DB City: {db_data.get('cityname')}")
        print(f"   Solr City: {solr_data.get('city_name')}")

        print(f"\n[1. JOB LINK COMPARISON]")
        db_joblink = db_data.get('joblink', '')
        solr_joblink = solr_data.get('joblink', '')
        print(f"   DB joblink: {repr(db_joblink)}")
        print(f"   Solr joblink: {repr(solr_joblink)}")
        
        if db_joblink and solr_joblink:
            # Extract domains like test does
            db_parsed = urlparse(db_joblink if '://' in db_joblink else f'https://{db_joblink}')
            solr_parsed = urlparse(solr_joblink if '://' in solr_joblink else f'https://{solr_joblink}')
            db_domain = db_parsed.netloc.lower().replace('www.', '')
            solr_domain = solr_parsed.netloc.lower().replace('www.', '')
            print(f"   DB Domain: {db_domain}")
            print(f"   Solr Domain: {solr_domain}")
            print(f"   Match: {db_domain == solr_domain}")
            if db_domain != solr_domain:
                print(f"   [X] MISMATCH DETECTED (but user says they're the same)")
            else:
                print(f"   [OK] Domains match")
        else:
            print(f"   One or both missing")
        
        print(f"\n[2. AI SKILLS COMPARISON]")
        db_skills = db_data.get('ai_skills', '')
        solr_skills = solr_data.get('ai_skills', [])
        print(f"   DB ai_skills (type: {type(db_skills)}): {str(db_skills)[:100]}...")
        print(f"   Solr ai_skills (type: {type(solr_skills)}): {solr_skills[:10] if isinstance(solr_skills, list) else solr_skills}")
        
        db_set = _normalize_skills_list(db_skills)
        solr_set = _normalize_skills_list(solr_skills)
        common = db_set & solr_set
        max_len = max(len(db_set), len(solr_set))
        overlap_pct = (len(common) / max_len * 100) if max_len > 0 else 0
        
        print(f"   DB Skills Count: {len(db_set)}")
        print(f"   Solr Skills Count: {len(solr_set)}")
        print(f"   Common Skills: {len(common)}")
        print(f"   Overlap: {overlap_pct:.1f}%")
        print(f"   Exact Match: {db_set == solr_set}")
        print(f"   Match (>=70%): {overlap_pct >= 70}")
        
        if not _skills_match(db_skills, solr_skills):
            print(f"   [X] MISMATCH DETECTED (overlap {overlap_pct:.1f}% < 70%)")
            print(f"   Common: {sorted(list(common))[:10]}")
            only_db = db_set - solr_set
            only_solr = solr_set - db_set
            print(f"   Only in DB: {sorted(list(only_db))[:10]}")
            print(f"   Only in Solr: {sorted(list(only_solr))[:10]}")
        else:
            print(f"   [OK] Skills match (overlap >= 70%)")
        
        print(f"\n[3. WORK MODE COMPARISON]")
        db_is_remote = db_data.get('is_remote')
        solr_remote = solr_data.get('remote')
        solr_workmode = solr_data.get('workmode')
        print(f"   DB is_remote: {db_is_remote} (Type: {type(db_is_remote)})")
        print(f"   Solr remote: {solr_remote} (Type: {type(solr_remote)})")
        print(f"   Solr workmode: {solr_workmode} (Type: {type(solr_workmode)})")
        
        # Normalize like test does
        db_val_normalized = _normalize_workmode(db_is_remote)
        remote_normalized = _normalize_workmode(solr_remote)
        workmode_normalized = _normalize_workmode(solr_workmode)

        print(f"   Normalized DB: {db_val_normalized}")
        print(f"   Normalized Solr remote: {remote_normalized}")
        print(f"   Normalized Solr workmode: {workmode_normalized}")

        if db_val_normalized is None:
            if remote_normalized is not None:
                print("   [X] MISMATCH DETECTED (DB empty, Solr remote has value)")
            else:
                print("   [OK] Work mode matches (both empty)")
        else:
            if remote_normalized is None:
                print("   [SKIP] Solr remote missing (ignored)")
            elif remote_normalized == db_val_normalized:
                print("   [OK] Work mode matches")
            else:
                print("   [X] MISMATCH DETECTED (remote mismatch)")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify DB vs Solr for job IDs")
    parser.add_argument(
        "--ids",
        help="Comma-separated job IDs to verify, e.g. 5725776,6091033",
    )
    parser.add_argument(
        "--from-report",
        action="store_true",
        help="Load IDs from reports/db_solr_sync_failures.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of IDs when using --from-report",
    )
    args = parser.parse_args()

    if args.ids:
        job_ids = [int(v.strip()) for v in args.ids.split(",") if v.strip()]
    elif args.from_report:
        job_ids = _load_ids_from_report(Path("reports/db_solr_sync_failures.json"), args.limit)
    else:
        job_ids = [5725776]

    verify_sample_jobs(job_ids)
