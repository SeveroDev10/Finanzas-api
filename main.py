import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import hashlib
import csv
from datetime import datetime, date
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ARCHIVO = "Finanzas_data.json"

CATEGORIAS_DEFAULT = [
    "Alimentación", "Transporte", "Salud", "Educación",
    "Entretenimiento", "Ropa", "Hogar", "Servicios", "Trabajo", "Otro"
]

# -------- PERSISTENCIA --------
def cargar():
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar(data):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# -------- ESTADO GLOBAL --------
usuarios = cargar()
usuario_actual = None

def datos():
    return usuarios[usuario_actual]

def movimientos():
    return datos()["movimientos"]

def presupuestos():
    return datos().setdefault("presupuestos", {})

def categorias():
    return datos().setdefault("categorias", list(CATEGORIAS_DEFAULT))

def recordatorios():
    return datos().setdefault("recordatorios", [])

# -------- AUTH --------
def login():
    global usuario_actual
    u = user_entry.get().strip()
    p = pass_entry.get()
    if not u or not p:
        messagebox.showwarning("Atención", "Completa usuario y contraseña.")
        return
    if u in usuarios and usuarios[u]["pass"] == hash_password(p):
        usuario_actual = u
        abrir_app()
    else:
        messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

def registrar():
    u = user_entry.get().strip()
    p = pass_entry.get()
    if not u or not p:
        messagebox.showwarning("Atención", "Completa usuario y contraseña.")
        return
    if len(p) < 4:
        messagebox.showwarning("Atención", "La contraseña debe tener al menos 4 caracteres.")
        return
    if u in usuarios:
        messagebox.showerror("Error", "Ese usuario ya existe.")
        return
    usuarios[u] = {
        "pass": hash_password(p),
        "movimientos": [],
        "presupuestos": {},
        "categorias": list(CATEGORIAS_DEFAULT),
        "recordatorios": []
    }
    guardar(usuarios)
    messagebox.showinfo("Registro exitoso", f"Cuenta creada para '{u}'.")

def cerrar_sesion():
    global usuario_actual
    usuario_actual = None
    app_frame.pack_forget()
    login_frame.pack(fill="both", expand=True)
    user_entry.delete(0, "end")
    pass_entry.delete(0, "end")

# -------- MOVIMIENTOS --------
def agregar(tipo):
    try:
        monto_txt = entry_monto.get().strip()
        nombre = entry_nombre.get().strip()
        desc = entry_desc.get().strip()
        categoria = combo_categoria.get().strip()

        if not monto_txt or not nombre:
            messagebox.showwarning("Atención", "Monto y nombre son obligatorios.")
            return
        monto = float(monto_txt)
        if monto <= 0:
            messagebox.showwarning("Atención", "El monto debe ser mayor a 0.")
            return

        fecha = datetime.now()
        movimientos().append({
            "tipo": tipo,
            "monto": round(monto, 2),
            "nombre": nombre,
            "desc": desc,
            "categoria": categoria,
            "mes": fecha.month,
            "año": fecha.year,
            "hora": fecha.hour,
            "fecha_iso": fecha.isoformat()
        })
        guardar(usuarios)
        limpiar_entradas()
        actualizar()
        revisar_alertas(categoria, tipo)
    except ValueError:
        messagebox.showerror("Error", "El monto debe ser un número válido.")

def limpiar_entradas():
    entry_monto.delete(0, "end")
    entry_nombre.delete(0, "end")
    entry_desc.delete(0, "end")

def eliminar():
    sel = tabla.focus()
    if not sel:
        messagebox.showwarning("Atención", "Selecciona un movimiento.")
        return
    if messagebox.askyesno("Confirmar", "¿Eliminar este movimiento?"):
        del movimientos()[int(sel)]
        guardar(usuarios)
        actualizar()

