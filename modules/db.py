import pyodbc

def get_conn():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=127.0.0.1;'
        'port=1433;' 
        'DATABASE=Hospital_data;'
        'UID=YLH;'           
        'PWD=YLH;'      
        'TrustServerCertificate=yes;'
    )
