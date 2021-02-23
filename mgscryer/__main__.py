from datetime import datetime
import json
import subprocess
import urllib

import urllib3
import sqlite3

APIBASE="https://www.ebi.ac.uk/metagenomics/api/latest"
BIOME_LINEAGES = ["root:Host-associated:Human", "root:Host-associated:Mammals"]
DATABASE_PATH = "/home/schudoma/mgscryer/sqlite/mgscryer.sqlite"

STUDY_COLUMNS = (
    "id", "bioproject", "accession", "samples_count", "secondary_accession",
    "centre_name", "is_public", "public_release_date", "abstract", "name", 
    "data_origination", "last_update", "status"
)

def check_study_exists(study_id, cursor):
    cmd = "SELECT * FROM study WHERE id = ?;"
    cursor.execute(cmd, (study_id,))
    rows = cursor.fetchall()
    return rows
    
    

def insert_study_record(record, cursor):
    study_id = record["id"]
    attributes = record["attributes"]

    values = (
        record["id"],
        attributes["bioproject"],
        attributes["accession"],
        int(attributes["samples-count"]),
        attributes["secondary-accession"],
        attributes["centre-name"],
        int(attributes["is-public"]),
        attributes["public-release-date"],
        attributes["study-abstract"],
        attributes["study-name"],
        attributes["data-origination"],
        attributes["last-update"],
        0
    )

    existing_record = check_study_exists(study_id, cursor)

    if existing_record:
        existing_record = existing_record[0]
        print("Study {id} is already known".format(id=study_id))
        #message = "Study {id} has an update.".format(id=record["id"])
        #p = subprocess.check_output("echo {message} | mailx -s 'mgscryer-update for {id}' christian.schudoma@embl.de".format(message=message, id=record["id"]), shell=True)
        update_cols, update_vals = list(), list()
        for col, old_value, new_value in zip(STUDY_COLUMNS, existing_record, values):
            if old_value != new_value:
                update_cols.append(col)
                update_vals.append(new_value)
        if update_cols:
            update_ops = ", ".join(["{col} = ?".format(col=col) for col in update_cols])
            cmd = "UPDATE study SET {update_ops} WHERE id = ?;".format(update_ops=update_ops)
            cursor.execute(cmd, update_vals + [study_id])
            return existing_record, values 

    else:
        cmd = "INSERT INTO study VALUES ({value_placeholders})"
        res = cursor.execute(cmd.format(value_placeholders=",".join("?" for f in values)), values)
        for row in res:
            print(row)
        return None, values

    return None, None
        


def process_data_block(n, data, cursor, latest_timestamp):
    print(n, len(data), "records")
    for record in data:
        timestamp = datetime.fromisoformat(record["attributes"]["last-update"])
        if timestamp > latest_timestamp:
            existing_record, updated_record = insert_study_record(record, cursor)
            message = ["Study {id} has an update.".format(id=record["id"])]
            if existing_record:
                message.append("existing record:")
                message.append("\n".join(":".join(item) for item in zip(STUDY_COLUMNS, map(str, existing_record))))
                message.append("updated record:")
                message.append("\n".join(":".join(item) for item in zip(STUDY_COLUMNS, map(str, updated_record))))
            elif updated_record:
                message.append("new record")
                message.append("\n".join(":".join(item) for item in zip(STUDY_COLUMNS, map(str, updated_record))))
            else:
                return True
            message = "\n".join(message)
            print(message)
            # subprocess.check_output("echo {message} | mailx -s 'mgscryer-update for {id}' christian.schudoma@embl.de".format(message=message, id=record["id"]), shell=True)
            
            
        else:
            print("Record has timestamp {}, which is not newer than our latest timestamp {}. Nothing new, aborting.".format(timestamp, latest_timestamp))
            return False
    return True

def get_latest_timestamp(cursor):
    cursor.execute("SELECT MAX(last_update) FROM study")
    rows = cursor.fetchall()
    return datetime.fromisoformat(rows[0][0]) 

def get_mgnify_studies(db):
    http = urllib3.PoolManager()
    conn = sqlite3.connect(db)

    with conn:
        cursor = conn.cursor()
        try:
            latest_timestamp = get_latest_timestamp(cursor)
        except:
            latest_timestamp = datetime(1900,1,1)

        for lineage in BIOME_LINEAGES:
            request_str = "{apibase}/studies?lineage={lineage}&page={page}&page_size=100".format(apibase=APIBASE, lineage=lineage, page="{page}")
            request = http.request("GET", request_str.format(page=1))
            page_data = json.loads(request.data)
            npages = page_data["meta"]["pagination"]["pages"]

            data = page_data
            for page in range(1, npages + 1):
                if page > 1:
                    data = json.loads(http.request("GET", request_str.format(page=page)).data)
                has_unknown_records = process_data_block(page, data["data"], cursor, latest_timestamp)
                if not has_unknown_records:
                    break
            

        
        




def main():


    get_mgnify_studies(DATABASE_PATH)

    pass



if __name__ == "__main__":
    main()
