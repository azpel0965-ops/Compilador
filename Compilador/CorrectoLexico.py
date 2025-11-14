import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import re
import difflib
import json
import os
from Sintactico import (SintacticoApp)
from Semantico import (SemanticoApp)
import sys, subprocess
from tkinter import messagebox


tokens = {
    'palabras_clave': ['Ini', 'end', 'mostrar', 'leer'],
    'tipos': ['ente', 'dec', 'carac', 'cade', 'bool'],
    'booleanos': ['verdadero', 'falso'],
    'operadores': ['=', r'\+', '-', r'\*', '/'],
    'caracteres': [r'\(', r'\)', r';', r','],
    'comentarios': r'#.*',
    'identificadores': r'\$[a-zA-Z_][a-zA-Z0-9_]*',
    'numeros': r'\d+(\.\d+)?',
    'cadenas': r'"[^"]*"',
    'espacios_blanco': r'\s+',
    'desconocidos': r'[^\s]+',
}

Patrones = {
    'palabras_clave': re.compile(r'\b(?:' + '|'.join(tokens['palabras_clave']) + r')\b'),
    'tipos': re.compile(r'\b(?:' + '|'.join(tokens['tipos']) + r')\b'),
    'booleanos': re.compile(r'\b(?:' + '|'.join(tokens['booleanos']) + r')\b'),
    'operadores': re.compile(r'|'.join(tokens['operadores'])),
    'comentarios': re.compile(tokens['comentarios']),
    'identificadores': re.compile(tokens['identificadores']),
    'numeros': re.compile(tokens['numeros']),
    'cadenas': re.compile(tokens['cadenas']),
    'espacios_blanco': re.compile(tokens['espacios_blanco']),
    'desconocidos': re.compile(tokens['desconocidos']),
    'caracteres': re.compile('|'.join(tokens['caracteres'])),
}

ventana = tk.Tk()
ventana.title("Compilador")
ventana.geometry("1100x700")

tk.Label(ventana, text="Compilador", bg="lightgreen", font=("Helvetica", 16, "bold")).pack(fill=tk.X)
frame1 = tk.Frame(ventana)
frame1.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
lefframe1 = tk.Frame(frame1)
lefframe1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
arribaframe1 = tk.Frame(lefframe1)
arribaframe1.pack(fill=tk.X, pady=5)
tk.Button(arribaframe1, text="Cargar Archivo", command=lambda: CargarArchivo(), font=("Arial", 10, "bold"), width=18, height=2, bg="lightgreen", fg="black").pack(side=tk.LEFT, padx=5)
tk.Button(arribaframe1, text="Limpiar", command=lambda: Limpiar(), font=("Arial", 10, "bold"), width=18, height=2, bg="lightgreen", fg="black").pack(side=tk.LEFT, padx=5)
codigotexto = scrolledtext.ScrolledText(lefframe1, height=25, font=("Courier", 12), bg="#eef3ff")
codigotexto.pack(fill=tk.BOTH, expand=True, padx=5)
muestraerrores = tk.LabelFrame(lefframe1, text="Errores detectados")
muestraerrores.pack(fill=tk.X, padx=5, pady=5)
erroresmensaje = scrolledtext.ScrolledText(muestraerrores, height=6, font=("Arial", 11), bg="lightgreen", fg="darkred", wrap=tk.WORD)
erroresmensaje.pack(fill=tk.BOTH, padx=5, pady=5)
erroresmensaje.config(state='disabled')


framebotones = tk.Frame(frame1)
framebotones.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

def correr_semantico():
    from Semantico import App
    SemanticoApp = App()
    # Hook para mandar errores al panel principal
    SemanticoApp.ERROR_SINK = mostrar_errores_semantico_en_principal

    # 1) Pre-chequeo sin abrir ventanas
    ok, errores, _roots = SemanticoApp._precheck_semantic()

    # 2) Manda errores (si hay) al panel de la ventana principal
    if errores:
        mostrar_errores_semantico_en_principal(errores)
    SemanticoApp.open_grammar_first(parent=ventana, auto_run=True)

    
def abrir_codigo_intermedio():
    # Ruta al script que abre la ventana 2x2
    base = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(base, "NP_PC_T_C.py")
    if not os.path.exists(script):
        messagebox.showerror("Error", f"No encuentro: {script}")
        return
    try:
        # Lanza en un proceso aparte para evitar 2 instancias de Tk()
        subprocess.Popen([sys.executable, script], cwd=base)
    except Exception as e:
        messagebox.showerror("Error", f"No pude abrir Código intermedio:\n{e}")