def editar():
    sel = tabla.focus()
    if not sel:
        messagebox.showwarning("Atención", "Selecciona un movimiento.")
        return
    m = movimientos()[int(sel)]
    nuevo = simpledialog.askfloat("Editar", "Nuevo monto:", initialvalue=m["monto"])
    if nuevo is None or nuevo <= 0:
        return
    nombre = simpledialog.askstring("Editar", "Nombre:", initialvalue=m["nombre"])
    desc = simpledialog.askstring("Editar", "Descripción:", initialvalue=m.get("desc", ""))
    m["monto"] = round(nuevo, 2)
    m["nombre"] = nombre or m["nombre"]
    m["desc"] = desc or ""
    guardar(usuarios)
    actualizar()

def get_movimientos_filtrados():
    filtro_texto = entry_buscar.get().strip().lower()
    filtro_tipo = combo_filtro_tipo.get()
    filtro_cat = combo_filtro_cat.get()
    resultado = []
    for i, m in enumerate(movimientos()):
        if filtro_tipo != "Todos" and m["tipo"] != filtro_tipo:
            continue
        if filtro_cat != "Todas" and m.get("categoria", "") != filtro_cat:
            continue
        if filtro_texto and filtro_texto not in m["nombre"].lower() and filtro_texto not in m.get("desc", "").lower():
            continue
        resultado.append((i, m))
    return resultado

def actualizar():
    tabla.delete(*tabla.get_children())
    saldo = ingresos_total = gastos_total = 0
    for i, m in get_movimientos_filtrados():
        if m["tipo"] == "Ingreso":
            saldo += m["monto"]
            ingresos_total += m["monto"]
        else:
            saldo -= m["monto"]
            gastos_total += m["monto"]
        tabla.insert("", "end", iid=i,
                     values=(m["tipo"], m["nombre"], m.get("categoria", ""), f"${m['monto']:.2f}", m["mes"], m["año"]),
                     tags=(m["tipo"],))
    tabla.tag_configure("Ingreso", foreground="#2ecc71")
    tabla.tag_configure("Gasto", foreground="#e74c3c")
    color_saldo = "#2ecc71" if saldo >= 0 else "#e74c3c"
    label_saldo.configure(text=f"${saldo:.2f}", text_color=color_saldo)
    label_ingresos.configure(text=f"Ingresos: ${ingresos_total:.2f}")
    label_gastos.configure(text=f"Gastos: ${gastos_total:.2f}")
    actualizar_combo_categorias()
    revisar_recordatorios()

def aplicar_filtro(*args):
    actualizar()

# -------- CATEGORÍAS --------
def actualizar_combo_categorias():
    cats = categorias()
    combo_categoria.configure(values=cats)
    combo_filtro_cat.configure(values=["Todas"] + cats)

def ventana_categorias():
    win = ctk.CTkToplevel(app)
    win.title("Gestionar Categorías")
    win.geometry("350x450")
    win.grab_set()
    ctk.CTkLabel(win, text="Mis Categorías", font=("Arial", 16, "bold")).pack(pady=10)
    lista_frame = ctk.CTkScrollableFrame(win, height=250)
    lista_frame.pack(fill="x", padx=10)

    def refrescar():
        for w in lista_frame.winfo_children():
            w.destroy()
        for cat in categorias():
            row = ctk.CTkFrame(lista_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=cat, width=200, anchor="w").pack(side="left", padx=5)
            ctk.CTkButton(row, text="🗑️", width=35, fg_color="#c0392b",
                          command=lambda c=cat: eliminar_cat(c)).pack(side="right")

    def eliminar_cat(cat):
        if cat in categorias():
            categorias().remove(cat)
            guardar(usuarios)
            refrescar()
            actualizar_combo_categorias()

    nueva_entry = ctk.CTkEntry(win, placeholder_text="Nueva categoría")
    nueva_entry.pack(pady=10, padx=10, fill="x")

    def agregar_cat():
        nombre = nueva_entry.get().strip()
        if nombre and nombre not in categorias():
            categorias().append(nombre)
            guardar(usuarios)
            nueva_entry.delete(0, "end")
            refrescar()
            actualizar_combo_categorias()

    ctk.CTkButton(win, text="➕ Agregar categoría", command=agregar_cat).pack(pady=5)
    refrescar()

