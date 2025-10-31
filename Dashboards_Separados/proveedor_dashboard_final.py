# pip install sqlalchemy mysql-connector-python pandas streamlit matplotlib seaborn
# python -m streamlit run proveedor_dashboard.py

# ============================================================================
# IMPORTACIONES
# ============================================================================
from sqlalchemy import create_engine, text
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import streamlit as st
import datetime

# ============================================================================
# CONFIGURACIÓN DE CONEXIÓN A MYSQL
# ============================================================================
MYSQL_USER = "root"
MYSQL_PASS = "Fp$c0105"
MYSQL_HOST = "localhost"
MYSQL_DB = "app_a"


def get_connection():
    """Establece una conexión a la base de datos MySQL utilizando SQLAlchemy."""
    try:
        ENGINE = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}/{MYSQL_DB}")
        return ENGINE
    except Exception as e:
        st.error(f"Error al conectar a la base de datos: {e}")
        return None
ENGINE = get_connection()
# ============================================================================
# FUNCIONES DE ACCESO A DATOS - PEDIDOS
# ============================================================================
def cargar_todos_pedidos():
    """Carga todos los pedidos básicos"""
    query = "SELECT cliente_id, producto, cantidad, detalle, fecha FROM pedidos_cliente"
    return pd.read_sql(query, ENGINE)

def cargar_todos_pedidos_sql():
    """Carga todos los pedidos con ID"""
    with ENGINE.connect() as conn:
        df = pd.read_sql("SELECT * FROM pedidos_cliente", conn)
        return df

def guardar_pedido(nuevo_pedido):
    """Guarda un nuevo pedido en la base de datos"""
    df_nuevo = pd.DataFrame([nuevo_pedido])
    df_nuevo.to_sql('pedidos_cliente', ENGINE, if_exists='append', index=False)

def eliminar_pedido_sql(id_pedido):
    """Elimina un pedido por ID"""
    with ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM pedidos_cliente WHERE id=:id"), {"id": id_pedido})

def registrar_pedido_pendiente(pedido):
    """Registra un pedido pendiente de envío"""
    pd.DataFrame([pedido]).to_sql('pedidos_pendientes', ENGINE, if_exists='append', index=False)

# ============================================================================
# FUNCIONES DE ACCESO A DATOS - INVENTARIO
# ============================================================================
def obtener_inventario_actual():
    """Obtiene el inventario actual de café"""
    df = pd.read_sql("SELECT * FROM inventario_cafe ORDER BY fecha_actualizacion DESC LIMIT 1", ENGINE)
    if df.empty:
        return {'cantidad_kg': 50.0, 'fecha_actualizacion': pd.Timestamp.now()}
    return df.iloc[0].to_dict()

def actualizar_inventario(nueva_cantidad, usuario):
    """Actualiza el inventario y registra el movimiento"""
    anterior = obtener_inventario_actual()["cantidad_kg"]
    fecha_actual = pd.Timestamp.now()
    
    # Actualizar inventario
    data = {
        "cantidad_kg": nueva_cantidad,
        "fecha_actualizacion": fecha_actual
    }
    pd.DataFrame([data]).to_sql('inventario_cafe', ENGINE, if_exists='append', index=False)
    
    # Registrar movimiento
    mov = {
        "cantidad_antes": anterior,
        "cantidad_despues": nueva_cantidad,
        "fecha_cambio": fecha_actual,
        "usuario": usuario
    }
    pd.DataFrame([mov]).to_sql('control_inventario_cafe', ENGINE, if_exists='append', index=False)

# ============================================================================
# FUNCIONES DE ACCESO A DATOS - PREDICCIONES
# ============================================================================
def cargar_predicciones():
    """Carga las predicciones de consumo"""
    df = pd.read_sql("SELECT Fecha, Kg_Predichos FROM predicciones_cafe_365_dias", ENGINE)
    df['fecha'] = pd.to_datetime(df['Fecha'])
    df['prediccion'] = pd.to_numeric(df['Kg_Predichos'])
    df = df[df['fecha'].notnull()].sort_values('fecha')
    return df[['fecha','prediccion']]

def eliminar_prediccion_usada(fecha_pred_usada, kg_predichos):
    """Elimina una predicción ya utilizada"""
    with ENGINE.begin() as conn:
        conn.execute(text(
            "DELETE FROM predicciones_cafe_365_dias WHERE Fecha=:fecha AND Kg_Predichos=:kg"
        ), {"fecha": fecha_pred_usada, "kg": kg_predichos})

# ============================================================================
# FUNCIONES DE ACCESO A DATOS - USUARIOS/CLIENTES
# ============================================================================
def cargar_clientes_usuarios():
    """Carga la lista de clientes"""
    query = "SELECT usuario FROM usuarios WHERE rol='cliente'"
    df = pd.read_sql(query, ENGINE)
    return sorted(df['usuario'].dropna().astype(str).tolist())

def crear_cliente(nuevo_usuario):
    """Crea un nuevo cliente"""
    pd.DataFrame([nuevo_usuario]).to_sql('usuarios', ENGINE, if_exists='append', index=False)

# ============================================================================
# FUNCIONES DE ACCESO A DATOS - LOGS Y COMPARACIONES
# ============================================================================
def guardar_log_eliminacion(fila_eliminada, usuario):
    """Guarda el log de una eliminación de pedido"""
    fila_elim = dict(fila_eliminada)
    fila_elim["usuario"] = usuario
    fila_elim["fecha_eliminacion"] = pd.Timestamp.now()
    pd.DataFrame([fila_elim]).to_sql('log_eliminaciones_pedidos', ENGINE, if_exists='append', index=False)

