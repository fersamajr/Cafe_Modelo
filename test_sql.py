import mysql.connector

try:
    conn = mysql.connector.connect(
        host="0.tcp.us-cal-1.ngrok.io",
        port=112240,
        user="root",
        password="Fp$c0105",
        database="Cafe"   # o el nombre real
    )
    print("¡Conexión exitosa con ngrok!")
    conn.close()
except Exception as e:
    print("Error de conexión:", e)