tk.Button(framebotones, text="Léxico", command=lambda: analizar(), bg="lightgreen", fg="black", width=20, height=2, font=("Arial", 10, "bold")).pack(pady=5)
boton_sintactico = tk.Button(framebotones,text="Sintáctico",command=lambda: SintacticoApp.run(parent=framebotones.winfo_toplevel()),bg="lightgreen", fg="black", width=20, height=2, font=("Arial", 10, "bold")).pack(pady=5)
boton_semantico = tk.Button(framebotones,text="Semántico",command=correr_semantico,bg="lightgreen", fg="black", width=20, height=2, font=("Arial", 10, "bold"))
boton_semantico.pack(pady=5)
tk.Button(framebotones,text="Código intermedio",command=abrir_codigo_intermedio,bg="lightgreen", fg="black",width=20, height=2, font=("Arial", 10, "bold")).pack(pady=5)
tk.Button(framebotones, text="Optimización", bg="lightgreen", fg="black", width=20, height=2, font=("Arial", 10, "bold")).pack(pady=5)
tk.Button(framebotones, text="Código Objeto", bg="lightgreen", fg="black", width=20, height=2, font=("Arial", 10, "bold")).pack(pady=5)


def CargarArchivo():
    muestratxt = filedialog.askopenfilename(filetypes=[("Archivos de texto", "*.txt")])
    if muestratxt:
        with open(muestratxt, 'r', encoding='utf-8') as file:
            codigotexto.delete('1.0', tk.END)
            codigotexto.insert(tk.END, file.read())

def Limpiar():
    codigotexto.delete('1.0', tk.END)
    erroresmensaje.config(state='normal')
    erroresmensaje.delete('1.0', tk.END)
    erroresmensaje.config(state='disabled')
    LimpiarColores()

def MarcarError(linea, start_col, end_col):
    start = f"{linea}.{start_col}"
    end = f"{linea}.{end_col}"
    codigotexto.tag_add("error", start, end)
    codigotexto.tag_config("error", background="red", foreground="white")

def LimpiarColores():
    codigotexto.tag_delete("error")

def mostrar_errores_semantico_en_principal(lista_errores):
    # Muestra los errores del semántico en la caja de errores de la ventana principal
    erroresmensaje.config(state='normal')

    texto_actual = erroresmensaje.get("1.0", "end-1c").strip()
    separador = "\n\n" if texto_actual else ""

    if not lista_errores:
        erroresmensaje.insert(tk.END, f"{separador}Sin errores semánticos.\n")
    else:
        erroresmensaje.insert(tk.END, f"{separador}Errores semánticos:\n" + "\n".join(lista_errores) + "\n")

    erroresmensaje.config(state='disabled')


def ClasificarToken(token):
    if token in tokens['palabras_clave'] or token in tokens['tipos'] or token in tokens['booleanos']:
        return "Palabra Reservada"
    elif Patrones['identificadores'].fullmatch(token):
        return "Identificador"
    elif Patrones['operadores'].fullmatch(token):
        return "Operador"
    elif Patrones['caracteres'].fullmatch(token):
        return "Carácter"
    elif Patrones['numeros'].fullmatch(token):
        return "Carácter"
    else:
        return "Otro"

def SugerirToken(token):
    todoslosvalidos = tokens['palabras_clave'] + tokens['tipos'] + tokens['booleanos']
    sugerencia = difflib.get_close_matches(token, todoslosvalidos, n=1, cutoff=0.6)
    return sugerencia[0] if sugerencia else None

def MostrarTabla(tokens_data):
    ventanatabla = tk.Toplevel(ventana)
    ventanatabla.title("Tabla de Tokens")
    ventanatabla.geometry("900x500")

    tabla = ttk.Treeview(ventanatabla, columns=("token", "tipo", "declara", "referencias"), show="headings")
    tabla.heading("token", text="Token")
    tabla.heading("tipo", text="Tipo")
    tabla.heading("declara", text="Declara")
    tabla.heading("referencias", text="Referencia")
    tabla.column("token", width=150)
    tabla.column("tipo", width=150)
    tabla.column("declara", width=100)
    tabla.column("referencias", width=500)

    ordenados = sorted(tokens_data.items(), key=lambda x: min(x[1]['lineas']))
    for token, data in ordenados:
        tipo = data["tipo"]
        declara = min(data["lineas"])
        otras = sorted(set(data["lineas"]) - {declara})
        referencias = ', '.join(map(str, otras)) if otras else "-"
        tabla.insert('', tk.END, values=(token, tipo, declara, referencias))

    tabla.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    tk.Button(ventanatabla, text="Regresar", command=ventanatabla.destroy, font=("Arial", 10, "bold"), bg="lightgreen", fg="black", width=15).pack(pady=10)

