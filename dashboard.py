import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import mysql.connector
import datetime
from joblib import load

# ========= MODELO Y DATOS DE PREDICCIÓN =========
modelo = load('modelo_cafe_pipeline.pkl')
df_pred = pd.read_excel('predicciones_365_dias.xlsx')
df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'])  # ← Esta línea es clave

# ================= SQL pedidos reales ==================
def obtener_pedidos_reales():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Fp$c0105",
        database="Cafe"
    )
    query = "SELECT fecha, valor FROM pedidos ORDER BY fecha"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ================= SQL inventario ==================
def obtener_inventario():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Fp$c0105",
        database="Cafe"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventario WHERE producto='cafe' ORDER BY fecha_actualizacion DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def actualizar_inventario(nueva_cantidad):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Fp$c0105",
        database="Cafe"
    )
    cursor = conn.cursor()
    cursor.execute("UPDATE inventario SET cantidad_kg=%s, fecha_actualizacion=NOW() WHERE producto='cafe'", (nueva_cantidad,))
    conn.commit()
    conn.close()

# ========= UNIR DATOS y PALETA =========
PALETA_CAFE = ["#8B5B29", "#FFD39B", "#FFE4C4"]  # Predicción, Real, fondo

pedidos_reales = obtener_pedidos_reales()
pedidos_reales['fecha'] = pd.to_datetime(pedidos_reales['fecha'])

df_merged = pd.merge(
    df_pred.rename(columns={'Fecha':'fecha', 'Kg_Predichos':'kg_predicho'}),
    pedidos_reales.rename(columns={'valor':'kg_real'}),
    on='fecha', how='left'
)

# ============ DASHBOARD =====================
st.title("Dashboard Predicción Café")

inventario_reg = obtener_inventario()
inventario_actual = inventario_reg['cantidad_kg'] if inventario_reg else 40.0

# =========== TABLAS Y GRÁFICOS PRINCIPALES ===========
tab1, tab2, tab3, tab4, tab5= st.tabs(["Tabla", "Hist. Predichos", "Heatmap Predichos", "Comparativa Real vs Predicción","Comparar dos rangos de fechas"])

max_dias = len(df_merged)
dias_mostrar = st.slider('Cantidad de predicciones a visualizar:', min_value=1, max_value=max_dias, value=30)
df_vista = df_merged.head(dias_mostrar)

# --- Tab1: Predicciones completas ---
with tab1:
    st.subheader("Predicciones y pedidos reales")
    st.dataframe(df_vista[['fecha', 'kg_predicho', 'kg_real']])

# --- Tab2: Histograma predichos ---
with tab2:
    st.subheader("Histograma de Kg Predichos")
    fig, ax = plt.subplots()
    ax.hist(df_vista['kg_predicho'].dropna(), bins=10, color=PALETA_CAFE[1], edgecolor=PALETA_CAFE[0])
    st.pyplot(fig)

# --- Tab3: Heatmap predichos ---
with tab3:
    st.subheader("Heatmap Día vs Mes (Kg Predichos)")
    df_vista['Mes'] = df_vista['fecha'].dt.strftime('%b')
    df_vista['DiaSemana'] = df_vista['fecha'].dt.strftime('%A')
    tabla = pd.pivot_table(df_vista, values='kg_predicho', index='DiaSemana', columns='Mes', aggfunc='sum')
    fig2, ax2 = plt.subplots()
    sns.heatmap(tabla, cmap="YlOrBr", annot=True, fmt='.1f', ax=ax2)
    st.pyplot(fig2)

# --- Tab4: Gráfica comparativa real vs predicción ---
with tab4:
    st.subheader("Consumo Real vs Predicción (Paleta tonos café)")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_merged['fecha'], df_merged['kg_predicho'], label='Predicción', color=PALETA_CAFE[0], linewidth=2)
    ax.plot(df_merged['fecha'], df_merged['kg_real'], label='Real', color=PALETA_CAFE[1], linestyle='--', linewidth=2)
    ax.fill_between(df_merged['fecha'], df_merged['kg_predicho'], df_merged['kg_real'], color=PALETA_CAFE[2], alpha=0.3)
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Kg')
    ax.legend()
    st.pyplot(fig)

