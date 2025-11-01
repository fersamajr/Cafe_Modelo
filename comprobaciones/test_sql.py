import mysql.connector
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
import pandas as pd

MYSQL_USER = os.getenv("DB_USER")
MYSQL_PASS = os.getenv("DB_PASSWORD")
MYSQL_HOST = os.getenv("DB_HOST")
MYSQL_DB = os.getenv("DB_DATABASE")
MYSQL_PORT = int(os.getenv("DB_PORT"))

try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE"),
        port=int(os.getenv("DB_PORT"))
    )
    print("¡Conexión exitosa con ngrok!")

    cursor = conn.cursor()
    consulta = "SELECT usuario, rol FROM Usuarios LIMIT 5;"
    cursor.execute(consulta)
    resultados = cursor.fetchall()

    print("Usuarios en la base de datos:")
    for fila in resultados:
        print(f"Usuario: {fila[0]}, Rol: {fila[1]}")

    cursor.close()
    conn.close()
except Exception as e:
    print("Error de conexión:", e)
    print("Revisa tu archivo .env para asegurarte de que las variables de entorno estén configuradas correctamente.")

def get_connection():
    """Establece una conexión a la base de datos MySQL utilizando SQLAlchemy."""
    try:
        ENGINE =create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")
        # Probar la conexión para asegurarnos de que los parámetros son correctos y la base de datos es accesible
        return ENGINE
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None
ENGINE = get_connection()
def cargar_todos_pedidos():
    """Carga todos los pedidos básicos"""
    query = "SELECT cliente_id, producto, cantidad, detalle, fecha FROM pedidos_cliente"
    return pd.read_sql(query, ENGINE)
a = cargar_todos_pedidos()
print(a)