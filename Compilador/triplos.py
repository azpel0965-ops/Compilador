# app_triplos.py
# Lee operaciones desde un archivo .txt y genera TRIPLOS automáticamente al iniciar.
# Ahora acepta enteros y flotantes (3.14, .5, 12.).

import os
import re
import tkinter as tk
from tkinter import messagebox

# --- Configuración: ajusta la ruta si lo necesitas ---
RUTA_OPERACIONES = os.path.join(os.path.dirname(__file__), "operaciones.txt")
# Ejemplo para pruebas en otro entorno:
# RUTA_OPERACIONES = r"/ruta/completa/a/operaciones.txt"


class GeneradorTriplos:
    OPERADORES = {
        '+': {'prec': 1, 'asoc': 'L'},
        '-': {'prec': 1, 'asoc': 'L'},
        '*': {'prec': 2, 'asoc': 'L'},
        '/': {'prec': 2, 'asoc': 'L'},
        '^': {'prec': 3, 'asoc': 'R'},  # exponente (derecha)
    }

    # ======== Utilidades básicas ========
    def es_numero(self, t: str) -> bool:
        # Acepta: 123   123.   .123   123.45
        return bool(re.fullmatch(r'(?:\d+\.\d*|\d*\.\d+|\d+)', t))

    def es_identificador(self, t: str) -> bool:
        return t.startswith('$') and len(t) > 1 and all(ch.isalnum() or ch == '_' for ch in t[1:])

    # ======== Lexer ========
    def tokenizar(self, expr: str):
        toks, i, n = [], 0, len(expr)
        while i < n:
            c = expr[i]
            if c.isspace():
                i += 1
                continue

            # números (enteros o flotantes con un solo punto)
            if c.isdigit() or (c == '.' and i + 1 < n and expr[i+1].isdigit()):
                j = i
                visto_punto = False
                while j < n and (expr[j].isdigit() or (expr[j] == '.' and not visto_punto)):
                    if expr[j] == '.':
                        visto_punto = True
                    j += 1
                num = expr[i:j]
                if not self.es_numero(num):
                    raise ValueError(f"Número mal formado: '{num}'")
                toks.append(num)
                i = j
                continue

            # identificadores con $
            if c == '$':
                j = i + 1
                if j >= n or not (expr[j].isalnum() or expr[j] == '_'):
                    raise ValueError("Después de '$' debe venir letra/número/_ (ej. $x).")
                while j < n and (expr[j].isalnum() or expr[j] == '_'):
                    j += 1
                toks.append(expr[i:j])
                i = j
                continue

            # operadores/paréntesis (detectar '**' antes que '*')
            if c == '*':
                if i + 1 < n and expr[i+1] == '*':
                    toks.append('^')  # normalizamos ** a ^
                    i += 2
                else:
                    toks.append('*')
                    i += 1
                continue

            if c in '+-/()^':
                toks.append(c)
                i += 1
                continue

            raise ValueError(f"Símbolo no válido: '{c}'")
        return toks

    # ======== Shunting-yard (infijo → postfijo) ========
    def infijo_a_postfijo(self, tokens):
        out, op = [], []
        for t in tokens:
            if self.es_numero(t) or self.es_identificador(t):
                out.append(t)
            elif t in self.OPERADORES:
                o1 = t
                while op and op[-1] in self.OPERADORES:
                    o2 = op[-1]
                    p1 = self.OPERADORES[o1]['prec']
                    p2 = self.OPERADORES[o2]['prec']
                    a1 = self.OPERADORES[o1]['asoc']
                    # ^ derecha: saca mientras p1 < p2; izquierda: p1 <= p2
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

    # ======== AST simple ========
    class Nodo:
        def __init__(self, op=None, izq=None, der=None, val=None):
            self.op = op
            self.izq = izq
            self.der = der
            self.val = val
            self.inorder_idx = None

        @property
        def es_hoja(self):
            return self.op is None

    def ast_desde_postfijo(self, post):
        pila = []
        for tk in post:
            if self.es_numero(tk) or self.es_identificador(tk):
                pila.append(self.Nodo(val=tk))
            elif tk in self.OPERADORES:
                if len(pila) < 2:
                    raise ValueError(f"Faltan operandos antes de '{tk}'.")
                b = pila.pop()
                a = pila.pop()
                pila.append(self.Nodo(op=tk, izq=a, der=b))
            else:
                raise ValueError(f"Token inesperado en postfijo: {tk}")
        if len(pila) != 1:
            raise ValueError("Expresión inválida: sobran operandos.")
        return pila[0]

    def asignar_inorder_idx(self, raiz):
        idx = 0
        def inorder(n):
            nonlocal idx
            if not n: return
            inorder(n.izq)
            n.inorder_idx = idx
            idx += 1
            inorder(n.der)
        inorder(raiz)

    # ======== Emisión de TRIPLOS por precedencia ========
    def emitir_triplos(self, raiz, var_obj):
        ops = []
        def reco(n):
            if not n: return
            reco(n.izq); reco(n.der)
            if not n.es_hoja:
                ops.append(n)
        reco(raiz)

        ids = {}
        triplos = []

        def listo(n):
            def ok(x): return x.es_hoja or x in ids
            return ok(n.izq) and ok(n.der)

        def prec(n): return self.OPERADORES[n.op]['prec']

        pendientes = set(ops)
        while pendientes:
            cand = [n for n in pendientes if listo(n)]
            if not cand:
                raise RuntimeError("No hay candidatos listos (¿expresión mal formada?).")
            cand.sort(key=lambda n: (-prec(n), n.inorder_idx))
            n = cand[0]

            def ref(x):
                return x.val if x.es_hoja else f'[{ids[x]}]'
            a1, a2 = ref(n.izq), ref(n.der)
            triplos.append((n.op, a1, a2))
            ids[n] = len(triplos) - 1
            pendientes.remove(n)

        res = raiz.val if raiz.es_hoja else f'[{ids[raiz]}]'
        triplos.append(('=', var_obj, res))
        return triplos

    # ======== API pública ========
    def generar_triplos(self, cadena: str):
        """
        Espera algo como: $x=34+5.5+3+2-10*2*10**2
        Devuelve lista de tuplas (op, arg1, arg2). Última es ('=', $x, [k])
        """
        if '=' not in cadena:
            raise ValueError("Incluye '='.")
        var, expr = [s.strip() for s in cadena.split('=', 1)]
        if not self.es_identificador(var):
            raise ValueError("La variable del lado izquierdo debe iniciar con '$'.")
        tokens = self.tokenizar(expr)           # ** → ^ dentro del lexer
        post = self.infijo_a_postfijo(tokens)
        raiz = self.ast_desde_postfijo(post)
        self.asignar_inorder_idx(raiz)
        return self.emitir_triplos(raiz, var)


