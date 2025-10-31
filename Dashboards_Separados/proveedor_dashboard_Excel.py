# -------------------- IMPORTS Y UTILIDADES --------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import os

def ruta_datos(filename):
    carpeta = 'datos_prueba'
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, filename)

# ----------- CONSTANTES DE ARCHIVO -----------
ARCHIVO_PEDIDOS = ruta_datos("pedidos_cliente.xlsx")
ARCHIVO_INVENTARIO = ruta_datos('inventario_cafe.xlsx')
ARCHIVO_CONTROL = ruta_datos('control_inventario_cafe.xlsx')
ARCHIVO_PREDICCIONES = ruta_datos('predicciones_cafe_365_dias.xlsx')
ARCHIVO_USUARIOS = ruta_datos('usuarios.xlsx')
ARCHIVO_COMPARACION = ruta_datos('comparacion_prediccion_vs_real.xlsx')
ARCHIVO_ELIMINADOS = ruta_datos('log_eliminaciones_pedidos.xlsx')

# -------------------- FUNCIONES DE PEDIDOS --------------------
def cargar_todos_pedidos():
    # Lee o crea estructura vacía
    if not os.path.exists(ARCHIVO_PEDIDOS):
        return pd.DataFrame(columns=['cliente_id','producto','cantidad','detalle','fecha'])
    df = pd.read_excel(ARCHIVO_PEDIDOS)
    df['producto'] = df['producto'].astype(str).str.lower().str.strip()
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    return df

def vista_ver_pedidos():
    """Muestra y filtra los pedidos registrados"""
    st.header("📦 Pedidos de clientes")
    df_all = cargar_todos_pedidos()
    if df_all.empty:
        st.info("No hay pedidos registrados.")
        return
    # Filtros
    productos_unicos = ["Todos"] + sorted(df_all['producto'].unique())
    producto_filtro = st.selectbox("Filtrar por producto:", productos_unicos, index=productos_unicos.index("cafe") if "cafe" in productos_unicos else 0)
    df_filtrado = df_all[df_all['producto'] == producto_filtro] if producto_filtro != "Todos" else df_all.copy()
    clientes = ["Todos"] + sorted(df_filtrado['cliente_id'].unique())
    cliente_seleccionado = st.selectbox("Filtrar por cliente:", clientes)
    if cliente_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['cliente_id'] == cliente_seleccionado]
    # Filtro por fecha
    st.markdown("#### Filtrar por rango de fechas (opcional)")
    aplicar_filtro_fecha = st.checkbox("Filtrar por fechas", value=False)
    fecha_min = df_filtrado['fecha'].min()
    fecha_max = df_filtrado['fecha'].max()
    if aplicar_filtro_fecha and pd.notnull(fecha_min) and pd.notnull(fecha_max):
        fecha_ini, fecha_fin = st.date_input("Selecciona rango:", value=(fecha_min.date(), fecha_max.date()), min_value=fecha_min.date(), max_value=fecha_max.date())
        df_filtrado = df_filtrado[(df_filtrado['fecha'] >= pd.Timestamp(fecha_ini)) & (df_filtrado['fecha'] <= pd.Timestamp(fecha_fin))]
    st.dataframe(df_filtrado.sort_values("fecha", ascending=False))
    st.info(f"Total pedidos mostrados: {len(df_filtrado)}")
    # Gráfica
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

# ---------------- FUNCIONES DE INVENTARIO Y PREDICCIÓN ----------------
def obtener_inventario_actual():
    if not os.path.exists(ARCHIVO_INVENTARIO):
        df = pd.DataFrame({'cantidad_kg':[50.0], 'fecha_actualizacion':[datetime.datetime.now()]})
        df.to_excel(ARCHIVO_INVENTARIO, index=False)
    df = pd.read_excel(ARCHIVO_INVENTARIO)
    return df.iloc[0].to_dict()

