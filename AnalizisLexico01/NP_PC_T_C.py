# NP_PC_T_C.py
# Ventana 2x2 (Notación Polaca | Código P | Triplos | Cuádruplos)
# MUESTRA TODAS las operaciones de operaciones.txt (una debajo de otra).

import os, re, sys, importlib.util, importlib.machinery
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Union

# -------- Colores (según tu ventana) --------
HEADER_BG = "lightgreen"
BTN_BG = "lightgreen"
BTN_FG = "black"
AREA_BG = "#eef3ff"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_OPERACIONES = os.path.join(BASE_DIR, "operaciones.txt")

# =========================================================
# CARGA FLEXIBLE (solo para TRIPLOS). P-Code lo definimos aquí mismo.
# =========================================================
def _cargar_clase(posibles_modulos, posibles_archivos, nombre_clase):
    for modname in posibles_modulos:
        try:
            mod = importlib.import_module(modname)
            cls = getattr(mod, nombre_clase, None)
            if cls:
                return cls
        except Exception:
            pass
    for fname in posibles_archivos:
        path = os.path.join(BASE_DIR, fname)
        if not os.path.isfile(path):
            continue
        try:
            safe_name = f"_dyn_{os.path.splitext(fname)[0].replace('-', '_')}"
            loader = importlib.machinery.SourceFileLoader(safe_name, path)
            spec = importlib.util.spec_from_loader(safe_name, loader)
            mod = importlib.util.module_from_spec(spec)
            loader.exec_module(mod)
            sys.modules[safe_name] = mod
            cls = getattr(mod, nombre_clase, None)
            if cls:
                return cls
        except Exception:
            continue
    raise RuntimeError(
        f"No pude cargar {nombre_clase}. "
        f"Busca alguno de: módulos={posibles_modulos} archivos={posibles_archivos}"
    )

GeneradorTriplos = _cargar_clase(
    posibles_modulos=["app_triplos", "triplos", "Triplos"],
    posibles_archivos=["app_triplos.py", "triplos.py", "Triplos.py"],
    nombre_clase="GeneradorTriplos"
)

