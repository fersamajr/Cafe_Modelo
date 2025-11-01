import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv 
import mysql.connector
from mysql.connector import Error   

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)
# Utilidad para archivar todo en datos_prueba
def ruta_datos(filename):
    carpeta = 'datos_prueba'
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, filename)
ARCHIVO_USUARIOS = ruta_datos("usuarios.xlsx")

def crear_archivo_usuarios_si_no_existe():
    if not os.path.exists(ARCHIVO_USUARIOS):
        df = pd.DataFrame({
            'usuario': ["proveedor1", "cliente1", "admin"],
            'rol': ["Proveedor", "Cliente", "Proveedor"],
            'contrasena': ["16", "1", "16"]
        })
        df.to_excel(ARCHIVO_USUARIOS, index=False)

def cargar_usuarios_excel():
    crear_archivo_usuarios_si_no_existe()
    return pd.read_excel(ARCHIVO_USUARIOS)

def validar_usuario_y_obtener_rol_excel(nombre_usuario, contrasena):
    usuarios = cargar_usuarios_excel()
    usuarios['usuario'] = usuarios['usuario'].astype(str).str.strip()
    usuarios['contrasena'] = usuarios['contrasena'].astype(str).str.strip()
    usuarios['rol'] = usuarios['rol'].astype(str).str.strip()
    nombre_usuario = str(nombre_usuario).strip()
    contrasena = str(contrasena).strip()
    usuario_row = usuarios[
        (usuarios['usuario'] == nombre_usuario) &
        (usuarios['contrasena'] == contrasena)
    ]
    if not usuario_row.empty:
        return True, usuario_row.iloc[0]['rol']
    return False, None

def intentar_cargar_usuarios_sql():
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE"),
            port=int(os.getenv("DB_PORT"))
        )
        query = "SELECT usuario, rol, contrasena FROM Usuarios;"
        df = pd.read_sql(query, conn)
        conn.close()
        return df, "SQL conectado exitosamente"
    except Exception as e:
        return None, f"SQL falló, motivo: {e}"

def validar_usuario_y_obtener_rol(usuario, contrasena):
    df_sql, sql_reason = intentar_cargar_usuarios_sql()
    if df_sql is not None:
        df_sql['usuario'] = df_sql['usuario'].astype(str).str.strip()
        df_sql['contrasena'] = df_sql['contrasena'].astype(str).str.strip()
        df_sql['rol'] = df_sql['rol'].astype(str).str.strip()
        usuario = str(usuario).strip()
        contrasena = str(contrasena).strip()
        usuario_row = df_sql[
            (df_sql['usuario'] == usuario) &
            (df_sql['contrasena'] == contrasena)
        ]
        if not usuario_row.empty:
            return True, usuario_row.iloc[0]['rol'], "SQL", sql_reason
        else:
            return False, None, "SQL", sql_reason
    # Si falla, usa Excel
    valido, rol = validar_usuario_y_obtener_rol_excel(usuario, contrasena)
    return valido, rol, "Excel", sql_reason

# Inicializar sesión
if "rol" not in st.session_state:
    st.session_state["rol"] = None
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "autenticacion_tipo" not in st.session_state:
    st.session_state["autenticacion_tipo"] = None
if "autenticacion_razon" not in st.session_state:
    st.session_state["autenticacion_razon"] = None

if st.session_state["rol"] is None:
    st.title("🔐 Login (autoconexión SQL o Excel)")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Iniciar Sesión")
        usuario = st.text_input("Nombre de usuario:")
        contrasena = st.text_input("Contrasena:", type="password")

        if st.button("Ingresar"):
            if not usuario or not contrasena:
                st.warning("Completa usuario y contraseña.")
            else:
                valido, rol_encontrado, metodo, razon = validar_usuario_y_obtener_rol(usuario, contrasena)
                if valido:
                    st.session_state["rol"] = rol_encontrado
                    st.session_state["usuario"] = usuario
                    st.session_state["autenticacion_tipo"] = metodo
                    st.session_state["autenticacion_razon"] = razon
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos. Verifica tus datos.")

    with col2:
        st.info(
            "Usuarios prueba (Excel):\n"
            "- proveedor1 | 16 (Proveedor)\n"
            "- cliente1   | 1  (Cliente)\n"
            "- admin      | 16 (Proveedor)"
        )

else:
    rol = st.session_state["rol"]
    usuario = st.session_state["usuario"]
    metodo = st.session_state["autenticacion_tipo"]
    razon = st.session_state["autenticacion_razon"]

    if rol.lower() == "proveedor":
        st.header(f"Hola, {usuario} 👋")
        st.write(f"**Método de autenticación:** {metodo}")
        st.write(f"**Razón:** {razon}")
    elif rol.lower() == "cliente":
        st.header("🙂")
    else:
        st.warning("Rol no reconocido.")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["rol"] = None
        st.session_state["usuario"] = None
        st.session_state["autenticacion_tipo"] = None
        st.session_state["autenticacion_razon"] = None
        st.experimental_rerun()
