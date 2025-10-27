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

# ============== CONFIGURACIÓN INICIAL ==============
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

PALETA_CAFE = ["#8B5B29", "#FFD39B", "#FFE4C4"]

# ============== FUNCIONES DE BASE DE DATOS ==============
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

def obtener_pedidos_reales(producto='cafe'):
    conn = get_connection()
    if conn:
        try:
            query = f"SELECT fecha, valor FROM pedidos WHERE producto='{producto}' ORDER BY fecha;"
            df = pd.read_sql(query, conn)
            conn.close()
            df['fecha'] = pd.to_datetime(df['fecha'], format='%Y-%m-%d', errors='coerce')
            return df
        except Error as e:
            st.error(f"⚠️ Error al obtener pedidos: {e}")
    return pd.DataFrame(columns=["fecha", "valor"])

def obtener_inventario(producto='cafe'):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM inventario WHERE producto='{producto}' ORDER BY fecha_actualizacion DESC LIMIT 1;")
            row = cursor.fetchone()
            conn.close()
            return row
        except Error as e:
            st.error(f"⚠️ Error al consultar inventario: {e}")
    return None

def actualizar_inventario_con_historial(producto, cantidad_nueva, usuario):
    inv_actual = obtener_inventario(producto)
    cantidad_antes = inv_actual['cantidad_kg'] if inv_actual else 0.0
    
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Actualizar inventario principal
            cursor.execute("UPDATE inventario SET cantidad_kg=%s, fecha_actualizacion=NOW() WHERE producto=%s;", 
                          (cantidad_nueva, producto))
            # Guardar en control_inventario
            cursor.execute(
                "INSERT INTO control_inventario (producto, cantidad_antes, cantidad_despues, fecha_cambio, usuario) "
                "VALUES (%s, %s, %s, NOW(), %s)",
                (producto, cantidad_antes, cantidad_nueva, usuario)
            )
            conn.commit()
            conn.close()
            st.sidebar.success("✅ Inventario actualizado y registrado en historial.")
        except Error as e:
            st.sidebar.error(f"❌ Error al actualizar inventario: {e}")

def agregar_pedido_cliente(cliente, producto, cantidad, detalle):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pedidos_cliente (cliente_id, producto, cantidad, detalle, fecha) VALUES (%s, %s, %s, %s, NOW())",
                (cliente, producto, cantidad, detalle)
            )
            conn.commit()
            conn.close()
            st.success(f"✅ Pedido guardado: {producto} ({cantidad}) - {detalle}")
        except Error as e:
            st.error(f"❌ Error al guardar pedido: {e}")

def obtener_productos_disponibles():
    """Obtiene lista de productos que tienen predicciones disponibles"""
    try:
        # Aquí verificarías qué productos tienen archivos de predicción o datos
        productos_con_prediccion = ['cafe']  # Por ahora solo café tiene predicción
        productos_sin_prediccion = ['azucar', 'leche', 'otro']
        return productos_con_prediccion, productos_sin_prediccion
    except:
        return ['cafe'], ['azucar', 'leche', 'otro']

# ============== SISTEMA DE LOGIN (PUNTO 1) ==============
if "rol" not in st.session_state:
    st.session_state["rol"] = None
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

if st.session_state["rol"] is None:
    st.title("🔐 Sistema de Predicción y Pedidos")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Iniciar Sesión")
        rol = st.selectbox("Selecciona tu rol:", ["Selecciona...", "Proveedor", "Cliente"])
        usuario = st.text_input("Nombre de usuario:")
        
        if st.button("Ingresar") and rol != "Selecciona..." and usuario:
            st.session_state["rol"] = rol
            st.session_state["usuario"] = usuario
            st.experimental_rerun()
    
    with col2:
        st.info("**Proveedor**: Acceso completo al sistema\n\n**Cliente**: Solo tu información y pedidos")