# =========================================================
# *** GeneradorPCode (integrado, NO TOCAR) ***
# =========================================================
class GeneradorPCode:
    class Node:
        def __init__(self, value=None, op=None, left=None, right=None):
            self.value = value
            self.op = op
            self.left = left
            self.right = right
        def is_leaf(self):
            return self.value is not None

    # --- MODIFICADO: acepta $identificadores ---
    def tokenizar(self, expr: str):
        s = expr.replace(' ', '')  # permite ambas formas (con o sin espacios)
        tokens = []
        i, n = 0, len(s)

        while i < n:
            ch = s[i]

            # número (soporta - unario y decimales)
            if (ch.isdigit() or ch == '.' or
                (ch == '-' and (i == 0 or s[i-1] in '+-*/(') and i+1 < n and (s[i+1].isdigit() or s[i+1] == '.'))):
                j = i + 1 if ch == '-' else i
                dot = (s[i] == '.')
                while j < n and (s[j].isdigit() or (s[j] == '.' and not dot)):
                    if s[j] == '.':
                        dot = True
                    j += 1
                tokens.append(s[i:j])
                i = j
                continue

            # --- NUEVO: $identificador ---
            if ch == '$':
                j = i + 1
                # Debe venir letra o _ después de $
                if j >= n or not (s[j].isalpha() or s[j] == '_'):
                    raise ValueError("Después de '$' debe venir letra o '_' (ej. $x, $tmp_1).")
                while j < n and (s[j].isalnum() or s[j] == '_'):
                    j += 1
                tokens.append(s[i:j])
                i = j
                continue

            # identificador normal: empieza con letra o _
            if ch.isalpha() or ch == '_':
                j = i + 1
                while j < n and (s[j].isalnum() or s[j] == '_'):
                    j += 1
                tokens.append(s[i:j])
                i = j
                continue

            # operadores y paréntesis
            if ch in '+-*/()':
                tokens.append(ch)
                i += 1
                continue

            raise ValueError(f"Carácter no válido: {ch}")

        return tokens

    def shunting_yard(self, tokens):
        prec = {'+': 1, '-': 1, '*': 2, '/': 2}
        output = []
        stack = []
        for token in tokens:
            # número entero o decimal (con posible signo unario ya tokenizado)
            if re.fullmatch(r'-?\d+(\.\d+)?', token):
                output.append(token)
            # --- MODIFICADO: reconocer $identificadores ---
            elif token.startswith('$') and len(token) > 1 and (token[1].isalpha() or token[1] == '_'):
                output.append(token)
            elif token.startswith('_') or token.isalpha():
                output.append(token)
            elif token in prec:
                while stack and stack[-1] in prec and prec[stack[-1]] >= prec[token]:
                    output.append(stack.pop())
                stack.append(token)
            elif token == '(':
                stack.append(token)
            elif token == ')':
                while stack and stack[-1] != '(':
                    output.append(stack.pop())
                if stack and stack[-1] == '(':
                    stack.pop()
        while stack:
            output.append(stack.pop())
        return output

    def build_ast_from_rpn(self, rpn):
        stack = []
        for t in rpn:
            if t in ('+', '-', '*', '/'):
                right = stack.pop()
                left = stack.pop()
                stack.append(self.Node(op=t, left=left, right=right))
            else:
                stack.append(self.Node(value=t))
        return stack[0] if stack else None

    def agrupacion_str(self, node):
        if node is None:
            return ""
        if node.is_leaf():
            return node.value
        return f"({self.agrupacion_str(node.left)} {node.op} {self.agrupacion_str(node.right)})"

    def gen_codigo_p(self, node, codigo):
        if node.is_leaf():
            tok = node.value
            if re.fullmatch(r'-?\d+(\.\d+)?', tok):
                codigo.append(f"ldc {tok}")
            else:
                nombre = tok if tok.startswith('_') else f"{tok}"
                codigo.append(f"lod {nombre}")
            return

        prec = {'+': 1, '-': 1, '*': 2, '/': 2}
        op = node.op

        def subtree_has_higher(n, my_prec):
            if n is None or (hasattr(n, 'is_leaf') and n.is_leaf()):
                return False
            if prec[n.op] > my_prec:
                return True
            return subtree_has_higher(n.left, my_prec) or subtree_has_higher(n.right, my_prec)

        my_prec = prec[op]
        left_higher = subtree_has_higher(node.left, my_prec)
        right_higher = subtree_has_higher(node.right, my_prec)

        if op in ('+', '*'):
            if left_higher and not right_higher:
                self.gen_codigo_p(node.left, codigo)
                self.gen_codigo_p(node.right, codigo)
            elif right_higher and not left_higher:
                self.gen_codigo_p(node.right, codigo)
                self.gen_codigo_p(node.left, codigo)
            else:
                self.gen_codigo_p(node.left, codigo)
                self.gen_codigo_p(node.right, codigo)
        elif op in ('-', '/'):
            if left_higher and not right_higher:
                self.gen_codigo_p(node.left, codigo)
                self.gen_codigo_p(node.right, codigo)
            elif right_higher and not left_higher:
                self.gen_codigo_p(node.right, codigo)
                self.gen_codigo_p(node.left, codigo)
            else:
                self.gen_codigo_p(node.left, codigo)
                self.gen_codigo_p(node.right, codigo)

        if op == '+':
            codigo.append("adi")
        elif op == '-':
            codigo.append("sbi")
        elif op == '*':
            codigo.append("mpi")
        elif op == '/':
            codigo.append("div")

    def _a_codigo_p(self, expresion):
        variable = None
        if '=' in expresion:
            left, right = expresion.split('=', 1)
            variable = left.strip()
            expresion = right.strip()

        tokens = self.tokenizar(expresion)
        rpn = self.shunting_yard(tokens)
        ast = self.build_ast_from_rpn(rpn)
        _ = self.agrupacion_str(ast)

        codigo = []
        if variable:
            codigo.append(f"lda {variable}")

        if ast:
            self.gen_codigo_p(ast, codigo)

        if variable:
            codigo.append("sto")

        return _, codigo

    def generar_pcode(self, linea: str):
        _, codigo = self._a_codigo_p(linea)
        return codigo


