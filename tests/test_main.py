"""Smoke: main.py não referencia nomes indefinidos (pega get_url faltante).

O CI roda `ruff check src/ --select F821`. Este teste usa AST para uma checagem
equivalente e leve: qualquer chamada `name(...)` cujo `name` não esteja
definido no módulo (imports, defs, atribuições) nem em builtins → falha.
"""

import ast
import builtins
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _defined_names(tree):
    """Nomes definidos no escopo do módulo (imports, defs, classes, assigns, args)."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    # nomes de argumentos de funções contam como definidos dentro delas
    return names


def _called_names(tree):
    """Nomes chamados como função no nível do módulo e dentro de defs."""
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.add(node.func.id)
    return called


def _params_by_func(tree):
    """Mapa func_name -> set(param names + locals assigned) para ignorar."""
    info = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = {a.arg for a in node.args.args + node.args.kwonlyargs}
            local_names = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            local_names.add(t.id)
                elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for a in sub.names:
                        local_names.add((a.asname or a.name).split(".")[0])
            info[node.name] = params | local_names
    return info


def test_main_has_no_undefined_calls():
    path = ROOT / "src" / "main.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defined = _defined_names(tree)
    params_by_func = _params_by_func(tree)
    builtin_names = set(dir(builtins)) | {"__file__", "__name__"}

    undefined = set()
    for name in _called_names(tree):
        if name in defined or name in builtin_names:
            continue
        undefined.add(name)

    assert not undefined, f"main.py chama nomes não definidos: {sorted(undefined)}"