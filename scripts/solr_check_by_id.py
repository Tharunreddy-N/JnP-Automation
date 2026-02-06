"""
Solr Job ID Checker
===================
Simply change the JOB_IDS list below and run this script.
Output will be neatly formatted in the console.
"""

import sys
import os
from pathlib import Path

# Add project root to path so imports work regardless of where script is run from
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pysolr
import json
from utils.connections import connections

# ============================================
# CHANGE JOB IDs HERE - Add or remove IDs as needed
# ============================================
JOB_IDS = [
    '6040331',
]


def _init_solr():
    """Initialize Solr connection"""
    cred_json = connections()
    if not cred_json or "solr_cred" not in cred_json:
        raise RuntimeError("Solr credentials not found from connections()")

    solr_cred = cred_json["solr_cred"]
    return pysolr.Solr(
        "https://solr.jobsnprofiles.com/solr/jnp_jobs_v6/",
        auth=(solr_cred["user"], solr_cred["password"]),
        always_commit=False,
        timeout=30,
    )


def _format_value(value):
    """Format value for display"""
    if isinstance(value, list):
        if len(value) == 1:
            return str(value[0])
        return ", ".join(str(v) for v in value)
    return str(value)


def _print_job_data(job_id, doc):
    """Print job data in a neat, formatted way"""
    print("\n" + "=" * 80)
    print(f"JOB ID: {job_id}")
    print("=" * 80)
    
    # Key fields in order
    key_fields = [
        ("Title", "title"),
        ("Company", "company_name"),
        ("City", "city_name"),
        ("State", "state_name"),
        ("Work Mode", "remote"),
        ("Work Mode (Boolean)", "workmode"),
        ("Job Link", "joblink"),
        ("AI Skills", "ai_skills"),
        ("Technologies", "technologies_used"),
        ("Preferred Skills", "preferred_skills_name"),
        ("Salary Range", "salaryrange_from"),
        ("Job Type", "jobtype_name"),
        ("Work Permit", "workpermit_name"),
        ("Industry", "industry_type"),
        ("Experience", "experience"),
        ("Qualifications", "qualifications"),
        ("Status", "status"),
        ("Created", "created"),
        ("Modified", "modified"),
    ]
    
    for label, field in key_fields:
        value = doc.get(field)
        if value is not None:
            formatted = _format_value(value)
            if formatted and formatted.strip():
                print(f"{label:25} : {formatted}")
    
    # Show all other fields
    print("\n" + "-" * 80)
    print("ALL FIELDS:")
    print("-" * 80)
    for key, value in sorted(doc.items()):
        if key not in [f[1] for f in key_fields]:  # Skip already displayed fields
            formatted = _format_value(value)
            if formatted and formatted.strip() and formatted != "null":
                print(f"{key:25} : {formatted}")
    
    print("=" * 80)


def main():
    """Main function"""
    if not JOB_IDS:
        print("[WARNING] No job IDs specified. Please add IDs to JOB_IDS list in the script.")
        return
    
    print(f"\n[INFO] Checking {len(JOB_IDS)} job ID(s) in Solr...")
    print(f"[INFO] IDs: {', '.join(JOB_IDS)}\n")
    
    try:
        solr = _init_solr()
        print("[OK] Connected to Solr successfully\n")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Solr: {e}")
        return
    
    found_count = 0
    not_found_ids = []
    
    for job_id in JOB_IDS:
        try:
            query = f"id:{job_id}"
            results = solr.search(query, rows=1)
            
            if len(results) > 0:
                found_count += 1
                _print_job_data(job_id, results.docs[0])
            else:
                not_found_ids.append(job_id)
                print(f"\n[WARNING] Job ID {job_id}: NOT FOUND in Solr")
                
        except Exception as e:
            print(f"\n[ERROR] Error querying job ID {job_id}: {e}")
            not_found_ids.append(job_id)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"[OK] Found    : {found_count}/{len(JOB_IDS)}")
    if not_found_ids:
        print(f"[FAIL] Not Found: {len(not_found_ids)} - {', '.join(not_found_ids)}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