# =========================================================
# *** PILAS (Notación Polaca) – INTEGRACIÓN TAL CUAL ***
# =========================================================

def _base_dir():
    return os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()

def tokenize(expr: str) -> List[str]:
    pat = r'\d+\.\d+|\d+|\$[A-Za-z_]\w*|[A-Za-z_]\w*|[()\[\]\{\}+\-*/]'
    return re.findall(pat, expr)

def es_operando(tok: str) -> bool:
    return re.fullmatch(r'\d+(?:\.\d+)?|\$[A-Za-z_]\w*|[A-Za-z_]\w*', tok) is not None

PREC = {'+':1, '-':1, '*':2, '/':2}
ABRE   = set("([{")
CIERRA = {')':'(', ']':'[', '}':'{'}

class Nodo:
    def __init__(self, op: str=None, izq: 'Nodo'=None, der: 'Nodo'=None, val: str=None):
        self.op, self.izq, self.der, self.val = op, izq, der, val
    def es_val(self): return self.val is not None

def construir_ast(tokens: List[str]) -> Nodo:
    vals: List[Nodo] = []
    ops:  List[str]  = []
    def reducir():
        op = ops.pop()
        der = vals.pop()
        izq = vals.pop()
        vals.append(Nodo(op=op, izq=izq, der=der))
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if es_operando(t):
            vals.append(Nodo(val=t))
        elif t in ABRE:
            ops.append(t)
        elif t in CIERRA:
            while ops and ops[-1] != CIERRA[t]:
                reducir()
            if ops and ops[-1] == CIERRA[t]:
                ops.pop()
        else:
            while ops and ops[-1] not in ABRE and PREC.get(ops[-1],0) >= PREC.get(t,0):
                reducir()
            ops.append(t)
        i += 1
    while ops:
        if ops[-1] in ABRE:
            ops.pop()
        else:
            reducir()
    if len(vals) != 1:
        raise ValueError("Expresión inválida o no soportada.")
    return vals[0]

PARES = [("(",")"), ("[","]"), ("{","}")]

def parentizar_total(n: Nodo, nivel: int=0) -> str:
    if n.es_val():
        return n.val
    a, c = PARES[nivel % len(PARES)]
    izq = parentizar_total(n.izq, nivel+1)
    der = parentizar_total(n.der, nivel+1)
    return f"{a}{izq}{n.op}{der}{c}"

_SENTINEL = object()

def solo_reales(vals: List[object]) -> List[str]:
    return [str(v) for v in vals if v is not _SENTINEL]

def emision_preview(val_stack: List[object], op: str) -> str:
    der = val_stack[-1] if len(val_stack) >= 1 else None
    izq = val_stack[-2] if len(val_stack) >= 2 else None
    partes = []
    if der is not None and der is not _SENTINEL: partes.append(str(der))
    if izq is not None and izq is not _SENTINEL: partes.append(str(izq))
    partes.append(op)
    return " ".join(partes)

def reducir_real(val_stack: List[object], op: str) -> str:
    der = val_stack.pop()
    izq = val_stack.pop()
    partes = []
    if der is not _SENTINEL: partes.append(str(der))
    if izq is not _SENTINEL: partes.append(str(izq))
    partes.append(op)
    val_stack.append(_SENTINEL)
    return " ".join(partes)

