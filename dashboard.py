import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import openpyxl
import datetime
import os

# ============== SEGURIDAD: variables de entorno ==============
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

PALETA_CAFE = ["#8B5B29", "#FFD39B", "#FFE4C4"]

# ================= FUNCIONES SQL SEGURAS =====================
def get_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE"),
            port=int(os.getenv("DB_PORT"))
        )
    except Error as e:
        st.error(f"❌ Error al conectar con la base de datos: {e}")
        return None

def obtener_pedidos_reales():
    conn = get_connection()
    if conn:
        try:
            query = "SELECT fecha, valor FROM pedidos ORDER BY fecha;"
            df = pd.read_sql(query, conn)
            conn.close()
            df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True)
            return df
        except Error as e:
            st.error(f"⚠️ Error al obtener pedidos: {e}")
    return pd.DataFrame(columns=["fecha", "valor"])

def obtener_inventario():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM inventario WHERE producto='cafe' ORDER BY fecha_actualizacion DESC LIMIT 1;")
            row = cursor.fetchone()
            conn.close()
            return row
        except Error as e:
            st.error(f"⚠️ Error al consultar inventario: {e}")
    return None

def actualizar_inventario(nueva_cantidad):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE inventario SET cantidad_kg=%s, fecha_actualizacion=NOW() WHERE producto='cafe';", (nueva_cantidad,))
            conn.commit()
            conn.close()
            st.sidebar.success("✅ Inventario actualizado correctamente.")
        except Error as e:
            st.sidebar.error(f"❌ Fallo al actualizar inventario: {e}")

# ================= CARGA SEGURA DE PREDICCIONES ===================
df_pred = pd.read_excel("predicciones_365_dias.xlsx")
# Asegura formato correcto y días primarios (verifica si es %d/%m/%Y)
df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'], dayfirst=True)

pedidos_reales = obtener_pedidos_reales()

# ============== UNIFICACIÓN DE DATAFRAMES =============
df_merged = pd.merge(
    df_pred.rename(columns={'Fecha': 'fecha', 'Kg_Predichos': 'kg_predicho'}),
    pedidos_reales.rename(columns={'valor': 'kg_real'}) if not pedidos_reales.empty else pedidos_reales,
    on='fecha',
    how='left'
)

# ============ STREAMLIT DASHBOARD ============
st.title("📊 Dashboard Predicción Café")

inventario_reg = obtener_inventario()
inventario_actual = inventario_reg['cantidad_kg'] if inventario_reg else 40.0

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Tabla", "Hist. Predichos", "Heatmap", "Comparativa", "Simulación"])

max_dias = len(df_merged)
dias_mostrar = st.slider("Cantidad de predicciones a visualizar:", 1, max_dias, 30)
df_vista = df_merged.head(dias_mostrar).copy()  # Evita el warning de SettingWithCopy

# --- TAB 1: TABLA ---
with tab1:
    st.subheader("Predicciones y pedidos reales")
    st.dataframe(df_vista[['fecha', 'kg_predicho', 'kg_real']])

# --- TAB 2: HISTOGRAMA ---
with tab2:
    st.subheader("Histograma de Kg Predichos")
    fig, ax = plt.subplots()
    ax.hist(df_vista['kg_predicho'].dropna().astype(float), bins=10, color=PALETA_CAFE[1], edgecolor=PALETA_CAFE[0])
    st.pyplot(fig)

# --- TAB 3: HEATMAP ---
with tab3:
    st.subheader("Heatmap Día vs Mes")
    df_vista['Mes'] = df_vista['fecha'].dt.strftime('%b')
    df_vista['Día'] = df_vista['fecha'].dt.strftime('%A')
    tabla = pd.pivot_table(df_vista, values='kg_predicho', index='Día', columns='Mes', aggfunc='sum')
    fig2, ax2 = plt.subplots()
    sns.heatmap(tabla, cmap="YlOrBr", annot=True, fmt=".1f", ax=ax2)
    st.pyplot(fig2)