def actualizar_inventario(nueva_cantidad, usuario):
    inv_actual = obtener_inventario_actual()
    cantidad_antes = inv_actual['cantidad_kg']
    fecha_actual = datetime.datetime.now()
    # Actualiza inventario principal y guarda historial
    df_inv = pd.DataFrame({'cantidad_kg':[nueva_cantidad], 'fecha_actualizacion':[fecha_actual]})
    df_inv.to_excel(ARCHIVO_INVENTARIO, index=False)
    if os.path.exists(ARCHIVO_CONTROL):
        df_hist = pd.read_excel(ARCHIVO_CONTROL)
    else:
        df_hist = pd.DataFrame(columns=['cantidad_antes','cantidad_despues','fecha_cambio','usuario'])
    nuevo = {'cantidad_antes': cantidad_antes, 'cantidad_despues': nueva_cantidad, 'fecha_cambio': fecha_actual, 'usuario': usuario}
    df_hist = pd.concat([df_hist, pd.DataFrame([nuevo])], ignore_index=True)
    df_hist.to_excel(ARCHIVO_CONTROL, index=False)
    st.success("Inventario actualizado y registrado en historial.")

def obtener_historial():
    if not os.path.exists(ARCHIVO_CONTROL):
        return pd.DataFrame(columns=['cantidad_antes','cantidad_despues','fecha_cambio','usuario'])
    return pd.read_excel(ARCHIVO_CONTROL)