# -------- PRESUPUESTOS --------
def ventana_presupuestos():
    win = ctk.CTkToplevel(app)
    win.title("Presupuestos por Categoría")
    win.geometry("420x500")
    win.grab_set()
    ctk.CTkLabel(win, text="💰 Presupuestos mensuales", font=("Arial", 16, "bold")).pack(pady=10)
    mes_actual = datetime.now().month
    año_actual = datetime.now().year
    gastos_mes = {}
    for m in movimientos():
        if m["tipo"] == "Gasto" and m["mes"] == mes_actual and m["año"] == año_actual:
            cat = m.get("categoria", "Otro")
            gastos_mes[cat] = gastos_mes.get(cat, 0) + m["monto"]
    scroll = ctk.CTkScrollableFrame(win, height=300)
    scroll.pack(fill="both", expand=True, padx=10)
    entradas = {}
    for cat in categorias():
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=cat, width=130, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, placeholder_text="Límite $", width=90)
        presup_actual = presupuestos().get(cat, "")
        if presup_actual:
            entry.insert(0, str(presup_actual))
        entry.pack(side="left", padx=5)
        gasto_real = gastos_mes.get(cat, 0)
        color = "#e74c3c" if presup_actual and gasto_real > presup_actual else "#2ecc71"
        ctk.CTkLabel(row, text=f"Gastado: ${gasto_real:.2f}", text_color=color, width=130).pack(side="left")
        entradas[cat] = entry

    def guardar_presupuestos():
        for cat, entry in entradas.items():
            val = entry.get().strip()
            if val:
                try:
                    presupuestos()[cat] = float(val)
                except ValueError:
                    pass
            elif cat in presupuestos():
                del presupuestos()[cat]
        guardar(usuarios)
        messagebox.showinfo("✅", "Presupuestos guardados.")
        win.destroy()

    ctk.CTkButton(win, text="💾 Guardar presupuestos", command=guardar_presupuestos).pack(pady=10)

def revisar_alertas(categoria, tipo):
    if tipo != "Gasto":
        return
    limite = presupuestos().get(categoria)
    if not limite:
        return
    mes_actual = datetime.now().month
    año_actual = datetime.now().year
    total = sum(m["monto"] for m in movimientos()
                if m["tipo"] == "Gasto" and m.get("categoria") == categoria
                and m["mes"] == mes_actual and m["año"] == año_actual)
    porcentaje = (total / limite) * 100
    if porcentaje >= 100:
        messagebox.showwarning("🚨 Presupuesto excedido",
                               f"¡Superaste el presupuesto de {categoria}!\nLímite: ${limite:.2f} | Gastado: ${total:.2f}")
    elif porcentaje >= 80:
        messagebox.showwarning("⚠️ Alerta de presupuesto",
                               f"Llevas el {porcentaje:.0f}% del presupuesto de {categoria}.\nLímite: ${limite:.2f} | Gastado: ${total:.2f}")

