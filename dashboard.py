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

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

PALETA_CAFE = ["#8B5B29", "#FFD39B", "#FFE4C4"]

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
            df['fecha'] = pd.to_datetime(df['fecha'], format='%Y-%m-%d', errors='coerce')
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

df_pred = pd.read_excel("predicciones_365_dias.xlsx")
df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'], dayfirst=True, errors='coerce')

pedidos_reales = obtener_pedidos_reales()

if not pedidos_reales.empty:
    df_pred_renamed = df_pred.rename(columns={'Fecha': 'fecha', 'Kg_Predichos': 'kg_predicho'})
    pedidos_reales_renamed = pedidos_reales.rename(columns={'valor': 'kg_real'})
    df_merged = pd.merge(
        df_pred_renamed,
        pedidos_reales_renamed,
        on='fecha',
        how='left'
    )
else:
    df_merged = df_pred.rename(columns={'Fecha': 'fecha', 'Kg_Predichos': 'kg_predicho'})
    df_merged['kg_real'] = None

st.title("📊 Dashboard Predicción Café")

inventario_reg = obtener_inventario()
inventario_actual = inventario_reg['cantidad_kg'] if inventario_reg else 40.0

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Tabla", "Hist. Predichos", "Heatmap", "Comparativa/Evolución", "Simulación"])

max_dias = len(df_merged)
dias_mostrar = st.slider("Cantidad de predicciones a visualizar:", 1, max_dias, 30)
df_vista = df_merged.head(dias_mostrar).copy()

with tab1:
    st.subheader("Predicciones")
    if 'kg_real' in df_vista.columns and df_vista['kg_real'].notna().any():
        st.dataframe(df_vista[['fecha', 'kg_predicho', 'kg_real']])
    else:
        st.dataframe(df_vista[['fecha', 'kg_predicho']])

with tab2:
    st.subheader("Histograma de Kg Predichos")
    fig, ax = plt.subplots()
    ax.hist(df_vista['kg_predicho'].dropna().astype(float), bins=10, color=PALETA_CAFE[1], edgecolor=PALETA_CAFE[0])
    ax.set_xlabel("Kg Predichos")
    ax.set_ylabel("Frecuencia")
    st.pyplot(fig)

with tab3:
    st.subheader("Heatmap Día vs Mes")
    df_vista_copy = df_vista.copy()
    df_vista_copy['Mes'] = df_vista_copy['fecha'].dt.strftime('%b')
    df_vista_copy['Día'] = df_vista_copy['fecha'].dt.strftime('%A')
    tabla = pd.pivot_table(df_vista_copy, values='kg_predicho', index='Día', columns='Mes', aggfunc='sum')
    if not tabla.empty:
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        sns.heatmap(tabla, cmap="YlOrBr", annot=True, fmt=".1f", ax=ax2)
        st.pyplot(fig2)
    else:
        st.warning("No hay suficientes datos para generar el heatmap")

# -------- TAB 4: COMPARATIVA Y EVOLUCIÓN POR AÑO --------
with tab4:
    st.subheader("Consumo anterior y consumo esperado ")
    # Define meses en inglés (puedes cambiar a español si gustas)
    meses_orden = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    # Preprocesa históricos y predicciones
    pedidos_reales['anio'] = pedidos_reales['fecha'].dt.year
    pedidos_reales['mes'] = pedidos_reales['fecha'].dt.month
    pedidos_reales['mes_lab'] = pedidos_reales['fecha'].dt.strftime('%b')

    df_pred['anio'] = df_pred['Fecha'].dt.year
    df_pred['mes'] = df_pred['Fecha'].dt.month
    df_pred['mes_lab'] = df_pred['Fecha'].dt.strftime('%b')

    pivot_hist = pedidos_reales.pivot_table(index='mes_lab', columns='anio', values='valor', aggfunc='sum').reindex(meses_orden).fillna(0)
    pivot_pred = df_pred.pivot_table(index='mes_lab', columns='anio', values='Kg_Predichos', aggfunc='sum').reindex(meses_orden).fillna(0)

    todos_anios = sorted(list(set(pivot_hist.columns.tolist() + pivot_pred.columns.tolist())))
    
    # Colores y hatched
    color_list_hist = ['#b3c6f7', '#6699ff', '#3366cc', '#003399', '#001147']
    color_list_pred = ['#ffcccc', '#ff6666', '#ff3300', '#cc0000', '#660000']
    borde_rojo_list = ['#ff3333', '#cc0000', '#990000', '#660000', '#330000']

    fig, ax = plt.subplots(figsize=(12,7))
    bar_width = 0.7 / len(todos_anios)
    x = np.arange(len(meses_orden))

    for i, anio in enumerate(todos_anios):
        vals_hist = pivot_hist[anio].values if anio in pivot_hist.columns else np.zeros(len(meses_orden))
        if np.any(vals_hist > 0):
            offset = (i - len(todos_anios)/2)*bar_width
            ax.bar(x+offset, vals_hist, width=bar_width, color=color_list_hist[i%5], alpha=0.87, label=f"Hist {anio}")
    for i, anio in enumerate(todos_anios):
        vals_pred = pivot_pred[anio].values if anio in pivot_pred.columns else np.zeros(len(meses_orden))
        if np.any(vals_pred > 0):
            offset = (i - len(todos_anios)/2)*bar_width
            ax.bar(x+offset, vals_pred, width=bar_width,
                   color=color_list_pred[i%5],
                   edgecolor=borde_rojo_list[i%5],
                   linewidth=1.8,
                   alpha=0.70,
                   label=f'Prev {anio}',
                   hatch='//')

    ax.set_xlabel('Mes')
    ax.set_ylabel('Kg')
    ax.set_xticks(x)
    ax.set_xticklabels(meses_orden, fontsize=10)
    # **Ajuste ticks cada 10 kg**
    max_kgs = int((ax.get_ylim()[1] // 10 + 1) * 10)
    ax.set_yticks(np.arange(0, max_kgs+1, 10))
    ax.legend(fontsize=10)
    ax.grid(True, axis='y', alpha=0.18)
    st.pyplot(fig)


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

st.sidebar.header("⚙️ Control de Inventario")
nuevo_inventario = st.sidebar.number_input("Inventario actual (kg):", 0.0, 10000.0, inventario_actual, step=1.0)
if st.sidebar.button("Actualizar inventario"):
    actualizar_inventario(nuevo_inventario)

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
    st.sidebar.metric("Pedidos cubiertos", dias_stock, delta=f"Hasta {fecha_quiebre.strftime('%d/%m/%Y')}")
    st.sidebar.write("Detalle del consumo proyectado:")
    st.sidebar.dataframe(df_pred.loc[:dias_stock-1, ['Fecha', 'Kg_Predichos']])
