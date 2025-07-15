import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='password',
    database='db_test'

)

print(conn.is_connected())

cur = conn.cursor()

cur.execute("select version()")
print(cur.fetchone())   

cur.close()
