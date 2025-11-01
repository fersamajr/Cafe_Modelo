import mysql.connector
import os


try:
    conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE"),
            port=int(os.getenv("DB_PORT"))
    )
    print("¡Conexión exitosa con ngrok!")
    conn.close()
except Exception as e:
    print("Error de conexión:", e)