def guardar_comparacion_predicion(datos):
    """Guarda una comparación entre predicción y realidad"""
    pd.DataFrame([datos]).to_sql('comparacion_prediccion_vs_real', ENGINE, if_exists='append', index=False)

# ============================================================================
# VISTAS DE LA APLICACIÓN - VER PEDIDOS
# ============================================================================
def vista_ver_pedidos():
    """Vista para visualizar y filtrar pedidos"""
    st.header("📦 Pedidos de clientes")
    df_all = cargar_todos_pedidos()
    
    if df_all.empty:
        st.info("No hay pedidos registrados.")
        return

    # Filtro por producto
    productos_unicos = ["Todos"] + sorted(df_all['producto'].unique())
    producto_filtro = st.selectbox("Filtrar por producto:", productos_unicos)
    
    if producto_filtro != "Todos":
        df_filtrado = df_all[df_all['producto'] == producto_filtro]
    else:
        df_filtrado = df_all.copy()
    
    # Filtro por cliente
    clientes = ["Todos"] + sorted(df_filtrado['cliente_id'].unique())
    cliente_seleccionado = st.selectbox("Filtrar por cliente:", clientes)
    if cliente_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['cliente_id'] == cliente_seleccionado]

    # Filtro por fechas
    st.markdown("#### Filtrar por rango de fechas (opcional)")
    aplicar_filtro_fecha = st.checkbox("Filtrar por fechas", value=False)
    fecha_min = df_filtrado['fecha'].min()
    fecha_max = df_filtrado['fecha'].max()
    
    if aplicar_filtro_fecha and pd.notnull(fecha_min) and pd.notnull(fecha_max):
        fecha_ini, fecha_fin = st.date_input(
            "Selecciona rango:", 
            value=(fecha_min, fecha_max), 
            min_value=fecha_min, 
            max_value=fecha_max
        )
        df_filtrado = df_filtrado[
            (df_filtrado['fecha'] >= pd.Timestamp(fecha_ini)) & 
            (df_filtrado['fecha'] <= pd.Timestamp(fecha_fin))
        ]

    # Mostrar resultados
    st.dataframe(df_filtrado.sort_values("fecha", ascending=False))
    st.info(f"Total pedidos mostrados: {len(df_filtrado)}")

    # Gráfica de evolución
    if not df_filtrado.empty:
        st.markdown("### Evolución de pedidos")
        df_graf = df_filtrado.copy()
        df_graf['fecha'] = pd.to_datetime(df_graf['fecha'])
        df_graf = df_graf.groupby('fecha').agg({'cantidad':'sum'}).reset_index()
        
        if len(df_graf) > 1:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(df_graf['fecha'], df_graf['cantidad'], marker='o')
            ax.set_title("Pedidos en el tiempo")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Cantidad total (kg)")
            st.pyplot(fig)
        else:
            st.info("No hay suficiente información para mostrar evolución (al menos 2 fechas únicas requeridas).")

# ============================================================================
# VISTAS DE LA APLICACIÓN - CONTROL DE INVENTARIO
# ============================================================================
def control_de_inventario():
    """Vista para controlar el inventario de café"""
    st.header("📊 Control de Inventario de Café")
    usuario = st.session_state.get("usuario", "sistema")
    
    # Inventario actual
    inv_actual = obtener_inventario_actual()
    cantidad_kg = inv_actual["cantidad_kg"]
    st.metric("Inventario actual (kg)", f"{cantidad_kg:.1f}")
    st.write(f"Última actualización: {inv_actual.get('fecha_actualizacion')}")
    
    # Actualizar inventario
    nueva_cant = st.number_input(
        "Nueva cantidad de inventario (kg):", 
        min_value=0.0, 
        max_value=99999.0, 
        value=float(cantidad_kg), 
        step=1.0
    )
    
    if st.button("Actualizar inventario"):
        if nueva_cant != cantidad_kg:
            actualizar_inventario(nueva_cant, usuario)
            st.success("Inventario actualizado correctamente.")
        else:
            st.warning("La cantidad ingresada es igual a la actual.")

    # Historial de movimientos
    st.subheader("Historial de movimientos")
    df_hist = pd.read_sql("SELECT * FROM control_inventario_cafe ORDER BY fecha_cambio DESC", ENGINE)
    if df_hist.empty:
        st.info("No hay movimientos registrados.")
    else:
        st.dataframe(df_hist)

    # Predicción de duración del inventario
    df_pred = cargar_predicciones()
    if not df_pred.empty and cantidad_kg > 0:
        hoy = pd.Timestamp(datetime.date.today())
        df_pred_fut = df_pred[df_pred['fecha'] >= hoy]
        dias_rest = None
        suma_acum = 0
        
        for i, row in df_pred_fut.iterrows():
            suma_acum += row['prediccion']
            if suma_acum >= cantidad_kg:
                dias_rest = i + 1
                fecha_lim = row['fecha']
                break
        
        if dias_rest is not None:
            st.info(f"Te quedan **{dias_rest} días** de inventario actual según predicción. Fecha límite: **{fecha_lim.date()}**")
        else:
            st.warning("No se pudo estimar el fin de inventario con las predicciones actuales.")
    else:
        st.warning("Sin datos de predicción suficientes para estimar duración.")

