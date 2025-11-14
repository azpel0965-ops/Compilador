# app_pcode.py
# Generador de P-Code con $variables, potencia ( ** / ^ ) y raíz √.
# Emisión con orden de evaluación: en '+' se evalúa primero el lado de MAYOR PRECEDENCIA
# (p.ej. la multiplicación), igual que en la captura. En '-', '*', '/' y '^' se respeta L→R.
# Acepta enteros y flotantes (3.14, .5, 12.) y usa 'ldc'.

import os
import re
import tkinter as tk
from tkinter import messagebox

RUTA_OPERACIONES = os.path.join(os.path.dirname(__file__), "operaciones.txt")

class GeneradorPCode:
    # Precedencia / asociatividad para construir el AST:
    #   √, ^  (mayor, derecha)  >  * , /  (izquierda)  >  + , -  (izquierda)
    OPERADORES = {
        '+': {'prec': 1, 'asoc': 'L', 'pcode': 'adi'},
        '-': {'prec': 1, 'asoc': 'L', 'pcode': 'sbi'},
        '*': {'prec': 2, 'asoc': 'L', 'pcode': 'mpi'},
        '/': {'prec': 2, 'asoc': 'L', 'pcode': 'div'},
        '^': {'prec': 3, 'asoc': 'R', 'pcode': 'exp'},
        '√': {'prec': 3, 'asoc': 'R', 'pcode': None},  # unario; se emite como ^0.5
    }

    # ---------- helpers ----------
    def es_numero(self, t: str) -> bool:
        return bool(re.fullmatch(r'(?:\d+\.\d*|\d*\.\d+|\d+)', t))  # 123 .5 5. .25 3.14

    def es_identificador(self, t: str) -> bool:
        return t.startswith('$') and len(t) > 1 and all(ch.isalnum() or ch == '_' for ch in t[1:])

    def _sin_dolar(self, name: str) -> str:
        return name[1:] if name.startswith('$') else name

    # ---------- lexer ----------
    def tokenizar(self, expr: str):
        tokens, i, n = [], 0, len(expr)
        while i < n:
            c = expr[i]
            if c.isspace():
                i += 1; continue

            # números (enteros o flotantes con un solo punto)
            if c.isdigit() or (c == '.' and i + 1 < n and expr[i+1].isdigit()):
                j = i; visto_punto = False
                while j < n and (expr[j].isdigit() or (expr[j] == '.' and not visto_punto)):
                    if expr[j] == '.': visto_punto = True
                    j += 1
                num = expr[i:j]
                if not self.es_numero(num):
                    raise ValueError(f"Número mal formado: '{num}'")
                tokens.append(num); i = j; continue

            # $identificadores
            if c == '$':
                j = i + 1
                if j >= n or not (expr[j].isalnum() or expr[j] == '_'):
                    raise ValueError("Después de '$' debe venir letra/número/_ (ej. $x).")
                while j < n and (expr[j].isalnum() or expr[j] == '_'):
                    j += 1
                tokens.append(expr[i:j]); i = j; continue

            # detectar '**' antes que '*'
            if c == '*':
                if i + 1 < n and expr[i+1] == '*':
                    tokens.append('^'); i += 2  # ** → ^
                else:
                    tokens.append('*'); i += 1
                continue

            # raíz cuadrada (símbolo √, U+221A). Prefijo: √x o √(x)
            if c == '√':
                tokens.append('√'); i += 1; continue

            if c in '+-/()^':
                tokens.append(c); i += 1; continue

            raise ValueError(f"Símbolo no válido: '{c}'")
        return tokens

    # ---------- shunting-yard (infijo → postfijo) ----------
    def infijo_a_postfijo(self, tokens):
        out, op = [], []
        for t in tokens:
            if self.es_numero(t) or self.es_identificador(t):
                out.append(t)
            elif t in self.OPERADORES:
                o1 = t
                while op and op[-1] in self.OPERADORES:
                    o2 = op[-1]
                    p1, p2 = self.OPERADORES[o1]['prec'], self.OPERADORES[o2]['prec']
                    a1 = self.OPERADORES[o1]['asoc']
                    # derecha: p1 < p2 ; izquierda: p1 <= p2
                    if (a1 == 'L' and p1 <= p2) or (a1 == 'R' and p1 < p2):
                        out.append(op.pop())
                    else:
                        break
                op.append(o1)
            elif t == '(':
                op.append(t)
            elif t == ')':
                while op and op[-1] != '(':
                    out.append(op.pop())
                if not op:
                    raise ValueError("Paréntesis desbalanceados.")
                op.pop()
            else:
                raise ValueError(f"Token inesperado: {t}")
        while op:
            top = op.pop()
            if top in ('(', ')'):
                raise ValueError("Paréntesis desbalanceados.")
            out.append(top)
        return out

    # ---------- AST desde postfijo ----------
    class _Node:
        __slots__ = ("op","left","right","val")
        def __init__(self, op=None, left=None, right=None, val=None):
            self.op, self.left, self.right, self.val = op, left, right, val
        @property
        def is_leaf(self): return self.val is not None

    def _ast_desde_postfijo(self, post):
        st = []
        for tk in post:
            if self.es_numero(tk) or self.es_identificador(tk):
                st.append(self._Node(val=tk))
            elif tk == '√':
                if len(st) < 1:
                    raise ValueError("Falta operando para '√'.")
                r = st.pop()
                st.append(self._Node(op='√', right=r))
            elif tk in {'+','-','*','/','^'}:
                if len(st) < 2:
                    raise ValueError("Faltan operandos.")
                r = st.pop(); l = st.pop()
                st.append(self._Node(op=tk, left=l, right=r))
            else:
                raise ValueError(f"Token inesperado en postfijo: {tk}")
        if len(st) != 1:
            raise ValueError("Expresión inválida.")
        return st[0]

    # ---------- Agrupación de términos (string) ----------
    def _agrupacion_str(self, n):
        if n is None: return ""
        if n.is_leaf: return self._sin_dolar(n.val)
        if n.op == '√': return f"√({self._agrupacion_str(n.right)})"
        return f"({self._agrupacion_str(n.left)} {n.op} {self._agrupacion_str(n.right)})"

    def agrupar(self, cadena: str) -> str:
        _var, expr = [s.strip() for s in cadena.split('=', 1)]
        tokens  = self.tokenizar(expr)
        post    = self.infijo_a_postfijo(tokens)
        raiz    = self._ast_desde_postfijo(post)
        return self._agrupacion_str(raiz)

    # ---------- Emisión P-Code ----------
    def _prec_de_nodo(self, n):
        if n is None or n.is_leaf: return -1
        return self.OPERADORES[n.op]['prec']

    def _emit_node(self, n, out):
        if n.is_leaf:
            if self.es_numero(n.val):
                out.append(f"ldc {n.val}")
            else:
                out.append(f"lod {self._sin_dolar(n.val)}")
            return

        op = n.op
        if op == '√':
            self._emit_node(n.right, out)
            out.append("ldc 0.5")
            out.append("exp")
            return

        if op == '+':
            # 👇 clave: si un lado tiene MAYOR precedencia (ej. *), emítelo primero
            pL, pR = self._prec_de_nodo(n.left), self._prec_de_nodo(n.right)
            if pR > pL:
                self._emit_node(n.right, out)
                self._emit_node(n.left, out)
            else:
                self._emit_node(n.left, out)
                self._emit_node(n.right, out)
            out.append('adi')
            return

        # En -, *, /, ^ respetamos izquierda→derecha
        self._emit_node(n.left, out)
        self._emit_node(n.right, out)
        out.append(self.OPERADORES[op]['pcode'])

    def generar_pcode(self, cadena: str):
        if '=' not in cadena:
            raise ValueError("Incluye '='. Ej: $x= a + b")
        var, expr = [s.strip() for s in cadena.split('=', 1)]
        if not self.es_identificador(var):
            raise ValueError("La variable a la izquierda del '=' debe iniciar con '$' (ej. $x).")

        tokens = self.tokenizar(expr)
        post   = self.infijo_a_postfijo(tokens)
        raiz   = self._ast_desde_postfijo(post)

        instr = [f"lda {self._sin_dolar(var)}"]
        self._emit_node(raiz, instr)
        instr.append("sto")
        return instr