def cargar_predicciones():
    try:
        df = pd.read_excel(ARCHIVO_PREDICCIONES)
        df['fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
        df['prediccion'] = pd.to_numeric(df['Kg_Predichos'], errors='coerce')
        df = df[df['fecha'].notnull()].sort_values('fecha')
        return df[['fecha','prediccion']]
    except Exception as e:
        st.warning(f"Error leyendo predicción: {e}")
        return pd.DataFrame(columns=['fecha','prediccion'])

def cargar_pedidos_reales_cliente():
    if not os.path.exists(ARCHIVO_PEDIDOS):
        return pd.DataFrame(columns=['cliente_id','producto','cantidad','detalle','fecha'])
    df = pd.read_excel(ARCHIVO_PEDIDOS)
    df_cafe = df[df['producto'].astype(str).str.lower().str.strip() == "cafe"].copy()
    df_cafe['fecha'] = pd.to_datetime(df_cafe['fecha'], errors='coerce')
    df_cafe['cantidad'] = pd.to_numeric(df_cafe['cantidad'], errors='coerce')
    df_cafe = df_cafe[df_cafe['fecha'].notnull()]
    return df_cafe[['fecha', 'cantidad', 'cliente_id']]

def estimar_dias_restantes(inventario, df_pred):
    suma_acum, dias, fecha_lim = 0, 0, None
    for i, row in df_pred.iterrows():
        suma_acum += row['prediccion']
        dias += 1
        if suma_acum >= inventario:
            fecha_lim = row['fecha']
            break
    return dias, fecha_lim

def control_de_inventario():
    st.header("📊 Control de Inventario de Café")
    usuario = st.session_state.get("usuario", "sistema")
    inv_actual = obtener_inventario_actual()
    cantidad_kg = inv_actual["cantidad_kg"]
    st.metric("Inventario actual (kg)", f"{cantidad_kg:.1f}")
    st.write(f"Última actualización: {inv_actual.get('fecha_actualizacion')}")
    nueva_cant = st.number_input("Nueva cantidad de inventario (kg):", min_value=0.0, max_value=99999.0, value=float(cantidad_kg), step=1.0)
    if st.button("Actualizar inventario"):
        if nueva_cant != cantidad_kg:
            actualizar_inventario(nueva_cant, usuario)
        else:
            st.warning("La cantidad ingresada es igual a la actual.")
    st.subheader("Historial de movimientos")
    df_hist = obtener_historial()
    if df_hist.empty:
        st.info("No hay movimientos registrados.")
    else:
        st.dataframe(df_hist.sort_values("fecha_cambio", ascending=False))
    # Predicciones/duración inventario
    df_pred = cargar_predicciones()
    if not df_pred.empty and cantidad_kg > 0:
        hoy = pd.Timestamp(datetime.date.today())
        df_pred_fut = df_pred[df_pred['fecha'] >= hoy]
        dias_rest, fecha_lim = estimar_dias_restantes(cantidad_kg, df_pred_fut)
        if fecha_lim is not None:
            st.info(f"Te quedan **{dias_rest} días** de inventario actual según predicción. Fecha límite: **{fecha_lim.date()}**")
        else:
            st.warning("No se pudo estimar el fin de inventario con las predicciones actuales.")
    else:
        st.warning("Sin datos de predicción suficientes para estimar duración.")
    # Pedidos reales para info
    st.subheader("Pedidos proximos de café")
    df_real = cargar_pedidos_reales_cliente()
    if not df_real.empty:
        st.dataframe(df_pred)
    else:
        st.info("No hay pedidos reales disponibles.")

# ---------------- FUNCIONES DE PREDICCIÓN y COMPARACIONES ----------------
def comprobar_prediccion_cafe(fecha_real, cantidad_real):
    df_pred = cargar_predicciones()
    df_pred['dias_diferencia'] = (pd.to_datetime(fecha_real) - df_pred['fecha']).dt.days
    pred_cercana = df_pred.iloc[(df_pred['dias_diferencia'].abs()).argmin()]
    pred_fecha = pred_cercana['fecha']
    kg_predichos = pred_cercana['prediccion']
    diferencia_dias = (pd.to_datetime(fecha_real) - pred_fecha).days
    diferencia_kg = cantidad_real - kg_predichos
    return pred_fecha, kg_predichos, diferencia_dias, diferencia_kg

def guardar_comparacion_predicion(cliente, fecha_real, cantidad_real, pred_fecha, kg_predichos, diferencia_dias, diferencia_kg, fue_pred_usada=False):
    nuevo = {
        "cliente_id": cliente,
        "fecha_real": fecha_real,
        "kg_real": cantidad_real,
        "fecha_predicha": pred_fecha,
        "kg_predicha": kg_predichos,
        "dif_dias": diferencia_dias,
        "dif_kg": diferencia_kg,
        "registro": datetime.datetime.now(),
        "fue_pred_usada": fue_pred_usada
    }
    if os.path.exists(ARCHIVO_COMPARACION):
        df_comp = pd.read_excel(ARCHIVO_COMPARACION)
    else:
        df_comp = pd.DataFrame()
    df_nuevo = pd.concat([df_comp, pd.DataFrame([nuevo])], ignore_index=True)
    df_nuevo.to_excel(ARCHIVO_COMPARACION, index=False)

def eliminar_prediccion_usada(fecha_pred_usada, kg_predichos):
    df_pred = pd.read_excel(ARCHIVO_PREDICCIONES)
    df_pred['Fecha'] = pd.to_datetime(df_pred['Fecha'],format='%d/%m/%Y',errors='coerce')
    mask = ~((df_pred['Fecha'] == pd.to_datetime(fecha_pred_usada)) & (df_pred['Kg_Predichos'] == kg_predichos))
    df_pred_filtrado = df_pred[mask]
    df_pred_filtrado.to_excel(ARCHIVO_PREDICCIONES, index=False)

# ----------------- FUNCIONES DE CLIENTES Y USUARIOS -----------------
def cargar_clientes_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        return []
    df_usuarios = pd.read_excel(ARCHIVO_USUARIOS)
    clientes = df_usuarios[df_usuarios['rol'].astype(str).str.lower().str.strip() == "cliente"]['usuario'].dropna().unique()
    return sorted(map(str, clientes))

def crear_cliente():
    st.header("👤 Crear nuevo cliente")
    nombre_usuario = st.text_input("Nombre de cliente (usuario)")
    nombre_real = st.text_input("Nombre real")
    contraseña = st.text_input("contraseña")
    telefono = st.text_input("Teléfono")
    if st.button("Registrar cliente"):
        if not nombre_usuario.strip():
            st.warning("El nombre de cliente no puede estar vacío.")
            return
        if os.path.exists(ARCHIVO_USUARIOS):
            df_usuarios = pd.read_excel(ARCHIVO_USUARIOS)
        else:
            df_usuarios = pd.DataFrame(columns=['usuario','nombre','correo','telefono','rol'])
        if nombre_usuario in df_usuarios['usuario'].astype(str).values:
            st.error("Ese cliente ya existe. Usa otro nombre o edítalo.")
            return
        nuevo_usuario = {
            'usuario': nombre_usuario,
            'nombre': nombre_real,
            'contraseña': contraseña,
            'telefono': telefono,
            'rol': 'cliente'
        }
        df_final = pd.concat([df_usuarios, pd.DataFrame([nuevo_usuario])], ignore_index=True)
        df_final.to_excel(ARCHIVO_USUARIOS, index=False)
        st.success("Cliente creado exitosamente. Ya puede recibir pedidos.")

def editar_cliente():
    st.header("✏️ Editar cliente")
    if not os.path.exists(ARCHIVO_USUARIOS):
        st.info("No hay clientes registrados para editar.")
        return
    df_usuarios = pd.read_excel(ARCHIVO_USUARIOS)
    clientes = df_usuarios[df_usuarios['rol'].astype(str).str.lower().str.strip() == "cliente"]['usuario'].dropna().unique()
    if not len(clientes):
        st.info("No hay clientes con rol 'cliente' para editar.")
        return
    cliente = st.selectbox("Selecciona el cliente a editar", clientes)
    fila_idx = df_usuarios[df_usuarios['usuario'] == cliente].index[0]
    datos_actuales = df_usuarios.loc[fila_idx]
    nuevo_nombre = st.text_input("Nombre real", value=str(datos_actuales.get('nombre','')))
    nuevo_telefono = st.text_input("Teléfono", value=str(datos_actuales.get('telefono','')))
    if st.button("Guardar cambios"):
        df_usuarios.at[fila_idx, 'nombre'] = nuevo_nombre
        df_usuarios.at[fila_idx, 'telefono'] = nuevo_telefono
        df_usuarios.to_excel(ARCHIVO_USUARIOS, index=False)
        st.success("Datos del cliente actualizados correctamente.")

def borrar_cliente():
    st.header("🗑️ Borrar cliente")
    if not os.path.exists(ARCHIVO_USUARIOS):
        st.info("No hay clientes para borrar.")
        return
    df_usuarios = pd.read_excel(ARCHIVO_USUARIOS)
    clientes = df_usuarios[df_usuarios['rol'].astype(str).str.lower().str.strip() == "cliente"]['usuario'].dropna().unique()
    if not len(clientes):
        st.info("No hay clientes con rol 'cliente' para borrar.")
        return
    cliente = st.selectbox("Selecciona el cliente a borrar", clientes)
    df_pedidos = cargar_todos_pedidos()
    tiene_pedidos = not df_pedidos[df_pedidos['cliente_id'] == cliente].empty
    st.write(f"¿Eliminar cliente '{cliente}'? {'(Tiene pedidos activos, se recomienda no borrar)' if tiene_pedidos else ''}")
    seguro = st.checkbox("Estoy seguro de borrar este cliente", value=False)
    confirmar = st.button("Borrar cliente", disabled=not seguro)
    if confirmar and seguro:
        fila_idx = df_usuarios[df_usuarios['usuario'] == cliente].index[0]
        df_usuarios_new = df_usuarios.drop(fila_idx)
        df_usuarios_new.to_excel(ARCHIVO_USUARIOS, index=False)
        st.success(f"Cliente '{cliente}' borrado correctamente.")
        if tiene_pedidos:
            st.warning("¡Este cliente tenía pedidos registrados! Estos datos NO se han borrado del historial de pedidos.")

# ------------ FUNCIONES DE GESTIÓN DE PEDIDOS -------------
def registrar_pedido():
    st.header("📝 Registrar nuevo pedido")
    df_pred = cargar_predicciones()
    hoy = pd.Timestamp(datetime.date.today())
    df_pred_fut = df_pred[df_pred['fecha'] >= hoy]
    prox_opciones = df_pred_fut.head(5).copy()
    prox_opciones['texto'] = prox_opciones.apply(lambda r: f"{r['fecha'].date()} | {r['prediccion']:.1f}kg", axis=1)
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

    clientes_validos = cargar_clientes_usuarios()
    if not clientes_validos:
        st.error("No hay clientes registrados en el sistema.")
        return
    cliente = st.selectbox("Cliente", clientes_validos)
    producto = st.selectbox("Producto", ["cafe", "otro"])
    cantidad_pedido = st.number_input("Cantidad (kg)", min_value=0.0, max_value=99999.0, value=sugerir_kg)
    fecha_pedido = st.date_input("Fecha del pedido", value=sugerir_fecha)
    detalle = st.text_input("Detalle (opcional)")
    if st.button("Agregar pedido"):
        df_pedidos = cargar_todos_pedidos()
        if producto.lower() == "cafe" and pred_usada:
            pred_fecha, kg_predichos, diferencia_dias, diferencia_kg = comprobar_prediccion_cafe(fecha_pedido, cantidad_pedido)
            st.success(f"Comparación con predicción:\n"  f"Predicción: {kg_predichos:.1f} kg para {pred_fecha.date()}\n"  f"Pedido real: {cantidad_pedido:.1f} kg para {fecha_pedido}\n"  f"Diferencia: {diferencia_dias:+} días, {diferencia_kg:+.1f} kg")
            guardar_comparacion_predicion(cliente, fecha_pedido, cantidad_pedido, pred_fecha, kg_predichos, diferencia_dias, diferencia_kg, fue_pred_usada=True)
            eliminar_prediccion_usada(pred_fecha, kg_predichos)
        elif producto.lower() == "cafe":
            pred_fecha, kg_predichos, diferencia_dias, diferencia_kg = None, None, None, None
        nuevo_pedido = {
            'cliente_id': cliente,
            'producto': producto,
            'cantidad': cantidad_pedido,
            'detalle': detalle,
            'fecha': fecha_pedido
        }
        df_final = pd.concat([df_pedidos, pd.DataFrame([nuevo_pedido])], ignore_index=True)
        df_final.to_excel(ARCHIVO_PEDIDOS, index=False)
        st.success("Pedido registrado. Comparación (y predicción usada) guardada en control auxiliar y archivo de predicciones actualizado.")

# ------------ GESTIÓN DE ELIMINACIÓN DE PEDIDOS ------------
def guardar_log_eliminacion(fila_eliminada, usuario):
    fila_elim = fila_eliminada.to_dict()
    fila_elim["usuario"] = usuario
    fila_elim["fecha_eliminacion"] = datetime.datetime.now()
    if os.path.exists(ARCHIVO_ELIMINADOS):
        df_log = pd.read_excel(ARCHIVO_ELIMINADOS)
    else:
        df_log = pd.DataFrame()
    df_nuevo = pd.concat([df_log, pd.DataFrame([fila_elim])], ignore_index=True)
    df_nuevo.to_excel(ARCHIVO_ELIMINADOS, index=False)

def eliminar_pedido():
    st.header("🗑️ Eliminar pedido")
    usuario = st.session_state.get("usuario", "desconocido")
    df_pedidos = cargar_todos_pedidos()
    if df_pedidos.empty:
        st.info("No hay pedidos registrados para eliminar.")
        return
    clientes = ["Todos"] + sorted(df_pedidos['cliente_id'].dropna().unique())
    cliente_seleccionado = st.selectbox("Filtrar por cliente", clientes)
    df_filtrado = df_pedidos[df_pedidos['cliente_id'] == cliente_seleccionado].copy() if cliente_seleccionado != "Todos" else df_pedidos.copy()
    fechas = ["Todas"] + sorted(list(set(str(f)[:10] for f in df_filtrado['fecha'] if pd.notna(f))))
    fecha_seleccionada = st.selectbox("Filtrar por fecha", fechas)
    if fecha_seleccionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['fecha'].astype(str).str.startswith(fecha_seleccionada)]
    df_filtrado["info"] = df_filtrado.apply(lambda r: f"{r['cliente_id']} | {r['producto']} | {r['cantidad']} kg | {r['fecha']}", axis=1)
    if df_filtrado.empty:
        st.warning("No hay pedidos con esos filtros.")
        return
    idx_seleccionado = st.selectbox("Selecciona el pedido a eliminar", options=list(df_filtrado.index), format_func=lambda i: df_filtrado.loc[i, 'info'])
    st.write("**Detalles del pedido a eliminar:**")
    st.write(df_filtrado.loc[idx_seleccionado])
    seguro = st.checkbox("Estoy seguro de eliminar este pedido", value=False)
    confirmar = st.button("Eliminar pedido", disabled=not seguro)
    if confirmar and seguro:
        guardar_log_eliminacion(df_filtrado.loc[idx_seleccionado], usuario)
        df_nuevo = df_pedidos.drop(idx_seleccionado)
        df_nuevo.to_excel(ARCHIVO_PEDIDOS, index=False)
        st.success("Pedido eliminado y guardado en registro de auditoría.")