# ============================================================================
# VISTAS DE LA APLICACIÓN - REGISTRAR PEDIDO
# ============================================================================
def registrar_pedido():
    """Vista para registrar un nuevo pedido"""
    st.header("📝 Registrar nuevo pedido")
    
    # Cargar predicciones
    df_pred = cargar_predicciones()
    hoy = pd.Timestamp(datetime.date.today())
    df_pred_fut = df_pred[df_pred['fecha'] >= hoy]
    prox_opciones = df_pred_fut.head(5).copy()
    prox_opciones['texto'] = prox_opciones.apply(
        lambda r: f"{r['fecha'].date()} | {r['prediccion']:.1f}kg", axis=1
    )
    
    # Selector de predicción
    opciones = ["Regularizar inventario"] + prox_opciones['texto'].tolist()
    seleccion = st.selectbox("Selecciona un próximo pedido predicho", opciones)
    pred_usada = False
    
    if seleccion != "Regularizar inventario":
        idx = prox_opciones[prox_opciones['texto'] == seleccion].index[0]
        fecha_menu = prox_opciones.loc[idx, 'fecha'].date()
        kg_menu = prox_opciones.loc[idx, 'prediccion']
        st.info(f"Predicción seleccionada: {fecha_menu} - {kg_menu:.1f}kg")
        sugerir_fecha = fecha_menu
        sugerir_kg = kg_menu
        pred_usada = True
    else:
        sugerir_fecha = datetime.date.today()
        sugerir_kg = 1.0

    # Formulario de pedido
    clientes_validos = cargar_clientes_usuarios()
    if not clientes_validos:
        st.error("No hay clientes registrados en el sistema.")
        return
    
    cliente = st.selectbox("Cliente", clientes_validos)
    
    # Cargar productos desde base de datos
    productos_df = pd.read_sql("SELECT nombre FROM precios_producto", ENGINE)
    productos_lista = productos_df['nombre'].tolist()
    producto = st.selectbox("Producto", productos_lista)
    
    cantidad_pedido = st.number_input("Cantidad (kg)", min_value=0.0, max_value=99999.0, value=sugerir_kg)
    fecha_pedido = st.date_input("Fecha del pedido", value=sugerir_fecha)
    detalle = st.text_input("Detalle (opcional)")
    
    if st.button("Agregar pedido"):
        nuevo_pedido = {
            'cliente_id': cliente,
            'producto': producto,
            'cantidad': cantidad_pedido,
            'detalle': detalle,
            'fecha': fecha_pedido
        }
        guardar_pedido(nuevo_pedido)
        st.success("Pedido registrado.")

# ============================================================================
# VISTAS DE LA APLICACIÓN - ELIMINAR PEDIDO
# ============================================================================
def eliminar_pedido():
    """Vista para eliminar pedidos"""
    st.header("🗑️ Eliminar pedido")
    usuario = st.session_state.get("usuario", "desconocido")
    df_pedidos = cargar_todos_pedidos_sql()
    
    if df_pedidos.empty:
        st.info("No hay pedidos registrados para eliminar.")
        return

    # Filtros
    clientes = ["Todos"] + sorted(df_pedidos['cliente_id'].dropna().unique())
    cliente_seleccionado = st.selectbox("Filtrar por cliente", clientes)
    df_filtrado = df_pedidos[df_pedidos['cliente_id'] == cliente_seleccionado].copy() if cliente_seleccionado != "Todos" else df_pedidos.copy()
    
    fechas = ["Todas"] + sorted(list(set(str(f)[:10] for f in df_filtrado['fecha'] if pd.notna(f))))
    fecha_seleccionada = st.selectbox("Filtrar por fecha", fechas)
    if fecha_seleccionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['fecha'].astype(str).str.startswith(fecha_seleccionada)]

    # Ordenar por ID descendente
    df_filtrado = df_filtrado.sort_values("id", ascending=False)
    df_filtrado["info"] = df_filtrado.apply(
        lambda r: f"ID {r['id']} | {r['cliente_id']} | {r['producto']} | {r['cantidad']} kg | {r['fecha']}", 
        axis=1
    )

    if df_filtrado.empty:
        st.warning("No hay pedidos con esos filtros.")
        return

    # Selector de pedido a eliminar
    idx_seleccionado = st.selectbox(
        "Selecciona el pedido a eliminar",
        options=list(df_filtrado['id']),
        format_func=lambda i: df_filtrado[df_filtrado['id']==i]['info'].values[0]
    )

    st.write("**Detalles del pedido a eliminar:**")
    st.write(df_filtrado[df_filtrado['id']==idx_seleccionado])

    # Confirmación
    seguro = st.checkbox("Estoy seguro de eliminar este pedido", value=False)
    confirmar = st.button("Eliminar pedido", disabled=not seguro)
    
    if confirmar and seguro:
        guardar_log_eliminacion(df_filtrado[df_filtrado['id']==idx_seleccionado].iloc[0], usuario)
        eliminar_pedido_sql(idx_seleccionado)
        st.success("Pedido eliminado y guardado en registro de auditoría.")