# -------- RECORDATORIOS --------
def ventana_recordatorios():
    win = ctk.CTkToplevel(app)
    win.title("📅 Recordatorios de Pagos")
    win.geometry("480x500")
    win.grab_set()
    ctk.CTkLabel(win, text="📅 Recordatorios", font=("Arial", 16, "bold")).pack(pady=10)
    scroll = ctk.CTkScrollableFrame(win, height=220)
    scroll.pack(fill="both", expand=True, padx=10)

    def refrescar():
        for w in scroll.winfo_children():
            w.destroy()
        for idx, r in enumerate(recordatorios()):
            row = ctk.CTkFrame(scroll, fg_color="#1e3a5f" if not r.get("pagado") else "#1a3a1a")
            row.pack(fill="x", pady=3, padx=2)
            estado = "✅" if r.get("pagado") else "🔔"
            ctk.CTkLabel(row, text=f"{estado} {r['nombre']} — ${r['monto']:.2f} — {r['fecha']}",
                         anchor="w").pack(side="left", padx=8, pady=4)
            if not r.get("pagado"):
                ctk.CTkButton(row, text="Pagar", width=60, fg_color="#27ae60",
                              command=lambda i=idx: marcar_pagado(i)).pack(side="right", padx=4)
            ctk.CTkButton(row, text="🗑️", width=35, fg_color="#c0392b",
                          command=lambda i=idx: eliminar_recordatorio(i)).pack(side="right", padx=2)

    def marcar_pagado(idx):
        recordatorios()[idx]["pagado"] = True
        guardar(usuarios)
        refrescar()

    def eliminar_recordatorio(idx):
        del recordatorios()[idx]
        guardar(usuarios)
        refrescar()

    ctk.CTkLabel(win, text="Nuevo recordatorio:", font=("Arial", 12)).pack(pady=(10, 0))
    form = ctk.CTkFrame(win)
    form.pack(fill="x", padx=10, pady=5)
    entry_rec_nombre = ctk.CTkEntry(form, placeholder_text="Nombre del pago", width=150)
    entry_rec_nombre.grid(row=0, column=0, padx=4, pady=4)
    entry_rec_monto = ctk.CTkEntry(form, placeholder_text="Monto", width=90)
    entry_rec_monto.grid(row=0, column=1, padx=4, pady=4)
    entry_rec_fecha = ctk.CTkEntry(form, placeholder_text="Fecha DD/MM/AAAA", width=150)
    entry_rec_fecha.grid(row=0, column=2, padx=4, pady=4)

    def agregar_recordatorio():
        nombre = entry_rec_nombre.get().strip()
        monto_txt = entry_rec_monto.get().strip()
        fecha_txt = entry_rec_fecha.get().strip()
        if not nombre or not monto_txt or not fecha_txt:
            messagebox.showwarning("Atención", "Completa todos los campos.")
            return
        try:
            monto = float(monto_txt)
            datetime.strptime(fecha_txt, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Error", "Monto o fecha inválidos. Usa DD/MM/AAAA.")
            return
        recordatorios().append({"nombre": nombre, "monto": monto, "fecha": fecha_txt, "pagado": False})
        guardar(usuarios)
        entry_rec_nombre.delete(0, "end")
        entry_rec_monto.delete(0, "end")
        entry_rec_fecha.delete(0, "end")
        refrescar()

    ctk.CTkButton(win, text="➕ Agregar recordatorio", command=agregar_recordatorio).pack(pady=5)
    refrescar()

def revisar_recordatorios():
    hoy = date.today()
    pendientes = []
    for r in recordatorios():
        if r.get("pagado"):
            continue
        try:
            fecha_rec = datetime.strptime(r["fecha"], "%d/%m/%Y").date()
            dias = (fecha_rec - hoy).days
            if 0 <= dias <= 3:
                pendientes.append(f"• {r['nombre']} ${r['monto']:.2f} vence {r['fecha']}")
        except ValueError:
            pass
    if pendientes:
        label_recordatorio.configure(text="🔔 " + " | ".join(pendientes), text_color="#f39c12")
    else:
        label_recordatorio.configure(text="", text_color="gray")

# -------- EXPORTAR --------
def exportar_csv():
    nombre_archivo = f"finanzas_{usuario_actual}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(nombre_archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Tipo", "Nombre", "Categoría", "Monto", "Descripción", "Mes", "Año", "Fecha"])
        for m in movimientos():
            writer.writerow([m["tipo"], m["nombre"], m.get("categoria", ""),
                             m["monto"], m.get("desc", ""), m["mes"], m["año"], m.get("fecha_iso", "")])
    messagebox.showinfo("✅ Exportado", f"Guardado como:\n{nombre_archivo}")

