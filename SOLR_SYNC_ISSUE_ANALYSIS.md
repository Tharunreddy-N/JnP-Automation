# DB-Solr Sync Issue Analysis

## Problem Summary
All 1998 jobs are failing with "Not Found in Solr" error in the `test_t1_09_db_solr_sync_verification` test.

## Root Cause Analysis

### What the Test Does
1. Fetches jobs from MySQL database that were modified in the last 24 hours
2. For each job, searches Solr using query: `id:{job_id}`
3. If job is found in Solr, validates field matches (title, company_name, etc.)
4. If job is NOT found, marks as "Not Found in Solr" failure

### Why All Jobs Are Failing
When the test searches Solr with `id:{job_id}`, it returns 0 results for all 1998 jobs. This indicates one of these issues:

#### Most Likely Causes:

1. **Wrong Solr Collection Name** ⚠️
   - Test is using: `jnp_jobs_v6`
   - Other code references: `jnp_jobs_v4_1`, `jnp_jobs_v2`
   - Jobs might be in a different collection

2. **Sync Delay** ⏱️
   - Jobs modified in DB may take time to sync to Solr
   - Sync process might be running on a schedule (e.g., every hour)
   - Jobs modified in last 24 hours might not have synced yet

3. **Sync Process Not Running** ❌
   - The sync process from MySQL to Solr might be stopped/failed
   - Need to check if sync service is running

4. **Query Format Issue** 🔍
   - The query `id:{job_id}` might need different format
   - Could need quotes: `id:"{job_id}"`

## Diagnostic Steps

### Step 1: Run Diagnostic Script
```bash
python diagnose_solr_sync.py
```

This will:
- Test multiple Solr collections (v6, v4_1, v2)
- Check if jobs exist in any collection
- Identify which collection has the data
- Provide recommendations

### Step 2: Check Sync Status
- Verify if sync process/service is running
- Check sync logs for errors
- Confirm sync schedule/frequency

### Step 3: Manual Verification
Test a specific job ID manually:
```python
import pysolr
solr = pysolr.Solr("https://solr.jobsnprofiles.com/solr/jnp_jobs_v6/", 
                   auth=("user", "password"))
result = solr.search("id:5995257")  # Use one of the failing job IDs
print(result)
```

## Solutions

### Solution 1: Update Collection Name
If diagnostic shows jobs are in a different collection:
```python
# In test_t1_09_db_solr_sync.py, line 152
solr_url = "https://solr.jobsnprofiles.com/solr/jnp_jobs_v4_1/"  # Change from v6
```

### Solution 2: Adjust Time Window
If sync has delay, check jobs modified longer ago:
```sql
-- In get_db_data() function, line 38
WHERE modified >= NOW() - INTERVAL 2 DAY  -- Increase from 1 DAY
```

### Solution 3: Fix Sync Process
- Restart sync service if stopped
- Fix any sync errors
- Verify sync is working correctly

## Test Improvements Made

1. ✅ Better error messages with diagnostic info
2. ✅ Tests multiple query formats
3. ✅ Verifies Solr connection before testing
4. ✅ Provides failure analysis (Not Found vs Mismatches vs Errors)
5. ✅ Includes diagnostic recommendations in logs

## Next Steps

1. **Run the diagnostic script** to identify which Solr collection has the jobs
2. **Check sync process status** - is it running?
3. **Verify collection name** - update test if needed
4. **Check sync logs** - are there any errors?
5. **Re-run test** after fixes

## Files Modified

- `tests/jobseeker/test_t1_09_db_solr_sync.py` - Enhanced with better diagnostics
- `diagnose_solr_sync.py` - New diagnostic tool
- `SOLR_SYNC_ISSUE_ANALYSIS.md` - This document