# ============================================================================
# VISTAS DE LA APLICACIÓN - RESUMEN Y ESTADÍSTICAS
# ============================================================================
def resumen_estadisticas_globales():
    """Vista de resumen y estadísticas globales"""
    st.header("📊 Resumen y Estadísticas Globales")
    
    # Cargar datos
    pedidos = cargar_todos_pedidos()
    inventario = obtener_inventario_actual()
    clientes = cargar_clientes_usuarios()
    
    # Métricas generales
    total_pedidos = len(pedidos)
    total_kg = pedidos['cantidad'].sum() if not pedidos.empty else 0
    pedidos_por_prod = pedidos.groupby('producto').agg({
        'cantidad':'sum',
        'fecha':'count'
    }).rename(columns={'fecha':'num_pedidos'})
    
    st.subheader("Resumen global:")
    st.metric("Total pedidos registrados", total_pedidos)
    st.metric("Total kg vendidos", total_kg)
    st.metric("Inventario actual (kg)", inventario.get('cantidad_kg', 0))
    st.metric("Clientes activos", len(clientes))
    
    st.subheader("Pedidos por producto:")
    if not pedidos_por_prod.empty:
        st.dataframe(pedidos_por_prod)
    else:
        st.info("No hay datos de pedidos.")

    # Auditoría de eliminaciones
    elim = pd.read_sql("SELECT * FROM log_eliminaciones_pedidos", ENGINE)
    st.subheader("Auditoría: Pedidos eliminados")
    st.write(f"Pedidos eliminados: {len(elim)}")
    st.dataframe(elim[['cliente_id','producto','cantidad','fecha','fecha_eliminacion','usuario']])

    # Ranking de clientes
    st.subheader("Ranking de clientes (por kg)")
    if not pedidos.empty:
        ranking = pedidos.groupby('cliente_id').agg(
            total_kg=('cantidad','sum'), 
            pedidos=('fecha','count')
        ).sort_values("total_kg", ascending=False)
        st.write("Top clientes por kg vendido:")
        st.dataframe(ranking)
    else:
        st.info("No hay ventas registradas en el periodo.")
    
    # Comparación de predicciones
    st.markdown("## Pedidos predichos comparación")
    df_comp = pd.read_sql("SELECT * FROM comparacion_prediccion_vs_real", ENGINE)
    
    if df_comp.empty:
        st.info("No hay datos de comparaciones registradas.")
        return
    
    # MÉTRICAS EN KG
    df_comp['error_kg'] = (df_comp['kg_real'] - df_comp['kg_predicha']).abs()
    error_promedio = df_comp['error_kg'].mean()
    error_max = df_comp['error_kg'].max()
    error_min = df_comp['error_kg'].min()
    error_std = df_comp['error_kg'].std()
    aciertos_kg = (df_comp['error_kg'] <= 1).sum()
    porcentaje_aciertos_kg = (aciertos_kg / len(df_comp) * 100) if len(df_comp) > 0 else 0

    st.write(f"**Error promedio (kg):** {error_promedio:.2f}")
    st.write(f"**Error máximo (kg):** {error_max:.2f}")
    st.write(f"**Error mínimo (kg):** {error_min:.2f}")
    st.write(f"**Desviación estándar del error (kg):** {error_std:.2f}")
    st.write(f"**Porcentaje de aciertos (±1kg):** {porcentaje_aciertos_kg:.1f} % ({aciertos_kg}/{len(df_comp)})")

    # MÉTRICAS EN DÍAS
    df_comp['error_dias'] = df_comp['dif_dias'].abs()
    error_promedio_dias = df_comp['error_dias'].mean()
    error_max_dias = df_comp['error_dias'].max()
    error_min_dias = df_comp['error_dias'].min()
    error_std_dias = df_comp['error_dias'].std()
    aciertos_dias = (df_comp['error_dias'] <= 1).sum()
    porcentaje_aciertos_dias = (aciertos_dias / len(df_comp) * 100) if len(df_comp) > 0 else 0

    st.write(f"\n**Error promedio (días):** {error_promedio_dias:.2f}")
    st.write(f"**Error máximo (días):** {error_max_dias}")
    st.write(f"**Error mínimo (días):** {error_min_dias}")
    st.write(f"**Desviación estándar del error (días):** {error_std_dias:.2f}")
    st.write(f"**Porcentaje de aciertos (±1 día):** {porcentaje_aciertos_dias:.1f} % ({aciertos_dias}/{len(df_comp)})")
    
    # Aciertos simultáneos
    cond_acierto_kgydia = (df_comp["error_kg"] <= 1) & (df_comp["error_dias"] <= 1)
    aciertos_kgydia = cond_acierto_kgydia.sum()
    porcentaje_aciertos_kgydia = (aciertos_kgydia / len(df_comp) * 100) if len(df_comp) > 0 else 0
    st.write(f"**Porcentaje de aciertos simultáneos (±1kg y ±1 día):** {porcentaje_aciertos_kgydia:.1f} % ({aciertos_kgydia}/{len(df_comp)})")

    df_comp['ACIERTO_CONJUNTO'] = cond_acierto_kgydia.map({True: "✅", False: ""})
    st.dataframe(df_comp[['cliente_id','fecha_real','kg_real','fecha_predicha','kg_predicha','error_kg','error_dias','ACIERTO_CONJUNTO']])
    
    # Tabla resumen
    st.dataframe(df_comp[['cliente_id','fecha_real','kg_real','fecha_predicha','kg_predicha','dif_dias','dif_kg','error_kg','error_dias']])

    # Histogramas
    fig, ax = plt.subplots()
    ax.hist(df_comp['error_kg'], bins=20, color='#6699ff', edgecolor='black', alpha=0.8)
    ax.set_xlabel("Error absoluto (kg)")
    ax.set_ylabel("Frecuencia")
    ax.set_title("Distribución de errores (kg)")
    st.pyplot(fig)
    
    fig2, ax2 = plt.subplots()
    ax2.hist(df_comp['error_dias'], bins=20, color='#ff6666', edgecolor='black', alpha=0.8)
    ax2.set_xlabel("Error absoluto (días)")
    ax2.set_ylabel("Frecuencia")
    ax2.set_title("Distribución de errores (días)")
    st.pyplot(fig2)

