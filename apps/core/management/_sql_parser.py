"""
Parser minimalista de INSERT statements de mysqldump.

Soporta strings escapados (\\', \\\\, \\n, etc.), NULL, enteros y floats.
Pensado para extraer tuplas de tablas concretas del dump legacy de DINAPI,
no es un parser SQL general.
"""


def _parse_sql_string(s, pos):
    """Parsea un string entre comillas simples con escapes. Devuelve (texto, nueva_pos)."""
    assert s[pos] == "'", f'esperaba comilla en pos {pos}, vi {s[pos]!r}'
    pos += 1
    out = []
    while pos < len(s):
        c = s[pos]
        if c == '\\' and pos + 1 < len(s):
            nxt = s[pos + 1]
            out.append({
                'n': '\n', 'r': '\r', 't': '\t',
                '\\': '\\', "'": "'", '"': '"', '0': '\0',
            }.get(nxt, nxt))
            pos += 2
        elif c == "'":
            return ''.join(out), pos + 1
        else:
            out.append(c)
            pos += 1
    raise ValueError('string SQL sin cerrar')


def _parse_sql_atom(s, pos):
    """Parsea un valor SQL (string, NULL o numero). Devuelve (valor, nueva_pos)."""
    while pos < len(s) and s[pos] in ' \t\n\r':
        pos += 1
    if s[pos] == "'":
        return _parse_sql_string(s, pos)
    if s[pos:pos + 4].upper() == 'NULL':
        return None, pos + 4
    start = pos
    if s[pos] in '+-':
        pos += 1
    while pos < len(s) and s[pos] not in ',)':
        pos += 1
    raw = s[start:pos].strip()
    try:
        return int(raw), pos
    except ValueError:
        try:
            return float(raw), pos
        except ValueError:
            return raw, pos


def _parse_sql_tuple(s, pos):
    """Parsea una tupla (v1, v2, ...) desde '('. Devuelve (lista, pos_despues_de_)."""
    assert s[pos] == '(', f'esperaba ( en pos {pos}, vi {s[pos]!r}'
    pos += 1
    values = []
    while True:
        while pos < len(s) and s[pos] in ' \t\n\r':
            pos += 1
        if s[pos] == ')':
            return values, pos + 1
        value, pos = _parse_sql_atom(s, pos)
        values.append(value)
        while pos < len(s) and s[pos] in ' \t\n\r':
            pos += 1
        if s[pos] == ',':
            pos += 1
        elif s[pos] == ')':
            return values, pos + 1


def iter_insert_tuples(sql_text, table_name):
    """
    Itera las tuplas de los INSERT INTO de la tabla dada. Yields list[valor].

    Skips otras tablas con nombre que comience igual (ej. AcordeonPage_Live)
    porque el match es exacto sobre `<table_name>`.
    """
    needle = f'INSERT INTO `{table_name}` '
    pos = 0
    while True:
        idx = sql_text.find(needle, pos)
        if idx < 0:
            return
        values_idx = sql_text.find(' VALUES', idx)
        if values_idx < 0:
            return
        cursor = values_idx + len(' VALUES')
        while True:
            while cursor < len(sql_text) and sql_text[cursor] in ' \t\n\r':
                cursor += 1
            if cursor >= len(sql_text) or sql_text[cursor] != '(':
                break
            tup, cursor = _parse_sql_tuple(sql_text, cursor)
            yield tup
            while cursor < len(sql_text) and sql_text[cursor] in ' \t\n\r':
                cursor += 1
            if cursor < len(sql_text) and sql_text[cursor] == ',':
                cursor += 1
                continue
            if cursor < len(sql_text) and sql_text[cursor] == ';':
                cursor += 1
                break
        pos = cursor
