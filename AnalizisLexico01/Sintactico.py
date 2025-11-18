import os, re, sys, threading, traceback

class SintacticoApp:
    DEBUG = False
    _total_declared = None  # leído de variables.txt
    _lex_values = {}        # idx(1-based) -> lexema real para num/strlit/boollit

    # --- buffers/control para capturar asignaciones aritméticas ---
    _ops_file_path = None          # ruta de operaciones.txt
    _rhs_buffer = []               # [{'text': str, 'snap': int}, ...]
    _assign_open = None            # {'lhs': str, 'tokens': [], 'snap': int, 'saw_strlit': bool, 'saw_op': bool}

    # ----------------- utilidades de rutas -----------------
    @classmethod
    def _log(cls, msg):
        if cls.DEBUG: print(msg)

    @classmethod
    def _ruta_base(cls):
        return os.path.dirname(__file__)

    @classmethod
    def _candidatos_base(cls):
        base = cls._ruta_base()
        return [base, os.path.dirname(base), os.getcwd()]

    @classmethod
    def _buscar_en_candidatos(cls, nombre_archivo: str) -> str:
        for base in cls._candidatos_base():
            ruta = os.path.join(base, nombre_archivo)
            if os.path.exists(ruta):
                cls._log(f"[Sintáctico] Usando {nombre_archivo} en: {ruta}")
                return ruta
        ruta_def = os.path.join(cls._ruta_base(), nombre_archivo)
        cls._log(f"[Sintáctico] {nombre_archivo} no encontrado. Intentaré en: {ruta_def}")
        return ruta_def

    # ----------------- lectura de variables ----------------
    @classmethod
    def leer_variables_desde_txt(cls, nombre="variables.txt"):
        ruta = cls._buscar_en_candidatos(nombre)
        vars_list, total_declared = [], None
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                for ln in f:
                    t = ln.strip()
                    if not t:
                        continue
                    m = re.search(r'^\s*TOTAL\s*[:=]\s*(\d+)\s*$', t, re.I)
                    if m:
                        total_declared = int(m.group(1))
                        continue
                    vars_list.append(t)
        else:
            cls._log(f"[Sintáctico] Advertencia: no existe {ruta}")
        cls._total_declared = total_declared
        return vars_list

    # ----------------- tokenización ------------------------
    @classmethod
    def leer_cadena_desde_txt(cls, nombre="cadena_entrada.txt"):
        ruta = cls._buscar_en_candidatos(nombre)
        if not os.path.exists(ruta):
            cls._log(f"[Sintáctico] Advertencia: no existe {ruta}")
            return ["#"]

        with open(ruta, "r", encoding="utf-8") as f:
            texto = f.read()

        # normalizar comillas curvas y quitar comentarios
        texto = texto.replace("“", "\"").replace("”", "\"")
        texto = re.sub(r'#.*?(?=\n|$)', '', texto)

        patron = re.compile(
            r'"[^"\n]*"'               # "texto"
            r'|\$[A-Za-z_]\w*'         # $var
            r'|\d+(?:\.\d+)?'          # número
            r'|[A-Za-z]+'              # palabras
            r'|[,;()=+\-*/]'           # símbolos
        )

        raw = patron.findall(texto)
        toks = []
        cls._lex_values = {}
        pos = 1  # índice 1-based

        for t in raw:
            if not t:
                continue
            if t[0] == '"':
                toks.append("strlit"); cls._lex_values[pos] = t
            elif t[0] == '$':
                toks.append(t)
            elif re.fullmatch(r'\d+(?:\.\d+)?', t):
                toks.append("num"); cls._lex_values[pos] = t
            elif t.lower() in ("verdadero", "falso"):
                toks.append("boollit"); cls._lex_values[pos] = t.lower()
            else:
                toks.append(t)
            pos += 1

        if not toks or toks[-1] != "#":
            toks.append("#")
        return toks

    # ----------------- gramática ---------------------------
    @classmethod
    def construir_gramatica_fija(cls, vars_nomvar):
        G = {
            "Sentencia": [["Ini", "Sentencias", "end"]],
            "Sentencias": [["TipoSent", ";", "Sentencias"], ["TipoSent", ";"]],
            "TipoSent": [["DeclaracionVar"], ["PideDatos"], ["MostrarDatos"], ["Asignacion"]],
            "DeclaracionVar": [["tipoDato", "ListaNomvar"]],
            "ListaNomvar": [["nomvar"], ["nomvar", ",", "ListaNomvar"]],
            "PideDatos": [["leer", "nomvar"], ["leer"]],
            "MostrarDatos": [["mostrar", "ListaMostrar"], ["mostrar"]],
            "ListaMostrar": [["MostrarItem"], ["MostrarItem", ",", "ListaMostrar"]],
            "MostrarItem": [["nomvar"], ["strlit"]],
            "Asignacion": [["nomvar", "=", "Exp"], ["nomvar", "=", "strlit"]],
            "Exp":   [["Term", "ExpP"]],
            "ExpP":  [["+", "Term", "ExpP"], ["-", "Term", "ExpP"], []],
            "Term":  [["Factor", "TermP"]],
            "TermP": [["*", "Factor", "TermP"], ["/", "Factor", "TermP"], []],
            "Factor":[["num"], ["nomvar"], ["boollit"], ["(", "Exp", ")"]],
            "tipoDato": [["ente"], ["dec"], ["carac"], ["cade"], ["bool"]],
        }
        G["nomvar"] = [[v] for v in (vars_nomvar or [])]
        labels = {(nt, i+1): f"{nt}{i+1}" for nt, alts in G.items() for i in range(len(alts))}
        return G, "Sentencia", labels

    # ----------------- helpers ------------------------------
    @staticmethod
    def alpha_to_str(alpha): return " ".join(alpha) if alpha else "ε"
    @staticmethod
    def beta_to_str(beta):  return " ".join(beta)
    @classmethod
    def _fmt_token(cls, tok, idx_1based):
        val = cls._lex_values.get(idx_1based)
        if tok in ("num", "strlit", "boollit") and val is not None:
            return f"{tok}({val})"
        return f"'{tok}'"
    @classmethod
    def _lexema(cls, tok, idx_1based):
        if tok in ("num", "strlit", "boollit"):
            return cls._lex_values.get(idx_1based, tok)
        return tok
    @classmethod
    def _ultimo_match_terminal(cls, actions):
        for k in range(len(actions) - 1, -1, -1):
            a = actions[k]
            if a.get("kind") == "match":
                return a["detail"], k
        return None, -1
    @classmethod
    def print_state(cls, mode, i, alpha, beta, note):
        print(f"( {mode}, {i}, {cls.alpha_to_str(alpha)}, {cls.beta_to_str(beta)} )".ljust(75), note)

    # ----------------- analizador (backtracking) ------------
    @classmethod
    def analyze(cls, grammar, start, labels, input_syms):
        beta = [start, "#"]
        alpha = []
        mode = "n"
        i = 1
        actions, decisions = [], []

        # buffers / archivo
        cls._rhs_buffer = []
        cls._assign_open = None
        if cls._ops_file_path is None:
            cls._ops_file_path = os.path.join(cls._ruta_base(), "operaciones.txt")
        # limpiar archivo al inicio
        try:
            with open(cls._ops_file_path, "w", encoding="utf-8") as _:
                pass
        except Exception as e:
            cls._log(f"[Sintáctico] No pude crear/limpiar operaciones.txt: {e}")

        def a_sym():
            idx = i - 1
            return input_syms[idx] if 0 <= idx < len(input_syms) else "#"

        print("\nTRAZA:")
        cls.print_state("n", 1, alpha, beta, "Inicio")

        while True:
            # Éxito
            if beta == ["#"] and a_sym() == "#":
                cls.print_state("n", i, alpha, beta, "(3) fin de pila con '#'")

                # volcar buffer sin duplicados
                try:
                    seen = set(); lines = []
                    for it in cls._rhs_buffer:
                        t = it["text"]
                        if t not in seen:
                            seen.add(t); lines.append(t)
                    with open(cls._ops_file_path, "w", encoding="utf-8") as f:
                        for t in lines: f.write(t + "\n")
                except Exception as e:
                    cls._log(f"[Sintáctico] Error al escribir operaciones.txt: {e}")

                cls.print_state("t", i+1, alpha, ["ε"], "ACEPTA")
                return True

            if mode == "n":
                X = beta[0]
                a = a_sym()

                # expandir no terminal
                if X in grammar:
                    rhss = grammar.get(X, [])
                    if not rhss:
                        mode = "r"
                        cls.print_state("r", i, alpha, beta, "(4) no hay producciones para no terminal")
                        continue
                    alt = 1
                    rhs = rhss[alt-1]
                    beta = rhs + beta[1:]
                    label = labels[(X, alt)]
                    alpha.append(label)
                    actions.append({"kind":"expand","detail":label,"nonterm":X,"alt":alt,"rhs":rhs})
                    decisions.append({"X":X,"alt":alt,"i0":i,"alpha_len":len(alpha),"rhs":rhs})
                    cls.print_state("n", i, alpha, beta, f"(1) entra {X}, aplica {label}")
                    continue

                # concordancia de terminal
                if X not in grammar:
                    if X == a:
                        i_before = i  # índice del token a consumir

                        # === CAPTURA de asignación completa LHS = RHS ; (backtracking-safe) ===
                        if X == "=":
                            prev_tok, _ = cls._ultimo_match_terminal(actions)
                            lhs = prev_tok if isinstance(prev_tok, str) else None
                            cls._assign_open = {
                                "lhs": lhs,
                                "tokens": [],
                                "snap": len(actions),
                                "saw_strlit": False,
                                "saw_op": False  # <-- SOLO guardamos si hay + - * /
                            }

                        elif X == ";" and cls._assign_open is not None:
                            # cerrar: guardar SOLO si no hubo strlit y sí hubo operador
                            ao = cls._assign_open
                            if not ao["saw_strlit"] and ao["saw_op"] and ao["tokens"] and ao["lhs"]:
                                rhs_text = " ".join(ao["tokens"])
                                linea = f"{ao['lhs']} = {rhs_text} ;"
                                cls._rhs_buffer.append({"text": linea, "snap": ao["snap"]})
                            cls._assign_open = None

                        elif cls._assign_open is not None:
                            # aún dentro de la RHS
                            if X == "strlit":
                                cls._assign_open["saw_strlit"] = True
                            if X in ("+", "-", "*", "/"):
                                cls._assign_open["saw_op"] = True
                            lex = cls._lexema(X, i_before)
                            cls._assign_open["tokens"].append(lex)
                        # === FIN CAPTURA ===

                        beta = beta[1:]
                        alpha.append(X)
                        actions.append({"kind":"match","detail":X})
                        i += 1
                        cls.print_state("n", i, alpha, beta, f"(2) concordancia {cls._fmt_token(X, i_before)}")
                        continue
                    else:
                        cls.print_state(
                            "r", i, alpha, beta,
                            f"(4) no concuerda: {cls._fmt_token(X, i)} ≠ {cls._fmt_token(a, i)}"
                        )
                        mode = "r"
                        continue

                mode = "r"
                cls.print_state("r", i, alpha, beta, "(4) estado no válido")
                continue

            # --------- retroceso ----------
            else:
                if not decisions:
                    cls.print_state("e", i, alpha, beta, "(6b) sin más alternativas: RECHAZA")
                    return False

                # deshacer último match
                if actions and actions[-1]["kind"] == "match":
                    last = actions.pop()
                    i -= 1
                    beta = [last["detail"]] + beta

                    # purgar capturas si retrocedimos por debajo del snapshot
                    if cls._assign_open is not None and len(actions) < cls._assign_open["snap"]:
                        cls._assign_open = None
                    while cls._rhs_buffer and cls._rhs_buffer[-1]["snap"] > len(actions):
                        cls._rhs_buffer.pop()

                    # quitar último terminal de alpha
                    for p in range(len(alpha)-1, -1, -1):
                        if alpha[p] == last["detail"]:
                            alpha.pop(p); break
                    cls.print_state("r", i, alpha, beta, "(5) retroceso a la entrada")
                    continue

                # punto de decisión
                dp = decisions[-1]
                X = dp["X"]; rhss = grammar[X]
                tried_alt = dp["alt"]; rhs = dp["rhs"]

                # deshacer matches posteriores a expandir X
                while i > dp["i0"]:
                    k = len(actions) - 1
                    while k >= 0 and actions[k]["kind"] != "match":
                        k -= 1
                    if k < 0: break
                    m = actions.pop(k)
                    i -= 1
                    beta = [m["detail"]] + beta

                    if cls._assign_open is not None and len(actions) < cls._assign_open["snap"]:
                        cls._assign_open = None
                    while cls._rhs_buffer and cls._rhs_buffer[-1]["snap"] > len(actions):
                        cls._rhs_buffer.pop()

                    for p in range(len(alpha)-1, -1, -1):
                        if alpha[p] == m["detail"]:
                            alpha.pop(p); break
                    cls.print_state("r", i, alpha, beta, "(5) retroceso a la entrada")

                # volver a X
                if beta[:len(rhs)] == rhs:
                    beta = [X] + beta[len(rhs):]
                else:
                    beta = [X] + beta
                # quitar etiqueta Xj de alpha
                for p in range(len(alpha)-1, -1, -1):
                    if alpha[p] == f"{X}{tried_alt}":
                        alpha.pop(p); break
                # quitar acción 'expand' de Xj
                q = len(actions) - 1
                while q >= 0:
                    a_act = actions[q]
                    if a_act["kind"] == "expand" and a_act["nonterm"] == X and a_act["alt"] == tried_alt:
                        actions.pop(q); break
                    q -= 1
                cls.print_state("r", i, alpha, beta, f"(6c) deshacer producción {X}{tried_alt} (volver a {X})")

                # siguiente alternativa
                next_alt = tried_alt + 1
                if next_alt <= len(rhss):
                    new_rhs = rhss[next_alt-1]
                    beta = new_rhs + beta[1:]
                    new_label = f"{X}{next_alt}"
                    alpha.append(new_label)
                    actions.append({"kind":"expand","detail":new_label,"nonterm":X,"alt":next_alt,"rhs":new_rhs})
                    decisions[-1] = {"X":X,"alt":next_alt,"i0":dp["i0"],"alpha_len":len(alpha),"rhs":new_rhs}
                    cls.print_state("n", i, alpha, beta, f"(6a) siguiente alternativa de {X}: aplica {new_label}")
                    mode = "n"
                else:
                    decisions.pop()
                continue

    # ----------------- API p/botón --------------------------
    @classmethod
    def analizar_sintactico(cls, *_):
        vars_nomvar = cls.leer_variables_desde_txt("variables.txt")
        total_decl = cls._total_declared
        if total_decl is not None and total_decl != len(vars_nomvar):
            raise ValueError(
                f"TOTAL declarado en variables.txt = {total_decl}, "
                f"pero se encontraron {len(vars_nomvar)} variables listadas."
            )
        if not vars_nomvar:
            print("[Aviso] No se leyeron variables; 'nomvar' quedará vacío.")
        grammar, start, labels = cls.construir_gramatica_fija(vars_nomvar)
        input_syms = cls.leer_cadena_desde_txt("cadena_entrada.txt")
        cls.analyze(grammar, start, labels, input_syms)

    # ----------------- Redirección a Text -------------------
    class _TextRedirector:
        def __init__(self, text_widget): self.text = text_widget
        def write(self, s):
            if s: self.text.after(0, self._append, s)
        def flush(self): pass
        def _append(self, s):
            try:
                self.text.insert("end", s); self.text.see("end")
            except Exception: pass

    # ----------------- UI (Tkinter) -------------------------
    def __init__(self, parent=None, limpiar=True, titulo="Sintáctico - Traza (Backtracking)"):
        import tkinter as tk
        from tkinter import ttk
        from tkinter import scrolledtext as st

        self.win = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.win.title(titulo); self.win.minsize(780, 520)

        main = ttk.Frame(self.win, padding=10); main.pack(fill="both", expand=True)
        top = ttk.Frame(main); top.pack(fill="x", pady=(0,8))
        ttk.Button(top, text="Cerrar", command=self.win.destroy).pack(side="right")

        self.txt = st.ScrolledText(main, wrap="none", height=28, undo=False)
        self.txt.configure(font=("Consolas", 10)); self.txt.pack(fill="both", expand=True)

        self.status = ttk.Label(main, text="Ejecutando…", anchor="w")
        self.status.pack(fill="x", pady=(8,0))

        threading.Thread(target=self._run, daemon=True).start()
        if parent is None: self.win.mainloop()

    def _run(self):
        so, se = sys.stdout, sys.stderr
        redir = self._TextRedirector(self.txt)
        try:
            self.txt.delete("1.0", "end")
            sys.stdout = redir; sys.stderr = redir
            self.status.config(text="Ejecutando…")
            self.__class__.analizar_sintactico()
            self.status.config(text="Ejecución terminada")
        except ValueError as e:
            print(f"[Error] {e}\n"); self.status.config(text="Error en variables.txt")
        except Exception:
            traceback.print_exc(); self.status.config(text="Ocurrió un error (ver traza arriba)")
        finally:
            sys.stdout, sys.stderr = so, se

    @classmethod
    def run(cls, parent=None, limpiar=True, titulo="Sintáctico "):
        return cls(parent=parent, limpiar=limpiar, titulo=titulo)

    @classmethod
    def correr_en_text(cls, text_widget, status_widget=None, limpiar=True):
        so, se = sys.stdout, sys.stderr
        redir = cls._TextRedirector(text_widget)
        def _runner():
            try:
                if limpiar: text_widget.delete("1.0", "end")
                sys.stdout = redir; sys.stderr = redir
                if status_widget is not None: status_widget.config(text="Ejecutando…")
                cls.analizar_sintactico()
                if status_widget is not None: status_widget.config(text="Ejecución terminada")
            except ValueError as e:
                print(f"[Error] {e}\n")
                if status_widget is not None: status_widget.config(text="Error en variables.txt")
            except Exception:
                traceback.print_exc()
                if status_widget is not None: status_widget.config(text="Ocurrió un error")
            finally:
                sys.stdout, sys.stderr = so, se
        threading.Thread(target=_runner, daemon=True).start()

if __name__ == "__main__":
    SintacticoApp.run(parent=None)