# ============================================================================
# VISTAS DE LA APLICACIÓN - GESTIÓN DE CLIENTES
# ============================================================================
def gestion_clientes():
    """Vista para gestionar clientes"""
    st.header("👤 Gestión de clientes")
    accion = st.radio("¿Qué acción deseas realizar?", ["Crear", "Editar", "Borrar"])
    
    if accion == "Crear":
        nombre_usuario = st.text_input("Nombre de cliente (usuario)")
        nombre_real = st.text_input("Nombre real")
        contrasena = st.text_input("Contraseña", type="password")
        telefono = st.text_input("Teléfono")
        
        if st.button("Registrar cliente"):
            nuevo_usuario = {
                'usuario': nombre_usuario,
                'nombre': nombre_real,
                'contrasena': contrasena,
                'telefono': telefono,
                'rol': 'cliente'
            }
            crear_cliente(nuevo_usuario)
            st.success("Cliente creado exitosamente. Ya puede recibir pedidos.")
    
    elif accion == "Editar":
        df_usuarios = pd.read_sql("SELECT * FROM usuarios WHERE rol='cliente'", ENGINE)
        clientes = df_usuarios['usuario'].dropna().unique()
        
        if not len(clientes):
            st.info("No hay clientes con rol 'cliente' para editar.")
            return
        
        cliente = st.selectbox("Selecciona el cliente a editar", clientes)
        fila_idx = df_usuarios[df_usuarios['usuario'] == cliente].index[0]
        datos_actuales = df_usuarios.loc[fila_idx]
        
        nuevo_nombre = st.text_input("Nombre real", value=str(datos_actuales.get('nombre','')))
        nuevo_telefono = st.text_input("Teléfono", value=str(datos_actuales.get('telefono','')))
        
        if st.button("Guardar cambios"):
            with ENGINE.begin() as conn:
                conn.execute(
                    text("UPDATE usuarios SET nombre=:n, telefono=:t WHERE usuario=:u"),
                    {"n": nuevo_nombre, "t": nuevo_telefono, "u": cliente}
                )
            st.success("Datos del cliente actualizados correctamente.")
    
    elif accion == "Borrar":
        df_usuarios = pd.read_sql("SELECT * FROM usuarios WHERE rol='cliente'", ENGINE)
        clientes = df_usuarios['usuario'].dropna().unique()
        
        if not len(clientes):
            st.info("No hay clientes con rol 'cliente' para borrar.")
            return
        
        cliente = st.selectbox("Selecciona el cliente a borrar", clientes)
        tiene_pedidos = not pd.read_sql(f"SELECT * FROM pedidos_cliente WHERE cliente_id='{cliente}'", ENGINE).empty
        
        st.write(f"¿Eliminar cliente '{cliente}'? {'(Tiene pedidos activos, se recomienda no borrar)' if tiene_pedidos else ''}")
        seguro = st.checkbox("Estoy seguro de borrar este cliente", value=False)
        confirmar = st.button("Borrar cliente", disabled=not seguro)
        
        if confirmar and seguro:
            with ENGINE.begin() as conn:
                conn.execute(text("DELETE FROM usuarios WHERE usuario=:u"), {"u": cliente})
            st.success(f"Cliente '{cliente}' borrado correctamente.")
            if tiene_pedidos:
                st.warning("¡Este cliente tenía pedidos registrados! Estos datos NO se han borrado del historial de pedidos.")

# ============================================================================
# VISTAS DE LA APLICACIÓN - PEDIDOS PENDIENTES
# ============================================================================
def pedidos_pendientes():
    """Vista para gestionar pedidos pendientes de envío"""
    st.header("📦 Pedidos pendientes de enviar")
    tab_registro, tab_lista = st.tabs(["Registrar pendiente", "Ver/Entregar pendientes"])

    # -------- REGISTRAR NUEVO PENDIENTE --------
    with tab_registro:
        clientes = pd.read_sql("SELECT usuario FROM usuarios WHERE rol='cliente'", ENGINE)['usuario'].tolist()
        cliente_id = st.selectbox("Cliente destino", clientes)
        
        # Cargar productos desde base de datos
        productos_df = pd.read_sql("SELECT nombre FROM precios_producto", ENGINE)
        productos_lista = productos_df['nombre'].tolist()
        producto = st.selectbox("Producto", productos_lista)
        
        cantidad = st.number_input("Cantidad", min_value=0.0, max_value=9999.0, value=1.0)
        detalle = st.text_input("Descripción/Detalle")
        fecha = st.date_input("Fecha de entrega solicitada", value=datetime.date.today())
        
        if st.button("Registrar pedido por enviar"):
            nuevo_pedido = {
                "cliente_id": cliente_id,
                "producto": producto,
                "cantidad": cantidad,
                "detalle": detalle,
                "fecha": fecha
            }
            pd.DataFrame([nuevo_pedido]).to_sql('pedidos_pendientes', ENGINE, if_exists='append', index=False)
            st.success("Pedido registrado y marcado como pendiente de envío.")

    # -------- VISUALIZAR/ENTREGAR PENDIENTES --------
    with tab_lista:
        df_pendientes = pd.read_sql("SELECT * FROM pedidos_pendientes ORDER BY fecha DESC", ENGINE)
        
        if df_pendientes.empty:
            st.info("No hay pedidos pendientes.")
            return

        st.dataframe(df_pendientes[['id','cliente_id','producto','cantidad','detalle','fecha']])
        
        ids = list(df_pendientes['id'])
        seleccionado = st.selectbox(
            "Selecciona pedido pendiente para entregar/loguear", 
            ids, 
            format_func=lambda i: f"ID {i} | Cliente {df_pendientes[df_pendientes['id']==i]['cliente_id'].iloc[0]}"
        )
        
        datos_seleccionado = df_pendientes[df_pendientes['id'] == seleccionado].iloc[0]
        st.markdown(f"**Detalles:**  Cliente: {datos_seleccionado['cliente_id']}  |  Producto: {datos_seleccionado['producto']}  |  Cantidad: {datos_seleccionado['cantidad']} kg  | Fecha solicitada: {datos_seleccionado['fecha']}")

        fecha_entrega = st.date_input("Fecha real de entrega", value=datetime.date.today())

        # --- Opcional: Asociar a predicción ---
        df_pred = pd.read_sql("SELECT Fecha, Kg_Predichos FROM predicciones_cafe_365_dias", ENGINE)
        df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'], dayfirst=True, errors='coerce')
        df_pred = df_pred[df_pred['Fecha'] >= pd.to_datetime(str(datos_seleccionado['fecha'])) - pd.Timedelta(days=7)]
        
        opciones_pred = ["No asociar a predicción"] + [
            f"{r.Fecha.date()} | {r.Kg_Predichos:.1f} kg" for _, r in df_pred.iterrows()
        ]
        prediccion_sel = st.selectbox("¿Asociar a una predicción?", opciones_pred)

        if st.button("Registrar entrega, loguear y quitar de pendientes"):
            # 1. Registrar como pedido real
            nuevo_pedido = {
                'cliente_id': datos_seleccionado['cliente_id'],
                'producto': datos_seleccionado['producto'],
                'cantidad': datos_seleccionado['cantidad'],
                'detalle': datos_seleccionado['detalle'],
                'fecha': fecha_entrega
            }
            pd.DataFrame([nuevo_pedido]).to_sql('pedidos_cliente', ENGINE, if_exists='append', index=False)

            # 2. Registrar LOG de entregado
            log_entregado = {
                'cliente_id': datos_seleccionado['cliente_id'],
                'producto': datos_seleccionado['producto'],
                'cantidad': datos_seleccionado['cantidad'],
                'detalle': datos_seleccionado['detalle'],
                'fecha_solicitada': datos_seleccionado['fecha'],
                'fecha_entrega': fecha_entrega,
                'id_pendiente': datos_seleccionado['id']
            }
            pd.DataFrame([log_entregado]).to_sql('log_pedidos_entregados', ENGINE, if_exists='append', index=False)

            # 3. Registrar comparación si hay predicción
            if prediccion_sel != "No asociar a predicción":
                fecha_pred_str = prediccion_sel.split('|')[0].strip()
                kg_pred_str = prediccion_sel.split('|')[1].replace('kg','').strip()
                datos_comparacion = {
                    "cliente_id": datos_seleccionado['cliente_id'],
                    "fecha_real": fecha_entrega,
                    "kg_real": datos_seleccionado['cantidad'],
                    "fecha_predicha": fecha_pred_str,
                    "kg_predicha": float(kg_pred_str),
                    "dif_dias": (pd.to_datetime(fecha_entrega) - pd.to_datetime(fecha_pred_str)).days,
                    "dif_kg": float(datos_seleccionado['cantidad']) - float(kg_pred_str),
                    "registro": pd.Timestamp.now(),
                    "fue_pred_usada": True
                }
                pd.DataFrame([datos_comparacion]).to_sql('comparacion_prediccion_vs_real', ENGINE, if_exists='append', index=False)

            # 4. Quitar de pendientes
            with ENGINE.begin() as conn:
                conn.execute(text("DELETE FROM pedidos_pendientes WHERE id=:id"), {"id": seleccionado})

            st.success("Entrega registrada, logueada y movida a pedidos reales.")

