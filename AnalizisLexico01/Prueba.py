# retroceso_parser.py
# Analizador por retroceso (backtracking) con trazado paso a paso.
# Trabaja por TOKENS (separados por espacios) y detecta no terminales con "X in grammar".
# 'nomvar' hace match con cualquier token que empiece con '$'.

def normalize_rhs(s):
    s = s.strip()
    if s == "ε":
        return []
    # cada símbolo es un token separado por espacios
    return s.split()

def parse_grammar():
    print("Introduce la gramática (una línea por no terminal). Ejemplo: S->a A d|a B")
    print("Termina con una línea vacía.\n")
    grammar = {}
    order = []
    while True:
        line = input().strip()
        if not line:
            break
        if "->" not in line:
            raise ValueError("Formato inválido. Usa: A->x|y")
        L, R = line.split("->", 1)
        L = L.strip()
        alts = [a.strip() for a in R.split("|")]
        grammar[L] = [normalize_rhs(a) for a in alts]
        order.append(L)
    if not grammar:
        raise ValueError("No se ingresó ninguna gramática.")
    start = order[0]
    labels = {}
    for nt in grammar:
        for i in range(len(grammar[nt])):
            labels[(nt, i+1)] = f"{nt}{i+1}"
    return grammar, start, labels

def read_input_syms():
    s = input("\nCadena a analizar (separa por espacios): ").strip()
    syms = s.split()
    if not syms or syms[-1] != "#":
        syms.append("#")
    return syms

def alpha_to_str(alpha):
    return " ".join(alpha) if alpha else "ε"

def beta_to_str(beta):
    return " ".join(beta)

def print_state(mode, i, alpha, beta, note):
    print(f"( {mode}, {i}, {alpha_to_str(alpha)}, {beta_to_str(beta)} )".ljust(80), note)