def generar_filas(expr_parentizada: str) -> Tuple[List[Tuple[str,str,str,str]], str]:
    tokens = tokenize(expr_parentizada)
    vals, ops = [], []
    filas: List[Tuple[str,str,str,str]] = []
    paso = 0
    emisiones_concat: List[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if es_operando(t):
            vals.append(t)
        elif t in ABRE:
            ops.append(t)
        elif t in CIERRA:
            while ops and ops[-1] != CIERRA[t]:
                op_top = ops[-1]
                paso += 1
                operandos_v = ", ".join(solo_reales(vals)) or "—"
                operadores_v = " , ".join(ops + [t])
                em_prev = emision_preview(vals, op_top)
                filas.append((str(paso), operandos_v, operadores_v, em_prev))
                ops.pop()
                em_real = reducir_real(vals, op_top)
                emisiones_concat.append(em_real)
            if ops and ops[-1] == CIERRA[t]:
                ops.pop()
        else:
            ops.append(t)
        i += 1
    while ops:
        top = ops.pop()
        if top in ABRE:
            continue
        paso += 1
        operandos_v = ", ".join(solo_reales(vals)) or "—"
        operadores_v = " , ".join(ops + [')'])
        em_prev = emision_preview(vals, top)
        filas.append((str(paso), operandos_v, operadores_v, em_prev))
        em_real = reducir_real(vals, top)
        emisiones_concat.append(em_real)
    return filas, " ".join(emisiones_concat)

# ================== Render BONITO ya existente (reutilizado) ==================
def _tabla_unicode(headers, rows, title=""):
    data = [headers] + rows
    colw = [0]*len(headers)
    for r in data:
        for j,c in enumerate(r):
            colw[j] = max(colw[j], len(str(c)))
    top    = "┏" + "┳".join("━"*(colw[j]+2) for j in range(len(headers))) + "┓"
    sep    = "┣" + "╋".join("━"*(colw[j]+2) for j in range(len(headers))) + "┫"
    mid    = "┠" + "┼".join("─"*(colw[j]+2) for j in range(len(headers))) + "┨"
    bottom = "┗" + "┻".join("━"*(colw[j]+2) for j in range(len(headers))) + "┛"
    out = []
    if title:
        out.append("\n" + title.center(sum(colw) + 3*len(headers) + 1))
    out.append(top)
    out.append("┃" + "┃".join(f" {headers[j]:<{colw[j]}} " for j in range(len(headers))) + "┃")
    out.append(sep)
    for i, r in enumerate(rows):
        out.append("┃" + "┃".join(f" {str(r[j]):<{colw[j]}} " for j in range(len(headers))) + "┃")
        if i != len(rows)-1:
            out.append(mid)
    out.append(bottom)
    return "\n".join(out) + "\n"

def _caja_unicode(texto, titulo):
    inner = texto or "—"
    w = max(len(titulo), len(inner)) + 2
    top = "┏" + "━"*w + "┓"
    mid = "┣" + "━"*w + "┫"
    bot = "┗" + "━"*w + "┛"
    return "\n".join([top, "┃" + f"{titulo:^{w}}" + "┃", mid, "┃" + f"{inner:^{w}}" + "┃", bot, ""])

# =========================================================
# LECTOR DE OPERACIONES (una por línea) – usado por todos
# =========================================================
def leer_operaciones(ruta=RUTA_OPERACIONES):
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f"No se encontró: {ruta}")
    ops = []
    with open(ruta, "r", encoding="utf-8") as f:
        for ln in f:
            ln = re.sub(r"//.*", "", ln)
            ln = re.sub(r"#.*",  "", ln)
            ln = ln.strip()
            if not ln:
                continue
            if ln.endswith(";"):
                ln = ln[:-1].strip()
            if "=" in ln:
                ops.append(ln)
    return ops