# ============================================================================
# VISTAS DE LA APLICACIÓN - DASHBOARD AVANZADO
# ============================================================================
def dashboard_graficas_avanzadas():
    """Dashboard con gráficas avanzadas de predicciones"""
    st.header("📊 Dashboard avanzado café")
    
    # Cargar datos
    df_pred = pd.read_sql("SELECT Fecha, Kg_Predichos FROM predicciones_cafe_365_dias", ENGINE)
    df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'], dayfirst=True, errors='coerce')
    
    pedidos_reales = pd.read_sql("SELECT fecha, cantidad AS kg_real FROM pedidos_cliente", ENGINE)
    pedidos_reales['fecha'] = pd.to_datetime(pedidos_reales['fecha'], errors='coerce')

    # Merge predicciones con pedidos reales
    df_pred_renamed = df_pred.rename(columns={'Fecha': 'fecha', 'Kg_Predichos': 'kg_predicho'})
    df_merged = pd.merge(df_pred_renamed, pedidos_reales, on='fecha', how='left')

    st.subheader("Visualización avanzada de predicciones y consumo")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Tabla", "Hist. Predichos", "Heatmap", "Comparativa/Evolución", "Simulación"]
    )

    max_dias = len(df_merged)
    dias_mostrar = st.slider("Cantidad de predicciones a visualizar:", 1, max_dias, min(30, max_dias))
    df_vista = df_merged.head(dias_mostrar).copy()

    # TAB 1: TABLA
    with tab1:
        st.subheader("Predicciones")
        st.dataframe(df_vista[['fecha', 'kg_predicho', 'kg_real']])

    # TAB 2: HISTOGRAMA
    with tab2:
        st.subheader("Histograma de Kg Predichos")
        fig, ax = plt.subplots()
        ax.hist(df_vista['kg_predicho'].dropna().astype(float), bins=10, color="#FFD39B", edgecolor="#8B5B29")
        ax.set_xlabel("Kg Predichos")
        ax.set_ylabel("Frecuencia")
        st.pyplot(fig)

    # TAB 3: HEATMAP
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

    # TAB 4: COMPARATIVA/EVOLUCIÓN
    with tab4:
        st.subheader("Consumo anterior y consumo esperado")
        meses_orden = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        
        # Preprocesar históricos y predicciones
        pedidos_reales['anio'] = pedidos_reales['fecha'].dt.year
        pedidos_reales['mes'] = pedidos_reales['fecha'].dt.month
        pedidos_reales['mes_lab'] = pedidos_reales['fecha'].dt.strftime('%b')

        df_pred['anio'] = df_pred['Fecha'].dt.year
        df_pred['mes'] = df_pred['Fecha'].dt.month
        df_pred['mes_lab'] = df_pred['Fecha'].dt.strftime('%b')

        pivot_hist = pedidos_reales.pivot_table(
            index='mes_lab', columns='anio', values='kg_real', aggfunc='sum'
        ).reindex(meses_orden).fillna(0)
        
        pivot_pred = df_pred.pivot_table(
            index='mes_lab', columns='anio', values='Kg_Predichos', aggfunc='sum'
        ).reindex(meses_orden).fillna(0)

        todos_anios = sorted(list(set(pivot_hist.columns.tolist() + pivot_pred.columns.tolist())))
        
        # Colores
        color_list_hist = ['#b3c6f7', '#6699ff', '#3366cc', '#003399', '#001147']
        color_list_pred = ['#ffcccc', '#ff6666', '#ff3300', '#cc0000', '#660000']
        borde_rojo_list = ['#ff3333', '#cc0000', '#990000', '#660000', '#330000']

        fig, ax = plt.subplots(figsize=(12,7))
        bar_width = 0.7 / len(todos_anios)
        x = np.arange(len(meses_orden))

        # Barras históricas
        for i, anio in enumerate(todos_anios):
            vals_hist = pivot_hist[anio].values if anio in pivot_hist.columns else np.zeros(len(meses_orden))
            if np.any(vals_hist > 0):
                offset = (i - len(todos_anios)/2)*bar_width
                ax.bar(x+offset, vals_hist, width=bar_width, color=color_list_hist[i%5], alpha=0.87, label=f"Hist {anio}")
        
        # Barras predichas
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
        
        # Ajuste ticks cada 10 kg
        max_kgs = int((ax.get_ylim()[1] // 10 + 1) * 10)
        ax.set_yticks(np.arange(0, max_kgs+1, 10))
        ax.legend(fontsize=10)
        ax.grid(True, axis='y', alpha=0.18)
        st.pyplot(fig)

    # TAB 5: SIMULACIÓN
    with tab5:
        st.header("📅 Simula el consumo hasta una fecha")
        fecha_min, fecha_max = df_pred['Fecha'].min().date(), df_pred['Fecha'].max().date()
        hoy = datetime.date.today()
        
        fecha_final = st.date_input(
            "Selecciona la fecha límite", 
            value=hoy + datetime.timedelta(weeks=4),
            min_value=hoy, 
            max_value=fecha_max
        )
        
        mask_pred = (df_pred['Fecha'].dt.date >= hoy) & (df_pred['Fecha'].dt.date <= fecha_final)
        consumo_periodo = df_pred.loc[mask_pred, 'Kg_Predichos'].astype(float).sum()
        
        inventario_actual = pd.read_sql(
            "SELECT cantidad_kg FROM inventario_cafe ORDER BY fecha_actualizacion DESC LIMIT 1", 
            ENGINE
        )['cantidad_kg'].iloc[0]
        
        compra_necesaria = max(0, consumo_periodo - inventario_actual)
        
        st.markdown(f"""
        **Periodo:** {hoy.strftime('%d/%m/%Y')} → {fecha_final.strftime('%d/%m/%Y')}  
        **Consumo estimado:** {consumo_periodo:.1f} kg  
        **Inventario actual:** {inventario_actual:.1f} kg  
        **Compra necesaria:** 🟠 {compra_necesaria:.1f} kg
        """)
        
        st.dataframe(df_pred.loc[mask_pred, ['Fecha', 'Kg_Predichos']].reset_index(drop=True))

    # ALERTA de inventario en la barra lateral
    st.sidebar.header("⚠️ Control de Inventario")
    sum_kg, dias_stock, fecha_quiebre = 0, 0, None
    
    for idx, row in df_pred.iterrows():
        if sum_kg < inventario_actual:
            sum_kg += float(row['Kg_Predichos'])
            dias_stock += 1
            fecha_quiebre = row['Fecha']
        else:
            break
    
    prox_pred = df_pred[df_pred['Fecha'] >= pd.Timestamp(datetime.date.today())]
    prox_prediccion = prox_pred['Kg_Predichos'].iloc[0] if not prox_pred.empty else 0.0

    # ALERTA visual
    if inventario_actual < float(prox_prediccion):
        st.sidebar.error(f"⚠️ Inventario insuficiente ({inventario_actual:.1f} kg). No cubre el siguiente pedido ({prox_prediccion:.1f} kg).")
    else:
        st.sidebar.success(f"Inven. OK: {inventario_actual:.1f} kg. Cubre hasta el {fecha_quiebre.strftime('%d/%m/%Y')}")
        st.sidebar.metric("Pedidos cubiertos", dias_stock, delta=f"Hasta {fecha_quiebre.strftime('%d/%m/%Y')}")
        st.sidebar.write("Detalle del consumo proyectado:")
        st.sidebar.dataframe(df_pred.loc[:dias_stock-1, ['Fecha', 'Kg_Predichos']])

# ============================================================================
# VISTAS DE LA APLICACIÓN - GESTIÓN DE PRODUCTOS
# ============================================================================
def gestion_productos():
    """Vista para gestionar productos y precios"""
    st.header("🛒 Gestión de productos y precios")
    tab_add, tab_edit, tab_del = st.tabs(["Agregar producto", "Editar precio", "Eliminar producto"])

    # --- Agregar producto ---
    with tab_add:
        nombre_new = st.text_input("Nombre del producto nuevo")
        precio_new = st.number_input("Precio unitario", min_value=0.0, value=0.0)
        
        if st.button("Agregar producto"):
            if nombre_new:
                producto = {'nombre': nombre_new, 'precio': precio_new}
                pd.DataFrame([producto]).to_sql('precios_producto', ENGINE, if_exists='append', index=False)
                st.success("Producto agregado correctamente.")
            else:
                st.warning("Ingresa un nombre.")

    # --- Editar producto ---
    with tab_edit:
        productos = pd.read_sql("SELECT * FROM precios_producto", ENGINE)
        
        if not productos.empty:
            nombres = productos['nombre'].tolist()
            prod_sel = st.selectbox("Producto a editar", nombres)
            precio_actual = productos[productos['nombre'] == prod_sel]['precio'].iloc[0]
            nuevo_precio = st.number_input("Nuevo precio unitario", min_value=0.0, value=float(precio_actual))
            
            if st.button("Actualizar precio"):
                with ENGINE.begin() as conn:
                    conn.execute(
                        text("UPDATE precios_producto SET precio=:p WHERE nombre=:n"),
                        {"p": nuevo_precio, "n": prod_sel}
                    )
                st.success("Precio actualizado.")
        else:
            st.info("No hay productos registrados.")

    # --- Eliminar producto ---
    with tab_del:
        productos = pd.read_sql("SELECT * FROM precios_producto", ENGINE)
        
        if not productos.empty:
            prod_del = st.selectbox("Producto a eliminar", productos['nombre'].tolist())
            
            if st.button("Eliminar producto"):
                with ENGINE.begin() as conn:
                    conn.execute(text("DELETE FROM precios_producto WHERE nombre=:n"), {"n": prod_del})
                st.success("Producto eliminado.")
        else:
            st.info("No hay productos registrados.")

    st.subheader("Lista de productos y precios actuales")
    st.dataframe(pd.read_sql("SELECT * FROM precios_producto", ENGINE))

# ============================================================================
# VISTAS DE LA APLICACIÓN - APARTADO DE PAGOS
# ============================================================================
def apartado_pagos():
    """Vista para control de pagos por cliente"""
    st.header("💰 Control de pagos por cliente")

    # 1. Selección de cliente
    df_entregados = pd.read_sql("SELECT * FROM log_pedidos_entregados", ENGINE)
    precios = pd.read_sql("SELECT * FROM precios_producto", ENGINE).set_index('nombre')['precio'].to_dict()
    clientes = df_entregados['cliente_id'].unique().tolist()
    
    if not clientes:
        st.warning("No hay entregas registradas.")
        return
    
    cliente_sel = st.selectbox("Cliente", clientes)

    # 2. Calcula total entregado y muestra detalle con precios automáticos
    df_cliente = df_entregados[df_entregados['cliente_id'] == cliente_sel].copy()
    df_cliente['precio_unitario'] = df_cliente['producto'].map(precios)
    df_cliente['importe'] = df_cliente['cantidad'] * df_cliente['precio_unitario']
    
    total_kg = df_cliente['cantidad'].sum()
    total_pagar = df_cliente['importe'].sum()
    
    st.subheader("Entregas a cobrar para el cliente seleccionado:")
    st.dataframe(df_cliente[['fecha_solicitada', 'fecha_entrega', 'producto', 'cantidad', 'detalle', 'precio_unitario', 'importe']])
    st.markdown(f"**Total entregado:** {total_kg:.2f} kg")
    st.markdown(f"**Monto a pagar:** ${total_pagar:,.2f}")

    # 3. Registrar nuevo pago
    st.markdown("### Registrar pago recibido")
    monto_pago = st.number_input("Monto recibido", min_value=0.0, value=float(total_pagar))
    fecha_pago = st.date_input("Fecha de pago", value=datetime.date.today())
    observ = st.text_input("Observaciones (opcional)")

    if st.button("Registrar pago"):
        pago = {
            'cliente_id': cliente_sel,
            'monto': monto_pago,
            'fecha_pago': fecha_pago,
            'observaciones': observ
        }
        pd.DataFrame([pago]).to_sql('pagos_cliente', ENGINE, if_exists='append', index=False)
        st.success("Pago registrado correctamente.")

    # 4. Mostrar pagos anteriores del cliente
    st.subheader("Pagos recibidos")
    pagos_hist = pd.read_sql(
        f"SELECT * FROM pagos_cliente WHERE cliente_id='{cliente_sel}' ORDER BY fecha_pago DESC", 
        ENGINE
    )
    st.dataframe(pagos_hist)

# ============================================================================
# MENÚ PRINCIPAL DE LA APLICACIÓN
# ============================================================================
st.sidebar.title("Menú proveedor")
opcion = st.sidebar.radio("Opciones:", [
    "Clientes", 
    "Gestion de pedidos previos",
    "Control de inventario", 
    "Resumen/Estadísticas",
    "Dashboard avanzado",
    "Pedidos pendientes",
    "Productos",
    "Apartado pagos",
    "Salir"
])

# ============================================================================
# NAVEGACIÓN ENTRE VISTAS
# ============================================================================
if opcion == "Apartado pagos":
    apartado_pagos()
elif opcion == "Productos":
    gestion_productos()
elif opcion == "Pedidos pendientes":
    pedidos_pendientes()
elif opcion == "Dashboard avanzado":
    dashboard_graficas_avanzadas()
elif opcion == "Resumen/Estadísticas":
    resumen_estadisticas_globales()
elif opcion == "Clientes":
    gestion_clientes()
elif opcion == "Gestion de pedidos previos":
    st.header("Gestion de pedidos previos")
    accion = st.radio("¿Qué acción deseas realizar?", ["Registrar pedido",  "Ver pedidos","Eliminar pedido"])
    if accion == "Registrar pedido":
        registrar_pedido()
    elif accion == "Ver pedidos":
        vista_ver_pedidos()
    elif accion == "Eliminar pedido":
        eliminar_pedido()
elif opcion == "Control de inventario":
    control_de_inventario()
elif opcion == "Salir":
    st.session_state["rol"] = None
    st.session_state["usuario"] = None
    st.experimental_rerun()

# ============================================================================
# FIN DEL CÓDIGO
# ============================================================================