# ================== GUI que procesa archivo automáticamente ==================
class AppTriplos(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TRIPLOS — Procesando operaciones.txt")
        self.geometry("800x520")
        self.gen = GeneradorTriplos()

        self._crear_menu()
        self._crear_widgets()

        # Ejecuta automáticamente el análisis al iniciar
        self.after(100, self._procesar_archivo)

    def _crear_menu(self):
        barra = tk.Menu(self)
        self.config(menu=barra)
        m_archivo = tk.Menu(barra, tearoff=0)
        m_archivo.add_command(label="Reprocesar archivo", command=self._procesar_archivo)
        m_archivo.add_separator()
        m_archivo.add_command(label="Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=m_archivo)

    def _crear_widgets(self):
        marco = tk.Frame(self, padx=10, pady=10)
        marco.pack(fill=tk.BOTH, expand=True)

        self.lbl = tk.Label(marco, text=f"Archivo: {RUTA_OPERACIONES}")
        self.lbl.pack(anchor='w')

        tk.Label(marco, text="Salida:").pack(anchor='w', pady=(6, 2))
        self.salida = tk.Text(marco, height=22)
        self.salida.pack(fill=tk.BOTH, expand=True)
        self.salida.config(state='disabled')

    # ----- utilidades de archivo -----
    def _leer_operaciones(self):
        if not os.path.isfile(RUTA_OPERACIONES):
            raise FileNotFoundError(f"No se encontró: {RUTA_OPERACIONES}")

        with open(RUTA_OPERACIONES, "r", encoding="utf-8") as f:
            texto = f.read()

        # Quitar comentarios tipo //... o #... hasta el final de línea
        texto = re.sub(r"//.*", "", texto)
        texto = re.sub(r"#.*", "", texto)

        # Permitir varias operaciones separadas por ';' y/o saltos de línea
        partes = [p.strip() for p in texto.replace("\n", " ").split(";")]
        # Quedarnos con no-vacíos que tengan '='
        ops = [p for p in partes if p and '=' in p]
        return ops

    def _procesar_archivo(self):
        try:
            operaciones = self._leer_operaciones()
        except Exception as e:
            messagebox.showerror("Error al leer archivo", str(e))
            return

        self._limpiar_salida()

        if not operaciones:
            self._escribir_linea("No se encontraron operaciones en el archivo.")
            return

        for idx, op in enumerate(operaciones, start=1):
            linea = op.strip()
            try:
                triplos = self.gen.generar_triplos(linea)
                self._escribir_linea(f"Operación {idx}: {linea}")
                for i, (op_, a1, a2) in enumerate(triplos):
                    self._escribir_linea(f"  [{i}] {op_}, {a1}, {a2}")
            except Exception as exc:
                self._escribir_linea(f"Operación {idx}: {linea}")
                self._escribir_linea(f"  ERROR: {exc}")
            # línea en blanco entre análisis
            self._escribir_linea("")

    # ----- helpers de UI -----
    def _limpiar_salida(self):
        self.salida.config(state='normal')
        self.salida.delete("1.0", tk.END)
        self.salida.config(state='disabled')

    def _escribir_linea(self, texto):
        self.salida.config(state='normal')
        self.salida.insert(tk.END, texto + "\n")
        self.salida.config(state='disabled')


# ========= Ejecutable =========
if __name__ == "__main__":
    app = AppTriplos()
    app.mainloop()
