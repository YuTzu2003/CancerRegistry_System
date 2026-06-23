import pyodbc
import os

def get_conn():
    server = os.environ.get("DB_SERVER")
    port = os.environ.get("DB_PORT")
    database = os.environ.get("DB_NAME")
    uid = os.environ.get("DB_USER")
    pwd = os.environ.get("DB_PASSWORD")

    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        f'SERVER={server};'
        f'port={port};' 
        f'DATABASE={database};'
        f'UID={uid};'           
        f'PWD={pwd};'      
        'TrustServerCertificate=yes;')