# ===== Util Pilas: extraer asignación (sin meter LHS a pilas) =====
def _extraer_asignacion(linea: str) -> Tuple[Union[str,None], str]:
    t = linea.strip()
    if not t:
        return None, ""
    m = re.match(r'^\s*(\$?[A-Za-z_]\w*)\s*=\s*(.*?)\s*;?\s*$', t)
    if m:
        lhs = m.group(1)
        rhs = m.group(2)
        return lhs, rhs
    return None, (t[:-1].strip() if t.endswith(";") else t)

# =========================================================
# VENTANA (muestra TODAS las expresiones)
# =========================================================
class Ventana2x2(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Notación Polaca - Código P - Triplos - Cuádruplos")
        self.geometry("1200x740")
        self.configure(background=AREA_BG)
        self._estilos()
        self.tri = GeneradorTriplos()
        self.pco = GeneradorPCode()
        self._armar()

    def _estilos(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except: pass
        s.configure("Hdr.TLabel", background=HEADER_BG, foreground="black",
                    font=("Helvetica", 14, "bold"), anchor="center")
        s.configure("Box.TFrame", background=AREA_BG)
        s.configure("Blue.Treeview", background=AREA_BG, fieldbackground=AREA_BG,
                    foreground="black", rowheight=22)
        s.configure("Blue.Treeview.Heading", background=HEADER_BG, foreground="black")

    def _armar(self):
        pass

        grid = ttk.Frame(self); grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        for c in (0,1): grid.columnconfigure(c, weight=1)
        for r in (0,1): grid.rowconfigure(r, weight=1)

        # TL: Notación Polaca (PILAS)
        tl = ttk.Frame(grid); tl.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=(0,6))
        ttk.Label(tl, text="Notación Polaca", style="Hdr.TLabel").pack(fill=tk.X)
        box_tl = ttk.Frame(tl, style="Box.TFrame"); box_tl.pack(fill=tk.BOTH, expand=True)
        box_tl.rowconfigure(0, weight=1); box_tl.columnconfigure(0, weight=1)
        self.txt_rpn = tk.Text(box_tl, wrap="none", font=("Consolas", 11), bg=AREA_BG)
        ysr = ttk.Scrollbar(box_tl, orient="vertical", command=self.txt_rpn.yview)
        xsr = ttk.Scrollbar(box_tl, orient="horizontal", command=self.txt_rpn.xview)
        self.txt_rpn.configure(yscrollcommand=ysr.set, xscrollcommand=xsr.set)
        self.txt_rpn.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        ysr.grid(row=0, column=1, sticky="ns")
        xsr.grid(row=1, column=0, sticky="ew")

        # TR: Código P
        tr = ttk.Frame(grid); tr.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=(0,6))
        ttk.Label(tr, text="Código P", style="Hdr.TLabel").pack(fill=tk.X)
        box_tr = ttk.Frame(tr, style="Box.TFrame"); box_tr.pack(fill=tk.BOTH, expand=True)
        box_tr.rowconfigure(0, weight=1); box_tr.columnconfigure(0, weight=1)
        self.txt_p = tk.Text(box_tr, wrap="none", font=("Consolas", 11), bg=AREA_BG)
        ysp = ttk.Scrollbar(box_tr, orient="vertical", command=self.txt_p.yview)
        xsp = ttk.Scrollbar(box_tr, orient="horizontal", command=self.txt_p.xview)
        self.txt_p.configure(yscrollcommand=ysp.set, xscrollcommand=xsp.set)
        self.txt_p.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        ysp.grid(row=0, column=1, sticky="ns")
        xsp.grid(row=1, column=0, sticky="ew")

        # BL: Triplos
        bl = ttk.Frame(grid); bl.grid(row=1, column=0, sticky="nsew", padx=(0,6), pady=(6,0))
        ttk.Label(bl, text="Triplos", style="Hdr.TLabel").pack(fill=tk.X)
        box_bl = ttk.Frame(bl, style="Box.TFrame"); box_bl.pack(fill=tk.BOTH, expand=True)
        self.tv_tri = ttk.Treeview(box_bl, columns=("dir","op","a1","a2"), show="headings", style="Blue.Treeview")
        for c,t,w in (("dir","Dir",70),("op","Operador",100),("a1","Operando 1",220),("a2","Operando 2",220)):
            self.tv_tri.heading(c, text=t, anchor="w"); self.tv_tri.column(c, width=w, anchor="w")
        self.tv_tri.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # BR: Cuádruplos
        br = ttk.Frame(grid); br.grid(row=1, column=1, sticky="nsew", padx=(6,0), pady=(6,0))
        ttk.Label(br, text="Cuádruplos", style="Hdr.TLabel").pack(fill=tk.X)
        box_br = ttk.Frame(br, style="Box.TFrame"); box_br.pack(fill=tk.BOTH, expand=True)
        self.tv_cuad = ttk.Treeview(box_br, columns=("op","a1","a2","res"), show="headings", style="Blue.Treeview")
        for c,t,w in (("op","Operador",100),("a1","Operando 1",220),("a2","Operando 2",220),("res","Auxiliar",140)):
            self.tv_cuad.heading(c, text=t, anchor="w"); self.tv_cuad.column(c, width=w, anchor="w")
        self.tv_cuad.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._cargar_y_mostrar()

    # ---------- pipeline ----------
    def _cargar_y_mostrar(self):
        try:
            ops = leer_operaciones(RUTA_OPERACIONES)
        except Exception as e:
            messagebox.showerror("Error al leer archivo", str(e)); return
        if not ops:
            messagebox.showinfo("Aviso", "No se encontraron asignaciones en el archivo."); return
        self._mostrar_todas(ops)

    def _mostrar_todas(self, ops):
        # ===================== PILAS (Notación Polaca) =====================
        self.txt_rpn.config(state='normal'); self.txt_rpn.delete("1.0", tk.END)
        for i, linea in enumerate(ops, start=1):
            lhs, rhs = _extraer_asignacion(linea)
            try:
                toks = tokenize(rhs)
                ast  = construir_ast(toks)
                expr_par = parentizar_total(ast)
                filas, concat = generar_filas(expr_par)

                self.txt_rpn.insert(tk.END, f"EXPRECION {i}\n")
                headers = [
                    "Paso",
                    "Operandos",
                    "Operadores",
                    "Resultado"
                ]
                tabla = _tabla_unicode(headers, filas, title=f"EXPRECION PARENTIZADA: {expr_par}")
                self.txt_rpn.insert(tk.END, tabla)

                concat_final = f"{concat} {lhs} =" if lhs else concat
                caja = _caja_unicode(concat_final, "RESULTADO")
                self.txt_rpn.insert(tk.END, caja)
                self.txt_rpn.insert(tk.END, "\n" + "─"*90 + "\n\n")

            except Exception as e:
                self.txt_rpn.insert(tk.END, f"EXPRECION {i}: {linea}\nERROR: {e}\n\n")
        self.txt_rpn.config(state='disabled')

        # ===================== P-Code =====================
        self.txt_p.config(state='normal'); self.txt_p.delete("1.0", tk.END)
        for i, linea in enumerate(ops, start=1):
            try:
                pcode = self.pco.generar_pcode(linea)
            except Exception as e:
                pcode = [f"ERROR: {e}"]
            self.txt_p.insert(tk.END, f"EXPRECION {i} --> {linea}\n" + "-"*40 + "\n")
            for ins in pcode: self.txt_p.insert(tk.END, ins + "\n")
            self.txt_p.insert(tk.END, "\n")
        self.txt_p.config(state='disabled')

        # ===================== Triplos =====================
        for r in self.tv_tri.get_children(): self.tv_tri.delete(r)
        for i, linea in enumerate(ops, start=1):
            self.tv_tri.insert("", tk.END, values=("", f"EXPRECION {i}", "", ""))
            try:
                tlist = self.tri.generar_triplos(linea)
                for j,(op,a1,a2) in enumerate(tlist):
                    self.tv_tri.insert("", tk.END, values=(f"[{j}]", op, a1, a2))
            except Exception as e:
                self.tv_tri.insert("", tk.END, values=("", f"ERROR: {e}", "", ""))

        # ===================== Cuádruplos =====================
        for r in self.tv_cuad.get_children(): self.tv_cuad.delete(r)
        for i, linea in enumerate(ops, start=1):
            var, expr = [s.strip() for s in linea.split("=",1)]
            self.tv_cuad.insert("", tk.END, values=(f"EXPRECION {i}", "", "", ""))
            try:
                post_ok = self.tri.infijo_a_postfijo(self.tri.tokenizar(expr))
                raiz, _Nodo = ast_desde_postfijo(post_ok, self.tri.OPERADORES)
                asignar_inorder_idx(raiz)
                cuad = emitir_cuadruplos(raiz, self.tri.OPERADORES, var)
            except Exception as e:
                cuad = [("ERROR", str(e), "", "")]
            for op,a1,a2,res in cuad:
                self.tv_cuad.insert("", tk.END, values=(op,a1,a2,res))