# ------------------- GUI -------------------
class AppPCode(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("P-Code — Precedencia en '+' como en la captura")
        self.geometry("900x560")
        self.gen = GeneradorPCode()
        self._crear_menu()
        self._crear_widgets()
        self.after(100, self._procesar_archivo)

    def _crear_menu(self):
        barra = tk.Menu(self); self.config(menu=barra)
        m_archivo = tk.Menu(barra, tearoff=0)
        m_archivo.add_command(label="Reprocesar archivo", command=self._procesar_archivo)
        m_archivo.add_separator(); m_archivo.add_command(label="Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=m_archivo)

    def _crear_widgets(self):
        marco = tk.Frame(self, padx=10, pady=10); marco.pack(fill=tk.BOTH, expand=True)
        self.lbl = tk.Label(marco, text=f"Archivo: {RUTA_OPERACIONES}"); self.lbl.pack(anchor='w')
        tk.Label(marco, text="Salida:").pack(anchor='w', pady=(6, 2))
        self.salida = tk.Text(marco, height=24); self.salida.pack(fill=tk.BOTH, expand=True)
        self.salida.config(state='disabled')

    def _leer_operaciones(self):
        if not os.path.isfile(RUTA_OPERACIONES):
            raise FileNotFoundError(f"No se encontró: {RUTA_OPERACIONES}")
        with open(RUTA_OPERACIONES, "r", encoding="utf-8") as f:
            texto = f.read()
        texto = re.sub(r"//.*", "", texto)
        texto = re.sub(r"#.*",  "", texto)
        partes = [p.strip() for p in texto.replace("\n", " ").split(";")]
        return [p for p in partes if p and '=' in p]

    def _procesar_archivo(self):
        try:
            operaciones = self._leer_operaciones()
        except Exception as e:
            messagebox.showerror("Error al leer archivo", str(e)); return
        self._limpiar_salida()
        if not operaciones:
            self._escribir_linea("No se encontraron operaciones en el archivo."); return

        for idx, op in enumerate(operaciones, start=1):
            linea = op.strip()
            self._escribir_linea(f"Operación {idx}: {linea}")

            # Agrupación (por jerarquía clásica)
            try:
                agr = self.gen.agrupar(linea)
                self._escribir_linea("  Agrupación de términos:")
                self._escribir_linea(f"    {agr}")
            except Exception as exc:
                self._escribir_linea(f"  ERROR en agrupación: {exc}")

            # P-Code
            try:
                pcode = self.gen.generar_pcode(linea)
                self._escribir_linea("  P-Code:")
                for ins in pcode:
                    self._escribir_linea(f"    {ins}")
            except Exception as exc:
                self._escribir_linea(f"  ERROR en P-Code: {exc}")
            self._escribir_linea("")

    def _limpiar_salida(self):
        self.salida.config(state='normal'); self.salida.delete("1.0", tk.END); self.salida.config(state='disabled')

    def _escribir_linea(self, texto):
        self.salida.config(state='normal'); self.salida.insert(tk.END, texto + "\n"); self.salida.config(state='disabled')


if __name__ == "__main__":
    app = AppPCode()
    app.mainloop()
