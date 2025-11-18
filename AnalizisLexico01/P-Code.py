# app_pcode.py
# Generador de P-Code con $variables y potencia **/^.
# Lee operaciones desde un archivo .txt y procesa TODO automáticamente al iniciar.
# Acepta enteros y flotantes (3.14, .5, 12.) y usa 'ldc' en lugar de 'lcd'.

import os
import re
import tkinter as tk
from tkinter import messagebox

# --- Configuración: ajusta la ruta si lo necesitas ---
RUTA_OPERACIONES = os.path.join(os.path.dirname(__file__), "operaciones.txt")
# Ejemplo:
# RUTA_OPERACIONES = r"C:\ruta\absoluta\operaciones.txt"


class GeneradorPCode:
    """
    Genera P-Code desde una asignación tipo:
        $x=27*5-40/2+13
    Reglas:
      - Variables deben iniciar con '$' (ej. $x, $total_1).
      - Potencia: ** o ^  (se normaliza a ^ internamente).
      - Precedencia: ^ (derecha) > * / > + -
      - Salida:
            lda $x
            ldc/lod ...
            (mpi/div/sbi/adi/exp)
            sto
    """

    OPERADORES = {
        '+': {'prec': 1, 'asoc': 'L', 'pcode': 'adi'},
        '-': {'prec': 1, 'asoc': 'L', 'pcode': 'sbi'},
        '*': {'prec': 2, 'asoc': 'L', 'pcode': 'mpi'},
        '/': {'prec': 2, 'asoc': 'L', 'pcode': 'div'},
        '^': {'prec': 3, 'asoc': 'R', 'pcode': 'exp'},  # exponente
    }

    # ---------- helpers ----------
    def es_numero(self, t: str) -> bool:
        # Acepta: 123   123.   .123   123.45
        return bool(re.fullmatch(r'(?:\d+\.\d*|\d*\.\d+|\d+)', t))

    def es_identificador(self, t: str) -> bool:
        return t.startswith('$') and len(t) > 1 and all(ch.isalnum() or ch == '_' for ch in t[1:])

    # ---------- lexer ----------
    def tokenizar(self, expr: str):
        tokens, i, n = [], 0, len(expr)
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
                tokens.append(num)
                i = j
                continue

            # $identificadores
            if c == '$':
                j = i + 1
                if j >= n or not (expr[j].isalnum() or expr[j] == '_'):
                    raise ValueError("Después de '$' debe venir letra/número/_ (ej. $x).")
                while j < n and (expr[j].isalnum() or expr[j] == '_'):
                    j += 1
                tokens.append(expr[i:j])
                i = j
                continue

            # operadores/paréntesis  (detectar '**' antes que '*')
            if c == '*':
                if i + 1 < n and expr[i+1] == '*':
                    tokens.append('^')        # normalizamos ** a ^
                    i += 2
                else:
                    tokens.append('*')
                    i += 1
                continue

            if c in '+-/()^':
                tokens.append(c)
                i += 1
                continue

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
                    # ^ (derecha): saca mientras p1 < p2;  izquierda: p1 <= p2
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

    # ---------- generación de P-Code desde postfijo ----------
    def generar_pcode(self, cadena: str):
        if '=' not in cadena:
            raise ValueError("Incluye una asignación con '='. Ej: $x=27*5-40/2+13")

        var, expr = [s.strip() for s in cadena.split('=', 1)]
        if not self.es_identificador(var):
            raise ValueError("La variable a la izquierda del '=' debe iniciar con '$' (ej. $x).")

        tokens = self.tokenizar(expr)           # aquí se normaliza ** → ^
        postfijo = self.infijo_a_postfijo(tokens)

        instr = [f"lda {var}"]
        for tk in postfijo:
            if self.es_numero(tk):
                instr.append(f"ldc {tk}")      # <<-- cambiado a ldc
            elif self.es_identificador(tk):
                instr.append(f"lod {tk}")
            elif tk in self.OPERADORES:
                instr.append(self.OPERADORES[tk]['pcode'])
            else:
                raise ValueError(f"Token inesperado al generar p-code: {tk}")
        instr.append("sto")
        return instr


# ------------------- GUI (procesa archivo automáticamente) -------------------
class AppPCode(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("P-Code — Procesando operaciones.txt")
        self.geometry("800x520")
        self.gen = GeneradorPCode()
        self._crear_menu()
        self._crear_widgets()
        # Ejecuta de forma automática el procesamiento al iniciar
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

    # ---- utilidades de archivo ----
    def _leer_operaciones(self):
        if not os.path.isfile(RUTA_OPERACIONES):
            raise FileNotFoundError(f"No se encontró: {RUTA_OPERACIONES}")

        with open(RUTA_OPERACIONES, "r", encoding="utf-8") as f:
            texto = f.read()

        # Quitar comentarios tipo //... o #... (hasta fin de línea)
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
            self._escribir_linea(f"Operación {idx}: {linea}")
            try:
                pcode = self.gen.generar_pcode(linea)
                for ins in pcode:
                    self._escribir_linea(f"  {ins}")
            except Exception as exc:
                self._escribir_linea(f"  ERROR: {exc}")
            # Línea en blanco entre análisis
            self._escribir_linea("")

    # ---- helpers UI ----
    def _limpiar_salida(self):
        self.salida.config(state='normal')
        self.salida.delete("1.0", tk.END)
        self.salida.config(state='disabled')

    def _escribir_linea(self, texto):
        self.salida.config(state='normal')
        self.salida.insert(tk.END, texto + "\n")
        self.salida.config(state='disabled')


# ------------- Ejecutable -------------
if __name__ == "__main__":
    app = AppPCode()
    app.mainloop()
