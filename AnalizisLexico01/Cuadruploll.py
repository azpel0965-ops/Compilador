# ==================== CUADRUPLOS (orden como en tu tabla) ====================
import os
import re
from typing import List, Tuple, Optional


def leer_operaciones() -> List[str]:
    nombre = "operaciones.txt"
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre)
    if not os.path.exists(ruta):
        print("[Aviso] No existe operaciones.txt")
        return []
    lineas = []
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            s = linea.strip()
            if s.endswith(";"):
                s = s[:-1]           # quitar ';'
            s = s.replace(" ", "")
            if s:
                lineas.append(s)
    return lineas


TOKEN_RE = re.compile(r'\d+\.\d+|\d+|\$[A-Za-z_]\w*|[A-Za-z_]\w*|[()\[\]\{\}+\-*/]')

def tokenizar(texto: str) -> List[str]:
    return TOKEN_RE.findall(texto)

def es_operando(tok: str) -> bool:
    return re.fullmatch(r'\d+(?:\.\d+)?|\$?[A-Za-z_]\w*', tok) is not None


PREC = {"+":1, "-":1, "*":2, "/":2}
ABRE   = set("([{")
CIERRA = {")":"(", "]":"[", "}":"{"}

class Nodo:
    def __init__(self, op: Optional[str]=None, izq:'Nodo'=None, der:'Nodo'=None, val:Optional[str]=None):
        self.op, self.izq, self.der, self.val = op, izq, der, val
    def es_val(self) -> bool: return self.val is not None

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
        raise ValueError("Expresión inválida.")
    return vals[0]

class Emisor:
    def __init__(self, prefijo="v"):
        self.prefijo = prefijo
        self.n = 1
        self.quads: List[Tuple[str,str,str,str]] = []

    def tmp(self) -> str:
        t = f"{self.prefijo}{self.n}"
        self.n += 1
        return t

    def colapsar_mul_div(self, nodo: Nodo) -> Nodo:
        if nodo.es_val():
            return nodo
        if nodo.op in {"+", "-"}:
            izq = self.colapsar_mul_div(nodo.izq)
            der = self.colapsar_mul_div(nodo.der)
            return Nodo(op=nodo.op, izq=izq, der=der)
        else:  # '*' o '/'
            izq = self.colapsar_mul_div(nodo.izq)
            der = self.colapsar_mul_div(nodo.der)
            a1 = izq.val if izq.es_val() else None
            a2 = der.val if der.es_val() else None
            if a1 is None or a2 is None:
                raise RuntimeError("Colapso */ inválido")
            r = self.tmp()
            self.quads.append((nodo.op, a1, a2, r))
            return Nodo(val=r)

    def emitir_suma_resta(self, nodo: Nodo) -> str:
        if nodo.es_val():
            return nodo.val
        a1 = self.emitir_suma_resta(nodo.izq)
        a2 = self.emitir_suma_resta(nodo.der)
        r = self.tmp()
        self.quads.append((nodo.op, a1, a2, r))
        return r

def imprimir_cuadruplas(quads: List[Tuple[str,str,str,str]]):
    print("\nTabla de cuádruplas:")
    print("Operador | Oper1 | Oper2 | Auxiliar")
    print("-------------------------------------")
    for op, a1, a2, r in quads:
        print(f"{op:^8} | {a1:^5} | {a2:^5} | {r:^8}")

if __name__ == "__main__":
    print("=== CUÁDRUPLAS (primero */ luego +- , y luego asignación) ===")
    lineas = leer_operaciones()

    if not lineas:
        print("No hay expresiones en el archivo.")
    else:
        for i, linea in enumerate(lineas, 1):
            print("\n" + "="*60)
            print(f"EXPRESIÓN {i}: {linea}")
            destino = None
            expr = linea
            if "=" in linea:
                destino, expr = linea.split("=", 1)
            tokens = tokenizar(expr)
            ast = construir_ast(tokens)
            em = Emisor(prefijo="v")
            ast2 = em.colapsar_mul_div(ast)
            ultimo = em.emitir_suma_resta(ast2) if not ast2.es_val() else ast2.val
            if destino:
                em.quads.append(("=", ultimo, "-", destino))

            imprimir_cuadruplas(em.quads)
