# ================== Tkinter: AST + Parentizado + Tabla de reducciones (sin botones) ==================
import os
import re
import tkinter as tk
from tkinter import scrolledtext
from typing import List, Tuple, Union

# ================== Util de ruta ==================
def _base_dir():
    return os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()

# ================== Tokenización ==================
# Soporta $variables, identificadores, números y ()[]{}+-*/
def tokenize(expr: str) -> List[str]:
    pat = r'\d+\.\d+|\d+|\$[A-Za-z_]\w*|[A-Za-z_]\w*|[()\[\]\{\}+\-*/]'
    return re.findall(pat, expr)

def es_operando(tok: str) -> bool:
    return re.fullmatch(r'\d+(?:\.\d+)?|\$[A-Za-z_]\w*|[A-Za-z_]\w*', tok) is not None

# ================== AST por shunting-yard ==================
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
                ops.pop()  # quitar abridor
        else:  # operador
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

# ================== Parentizado total con () [] {} alternando ==================
PARES = [("(",")"), ("[","]"), ("{","}")]

def parentizar_total(n: Nodo, nivel: int=0) -> str:
    if n.es_val():
        return n.val
    a, c = PARES[nivel % len(PARES)]
    izq = parentizar_total(n.izq, nivel+1)
    der = parentizar_total(n.der, nivel+1)
    # sin espacios para que luzca compacto
    return f"{a}{izq}{n.op}{der}{c}"

# ================== Tabla por reducciones (tu estilo) ==================
_SENTINEL = object()  # resultado intermedio oculto

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
    filas: List[Tuple[str,str,str,str]] = []  # (Paso, Operand, Operador, Emisión)
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
                operadores_v = " , ".join(ops + [t])  # cerrador que dispara
                em_prev = emision_preview(vals, op_top)
                filas.append((str(paso), operandos_v, operadores_v, em_prev))
                ops.pop()
                em_real = reducir_real(vals, op_top)
                emisiones_concat.append(em_real)
            if ops and ops[-1] == CIERRA[t]:
                ops.pop()
        else:  # operador (en expresión ya parentizada, estos irán entre abridores/cerradores)
            ops.append(t)
        i += 1

    # Por si quedara algo (no debería en parentizada total), vaciar
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

# ================== Render a STRING (igual que tu print, pero retornando texto) ==================
def render_table(rows: List[Tuple[str,str,str,str]], title: str) -> str:
    headers = ["Paso", "Operandos (↓→↑)", "Operadores (↓→↑, con el cerrador que dispara)", "Resultado (emisión)"]
    data = [headers] + rows
    colw = [0]*len(headers)
    for r in data:
        for j,c in enumerate(r):
            colw[j] = max(colw[j], len(c))
    total_w = sum(colw) + 3*len(headers) + 1

    top    = "┏" + "┳".join("━"*(colw[j]+2) for j in range(len(headers))) + "┓"
    sep    = "┣" + "╋".join("━"*(colw[j]+2) for j in range(len(headers))) + "┫"
    mid    = "┠" + "┼".join("─"*(colw[j]+2) for j in range(len(headers))) + "┨"
    bottom = "┗" + "┻".join("━"*(colw[j]+2) for j in range(len(headers))) + "┛"

    out = []
    out.append("\n" + title.center(total_w))
    out.append(top)
    out.append("┃" + "┃".join(f" {headers[j]:<{colw[j]}} " for j in range(len(headers))) + "┃")
    out.append(sep)
    for i, r in enumerate(rows):
        out.append("┃" + "┃".join(f" {r[j]:<{colw[j]}} " for j in range(len(headers))) + "┃")
        if i != len(rows)-1:
            out.append(mid)
    out.append(bottom)
    return "\n".join(out) + "\n"

def render_boxed(text: str, title: str) -> str:
    inner = text or "—"
    w = max(len(title), len(inner)) + 2
    top = "┏" + "━"*w + "┓"
    mid = "┣" + "━"*w + "┫"
    bot = "┗" + "━"*w + "┛"
    lines = [
        top,
        "┃" + f"{title:^{w}}" + "┃",
        mid,
        "┃" + f"{inner:^{w}}" + "┃",
        bot
    ]
    return "\n".join(lines) + "\n"

# ================== Util: leer operaciones.txt (con/ sin LHS) ==================
def _extraer_asignacion(linea: str) -> Tuple[Union[str,None], str]:
    """
    Devuelve (lhs, rhs). Si no hay asignación, lhs=None y rhs = expresión/linea.
    Acepta con o sin ';' final y con o sin '$' en el identificador.
    """
    t = linea.strip()
    if not t:
        return None, ""
    m = re.match(r'^\s*(\$?[A-Za-z_]\w*)\s*=\s*(.*?)\s*;?\s*$', t)
    if m:
        lhs = m.group(1)
        rhs = m.group(2)
        return lhs, rhs
    # sin asignación: quitar ';' si existe
    return None, (t[:-1].strip() if t.endswith(";") else t)

def leer_operaciones_con_asign(path: str) -> Tuple[List[str], List[Union[str,None]]]:
    if not os.path.exists(path):
        return [], []
    exprs, lhs_list = [], []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            lhs, rhs = _extraer_asignacion(ln)
            if rhs:
                exprs.append(rhs)
                lhs_list.append(lhs)
    return exprs, lhs_list

# ================== Generar TODO el texto (igual que tu main, pero a string) ==================
def ejecutar_y_formatear() -> str:
    out = []
    out.append("=== Conversor con jerarquía → parentizado total → tabla de reducciones ===\n")
    ops_path = os.path.join(_base_dir(), "operaciones.txt")
    expresiones, asignaciones = leer_operaciones_con_asign(ops_path)

    if not expresiones:
        if not os.path.exists(ops_path):
            out.append(f"[Aviso] No existe {ops_path}\n")
        out.append("No hay expresiones en operaciones.txt\n")
        return "".join(out)

    for idx, expr in enumerate(expresiones, start=1):
        lhs = asignaciones[idx-1]
        try:
            toks = tokenize(expr)
            ast = construir_ast(toks)                  # 1) AST por precedencia
            expr_par = parentizar_total(ast)           # 2) Parentizado alternando () [] {}
            filas, concat = generar_filas(expr_par)    # 3) Tabla por cierres

            out.append("\n" + "="*80 + "\n")
            vista = f"{lhs} = {expr}" if lhs else expr
            out.append(f"EXPRESIÓN {idx}: {vista}\n")
            out.append(render_table(filas, title=f"EXPRESIÓN PARENTIZADA: {expr_par}"))

            # Si hubo asignación, NO se mete a pilas; solo se anexa al final de la emisión
            concat_final = f"{concat} {lhs} =" if lhs else concat
            out.append(render_boxed(concat_final, title="EMISIONES (tu estilo)"))
        except Exception as e:
            out.append("\n" + "="*80 + "\n")
            vista = f"{lhs} = {expr}" if lhs else expr
            out.append(f"EXPRESIÓN {idx}: {vista}\n")
            out.append(f"[Error] {e}\n")
    return "".join(out)

# ================== Tkinter (sin botones) ==================
def main():
    root = tk.Tk()
    root.title("Notaciones Polacas")
    root.geometry("1000x650")

    txt = scrolledtext.ScrolledText(root, wrap="none", font=("Consolas", 11))
    txt.pack(fill="both", expand=True)

    salida = ejecutar_y_formatear()
    txt.insert("1.0", salida)
    txt.configure(state="disabled")  # solo lectura

    root.mainloop()

if __name__ == "__main__":
    main()
