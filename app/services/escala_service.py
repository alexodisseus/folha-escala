ESCALAS = {
    "SEG_SEX": [0, 1, 2, 3, 4],
    "TER_SAB": [1, 2, 3, 4, 5],
    "DOM_QUI": [6, 0, 1, 2, 3],
    "QUA_DOM": [2, 3, 4, 5, 6],
}

CARGA_DIARIA = 8


def dia_eh_folga(funcionario, data):
    return data.weekday() not in ESCALAS[funcionario.tipo_escala]


def calcular_he(funcionario, data, trabalhou):
    if not trabalhou:
        return 0

    if dia_eh_folga(funcionario, data):
        return CARGA_DIARIA

    return 0