# ------------ ESTADÍSTICAS Y DASHBOARD ------------
def resumen_estadisticas_globales():
    st.header("📊 Resumen y Estadísticas Globales")
    pedidos = cargar_todos_pedidos()
    inventario = obtener_inventario_actual()
    clientes = cargar_clientes_usuarios()
    total_pedidos = len(pedidos)
    total_kg = pedidos['cantidad'].sum() if not pedidos.empty else 0
    pedidos_por_prod = pedidos.groupby('producto').agg({'cantidad':'sum','fecha':'count'}).rename(columns={'fecha':'num_pedidos'})
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
    # Exactitud (si hay)
    if os.path.exists(ARCHIVO_COMPARACION):
        comp = pd.read_excel(ARCHIVO_COMPARACION)
        comp = comp[comp['fue_pred_usada'] == True]
        if not comp.empty:
            st.subheader("Exactitud modelo de predicción (solo pedidos asociados)")
            mean_dia = comp['dif_dias'].mean()
            std_dia = comp['dif_dias'].std()
            mean_kg = comp['dif_kg'].mean()
            std_kg = comp['dif_kg'].std()
            st.write(f"- Diferencia promedio días: {mean_dia:+.2f}")
            st.write(f"- Diferencia promedio kg: {mean_kg:+.2f}")
            st.write(f"- Desviación estándar días: {std_dia:.2f}")
            st.write(f"- Desviación estándar kg: {std_kg:.2f}")
            st.markdown("#### Distribución de diferencias (hist)")
            fig, ax = plt.subplots(1,2,figsize=(10,4))
            comp['dif_dias'].hist(ax=ax[0], bins=15, color="tab:blue")
            ax[0].set_title("Diferencia vs predicción (días)")
            ax[0].set_xlabel("Dif. días")
            ax[0].set_ylabel("Número de pedidos")
            comp['dif_kg'].hist(ax=ax[1], bins=15, color="tab:green")
            ax[1].set_title("Diferencia vs predicción (kg)")
            ax[1].set_xlabel("Dif. kg")
            st.pyplot(fig)
        else:
            st.info("No hay pedidos asociados a predicción para evaluar exactitud.")
    else:
        st.info("Archivo de comparaciones no encontrado.")
    # Auditoría eliminaciones
    if os.path.exists(ARCHIVO_ELIMINADOS):
        elim = pd.read_excel(ARCHIVO_ELIMINADOS)
        st.subheader("Auditoría: Pedidos eliminados")
        st.write(f"Pedidos eliminados: {len(elim)}")
        st.dataframe(elim[['cliente_id','producto','cantidad','fecha','fecha_eliminacion','usuario']])
    else:
        st.info("No hay eliminaciones registradas.")
    st.subheader("Ranking de clientes (por kg)")
    if not pedidos.empty:
        ranking = pedidos.groupby('cliente_id').agg(total_kg=('cantidad','sum'), pedidos=('fecha','count')).sort_values("total_kg", ascending=False)
        st.write("Top clientes por kg vendido:")
        st.dataframe(ranking)
    else:
        st.info("No hay ventas registradas en el periodo.")

# ----------- DASHBOARD MENÚ PRINCIPAL -----------
st.sidebar.title("Menú proveedor")
opcion = st.sidebar.radio("Opciones:", [
    "Clientes",
    "Registrar pedido",
    "Ver pedidos",
    "Eliminar pedido",
    "Control de inventario",
    "Resumen/Estadísticas",
    "Salir"
])

if opcion == "Resumen/Estadísticas":
    resumen_estadisticas_globales()
elif opcion == "Clientes":
    st.header("👤 Gestión de clientes")
    accion = st.radio("¿Qué acción deseas realizar?", ["Crear", "Editar", "Borrar"])
    if accion == "Crear":
        crear_cliente()
    elif accion == "Editar":
        editar_cliente()
    elif accion == "Borrar":
        borrar_cliente()
elif opcion == "Registrar pedido":
    registrar_pedido()
elif opcion == "Ver pedidos":
    vista_ver_pedidos()
elif opcion == "Eliminar pedido":
    eliminar_pedido()
elif opcion == "Control de inventario":
    control_de_inventario()
elif opcion == "Salir":
    st.session_state["rol"] = None
    st.session_state["usuario"] = None
    st.experimental_rerun()