# --- TAB 4: COMPARATIVA ---
with tab4:
    st.subheader("Consumo Real vs Predicción")
    # Asegura columnas numéricas y sin NaN
    mask = df_merged['kg_predicho'].notnull() & df_merged['kg_real'].notnull()
    df_plot = df_merged[mask].copy()
    df_plot['kg_predicho'] = df_plot['kg_predicho'].astype(float)
    df_plot['kg_real'] = df_plot['kg_real'].astype(float)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_plot['fecha'], df_plot['kg_predicho'], label="Predicción", color=PALETA_CAFE[0], linewidth=2)
    ax.plot(df_plot['fecha'], df_plot['kg_real'], label="Real", color=PALETA_CAFE[1], linestyle="--", linewidth=2)
    ax.fill_between(df_plot['fecha'], df_plot['kg_predicho'], df_plot['kg_real'], color=PALETA_CAFE[2], alpha=0.3)
    ax.legend()
    st.pyplot(fig)

# --- TAB 5: SIMULACIÓN ---
with tab5:
    st.header("📅 Simula el consumo hasta una fecha")
    fecha_min, fecha_max = df_pred['Fecha'].min().date(), df_pred['Fecha'].max().date()
    hoy = datetime.date.today()
    fecha_inicio = hoy
    fecha_final = st.date_input("Selecciona la fecha límite", value=hoy + datetime.timedelta(weeks=4),
                                min_value=fecha_inicio, max_value=fecha_max)

    mask_pred = (df_pred['Fecha'].dt.date >= fecha_inicio) & (df_pred['Fecha'].dt.date <= fecha_final)
    consumo_periodo = df_pred.loc[mask_pred, 'Kg_Predichos'].astype(float).sum()
    compra_necesaria = max(0, consumo_periodo - inventario_actual)

    st.markdown(f"""
    **Periodo:** {fecha_inicio.strftime('%d/%m/%Y')} → {fecha_final.strftime('%d/%m/%Y')}  
    **Consumo estimado:** {consumo_periodo:.1f} kg  
    **Inventario actual:** {inventario_actual:.1f} kg  
    **Compra necesaria:** 🟠 {compra_necesaria:.1f} kg
    """)
    st.dataframe(df_pred.loc[mask_pred, ['Fecha', 'Kg_Predichos']].reset_index(drop=True))

# ================= SIDEBAR: CONTROL DE INVENTARIO =================
st.sidebar.header("⚙️ Control de Inventario")
nuevo_inventario = st.sidebar.number_input("Inventario actual (kg):", 0.0, 10000.0, inventario_actual, step=1.0)
if st.sidebar.button("Actualizar inventario"):
    actualizar_inventario(nuevo_inventario)

# Calcular cobertura de stock
sum_kg, dias_stock, fecha_quiebre = 0, 0, None
for idx, row in df_pred.iterrows():
    if sum_kg < nuevo_inventario:
        sum_kg += float(row['Kg_Predichos'])
        dias_stock += 1
        fecha_quiebre = row['Fecha']
    else:
        break

hoy = pd.to_datetime(datetime.date.today())
prox_pred = df_merged[df_merged['fecha'] >= hoy]
prox_prediccion = prox_pred['kg_predicho'].iloc[0] if not prox_pred.empty else 0.0

if nuevo_inventario < float(prox_prediccion):
    st.sidebar.error(f"⚠️ Inventario insuficiente ({nuevo_inventario:.1f} kg). No cubre el siguiente pedido ({prox_prediccion:.1f} kg).")
else:
    st.sidebar.success(f"Inven. OK: {nuevo_inventario:.1f} kg. Cubre hasta el {fecha_quiebre.strftime('%d/%m/%Y')}")
    st.sidebar.metric("Días cubiertos", dias_stock, delta=f"Hasta {fecha_quiebre.strftime('%d/%m/%Y')}")
    st.sidebar.write("Detalle del consumo proyectado:")
    st.sidebar.dataframe(df_pred.loc[:dias_stock-1, ['Fecha', 'Kg_Predichos']])