def analyze(grammar, start, labels, input_syms):
    # Estado
    beta = [start, "#"]   # pila (por derivar)
    alpha = []            # reconocidos + etiquetas (S1, A2, ...)
    mode = "n"            # 'n' normal, 'r' retroceso
    i = 1                 # posición 1-based en la entrada (tokens)
    actions = []          # [{'kind':'expand'|'match','detail':..., 'nonterm':..., 'alt':..., 'rhs':...}]
    decisions = []        # [{'X':..., 'alt':..., 'i0':..., 'alpha_len':..., 'rhs':...}]

    def a_sym():
        idx = i - 1
        if 0 <= idx < len(input_syms):
            return input_syms[idx]
        return "#"

    print("\nTRAZA:")
    print_state("n", 1, alpha, beta, "Inicio")

    while True:
        # Regla 3: éxito
        if beta == ["#"] and a_sym() == "#":
            print_state("n", i, alpha, beta, "(3) fin de pila con '#'")
            print_state("t", i+1, alpha, ["ε"], "ACEPTA")
            return True

        if mode == "n":
            X = beta[0]
            a = a_sym()

            # Regla 1: expandir no terminal (X es no terminal si está en la gramática)
            if X in grammar:
                rhss = grammar.get(X, [])
                if not rhss:
                    mode = "r"
                    print_state("r", i, alpha, beta, "(4) no hay producciones para no terminal")
                    continue
                alt = 1
                rhs = rhss[alt-1]
                beta = rhs + beta[1:]                # sustituye X por rhs
                label = labels[(X, alt)]
                alpha.append(label)                  # agrega S1 / A1 / ...
                actions.append({"kind":"expand","detail":label,"nonterm":X,"alt":alt,"rhs":rhs})
                decisions.append({"X":X,"alt":alt,"i0":i,"alpha_len":len(alpha),"rhs":rhs})
                print_state("n", i, alpha, beta, f"(1) entra {X}, aplica {label}")
                continue

            # Regla 2: concordancia de terminal (con caso especial 'nomvar')
            if X not in grammar:
                ok = False
                if X.lower() == "nomvar" and a.startswith("$"):
                    ok = True
                elif X == a:
                    ok = True

                if ok:
                    beta = beta[1:]                   # consume terminal de la pila
                    alpha.append(X)                   # guardamos el símbolo esperado (no el lexema) para retroceso
                    actions.append({"kind":"match","detail":X})
                    i += 1
                    # Mostrar el lexema real si es nomvar, para que la traza sea clara
                    note = f"(2) concordancia '{a}'" if X.lower() == "nomvar" else f"(2) concordancia '{X}'"
                    print_state("n", i, alpha, beta, note)
                    continue
                else:
                    mode = "r"
                    if X == "#":
                        print_state("r", i, alpha, beta, "(4) fin inválido (sobra entrada)")
                    else:
                        print_state("r", i, alpha, beta, f"(4) no concuerda: {X} ≠ {a}")
                    continue

            # Cualquier otro caso
            mode = "r"
            print_state("r", i, alpha, beta, "(4) estado no válido")
            continue

        # ===== MODO 'r' (retroceso) =====
        else:
            if not decisions:
                print_state("r", i, alpha, beta, "(6b) sin más alternativas: RECHAZA")
                return False

            # Regla 5: deshacer matches
            if actions and actions[-1]["kind"] == "match":
                last = actions.pop()
                i -= 1
                beta = [last["detail"]] + beta   # devolvemos el símbolo esperado (ej. 'nomvar')
                # quitar terminal de alpha (última ocurrencia)
                if alpha and alpha[-1] == last["detail"]:
                    alpha.pop()
                else:
                    for p in range(len(alpha)-1, -1, -1):
                        if alpha[p] == last["detail"]:
                            alpha.pop(p)
                            break
                print_state("r", i, alpha, beta, "(5) retroceso a la entrada")
                continue

            # Tomar el último punto de decisión
            dp = decisions[-1]
            X = dp["X"]
            rhss = grammar[X]
            tried_alt = dp["alt"]
            rhs = dp["rhs"]

            # Deshacer TODOS los matches hechos después de expandir X (si quedara alguno)
            while i > dp["i0"]:
                # buscar el último 'match' en acciones
                k = len(actions) - 1
                while k >= 0 and actions[k]["kind"] != "match":
                    k -= 1
                if k < 0:
                    break
                m = actions.pop(k)
                i -= 1
                beta = [m["detail"]] + beta
                for p in range(len(alpha)-1, -1, -1):
                    if alpha[p] == m["detail"]:
                        alpha.pop(p)
                        break
                print_state("r", i, alpha, beta, "(5) retroceso a la entrada")

            # Regla 6c: deshacer producción Xj → volver a X
            if beta[:len(rhs)] == rhs:
                beta = [X] + beta[len(rhs):]
            else:
                beta = [X] + beta
            # quitar etiqueta Xj de alpha (última ocurrencia)
            for p in range(len(alpha)-1, -1, -1):
                if alpha[p] == f"{X}{tried_alt}":
                    alpha.pop(p)
                    break
            # quitar acción 'expand' correspondiente
            q = len(actions) - 1
            while q >= 0:
                a_act = actions[q]
                if a_act["kind"] == "expand" and a_act["nonterm"] == X and a_act["alt"] == tried_alt:
                    actions.pop(q)
                    break
                q -= 1
            print_state("r", i, alpha, beta, f"(6c) deshacer producción {X}{tried_alt} (volver a {X})")

            # Regla 6a: ¿hay siguiente alternativa?
            next_alt = tried_alt + 1
            if next_alt <= len(rhss):
                new_rhs = rhss[next_alt-1]
                beta = new_rhs + beta[1:]     # sustituir X por la nueva RHS
                new_label = f"{X}{next_alt}"
                alpha.append(new_label)
                actions.append({"kind":"expand","detail":new_label,"nonterm":X,"alt":next_alt,"rhs":new_rhs})
                decisions[-1] = {"X":X,"alt":next_alt,"i0":dp["i0"],"alpha_len":len(alpha),"rhs":new_rhs}
                print_state("n", i, alpha, beta, f"(6a) siguiente alternativa de {X}: aplica {new_label}")
                mode = "n"
                continue
            else:
                # No hay más alternativas para X → subir un nivel
                decisions.pop()
                continue

def main():
    grammar, start, labels = parse_grammar()
    input_syms = read_input_syms()
    analyze(grammar, start, labels, input_syms)

if __name__ == "__main__":
    main()
