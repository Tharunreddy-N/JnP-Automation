import mysql.connector
import json

def get_secret_keys():
    try:
        # Connect to the Secrets Database
        mysql_secret_keys_connection = mysql.connector.connect(
            host="65.109.71.75",
            username="pyth_db_cred",
            password="6HzXou8t?973g@768n",
            database="pyth_db_cred",
        )
        
        cursor = mysql_secret_keys_connection.cursor()
        get_cred = "SELECT id,name,data,status,source FROM pyth_db_cred.jnp_credentials"
        cursor.execute(get_cred)
        
        # Parse the results
        get_cred_json = {element[0]: [element[1], element[2], element[3], element[4]] for element in cursor.fetchall()}
        
        cred_json = {
            "open_ai_keys": [],
            "mysql_cred": "",
            "solr_jobs": "",
            "apollo_keys": [],
            "solr_cred": "",
            "solr_bench": "",
            "solr_resumes": ""
        }

        for element, vals in get_cred_json.items():
            if 'mysql_prod' in vals[0]:
                cred_json['mysql_cred'] = json.loads(vals[1])
            elif 'solr_jobs' in vals[0]:
                cred_json['solr_jobs'] = vals[1]
            elif 'openai' in vals[0] and 'scraping' in vals[3] and vals[2] == 1:
                cred_json['open_ai_keys'].append(vals[1])
            elif 'apollo' in vals[0]:
                cred_json['apollo_keys'].append(vals[1])
            elif 'solr_account' in vals[0]:
                cred_json['solr_cred'] = json.loads(vals[1])
            elif 'solr_bench' in vals[0]:
                cred_json['solr_bench'] = vals[1]
            elif 'mysql_reports' in vals[0]:
                cred_json['mysql_reports'] = json.loads(vals[1])
            elif 'solr_resumes' in vals[0]:
                cred_json['solr_resumes'] = vals[1]

        if mysql_secret_keys_connection.is_connected():
            cursor.close()
            mysql_secret_keys_connection.close()

        return cred_json

    except Exception as e:
        print(f"Error fetching secret keys: {e}")
        return None

def connections():
    return get_secret_keys()