# --- Tab5:  Comparar dos rangos de fechas ---
with tab5:
    st.header("Simula el consumo necesario hasta una fecha objetivo")

    df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'])
    fecha_min, fecha_max = df_pred['Fecha'].min().date(), df_pred['Fecha'].max().date()
    hoy = datetime.date.today()
    # ...
    if hoy not in set(df_pred['Fecha'].dt.date):
        fecha_inicio = hoy
    else:
        fecha_inicio = hoy
    # ...


    # Entrada para la fecha final objetivo (default 4 semanas desde hoy, ajustable)
    fecha_final = st.date_input(
        "Selecciona la fecha límite de tu simulación",
        value=(fecha_inicio + datetime.timedelta(weeks=4)),
        min_value=fecha_inicio,
        max_value=fecha_max
    )

    # Filtro de pedidos entre HOY y la fecha elegida (incluye hoy, excluye final)
    mask = (df_pred['Fecha'].dt.date >= fecha_inicio) & (df_pred['Fecha'].dt.date <= fecha_final)
    consumo_periodo = df_pred.loc[mask, 'Kg_Predichos'].sum()

    inventario_reg = obtener_inventario()
    inventario_actual = inventario_reg['cantidad_kg'] if inventario_reg else 40.0
    compra_necesaria = max(0, consumo_periodo - inventario_actual)

    st.markdown(
        f"""<b>Tu periodo:</b> {fecha_inicio.strftime('%d/%m/%Y')} → {fecha_final.strftime('%d/%m/%Y')}  
        <br>Consumo estimado: <b>{consumo_periodo:.1f} kg</b>  
        <br>Inventario actual: <b>{inventario_actual:.1f} kg</b>  
        <br><b>Kilos que necesitas comprar:</b> <span style='color:orange'>{compra_necesaria:.1f} kg</span>""",
        unsafe_allow_html=True
    )

    st.dataframe(df_pred.loc[mask, ['Fecha', 'Kg_Predichos']].reset_index(drop=True))

# ================== LÓGICA DE STREAMLIT =====================
st.title("Dashboard Predicción Café")

# Consulta de inventario inicial de la base
inventario_reg = obtener_inventario()
inventario_actual = inventario_reg['cantidad_kg'] if inventario_reg else 40.0

st.sidebar.header("Inventario de la Base de Datos")
nuevo_inventario = st.sidebar.number_input("Inventario actual (kg):", min_value=0.0, value=inventario_actual, step=1.0)
if st.sidebar.button("Actualizar inventario en BD"):
    actualizar_inventario(nuevo_inventario)
    st.sidebar.success("Inventario actualizado en la base de datos. Refresca la página para ver cambios.")

st.sidebar.write(f"Inventario real en BD: **{nuevo_inventario:.1f} kg**")

# Calcula días de stock según el inventario real de BD y predicción diaria
sum_kg = 0
dias_stock = 0
fecha_quiebre = None
for idx, row in df_pred.iterrows():
    if sum_kg < nuevo_inventario:
        sum_kg += row['Kg_Predichos']
        dias_stock += 1
        fecha_quiebre = row['Fecha'] 
    else:
        break
# ----------- ALERTA bajo inventario ----------
hoy = pd.to_datetime(datetime.date.today())
prox_prediccion = df_merged[df_merged['fecha'] >= hoy]['kg_predicho'].iloc[0]  # Próximo pedido predicho

if nuevo_inventario < prox_prediccion:
    st.sidebar.error(f"⚠️ Inventario insuficiente: solo {nuevo_inventario:.1f} kg, no cubre el siguiente pedido de {prox_prediccion:.1f} kg.")
else:
    st.sidebar.success(f"Inventario OK: {nuevo_inventario:.1f} kg. Cubre el siguiente pedido de {prox_prediccion:.1f} kg.")
    if fecha_quiebre is not None:
        st.sidebar.info(
            f"Tienes café para: **{dias_stock} pedidos** y hasta el {fecha_quiebre.strftime('%d/%m/%Y')} según el modelo."
        )
    else:
        st.sidebar.warning("Inventario insuficiente para siquiera un día de predicción.")

    st.sidebar.subheader("Detalle consumo hasta quiebre de inventario")
    st.sidebar.dataframe(df_pred.loc[:dias_stock-1][['Fecha','Kg_Predichos']])
