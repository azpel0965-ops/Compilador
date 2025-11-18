

import re
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont

class SemanticoApp:

    BASE_BOX_W, BASE_BOX_H = 64*2, 64
    BASE_HSPACE, BASE_VSPACE = 36, 84
    TOP_MARGIN, LEFT_MARGIN = 24, 24
    BASE_FONT = ("Segoe UI", 10, "bold")
    BOX_FILL = "#e6e6e6"
    BOX_STROKE = "#333333"
    TEXT_COLOR = "black"
    MIN_BOX_W = 90
    MAX_BOX_W = 220


    GRAMMAR_TEXT_BASE = """
    Sentencia   -> Ini Sentencias end
    _______________________________________________________________________
    Sentencias  -> TipoSent ; Sentencias | TipoSent ;
    _______________________________________________________________________
    TipoSent    -> DeclaracionVar | PideDatos | MostrarDatos |
                   Asignacion
    _______________________________________________________________________              
    DeclaracionVar -> tipoDato ListaNomvar
    _______________________________________________________________________
    ListaNomvar    -> nomvar | nomvar , ListaNomvar
    _______________________________________________________________________
    PideDatos   -> leer nomvar | leer
    _______________________________________________________________________
    MostrarDatos-> mostrar ListaMostrar | mostrar
    _______________________________________________________________________
    ListaMostrar-> MostrarItem | MostrarItem , ListaMostrar
    _______________________________________________________________________
    MostrarItem -> nomvar | strlit
    _______________________________________________________________________
    Asignacion  -> nomvar = Exp | nomvar = strlit
    _______________________________________________________________________
    Exp         -> Term ExpP | Exp-Term |Term + Term | Exp + Term |
                   Term - Term
    _______________________________________________________________________              
    ExpP        -> + Term ExpP | - Term ExpP | ε
    _______________________________________________________________________
    Term        -> Factor TermP | Numero | Numero * Numero |
                   Numero / Numero | nomvar * nomvar | nomvar | 
                   nomvar / nomvar | nomvar / Numero | nomvar * Numero | 
                   Term * nomvar | Term / nomvar
    _______________________________________________________________________              
    TermP       -> * Factor TermP | / Factor TermP | ε
    _______________________________________________________________________
    Factor      -> num | nomvar | boollit | ( Exp )
    _______________________________________________________________________
    tipoDato    -> ente | dec | carac | cade | bool
    _______________________________________________________________________
    nomvar      -> (alternativas desde variables.txt)
    _______________________________________________________________________
    Numero      -> 0.....1000000 """

    GRAMMAR_TEXT_RIGHTT = """
    Sentencia.valor   -> Ini.valor Sentencias.valor end.valor
    ___________________________________________________________________________________
    Sentencias.valor  -> TipoSent.valor ;.valor Sentencias.valor |
                         TipoSent.valor ;.valor
    ___________________________________________________________________________________                    
    TipoSent.valor    -> DeclaracionVar.valor | PideDatos.valor |
                         MostrarDatos.valor | Asignacion.valor
    ___________________________________________________________________________________                     
    DeclaracionVar.valor -> tipoDato.valor ListaNomvar.valor
    ___________________________________________________________________________________
    ListaNomvar.valor    -> nomvar.valor | nomvar.valor ,.valor ListaNomvar.valor
    ___________________________________________________________________________________
    PideDatos.valor   -> leer.valor nomvar.valor | leer.valor
    ___________________________________________________________________________________
    MostrarDatos.valor-> mostrar.valor ListaMostrar.valor | mostrar.valor
    ___________________________________________________________________________________
    ListaMostrar.valor-> MostrarItem.valor | MostrarItem.valor ,.valor ListaMostrar.valor
    ___________________________________________________________________________________
    MostrarItem.valor -> nomvar.valor | strlit.valor
    ___________________________________________________________________________________
    Asignacion.valor  -> nomvar.valor =.valor Exp.valor | 
                         nomvar.valor =.valor strlit.valor
    ___________________________________________________________________________________
    Exp.valor         -> Term.valor ExpP.valor | Exp.valor -.valor Term.valor | 
                         Term.valor +.valor Term.valor | Exp.valor +.valor Term.valor |
                         Term.valor -.valor Term.valor
    ___________________________________________________________________________________                     
    ExpP.valor        -> +.valor Term.valor ExpP.valor | -.valor Term.valor ExpP.valor |
                         ε.valor
    ___________________________________________________________________________________                     
    Term.valor        -> Factor.valor TermP.valor | Numero.valor | Numero.valor *.valor Numero.valor | 
                         Numero.valor /.valor Numero.valor | nomvar.valor *.valor nomvar.valor | 
                         nomvar.valor |nomvar.valor /.valor nomvar.valor | nomvar.valor /.valor Numero.valor | 
                         nomvar.valor *.valor Numero.valor | Term.valor *.valor nomvar.valor |
                         Term.valor /.valor nomvar.valor
    ___________________________________________________________________________________                    
    TermP.valor       -> *.valor Factor.valor TermP.valor | /.valor Factor.valor TermP.valor |
                         ε.valor
    ___________________________________________________________________________________                     
    Factor.valor      -> num.valor | nomvar.valor | boollit.valor | (.valor Exp.valor ).valor
    ___________________________________________________________________________________
    tipoDato.valor    -> ente.valor | dec.valor | carac.valor | cade.valor | bool.valor
    ___________________________________________________________________________________
    nomvar.valor      -> (alternativas desde variables.txt).valor
    ___________________________________________________________________________________
    Numero.valor      -> 0. valor .....1000000.valor"""


    GRAMMAR_TEXT_LEFT = GRAMMAR_TEXT_BASE
    GRAMMAR_TEXT_RIGHT = GRAMMAR_TEXT_RIGHTT
    ERROR_SINK = None

    # ---------- Léxico ----------
    TOKENS = [
        ("COMMENT", r"\#[^\n]*"),
        ("WS",      r"[ \t\r\n]+"),
        ("NUM",     r"\d+(\.\d+)?"),
        ("ID",      r"\$[A-Za-z_]\w*|[A-Za-z_]\w*"),
        ("STR",     r"\"[^\"\n]*\"|“[^”\n]*”"),
        ("PLUS",    r"\+"), ("MINUS", r"-"),
        ("MUL",     r"\*"), ("DIV", r"/"),
        ("ASSIGN",  r"="),
        ("COMMA",   r","), ("SEMI", r";"),
        ("LPAREN",  r"\("), ("RPAREN", r"\)"),
    ]
    KEYWORDS = {
        "Ini":"INI", "end":"END",
        "ente":"TIPO","dec":"TIPO","carac":"TIPO","cade":"TIPO","bool":"TIPO",
        "mostrar":"MOSTRAR", "leer":"LEER",
        "verdadero":"BOOL", "falso":"BOOL"
    }
    token_re = re.compile("|".join(f"(?P<{n}>{p})" for n,p in TOKENS))

    NUMERIC_TYPES = {"ente", "dec"}
    NON_NUMERIC_TYPES = {"cade", "carac", "bool"}


    @classmethod
    def run(cls, auto_run=False, parent=None):
        app = cls(parent=parent, auto_run=auto_run)
        app._mainloop_if_root()


    def __init__(self, parent=None, auto_run=False):
        self.parent = parent
        self.auto_run = auto_run

        self.root = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.root.title("Árbol semántico")
        self.root.geometry("1250x760")

        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cadena_entrada.txt")
        self.valid_ids = self._load_vars_file()

        self.expr_roots = []
        self.current_scale = 1.0
        self.err_box = None

        self._build_ui()

        if self.auto_run:
            self.root.after(120, self.run_analysis)
            self.root.after(200, self.root.lift)


    class TreeNode:
        def __init__(self, label, valor=None, children=None):
            self.label = label
            self.valor = valor
            self.children = children or []
            self.x = 0; self.y = 0; self.w = 0; self.h = 0
        def text(self):

            if self.valor is not None:
                return f"{self.label}\nValor\n{self.valor}"
            return f"{self.label}"


    @classmethod
    def tokenize(cls, text, valid_ids=None):
        out, pos = [], 0
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n": line_starts.append(i+1)

        def line_of(idx):
            lo, hi = 0, len(line_starts)-1
            while lo <= hi:
                mid = (lo+hi)//2
                if line_starts[mid] <= idx: lo = mid+1
                else: hi = mid-1
            return hi+1

        while pos < len(text):
            m = cls.token_re.match(text, pos)
            if not m:
                ln = line_of(pos)
                raise SyntaxError(f"Léxico: carácter inesperado en línea {ln}: {text[pos]!r}")
            typ, val = m.lastgroup, m.group()
            pos = m.end()
            if typ in ("WS","COMMENT"): continue
            if typ == "ID":
                if val in cls.KEYWORDS:
                    out.append((cls.KEYWORDS[val], val, line_of(m.start())))
                else:
                    out.append(("ID", val, line_of(m.start())))
            elif typ == "NUM":
                out.append(("NUM", float(val) if "." in val else int(val), line_of(m.start())))
            elif typ == "STR":
                txt = val[1:-1]
                out.append(("STR", txt, line_of(m.start())))
            else:
                out.append((typ, val, line_of(m.start())))
        out.append(("EOF","EOF", line_of(len(text)-1 if text else 0)))
        return out


    class Parser:
        def __init__(self, owner, toks):
            self.o = owner
            self.toks = toks; self.i = 0
            self.symtab = {}         # nombre -> {tipo, valor, usada, inicializada}
            self.expr_roots = []     # árboles de Exp (uno por asignación)
            self.errors = []         # lista de errores semánticos (lineados)
            self.had_div = False
            self.had_op = False      # evita dibujar $a=4; o $b=$a;

        def _error(self, msg, line=None):
            if line is None: line = self.cur()[2] if self.i < len(self.toks) else 1
            self.errors.append(f"Línea {line}: {msg}")

        def cur(self): return self.toks[self.i]
        def eat(self, t):
            c = self.cur()
            if c[0]!=t:
                self._error(f"Sintaxis: se esperaba {t} y llegó {c[0]}", c[2])
                self.i += 1
                return c
            self.i += 1; return c

        def parse(self):
            self.Sentencia()
            return self.symtab, self.expr_roots, self.errors

        def Sentencia(self):
            self.eat("INI")
            self.Sentencias()
            self.eat("END")

        def Sentencias(self):
            while True:
                if self.cur()[0] in ("END","EOF"): break
                self.TipoSent()
                self.eat("SEMI")
                if self.cur()[0] in ("END","EOF"): break

        def TipoSent(self):
            tk = self.cur()[0]
            if tk == "TIPO":
                self.DeclaracionVar()
            elif tk == "ID":
                self.Asignacion_o_IgnorarSiNoNumerica()
            elif tk in ("MOSTRAR", "LEER"):
                self.IgnorarHastaPuntoYComa()
            else:
                self.IgnorarHastaPuntoYComa()

        def IgnorarHastaPuntoYComa(self):
            self.i += 1
            while self.cur()[0] not in ("SEMI","END","EOF"):
                self.i += 1

        def DeclaracionVar(self):
            tipo_tok = self.eat("TIPO")
            tipo = tipo_tok[1]
            idtok = self.eat("ID")
            first, ln1 = idtok[1], idtok[2]
            if not first.startswith("$"):
                self._error(f"Las variables deben iniciar con '$': {first}", ln1)
            nombres = [first]
            while self.cur()[0]=="COMMA":
                self.eat("COMMA")
                idtok = self.eat("ID")
                nm, ln = idtok[1], idtok[2]
                if not nm.startswith("$"):
                    self._error(f"Las variables deben iniciar con '$': {nm}", ln)
                nombres.append(nm)
            for n in nombres:
                if n in self.symtab:
                    prev = self.symtab[n]["tipo"]
                    self._error(f"Variable '{n}' redeclarada (antes: {prev}, ahora: {tipo})", tipo_tok[2])
                    continue
                self.symtab[n]={"tipo":tipo,"valor":None,"usada":False,"inicializada":False}

        def Asignacion_o_IgnorarSiNoNumerica(self):
            idtok = self.eat("ID")
            # nombre y línea ya vienen de: idtok = self.eat("ID")
            nombre, ln = idtok[1], idtok[2]
            if not nombre.startswith("$"):
                self._error(f"Las variables deben iniciar con '$': {nombre}", ln)


            if nombre not in self.symtab:
                self._error(f"Variable no declarada/definida: '{nombre}'", ln)
                self.IgnorarHastaPuntoYComa()
                return

            self.eat("ASSIGN")

            nxt = self.cur()[0]

            if nxt in ("STR","BOOL","MOSTRAR","LEER"):
                self._error(f"Asigna un valor no numérico a {nombre}", self.cur()[2])
                self.IgnorarHastaPuntoYComa()
                return

            save_i = self.i
            self.had_div = False
            self.had_op = False
            try:
                enode, val, typ = self.Exp()
            except Exception:
                self.i = save_i
                self._error(f"Asignación inválida en {nombre}", self.cur()[2])
                self.IgnorarHastaPuntoYComa()
                return

            # LHS debe existir (si lo declaras en otro lado) – ya insertado si faltaba
            lhs_tipo = self.symtab[nombre]["tipo"]
            if self.had_div: typ = "dec" if typ in self.o.NUMERIC_TYPES else typ

            if lhs_tipo in self.o.NUMERIC_TYPES:
                if typ not in self.o.NUMERIC_TYPES:
                    self._error(f"No se puede asignar {typ} a {lhs_tipo}", idtok[2])
                else:
                    if lhs_tipo == "ente":
                        # Nueva regla: permitir dec -> ente redondeando
                        val = float(round(val))
                        typ = "ente"
                    # Si LHS es 'dec', se deja tal cual
            else:
                self._error(f"No se puede asignar valor numérico a {lhs_tipo}", idtok[2])

            self.symtab[nombre]["valor"]=val
            self.symtab[nombre]["inicializada"]=True


            if self.had_op:
                self.expr_roots.append(self.o.TreeNode(f"Asignación a {nombre}", valor=val, children=[enode]))


        def Exp(self):
            tnode, tval, ttyp = self.Term()
            return self.ExpP(tnode, tval, ttyp)

        def ExpP(self, left_node, left_val, left_typ):
            while self.cur()[0] in ("PLUS","MINUS"):
                self.had_op = True
                op=self.cur()[0]; self.i+=1
                rnode, rval, rtyp = self.Term()
                if left_typ not in self.o.NUMERIC_TYPES or rtyp not in self.o.NUMERIC_TYPES:
                    self._error(f"Operación aritmética inválida: {left_typ} y {rtyp}", self.cur()[2])
                    lval_num = 0.0 if left_typ not in self.o.NUMERIC_TYPES else left_val
                    rval_num = 0.0 if rtyp not in self.o.NUMERIC_TYPES else rval
                    left_val = lval_num + rval_num if op=="PLUS" else lval_num - rval_num
                    left_typ = "dec" if (left_typ=="dec" or rtyp=="dec") else "ente"
                else:
                    left_val = left_val + rval if op=="PLUS" else left_val - rval
                    left_typ = "dec" if (left_typ=="dec" or rtyp=="dec") else "ente"
                label = "+" if op=="PLUS" else "-"
                left_node = self.o.TreeNode("Exp", left_val, [left_node, self.o.TreeNode("operador", label), rnode])
            if left_node.label!="Exp":
                left_node = self.o.TreeNode("Exp", left_val, [left_node])
            return left_node, float(left_val), left_typ

        def Term(self):
            fnode, fval, ftyp = self.Factor()
            return self.TermP(fnode, fval, ftyp)

        def TermP(self, left_node, left_val, left_typ):
            while self.cur()[0] in ("MUL","DIV"):
                self.had_op = True
                op=self.cur()[0]; self.i+=1
                rnode, rval, rtyp = self.Factor()
                if op=="DIV": self.had_div = True

                if left_typ not in self.o.NUMERIC_TYPES or rtyp not in self.o.NUMERIC_TYPES:
                    self._error(f"Operación aritmética inválida: {left_typ} y {rtyp}", self.cur()[2])
                    lval_num = 0.0 if left_typ not in self.o.NUMERIC_TYPES else left_val
                    rval_num = 1.0 if (rtyp not in self.o.NUMERIC_TYPES) else rval
                    if op=="MUL":
                        left_val = lval_num * rval_num
                        left_typ = "dec" if (left_typ=="dec" or rtyp=="dec") else "ente"
                    else:
                        if abs(rval_num) < 1e-12:
                            self._error("División entre cero", self.cur()[2]); rval_num = 1.0
                        left_val = lval_num / rval_num; left_typ = "dec"
                else:
                    if op=="MUL":
                        left_val = left_val * rval
                        left_typ = "dec" if (left_typ=="dec" or rtyp=="dec") else "ente"
                    else:
                        if abs(rval) < 1e-12:
                            self._error("División entre cero", self.cur()[2]); rval = 1.0
                        left_val = left_val / rval; left_typ = "dec"

                label="*" if op=="MUL" else "/"
                left_node = self.o.TreeNode("Term", left_val, [left_node, self.o.TreeNode("operador", label), rnode])

            if left_node.label!="Term":
                left_node = self.o.TreeNode("Term", left_val, [left_node])
            return left_node, float(left_val), left_typ

        def Factor(self):
            t=self.cur()


            if t[0]=="NUM":
                self.i+=1
                typ = "dec" if isinstance(t[1], float) else "ente"
                return self.o.TreeNode("Numero", float(t[1]), []), float(t[1]), typ


            if t[0]=="ID":
                name, ln = t[1], t[2]
                if not name.startswith("$"):
                    self._error(f"Las variables deben iniciar con '$': {name}", ln)
                    self.i+=1
                    return self.o.TreeNode("nomvar", name), 0.0, "otro"
                self.i+=1
                if name not in self.symtab:
                    self._error(f"Identificador no declarado: '{name}'", ln)
                    self.symtab[name] = {"tipo":"ente","valor":None,"usada":True,"inicializada":False}
                    return self.o.TreeNode("nomvar", name), 0.0, "ente"
                self.symtab[name]["usada"] = True
                var_tipo = self.symtab[name]["tipo"]
                if var_tipo in self.o.NON_NUMERIC_TYPES:
                    self._error(f"Uso no numérico en aritmética: '{name}' es {var_tipo}", ln)
                    return self.o.TreeNode("nomvar", name), 0.0, var_tipo
                v = self.symtab[name]["valor"]
                if v is None or not self.symtab[name]["inicializada"]:
                    self._error(f"La variable '{name}' se usa antes de ser inicializada", ln)
                    v = 0.0
                    typ = "ente" if var_tipo=="ente" else "dec"
                else:
                    typ = "ente" if var_tipo=="ente" else "dec"
                return self.o.TreeNode("nomvar", name), float(v), typ


            if t[0]=="STR":
                self._error("No se puede usar cadena en expresión aritmética", t[2])
                self.i += 1
                return self.o.TreeNode("cadena"), 0.0, "cade"


            if t[0]=="BOOL":
                self._error("No se puede usar booleano en expresión aritmética", t[2])
                self.i += 1
                return self.o.TreeNode("booleano"), 0.0, "bool"


            if t[0]=="LPAREN":
                self.i+=1
                en, val, typ = self.Exp()
                self.eat("RPAREN")
                return self.o.TreeNode("Factor", val, [self.o.TreeNode("("), en, self.o.TreeNode(")")]), float(val), typ


            self._error(f"Se esperaba NUM, ID ($var), cadena no, o '(' y llegó {t[0]}", t[2])
            self.i += 1
            return self.o.TreeNode("Error"), 0.0, "otro"

    # ---------- Dibujo ----------
    class Drawer:
        def __init__(self, owner, canvas):
            self.o = owner
            self.canvas = canvas
            self.font = tkfont.Font(self.canvas, family=owner.BASE_FONT[0], size=owner.BASE_FONT[1], weight="bold")

        def _node_width(self, node, box_w):
            lines = node.text().split("\n")
            tw = max(self.font.measure(s) for s in lines) + 16
            return max(self.o.MIN_BOX_W, min(self.o.MAX_BOX_W, max(box_w, tw)))

        def _layout(self, node, depth, xstart, box_w, box_h, hspace, vspace):
            node.y = self.o.TOP_MARGIN + depth * (box_h + vspace)
            node_min_w = self._node_width(node, box_w)
            if not node.children:
                node.w = node_min_w; node.h = box_h; node.x = xstart
                return node.w, node.x + node.w//2
            widths, centers = [], []; curx = xstart
            for ch in node.children:
                w, c = self._layout(ch, depth+1, curx, box_w, box_h, hspace, vspace)
                widths.append(w); centers.append(c); curx += w + hspace
            total_w = sum(widths) + hspace*(len(widths)-1)
            cx = (centers[0] + centers[-1]) // 2
            node.w = max(total_w, node_min_w); node.h = box_h; node.x = cx - node.w//2
            return node.w, cx

        def draw_tree(self, node, box_w, box_h):
            for ch in node.children:
                self.canvas.create_line(
                    node.x + node.w//2, node.y + box_h,
                    ch.x + ch.w//2, ch.y,
                    width=2
                )
                self.draw_tree(ch, box_w, box_h)
            x0, y0 = node.x, node.y; x1, y1 = x0 + node.w, y0 + box_h
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=self.o.BOX_FILL, outline=self.o.BOX_STROKE, width=2)
            self.canvas.create_text((x0+x1)//2, (y0+y1)//2, text=node.text(),
                                    fill=self.o.TEXT_COLOR, font=self.font, width=node.w-10, justify="center")

    @classmethod
    def draw_forest(cls, canvas, roots, scale=1.0):
        drawer = cls.Drawer(cls, canvas)
        drawer.font.configure(size=max(7, int(cls.BASE_FONT[1]*scale)))
        box_w = int(cls.BASE_BOX_W*scale); box_h = int(cls.BASE_BOX_H*scale)
        hspace = int(cls.BASE_HSPACE*scale); vspace = int(cls.BASE_VSPACE*scale)

        canvas.delete("all")
        x = cls.LEFT_MARGIN
        for root in roots:
            drawer._layout(root, 0, x, box_w, box_h, hspace, vspace)
            drawer.draw_tree(root, box_w, box_h)
            x = root.x + root.w + 3*hspace
        x0,y0,x1,y1 = canvas.bbox("all")
        canvas.configure(scrollregion=(x0-40, y0-40, x1+40, y1+40))

    # ---------- UI helpers ----------
    def _build_ui(self):


        # Panel derecho con canvas para árboles
        right = ttk.Frame(self.root, padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        cf = ttk.Frame(right);
        cf.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(cf, bg="#f6f6f6")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar = ttk.Scrollbar(cf, orient="vertical", command=self.canvas.yview);
        vbar.grid(row=0, column=1, sticky="ns")
        hbar = ttk.Scrollbar(cf, orient="horizontal", command=self.canvas.xview);
        hbar.grid(row=1, column=0, sticky="ew")
        cf.rowconfigure(0, weight=1);
        cf.columnconfigure(0, weight=1)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

    def show_grammar(self):
        """Muestra la gramática en 2 columnas (solo lectura, sin botones)."""
        top = tk.Toplevel(self.root)
        top.title("Gramática ")
        top.geometry("1250x660")

        # Contenedor principal con dos columnas
        container = ttk.Frame(top, padding=8)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        # Encabezados
        ttk.Label(container, text="Regla gramatical", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w",
                                                                                    pady=(0, 4))
        ttk.Label(container, text="Regla semantica", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w",
                                                                                    pady=(0, 4))

        # --- Columna izquierda ---
        left_frame = ttk.Frame(container)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        lscroll_y = ttk.Scrollbar(left_frame, orient="vertical")
        lscroll_x = ttk.Scrollbar(left_frame, orient="horizontal")

        txt_left = tk.Text(left_frame, font=("Consolas", 11),
                           wrap="none", padx=6, pady=6,
                           yscrollcommand=lscroll_y.set,
                           xscrollcommand=lscroll_x.set)
        txt_left.grid(row=0, column=0, sticky="nsew")
        lscroll_y.config(command=txt_left.yview);
        lscroll_y.grid(row=0, column=1, sticky="ns")
        lscroll_x.config(command=txt_left.xview);
        lscroll_x.grid(row=1, column=0, sticky="ew")

        txt_left.insert("1.0", self.GRAMMAR_TEXT_LEFT)
        txt_left.configure(state="disabled")  # solo lectura

        # --- Columna derecha ---
        right_frame = ttk.Frame(container)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        rscroll_y = ttk.Scrollbar(right_frame, orient="vertical")
        rscroll_x = ttk.Scrollbar(right_frame, orient="horizontal")

        txt_right = tk.Text(right_frame, font=("Consolas", 11),
                            wrap="none", padx=6, pady=6,
                            yscrollcommand=rscroll_y.set,
                            xscrollcommand=rscroll_x.set)
        txt_right.grid(row=0, column=0, sticky="nsew")
        rscroll_y.config(command=txt_right.yview);
        rscroll_y.grid(row=0, column=1, sticky="ns")
        rscroll_x.config(command=txt_right.xview);
        rscroll_x.grid(row=1, column=0, sticky="ew")

        txt_right.insert("1.0", self.GRAMMAR_TEXT_RIGHT)
        txt_right.configure(state="disabled")  # solo lectura

    @classmethod
    def _precheck_semantic(cls):
        """
        Corre el análisis semántico sin UI para saber si hay errores.
        Devuelve (ok, errores, roots).
        - ok = True si NO hay errores.
        - errores = lista de strings (puede estar vacía).
        - roots = árboles de expresiones que se dibujarían.
        """
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cadena_entrada.txt")
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            toks = cls.tokenize(code)
            parser = cls.Parser(cls, toks)
            _symtab, roots, errors = parser.parse()
            ok = (len(errors) == 0)
            return ok, errors, roots
        except Exception as e:
            # si pasa algo raro, consideramos que no está ok y devolvemos un error genérico
            return False, [f"Error interno en prechequeo: {str(e)}"], []

    @classmethod
    def open_grammar_first(cls, parent=None, auto_run=True):

        """
            Abre una ventana con la gramática en dos columnas (solo lectura)
            y un botón 'Mostrar árbol' que abre la ventana de árboles.
            Antes de abrir, hace pre-chequeo semántico: si hay errores, NO abre nada.
            """
        # ===== BLOQUEO: pre-chequeo semántico SIN UI =====
        ok, errores, roots = cls._precheck_semantic()

        # manda errores al panel principal si hay hook
        sink = getattr(cls, "ERROR_SINK", None)
        if sink is not None and errores:
            try:
                sink(list(errores))
            except Exception:
                pass

        # si hay errores, NO abrir la ventana de gramática
        if not ok:
            return

        top = tk.Toplevel(parent) if parent is not None else tk.Tk()
        top.title("Gramática ")
        top.geometry("1250x660")

        # Contenedor principal con dos columnas
        container = ttk.Frame(top, padding=8)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        # Encabezados (CORRECTOS)
        ttk.Label(container, text="Regla gramatical", font=("Segoe UI", 10, "bold")) \
            .grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(container, text="Regla semántica", font=("Segoe UI", 10, "bold")) \
            .grid(row=0, column=1, sticky="w", pady=(0, 4))

        # --- Columna izquierda ---
        left_frame = ttk.Frame(container)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        left_frame.rowconfigure(0, weight=1);
        left_frame.columnconfigure(0, weight=1)

        lscroll_y = ttk.Scrollbar(left_frame, orient="vertical")
        lscroll_x = ttk.Scrollbar(left_frame, orient="horizontal")
        txt_left = tk.Text(left_frame, font=("Consolas", 11), wrap="none",
                           padx=6, pady=6, yscrollcommand=lscroll_y.set, xscrollcommand=lscroll_x.set)
        txt_left.grid(row=0, column=0, sticky="nsew")
        lscroll_y.config(command=txt_left.yview);
        lscroll_y.grid(row=0, column=1, sticky="ns")
        lscroll_x.config(command=txt_left.xview);
        lscroll_x.grid(row=1, column=0, sticky="ew")
        txt_left.insert("1.0", cls.GRAMMAR_TEXT_LEFT)
        txt_left.configure(state="disabled")  # solo lectura

        # --- Columna derecha ---
        right_frame = ttk.Frame(container)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        right_frame.rowconfigure(0, weight=1);
        right_frame.columnconfigure(0, weight=1)

        rscroll_y = ttk.Scrollbar(right_frame, orient="vertical")
        rscroll_x = ttk.Scrollbar(right_frame, orient="horizontal")
        txt_right = tk.Text(right_frame, font=("Consolas", 11), wrap="none",
                            padx=6, pady=6, yscrollcommand=rscroll_y.set, xscrollcommand=rscroll_x.set)
        txt_right.grid(row=0, column=0, sticky="nsew")
        rscroll_y.config(command=txt_right.yview);
        rscroll_y.grid(row=0, column=1, sticky="ns")
        rscroll_x.config(command=txt_right.xview);
        rscroll_x.grid(row=1, column=0, sticky="ew")
        txt_right.insert("1.0", cls.GRAMMAR_TEXT_RIGHT)
        txt_right.configure(state="disabled")  # solo lectura

        # --- Pie con botón ---
        footer = ttk.Frame(top, padding=(8, 6))
        footer.pack(fill=tk.X)

        def abrir_arbol():
            # 1) Pre–chequeo semántico sin UI
            ok, errores, roots = cls._precheck_semantic()

            # 2) Si hay hook de errores (ventana principal), envía ahí para que el usuario los vea
            sink = getattr(cls, "ERROR_SINK", None)
            if sink is not None:
                try:
                    sink(list(errores) if errores else [])
                except Exception:
                    pass

            # 3) Si hay errores, no abrir ventana de árboles y avisar
            if not ok:

                return

            # 4) Si TODO OK, ahora sí abre la ventana de árboles
            cls.run(auto_run=True, parent=parent if parent is not None else top)
            # Si deseas cerrar la ventana de gramática al abrir árboles, descomenta:
            # top.destroy()

        ttk.Button(footer, text="Mostrar árbol", command=abrir_arbol).pack(side=tk.RIGHT)

        if isinstance(top, tk.Tk):
            top.mainloop()

    def _load_vars_file(self, path="variables.txt"):
        try:
            with open(path,"r",encoding="utf-8") as f:
                return [s.strip() for s in re.split(r"[,\r\n]+", f.read()) if s.strip()]
        except Exception:
            return None

    def _show_errors(self, errors):
        """
        Ya no mostramos errores en la ventana del semántico.
        Si hay hook (ERROR_SINK), los mandamos a la ventana principal.
        """
        sink = getattr(self.__class__, "ERROR_SINK", None)
        if sink is not None:
            try:
                sink(list(errors) if errors else [])
            except Exception:
                pass



    # ---------- Acciones de UI ----------
    def run_analysis(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                code = f.read()
            toks = self.tokenize(code, valid_ids=self.valid_ids)
            parser = self.Parser(self, toks)
            _symtab, roots, errors = parser.parse()

            self._show_errors(errors)
            self.expr_roots = roots
            self.canvas.delete("all")
            if errors or not roots:
                return
            self.draw_forest(self.canvas, roots, scale=1.0)
            self.current_scale = 1.0
        except FileNotFoundError:
            messagebox.showerror("Error", f"No se encontró el archivo:\n{self.file_path}")
        except SyntaxError as e:
            self._show_errors([str(e)])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def fit_to_view(self):
        if not self.expr_roots: return
        self.draw_forest(self.canvas, self.expr_roots, scale=1.0)

    def export_pdf(self):
        if not self.expr_roots:
            messagebox.showinfo("Exportar PDF", "No hay expresiones aritméticas que dibujar.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF","*.pdf")],
                                            title="Guardar árbol como PDF")
        if not path: return
        try:
            from reportlab.pdfgen import canvas as rlcanvas
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.colors import black, HexColor
        except Exception:
            messagebox.showerror("Falta dependencia", "Instala reportlab:\n\npip install reportlab")
            return

        # preparar layout lógico
        tmp = tk.Canvas(); drawer = self.Drawer(self, tmp)
        roots = []
        for r in self.expr_roots:
            def clone(n): return self.TreeNode(n.label, n.valor, [clone(x) for x in n.children])
            roots.append(clone(r))
        x = self.LEFT_MARGIN; max_h = 0
        for r in roots:
            drawer._layout(r, 0, x, self.BASE_BOX_W, self.BASE_BOX_H, self.BASE_HSPACE, self.BASE_VSPACE)
            x = r.x + r.w + 3*self.BASE_HSPACE
            max_h = max(max_h, r.y + self.BASE_BOX_H)

        pw, ph = A4
        total_w = x + self.LEFT_MARGIN
        total_h = max_h + self.TOP_MARGIN
        pagesize = A4
        if total_w > pw - 40 or total_h > ph - 40:
            pagesize = landscape(A4); pw, ph = ph, pw
        c = rlcanvas.Canvas(path, pagesize=pagesize)

        sx = (pw - 40) / total_w
        sy = (ph - 40) / total_h
        scale = min(1.0, sx, sy)

        def draw_pdf_tree(n):
            for ch in n.children:
                c.setLineWidth(1.2); c.setStrokeColor(black)
                x1 = (n.x + n.w/2) * scale + 20
                y1 = (total_h - (n.y + self.BASE_BOX_H)) * scale + 20
                x2 = (ch.x + ch.w/2) * scale + 20
                y2 = (total_h - ch.y) * scale + 20
                c.line(x1, y1, x2, y2); draw_pdf_tree(ch)
            x0 = n.x * scale + 20; y0 = (total_h - (n.y + self.BASE_BOX_H)) * scale + 20
            ww = n.w * scale; hh = self.BASE_BOX_H * scale
            c.setFillColor(HexColor(self.BOX_FILL)); c.setStrokeColor(HexColor(self.BOX_STROKE))
            c.rect(x0, y0, ww, hh, stroke=1, fill=1)
            c.setFillColor(black); label = n.text()
            c.setFont("Helvetica-Bold", max(6, int(10*scale)))
            lines = label.split("\n")
            if len(lines) == 1:
                c.drawCentredString(x0 + ww/2, y0 + hh/2 - 4*scale, lines[0])
            elif len(lines) == 2:
                c.drawCentredString(x0 + ww/2, y0 + hh/2 + 4*scale, lines[0])
                c.drawCentredString(x0 + ww/2, y0 + hh/2 - 10*scale, lines[1])
            else:  # 3 líneas: Título / Valor / número
                c.drawCentredString(x0 + ww/2, y0 + hh/2 + 10*scale, lines[0])
                c.drawCentredString(x0 + ww/2, y0 + hh/2 - 0*scale,  lines[1])
                c.drawCentredString(x0 + ww/2, y0 + hh/2 - 12*scale, lines[2])

        for r in roots:
            draw_pdf_tree(r)
        c.showPage(); c.save()
        messagebox.showinfo("Exportar PDF", "PDF generado correctamente.")

    def _mainloop_if_root(self):
        if isinstance(self.root, tk.Tk):
            self.root.mainloop()


#if __name__ == "__main__":
 #   SemanticoApp.run(auto_run=False)
