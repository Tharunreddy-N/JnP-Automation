"""
Database helper functions for BenchSale tests
Converted from jnp_bs.py
"""
import mysql.connector
from typing import Optional


def delete_bs_user_from_db(bs_user: str) -> str:
    """
    Delete benchsale user from database
    Need to delete from 2 tables: 
    i. jnp_bench_2024.jnp_users 
    ii. jnp_bench_2024.jnp_bench_recruiters
    """
    conn = mysql.connector.connect(
        host="65.109.17.58",
        user="jnp_prod_user",
        password="?Jf03r0d7",
        database="jnp_bench_2024"
    )
    cursor = conn.cursor()
    
    sql_bs_in_user = "Delete FROM jnp_bench_2024.jnp_users where username = %s"
    sql_bs_in_recruiter = "Delete FROM jnp_bench_2024.jnp_bench_recruiters where email = %s"
    params = (bs_user,)
    
    user_rowcount = 0
    recruiter_rowcount = 0
    
    try:
        cursor.execute(sql_bs_in_user, params)
        user_rowcount = cursor.rowcount
        if user_rowcount == 1:
            conn.commit()
    except mysql.connector.Error as err:
        return f"Error in deleting New Bench Sale user from 'jnp_bench_2024.jnp_users' with email {bs_user}: {err}"
    
    try:
        cursor.execute(sql_bs_in_recruiter, params)
        recruiter_rowcount = cursor.rowcount
        conn.commit()
    except mysql.connector.Error as err:
        return f"Error in deleting New Bench Sale user from 'jnp_bench_2024.jnp_bench_recruiters' with email {bs_user}: {err}"
    finally:
        cursor.close()
        conn.close()
    
    return f"{user_rowcount} Row deleted from 'jnp_bench_2024.jnp_users' and {recruiter_rowcount} Row deleted from 'jnp_bench_2024.jnp_bench_recruiters' successfully with mail id: {bs_user}"


def delete_bs_candidate_from_db(candidate_email: str) -> str:
    """
    Delete benchsale candidate from database
    Need to delete from 2 tables:
    i. jnp_bench_2024.jnp_users
    ii. jnp_bench_2024.jnp_candidates
    """
    conn = mysql.connector.connect(
        host="65.109.17.58",
        user="jnp_prod_user",
        password="Rwmx13Uh3o&n380$56",
        database="jnp_bench_2024"
    )
    cursor = conn.cursor()
    
    sql_bs_in_user = "Delete FROM jnp_bench_2024.jnp_users where username = %s"
    sql_bs_in_candidate = "Delete FROM jnp_bench_2024.jnp_candidates where email = %s"
    params = (candidate_email,)
    
    user_rowcount = 0
    candidate_rowcount = 0
    
    try:
        cursor.execute(sql_bs_in_user, params)
        user_rowcount = cursor.rowcount
        if user_rowcount == 1:
            conn.commit()
    except mysql.connector.Error as err:
        return f"Error in deleting candidate from 'jnp_bench_2024.jnp_users' with email {candidate_email}: {err}"
    
    try:
        cursor.execute(sql_bs_in_candidate, params)
        candidate_rowcount = cursor.rowcount
        if candidate_rowcount == 1:
            conn.commit()
    except mysql.connector.Error as err:
        return f"Error in deleting candidate from 'jnp_bench_2024.jnp_candidates' with email {candidate_email}: {err}"
    finally:
        cursor.close()
        conn.close()
    
    return f"{user_rowcount} Row deleted from 'jnp_bench_2024.jnp_users' and {candidate_rowcount} Row deleted from 'jnp_bench_2024.jnp_candidates' successfully with mail id: {candidate_email}"