def analizar():
    LimpiarColores()
    erroresmensaje.config(state='normal')
    erroresmensaje.delete('1.0', tk.END)

    texto_crudo = codigotexto.get("1.0", tk.END)

    # Guardar SIEMPRE la cadena de entrada para otros programas
    guardarCadenaEntrada(texto_crudo)

    if not texto_crudo.strip():
        erroresmensaje.insert(tk.END, "Error: No se ha escrito ningún código. Por favor, ingrese algo para analizar.   ε")
        erroresmensaje.config(state='disabled')
        return  # NO analiza nada

    erroresmensaje.config(state='disabled')
    errores = []
    texto = codigotexto.get("1.0", tk.END).split('\n')
    tokendatos = {}

    for lineno, linea in enumerate(texto, start=1):
        col = 0
        while col < len(linea):
            if linea[col] == '"':
                token = '"'
                if token not in tokendatos:
                    tokendatos[token] = {"tipo": "Carácter", "lineas": [lineno]}
                else:
                    tokendatos[token]["lineas"].append(lineno)
                col += 1
                while col < len(linea) and linea[col] != '"':
                    col += 1
                if col < len(linea) and linea[col] == '"':
                    token = '"'
                    if token not in tokendatos:
                        tokendatos[token] = {"tipo": "Carácter", "lineas": [lineno]}
                    else:
                        tokendatos[token]["lineas"].append(lineno)
                    col += 1
                else:
                    errores.append(f"Error de léxico!!! Línea {lineno}: Cadena no cerrada")
                    MarcarError(lineno, col - 1, col)
                continue

            if linea[col] == '#':
                token = '#'
                if token not in tokendatos:
                    tokendatos[token] = {"tipo": "Carácter", "lineas": [lineno]}
                else:
                    tokendatos[token]["lineas"].append(lineno)
                break

            bandera = False
            for token_type, pattern in Patrones.items():
                match = pattern.match(linea[col:])
                if match:
                    token = match.group()
                    esvalido = False
                    for tiposvalido in ['palabras_clave', 'tipos', 'booleanos', 'operadores', 'caracteres', 'comentarios', 'identificadores', 'numeros', 'espacios_blanco']:
                        if Patrones[tiposvalido].fullmatch(token):
                            esvalido = True
                            break
                    if not esvalido:
                        sugerencia = SugerirToken(token)
                        if sugerencia:
                            errores.append(f"Error de léxico!!! Línea {lineno} En palabra reservada '{token}', ¿quisiste escribir '{sugerencia}'?")
                        else:
                            errores.append(f"Error de léxico!!! Línea {lineno} En token inválido '{token}'")
                        MarcarError(lineno, col, col + len(token))
                    else:
                        tokenclave = token.strip()
                        if tokenclave:
                            if tokenclave not in tokendatos:
                                tokendatos[tokenclave] = {"tipo": ClasificarToken(tokenclave), "lineas": [lineno]}
                            else:
                                tokendatos[tokenclave]["lineas"].append(lineno)
                    col += len(token)
                    bandera = True
                    break
            if not bandera:
                col += 1

    erroresmensaje.config(state='normal')
    erroresmensaje.delete('1.0', tk.END)
    erroresmensaje.insert(tk.END, "\n".join(errores))
    erroresmensaje.config(state='disabled')

    if not errores:
        MostrarTabla(tokendatos)
        guardar_tokens_para_sintactico(tokendatos)
        ruta_vars = guardarVariables(tokendatos)   # guarda variables para otros módulos
        # Si quieres avisar en pantalla:
        # erroresmensaje.config(state='normal')
        # erroresmensaje.insert(tk.END, f"\nVariables guardadas en: {ruta_vars}")
        # erroresmensaje.config(state='disabled')


def guardar_tokens_para_sintactico(tokendatos):
    ruta_directorio = os.path.dirname(__file__)
    os.makedirs(ruta_directorio, exist_ok=True)
    ruta_archivo = os.path.join(ruta_directorio, "tokens_aceptados.json")
    with open(ruta_archivo, "w", encoding="utf-8") as archivo:
        json.dump(tokendatos, archivo, indent=4, ensure_ascii=False)

def guardarVariables(tokendatos, nombre_archivo="variables.txt"):
    """
    Extrae las variables ($identificadores) de tokendatos y las guarda en un .txt.
    - Una variable por línea
    - Sin duplicados (tokendatos ya trae clave única por token)
    - Ordenadas por la primera línea donde aparecen
    - Al final escribe 'TOTAL=n'
    Devuelve la ruta completa del archivo generado.
    """
    variables = []
    for tok, data in tokendatos.items():
        if data.get("tipo") == "Identificador" and isinstance(tok, str) and tok.startswith("$"):
            primera_linea = min(data.get("lineas", [0]) or [0])
            variables.append((tok, primera_linea))

    variables.sort(key=lambda x: x[1])

    ruta_directorio = os.path.dirname(__file__)
    os.makedirs(ruta_directorio, exist_ok=True)
    ruta_archivo = os.path.join(ruta_directorio, nombre_archivo)

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        for tok, _ in variables:
            f.write(f"{tok}\n")
        f.write(f"TOTAL={len(variables)}\n")

    return ruta_archivo

def guardarCadenaEntrada(cadena_texto, nombre_archivo="cadena_entrada.txt"):
    """
    Guarda la cadena (el código completo del editor) en un archivo .txt
    para que otro programa pueda leerla después (haya o no errores léxicos).
    Devuelve la ruta completa del archivo generado.
    """
    ruta_directorio = os.path.dirname(__file__)
    os.makedirs(ruta_directorio, exist_ok=True)
    ruta_archivo = os.path.join(ruta_directorio, nombre_archivo)

    # Guardar el texto tal cual (incluye saltos de línea)
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write(cadena_texto)

    return ruta_archivo


ventana.mainloop()