# =========================================================
# Helper para Cuádruplos ya existente (no tocado)
# =========================================================
def ast_desde_postfijo(post, opdef):
    class Nodo2:
        __slots__ = ("op","izq","der","val","inorder_idx")
        def __init__(self, op=None, izq=None, der=None, val=None):
            self.op, self.izq, self.der, self.val = op, izq, der, val
            self.inorder_idx = None
        @property
        def es_hoja(self): return self.op is None
    def es_num(x):  return bool(re.fullmatch(r'(?:\d+\.\d*|\d*\.\d+|\d+)', x))
    def es_id(x):   return x.startswith("$") and len(x)>1 and all(ch.isalnum() or ch=="_" for ch in x[1:])
    pila=[]
    for tk_ in post:
        if es_num(tk_) or es_id(tk_):
            pila.append(Nodo2(val=tk_))
        elif tk_ in opdef:
            if len(pila)<2: raise ValueError("Faltan operandos.")
            b = pila.pop(); a = pila.pop()
            pila.append(Nodo2(op=tk_, izq=a, der=b))
        else:
            raise ValueError(f"Token inesperado: {tk_}")
    if len(pila)!=1: raise ValueError("Expresión inválida.")
    return pila[0], Nodo2

def asignar_inorder_idx(raiz):
    idx=0
    def ino(n):
        nonlocal idx
        if not n: return
        ino(n.izq); n.inorder_idx=idx; idx+=1; ino(n.der)
    ino(raiz)

def emitir_cuadruplos(raiz, opdef, var_obj):
    ids={}; cuad=[]; temp=0
    def nuevo():
        nonlocal temp; temp+=1; return f"Var{temp}"
    def listo(n):
        ok=lambda x: (x.op is None) or (x in ids)
        return ok(n.izq) and ok(n.der)
    ops=[]
    def reco(n):
        if not n: return
        reco(n.izq); reco(n.der)
        if n.op is not None: ops.append(n)
    reco(raiz)
    pend=set(ops)
    while pend:
        cand=[n for n in pend if listo(n)]
        cand.sort(key=lambda n:(-opdef[n.op]['prec'], n.inorder_idx))
        n=cand[0]
        a1 = n.izq.val if n.izq.op is None else ids[n.izq]
        a2 = n.der.val if n.der.op is None else ids[n.der]
        aux = nuevo()
        cuad.append((n.op, a1, a2, aux))
        ids[n]=aux
        pend.remove(n)
    final = raiz.val if raiz.op is None else ids[raiz]
    cuad.append(("=", final, "", var_obj))
    return cuad

# =========================================================
# Arranque autónomo
# =========================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    Ventana2x2(master=root)
    root.mainloop()