else:
    rol = st.session_state["rol"]
    usuario = st.session_state["usuario"]
    
    # Botón de logout
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["rol"] = None
        st.session_state["usuario"] = None
        st.experimental_rerun()

    # ============== VISTA CLIENTE (PUNTOS 2, 3, 6) ==============
    if rol == "Cliente":
        st.sidebar.success(f"👤 Cliente: {usuario}")
        st.title(f"👋 Bienvenido {usuario}")
        
        # PUNTO 2: Sistema de múltiples productos
        st.subheader("📋 Nuevo Pedido")
        col1, col2 = st.columns(2)
        
        with col1:
            producto_sel = st.selectbox("Producto:", ["cafe", "azucar", "leche", "otro"])
            cantidad = st.number_input("Cantidad total:", 0.0, 10000.0, step=1.0)
            
        with col2:
            detalle = st.text_area("Desglose/Detalle:", placeholder="Ej: 5kg molido, 4kg grano")
            
        if st.button("🛒 Agregar Pedido"):
            if cantidad > 0:
                agregar_pedido_cliente(usuario, producto_sel, cantidad, detalle)
        
        # Mostrar historial del cliente
        conn = get_connection()
        if conn:
            try:
                df_cliente = pd.read_sql(f"SELECT * FROM pedidos_cliente WHERE cliente_id='{usuario}' ORDER BY fecha DESC", conn)
                if not df_cliente.empty:
                    st.subheader("📈 Tu Historial de Pedidos")
                    st.dataframe(df_cliente)
                    
                    # Gráfico simple para el cliente
                    if len(df_cliente) > 1:
                        fig, ax = plt.subplots(figsize=(10, 4))
                        df_cliente['fecha'] = pd.to_datetime(df_cliente['fecha'])
                        ax.plot(df_cliente['fecha'], df_cliente['cantidad'], marker='o', color=PALETA_CAFE[0])
                        ax.set_title("Evolución de tus pedidos")
                        ax.set_xlabel("Fecha")
                        ax.set_ylabel("Cantidad (kg)")
                        st.pyplot(fig)
                conn.close()
            except Error as e:
                st.error(f"Error al consultar historial: {e}")

    # ============== VISTA PROVEEDOR (PUNTOS 3, 4, 5, 7) ==============
    elif rol == "Proveedor":
        st.sidebar.success(f"🔧 Proveedor: {usuario}")
        st.title("📊 Dashboard Completo - Modo Proveedor")
        
        # PUNTO 4: Selector de producto dinámico
        productos_con_pred, productos_sin_pred = obtener_productos_disponibles()
        producto_sel = st.selectbox("🎯 Producto a analizar:", productos_con_pred + productos_sin_pred)
        
        tiene_prediccion = producto_sel in productos_con_pred
        
        if tiene_prediccion:
            # Cargar datos de predicción (solo para productos que la tienen)
            try:
                if producto_sel == 'cafe':
                    df_pred = pd.read_excel("predicciones_365_dias.xlsx")
                    df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'], dayfirst=True, errors='coerce')
                else:
                    df_pred = pd.DataFrame()  # Para otros productos sin predicción aún
            except:
                df_pred = pd.DataFrame()
                st.warning(f"No se encontró archivo de predicción para {producto_sel}")
        else:
            df_pred = pd.DataFrame()
        
        # Obtener datos reales del producto seleccionado
        pedidos_reales = obtener_pedidos_reales(producto_sel)
        
        # Merge de datos
        if not df_pred.empty and not pedidos_reales.empty:
            df_pred_renamed = df_pred.rename(columns={'Fecha': 'fecha', 'Kg_Predichos': 'kg_predicho'})
            pedidos_reales_renamed = pedidos_reales.rename(columns={'valor': 'kg_real'})
            df_merged = pd.merge(df_pred_renamed, pedidos_reales_renamed, on='fecha', how='left')
        elif not df_pred.empty:
            df_merged = df_pred.rename(columns={'Fecha': 'fecha', 'Kg_Predichos': 'kg_predicho'})
            df_merged['kg_real'] = None
        else:
            df_merged = pedidos_reales.rename(columns={'valor': 'kg_real'}) if not pedidos_reales.empty else pd.DataFrame()
        
        # TABS dinámicos según disponibilidad de predicción
        if tiene_prediccion and not df_merged.empty:
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "📋 Tabla", "📊 Histograma", "🔥 Heatmap", 
                "📈 Comparativa", "🎯 Simulación", "✅ Verificación"
            ])
        else:
            tab1, tab2, tab6 = st.tabs(["📋 Datos", "📊 Resumen", "⚙️ Gestión"])
        
        # ============== TAB 1: TABLA ==============
        with tab1:
            st.subheader(f"Datos de {producto_sel}")
            if not df_merged.empty:
                max_dias = len(df_merged)
                dias_mostrar = st.slider("Días a mostrar:", 1, max_dias, min(30, max_dias))
                df_vista = df_merged.head(dias_mostrar)
                st.dataframe(df_vista)
            else:
                st.warning(f"No hay datos disponibles para {producto_sel}")
        
        # ============== TAB 2: HISTOGRAMA ==============
        with tab2:
            st.subheader(f"Distribución - {producto_sel}")
            if not df_merged.empty and 'kg_predicho' in df_merged.columns:
                fig, ax = plt.subplots()
                ax.hist(df_merged['kg_predicho'].dropna(), bins=10, color=PALETA_CAFE[1], edgecolor=PALETA_CAFE[0])
                ax.set_xlabel("Kg Predichos")
                ax.set_ylabel("Frecuencia")
                st.pyplot(fig)
            elif not pedidos_reales.empty:
                fig, ax = plt.subplots()
                ax.hist(pedidos_reales['valor'].dropna(), bins=10, color=PALETA_CAFE[0])
                ax.set_xlabel("Kg Reales")
                ax.set_ylabel("Frecuencia")
                st.pyplot(fig)
            else:
                st.info("No hay datos suficientes para el histograma")
        
        # ============== TABS AVANZADAS (solo si tiene predicción) ==============
        if tiene_prediccion and not df_merged.empty and 'kg_predicho' in df_merged.columns:
            
            with tab3:  # HEATMAP
                st.subheader("Heatmap Día vs Mes")
                df_vista_copy = df_merged.copy()
                df_vista_copy['Mes'] = df_vista_copy['fecha'].dt.strftime('%b')
                df_vista_copy['Día'] = df_vista_copy['fecha'].dt.strftime('%A')
                tabla = pd.pivot_table(df_vista_copy, values='kg_predicho', index='Día', columns='Mes', aggfunc='sum')
                if not tabla.empty:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    sns.heatmap(tabla, cmap="YlOrBr", annot=True, fmt=".1f", ax=ax)
                    st.pyplot(fig)
            
            with tab4:  # COMPARATIVA
                st.subheader("Comparativa Histórico vs Predicción")
                # Tu código de gráfico de barras aquí
                meses_orden = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                
                if not pedidos_reales.empty:
                    pedidos_reales['anio'] = pedidos_reales['fecha'].dt.year
                    pedidos_reales['mes_lab'] = pedidos_reales['fecha'].dt.strftime('%b')
                    df_pred['anio'] = df_pred['Fecha'].dt.year
                    df_pred['mes_lab'] = df_pred['Fecha'].dt.strftime('%b')
                    
                    pivot_hist = pedidos_reales.pivot_table(index='mes_lab', columns='anio', values='valor', aggfunc='sum').reindex(meses_orden).fillna(0)
                    pivot_pred = df_pred.pivot_table(index='mes_lab', columns='anio', values='Kg_Predichos', aggfunc='sum').reindex(meses_orden).fillna(0)
                    
                    todos_anios = sorted(list(set(pivot_hist.columns.tolist() + pivot_pred.columns.tolist())))
                    
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
                                   color=color_list_pred[i%5], edgecolor=borde_rojo_list[i%5],
                                   linewidth=1.8, alpha=0.70, label=f'Prev {anio}', hatch='//')
                    
                    ax.set_xlabel('Mes')
                    ax.set_ylabel('Kg')
                    ax.set_xticks(x)
                    ax.set_xticklabels(meses_orden, fontsize=10)
                    max_kgs = int((ax.get_ylim()[1] // 10 + 1) * 10)
                    ax.set_yticks(np.arange(0, max_kgs+1, 10))
                    ax.legend(fontsize=10)
                    ax.grid(True, axis='y', alpha=0.18)
                    st.pyplot(fig)
            
            with tab5:  # SIMULACIÓN
                st.subheader("Simulador de Consumo")
                fecha_min, fecha_max = df_pred['Fecha'].min().date(), df_pred['Fecha'].max().date()
                hoy = datetime.date.today()
                fecha_inicio = hoy
                fecha_final = st.date_input("Fecha límite:", value=hoy + datetime.timedelta(weeks=4),
                                           min_value=fecha_inicio, max_value=fecha_max)
                
                mask_pred = (df_pred['Fecha'].dt.date >= fecha_inicio) & (df_pred['Fecha'].dt.date <= fecha_final)
                consumo_periodo = df_pred.loc[mask_pred, 'Kg_Predichos'].astype(float).sum()
                
                inventario_actual = obtener_inventario(producto_sel)
                inv_actual = inventario_actual['cantidad_kg'] if inventario_actual else 0.0
                compra_necesaria = max(0, consumo_periodo - inv_actual)
                
                st.markdown(f"""
                **Periodo:** {fecha_inicio.strftime('%d/%m/%Y')} → {fecha_final.strftime('%d/%m/%Y')}  
                **Consumo estimado:** {consumo_periodo:.1f} kg  
                **Inventario actual:** {inv_actual:.1f} kg  
                **Compra necesaria:** 🟠 {compra_necesaria:.1f} kg
                """)
                st.dataframe(df_pred.loc[mask_pred, ['Fecha', 'Kg_Predichos']].reset_index(drop=True))
        
        # ============== TAB VERIFICACIÓN (PUNTO 5) ==============
        with (tab6 if tiene_prediccion else tab6):
            st.subheader("Verificación y Control")
            
            # PUNTO 5: Verificación de predicciones
            if tiene_prediccion and not df_merged.empty and 'kg_real' in df_merged.columns:
                df_verificacion = df_merged[df_merged['kg_real'].notna()].copy()
                if not df_verificacion.empty:
                    df_verificacion['diferencia_kg'] = df_verificacion['kg_real'] - df_verificacion['kg_predicho']
                    df_verificacion['diferencia_abs'] = abs(df_verificacion['diferencia_kg'])
                    df_verificacion['acierto'] = df_verificacion['diferencia_abs'] <= 2  # Tolerancia de 2kg
                    
                    precisio = (df_verificacion['acierto'].sum() / len(df_verificacion)) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Precisión del modelo", f"{precisio:.1f}%")
                    with col2:
                        st.metric("Predicciones verificadas", len(df_verificacion))
                    with col3:
                        diferencia_promedio = df_verificacion['diferencia_kg'].mean()
                        st.metric("Diferencia promedio", f"{diferencia_promedio:+.1f} kg")
                    
                    st.dataframe(df_verificacion[['fecha', 'kg_predicho', 'kg_real', 'diferencia_kg', 'acierto']])
            
            # PUNTO 7: Control de inventario con historial
            st.subheader("Control de Inventario")
            inventario_actual = obtener_inventario(producto_sel)
            inv_actual = inventario_actual['cantidad_kg'] if inventario_actual else 0.0
            
            nueva_cantidad = st.number_input(f"Inventario de {producto_sel} (kg):", 0.0, 10000.0, inv_actual, step=1.0)
            
            if st.button("🔄 Actualizar Inventario"):
                actualizar_inventario_con_historial(producto_sel, nueva_cantidad, usuario)
            
            # Mostrar historial de cambios
            conn = get_connection()
            if conn:
                try:
                    df_control = pd.read_sql(f"SELECT * FROM control_inventario WHERE producto='{producto_sel}' ORDER BY fecha_cambio DESC LIMIT 10", conn)
                    if not df_control.empty:
                        st.subheader("Últimos cambios de inventario")
                        st.dataframe(df_control)
                    conn.close()
                except:
                    st.info("No hay historial de cambios de inventario")
            
            # Mostrar todos los pedidos de clientes
            conn = get_connection()
            if conn:
                try:
                    df_todos_pedidos = pd.read_sql("SELECT * FROM pedidos_cliente ORDER BY fecha DESC LIMIT 20", conn)
                    if not df_todos_pedidos.empty:
                        st.subheader("Últimos pedidos de clientes")
                        st.dataframe(df_todos_pedidos)
                    conn.close()
                except:
                    st.info("No hay pedidos de clientes registrados")
