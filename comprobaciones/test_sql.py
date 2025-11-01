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