def exportar_txt():
    nombre_archivo = f"reporte_{usuario_actual}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    saldo = ingresos_total = gastos_total = 0
    for m in movimientos():
        if m["tipo"] == "Ingreso":
            saldo += m["monto"]
            ingresos_total += m["monto"]
        else:
            saldo -= m["monto"]
            gastos_total += m["monto"]
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("=" * 45 + "\n")
        f.write(f"  REPORTE FINANCIERO — {usuario_actual.upper()}\n")
        f.write(f"  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        f.write("=" * 45 + "\n\n")
        f.write(f"  Ingresos totales : ${ingresos_total:.2f}\n")
        f.write(f"  Gastos totales   : ${gastos_total:.2f}\n")
        f.write(f"  Saldo actual     : ${saldo:.2f}\n\n")
        f.write("-" * 45 + "\n")
        f.write(f"{'Tipo':<10} {'Nombre':<18} {'Cat':<12} {'Monto':>8}\n")
        f.write("-" * 45 + "\n")
        for m in movimientos():
            f.write(f"{m['tipo']:<10} {m['nombre'][:17]:<18} {m.get('categoria','')[:11]:<12} ${m['monto']:>7.2f}\n")
        f.write("=" * 45 + "\n")
    messagebox.showinfo("✅ Exportado", f"Guardado como:\n{nombre_archivo}")

# -------- RESÚMENES --------
def resumen_mensual():
    resumen = {}
    for m in movimientos():
        clave = f"{m['mes']:02d}/{m['año']}"
        resumen.setdefault(clave, {"ingresos": 0, "gastos": 0})
        if m["tipo"] == "Ingreso":
            resumen[clave]["ingresos"] += m["monto"]
        else:
            resumen[clave]["gastos"] += m["monto"]
    if not resumen:
        messagebox.showinfo("Resumen mensual", "No hay movimientos.")
        return
    lines = [f"{k}  |  +${v['ingresos']:.2f}  -${v['gastos']:.2f}  = ${v['ingresos']-v['gastos']:.2f}"
             for k, v in sorted(resumen.items())]
    messagebox.showinfo("Resumen mensual", "\n".join(lines))

def resumen_anual():
    resumen = {}
    for m in movimientos():
        resumen.setdefault(m["año"], {"ingresos": 0, "gastos": 0})
        if m["tipo"] == "Ingreso":
            resumen[m["año"]]["ingresos"] += m["monto"]
        else:
            resumen[m["año"]]["gastos"] += m["monto"]
    if not resumen:
        messagebox.showinfo("Resumen anual", "No hay movimientos.")
        return
    lines = [f"{k}  |  +${v['ingresos']:.2f}  -${v['gastos']:.2f}  = ${v['ingresos']-v['gastos']:.2f}"
             for k, v in sorted(resumen.items())]
    messagebox.showinfo("Resumen anual", "\n".join(lines))

# -------- GRÁFICAS --------
def mostrar_grafica(fig):
    win = ctk.CTkToplevel(app)
    win.title("Gráfica")
    win.geometry("700x500")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def grafica_ingresos_gastos():
    if not movimientos():
        messagebox.showinfo("Info", "No hay movimientos.")
        return
    ingresos = sum(m["monto"] for m in movimientos() if m["tipo"] == "Ingreso")
    gastos = sum(m["monto"] for m in movimientos() if m["tipo"] == "Gasto")
    fig, ax = plt.subplots(facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    bars = ax.bar(["Ingresos", "Gastos"], [ingresos, gastos], color=["#2ecc71", "#e74c3c"])
    ax.set_title("Ingresos vs Gastos", color="white", fontsize=14)
    ax.tick_params(colors="white")
    for spine in ax.spines.values(): spine.set_edgecolor("#444")
    for bar, val in zip(bars, [ingresos, gastos]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()+0.5, f"${val:.2f}", ha="center", color="white")
    mostrar_grafica(fig)

def grafica_pastel():
    cats = {}
    for m in movimientos():
        if m["tipo"] == "Gasto":
            cat = m.get("categoria", "Otro")
            cats[cat] = cats.get(cat, 0) + m["monto"]
    if not cats:
        messagebox.showinfo("Info", "No hay gastos.")
        return
    fig, ax = plt.subplots(facecolor="#1a1a2e")
    ax.pie(list(cats.values()), labels=list(cats.keys()), autopct="%1.1f%%", textprops={"color": "white"})
    ax.set_title("Distribución de gastos", color="white", fontsize=14)
    mostrar_grafica(fig)

def grafica_linea():
    if not movimientos():
        messagebox.showinfo("Info", "No hay movimientos.")
        return
    saldo, valores, fechas = 0, [], []
    for m in movimientos():
        saldo += m["monto"] if m["tipo"] == "Ingreso" else -m["monto"]
        valores.append(round(saldo, 2))
        fechas.append(f"{m['mes']:02d}/{m['año']}")
    fig, ax = plt.subplots(facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.plot(fechas, valores, marker="o", color="#3498db", linewidth=2)
    ax.fill_between(range(len(valores)), valores, alpha=0.15, color="#3498db")
    ax.set_title("Evolución del saldo", color="white", fontsize=14)
    ax.tick_params(colors="white")
    ax.set_xticklabels(fechas, rotation=45, ha="right")
    for spine in ax.spines.values(): spine.set_edgecolor("#444")
    fig.tight_layout()
    mostrar_grafica(fig)

def grafica_presupuestos():
    if not presupuestos():
        messagebox.showinfo("Info", "No hay presupuestos configurados.")
        return
    mes_actual = datetime.now().month
    año_actual = datetime.now().year
    gastos_mes = {}
    for m in movimientos():
        if m["tipo"] == "Gasto" and m["mes"] == mes_actual and m["año"] == año_actual:
            cat = m.get("categoria", "Otro")
            gastos_mes[cat] = gastos_mes.get(cat, 0) + m["monto"]
    cats = list(presupuestos().keys())
    limites = [presupuestos()[c] for c in cats]
    gastados = [gastos_mes.get(c, 0) for c in cats]
    x = range(len(cats))
    fig, ax = plt.subplots(facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.bar([i-0.2 for i in x], limites, width=0.4, label="Presupuesto", color="#3498db")
    ax.bar([i+0.2 for i in x], gastados, width=0.4, label="Gastado", color="#e74c3c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, rotation=30, ha="right", color="white")
    ax.tick_params(colors="white")
    ax.set_title("Presupuesto vs Gasto real (mes actual)", color="white", fontsize=13)
    ax.legend(facecolor="#1a1a2e", labelcolor="white")
    for spine in ax.spines.values(): spine.set_edgecolor("#444")
    fig.tight_layout()
    mostrar_grafica(fig)

# ======================================================
# UI
# ======================================================
app = ctk.CTk()
app.geometry("1050x620")
app.title("💰 Finanzas Fáciles")
app.resizable(True, True)

# LOGIN
login_frame = ctk.CTkFrame(app)
login_frame.pack(fill="both", expand=True)

ctk.CTkLabel(login_frame, text="💰 Finanzas Fáciles", font=("Arial", 28, "bold")).pack(pady=30)
ctk.CTkLabel(login_frame, text="Inicia sesión o crea una cuenta", font=("Arial", 13), text_color="gray").pack()

user_entry = ctk.CTkEntry(login_frame, placeholder_text="Usuario", width=280)
user_entry.pack(pady=10)
pass_entry = ctk.CTkEntry(login_frame, placeholder_text="Contraseña", show="*", width=280)
pass_entry.pack(pady=10)

app.bind("<Return>", lambda e: login())
ctk.CTkButton(login_frame, text="Entrar", command=login, width=280).pack(pady=5)
ctk.CTkButton(login_frame, text="Registrar", command=registrar, width=280,
              fg_color="transparent", border_width=2).pack(pady=5)

# APP FRAME
app_frame = ctk.CTkFrame(app)

# Sidebar
sidebar = ctk.CTkFrame(app_frame, width=210, corner_radius=0)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

ctk.CTkLabel(sidebar, text="💰 Finanzas Fáciles", font=("Arial", 15, "bold")).pack(pady=15)

ctk.CTkLabel(sidebar, text="📋 Resúmenes", font=("Arial", 11), text_color="gray").pack(pady=(8,0))
ctk.CTkButton(sidebar, text="Resumen mensual", command=resumen_mensual, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="Resumen anual", command=resumen_anual, width=185).pack(pady=3)

ctk.CTkLabel(sidebar, text="⚙️ Gestión", font=("Arial", 11), text_color="gray").pack(pady=(12,0))
ctk.CTkButton(sidebar, text="💰 Presupuestos", command=ventana_presupuestos, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="🏷️ Categorías", command=ventana_categorias, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="📅 Recordatorios", command=ventana_recordatorios, width=185).pack(pady=3)

ctk.CTkLabel(sidebar, text="📊 Gráficas", font=("Arial", 11), text_color="gray").pack(pady=(12,0))
ctk.CTkButton(sidebar, text="Ingresos vs Gastos", command=grafica_ingresos_gastos, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="Gastos por categoría", command=grafica_pastel, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="Evolución del saldo", command=grafica_linea, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="Presupuesto vs Real", command=grafica_presupuestos, width=185).pack(pady=3)

ctk.CTkLabel(sidebar, text="📤 Exportar", font=("Arial", 11), text_color="gray").pack(pady=(12,0))
ctk.CTkButton(sidebar, text="Exportar CSV", command=exportar_csv, width=185).pack(pady=3)
ctk.CTkButton(sidebar, text="Exportar reporte .txt", command=exportar_txt, width=185).pack(pady=3)

ctk.CTkButton(sidebar, text="🚪 Cerrar sesión", command=cerrar_sesion,
              width=185, fg_color="#c0392b", hover_color="#922b21").pack(side="bottom", pady=15)

# Main area
main = ctk.CTkFrame(app_frame)
main.pack(side="right", fill="both", expand=True, padx=8, pady=8)

# Saldo
top_frame = ctk.CTkFrame(main)
top_frame.pack(fill="x", pady=(0,6))

label_saldo = ctk.CTkLabel(top_frame, text="$0.00", font=("Arial", 36, "bold"))
label_saldo.pack(side="left", padx=20)

metrics_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
metrics_frame.pack(side="right", padx=20)
label_ingresos = ctk.CTkLabel(metrics_frame, text="Ingresos: $0.00", font=("Arial", 13), text_color="#2ecc71")
label_ingresos.pack(anchor="e")
label_gastos = ctk.CTkLabel(metrics_frame, text="Gastos: $0.00", font=("Arial", 13), text_color="#e74c3c")
label_gastos.pack(anchor="e")

label_recordatorio = ctk.CTkLabel(main, text="", font=("Arial", 11), text_color="#f39c12")
label_recordatorio.pack(fill="x", padx=5)

# Formulario
form_frame = ctk.CTkFrame(main)
form_frame.pack(fill="x", pady=4)

entry_monto = ctk.CTkEntry(form_frame, placeholder_text="Monto", width=110)
entry_monto.grid(row=0, column=0, padx=4, pady=4)
entry_nombre = ctk.CTkEntry(form_frame, placeholder_text="Nombre", width=160)
entry_nombre.grid(row=0, column=1, padx=4, pady=4)
entry_desc = ctk.CTkEntry(form_frame, placeholder_text="Descripción (opcional)", width=180)
entry_desc.grid(row=0, column=2, padx=4, pady=4)
combo_categoria = ctk.CTkComboBox(form_frame, values=CATEGORIAS_DEFAULT, width=150)
combo_categoria.set("Otro")
combo_categoria.grid(row=0, column=3, padx=4, pady=4)

# Botones
btn_frame = ctk.CTkFrame(main, fg_color="transparent")
btn_frame.pack(pady=4)
ctk.CTkButton(btn_frame, text="➕ Ingreso", command=lambda: agregar("Ingreso"),
              fg_color="#27ae60", hover_color="#1e8449", width=115).pack(side="left", padx=4)
ctk.CTkButton(btn_frame, text="➖ Gasto", command=lambda: agregar("Gasto"),
              fg_color="#c0392b", hover_color="#922b21", width=115).pack(side="left", padx=4)
ctk.CTkButton(btn_frame, text="✏️ Editar", command=editar, width=115).pack(side="left", padx=4)
ctk.CTkButton(btn_frame, text="🗑️ Eliminar", command=eliminar,
              fg_color="#7f8c8d", hover_color="#636e72", width=115).pack(side="left", padx=4)

# Filtros y búsqueda
filtro_frame = ctk.CTkFrame(main, fg_color="transparent")
filtro_frame.pack(fill="x", pady=4)
ctk.CTkLabel(filtro_frame, text="🔍", font=("Arial", 14)).pack(side="left", padx=(4,0))
entry_buscar = ctk.CTkEntry(filtro_frame, placeholder_text="Buscar...", width=180)
entry_buscar.pack(side="left", padx=4)
entry_buscar.bind("<KeyRelease>", aplicar_filtro)

combo_filtro_tipo = ctk.CTkComboBox(filtro_frame, values=["Todos", "Ingreso", "Gasto"],
                                    width=110, command=aplicar_filtro)
combo_filtro_tipo.set("Todos")
combo_filtro_tipo.pack(side="left", padx=4)

combo_filtro_cat = ctk.CTkComboBox(filtro_frame, values=["Todas"] + CATEGORIAS_DEFAULT,
                                   width=140, command=aplicar_filtro)
combo_filtro_cat.set("Todas")
combo_filtro_cat.pack(side="left", padx=4)

ctk.CTkButton(filtro_frame, text="✖ Limpiar", width=100,
              fg_color="transparent", border_width=1,
              command=lambda: [entry_buscar.delete(0,"end"),
                               combo_filtro_tipo.set("Todos"),
                               combo_filtro_cat.set("Todas"),
                               actualizar()]).pack(side="left", padx=4)

# Tabla
style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview", background="#2b2b2b", foreground="white",
                fieldbackground="#2b2b2b", rowheight=26)
style.configure("Treeview.Heading", background="#1a1a2e", foreground="white", font=("Arial", 10, "bold"))
style.map("Treeview", background=[("selected", "#2980b9")])

tabla = ttk.Treeview(main, columns=("Tipo", "Nombre", "Categoría", "Monto", "Mes", "Año"), show="headings")
for col, w in zip(("Tipo", "Nombre", "Categoría", "Monto", "Mes", "Año"), (80, 180, 120, 90, 55, 60)):
    tabla.heading(col, text=col)
    tabla.column(col, width=w, anchor="center")
tabla.pack(fill="both", expand=True, pady=6)

scrollbar = ttk.Scrollbar(tabla, orient="vertical", command=tabla.yview)
tabla.configure(yscroll=scrollbar.set)
scrollbar.pack(side="right", fill="y")

def abrir_app():
    login_frame.pack_forget()
    app_frame.pack(fill="both", expand=True)
    actualizar_combo_categorias()
    actualizar()

app.mainloop()
