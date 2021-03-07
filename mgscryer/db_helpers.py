DEBUG = False

def check_link_exists(cursor, table, field1, field2, id1, id2):
    cmd = "SELECT * FROM {table} WHERE {field1} = ? AND {field2} = ?;".format(
        table=table, entity1=entity1, entity2=entity2)
    cursor.execute(cmd, (id1, id2))
    rows = cursor.fetchall()
    return rows

# https://stackoverflow.com/questions/7831371/is-there-a-way-to-get-a-list-of-column-names-in-sqlite
def check_record_exists(cursor, table, id_):
    cmd = "SELECT * FROM {table} WHERE {table}_accession = ?;".format(table=table)
    cursor.execute(cmd, (id_,))
    rows = cursor.fetchall()
    if rows:
        return zip([d[0] for d in cursor.description], rows[0])
    return list()

def check_link_exists(cursor, table1, table2, id1, id2):
    cmd = f"SELECT * FROM {table1}_{table2} WHERE {table1}_accession = ? AND {table2}_accession = ?;"
    cursor.execute(cmd, (id1, id2))
    rows = cursor.fetchall()
    if rows:
        return zip([d[0] for d in cursor.description], rows[0])
    return list()


def insert_record(cursor, table, values):
    cmd = "INSERT INTO {table} VALUES ({dummy})".format(
        table=table, dummy=",".join("?" for f in values))
    res = cursor.execute(cmd, values)
    if DEBUG:
        for row in res:
            print(row)

def get_latest_timestamp(cursor):
    try:
        cursor.execute("SELECT MAX(ena_last_update) FROM study;")
        rows = cursor.fetchall()
        return datetime.fromisoformat(rows[0][0])
    except:
        return datetime(1970, 1, 1)

def update_record(cursor, table, _id, updates):
    update_ops = ", ".join(["{col} = ?".format(col=col) for col, _ in updates])
    cmd = "UPDATE {table} SET {update_ops} WHERE {table}_accession = ?;".format(table=table, update_ops=update_ops)
    if DEBUG:
        print(cmd)
    res = cursor.execute(cmd, [val for _, val in updates] + [_id])
    if DEBUG:
        for row in res:
            print(row)
