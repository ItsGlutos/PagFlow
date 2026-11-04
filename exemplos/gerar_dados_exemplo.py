"""
Gera arquivos .xls de exemplo (dados 100% fictícios) para parametrizar o PagFlow.

Os .xls do SAP que o PagFlow lê NÃO são planilhas binárias: são texto separado
por TAB, codificado em UTF-16 (com BOM) e extensão .xls. Este script reproduz
exatamente esse formato para os dois layouts aceitos:

  • FBL1N  (Tipo A) — extrato de fornecedor, cabeçalho em 8 linhas  → skiprows=8
  • REL_LOG (Tipo B) — log de pagamentos, cabeçalho em 3 linhas      → skiprows=3

A ordem posicional das colunas segue o que funcoes.py espera:

  FBL1N: remove colunas [0, 12, 14, 15] e renomeia as 12 restantes.
  REL_LOG: remove colunas [15, 14, 13, 8] e renomeia as 12 restantes
           por posição (0..11).

Uso:
    python exemplos/gerar_dados_exemplo.py
"""

from pathlib import Path

AQUI = Path(__file__).resolve().parent
TRANSPORTADORA = "GutoLog Express Ltda."
CNPJ = "12.345.678/0001-90"

# ──────────────────────────────────────────────────────────────────────────────
# FBL1N — 16 colunas no arquivo; o código descarta 0, 12, 14 e 15.
# Depois do descarte sobram 12 colunas, nesta ordem:
#   1 Empresa | 2 Fornecedor | 3 LNeg | 4 Referência | 5 Nº documento
#   6 Data doc. | 7 Doc. Compensação | 8 Valor | 9 Vencimento | 10 Texto
#   11 Tipo | 13 Compensaç.
# ──────────────────────────────────────────────────────────────────────────────
CABECALHO_FBL1N = [
    "Seq",                # 0  → descartada
    "Empresa",            # 1
    "Fornecedor",         # 2
    "LNeg",               # 3
    "Referência",         # 4
    "Nº documento",       # 5
    "Data doc.",          # 6
    "Doc. Compensação",   # 7
    "Valor",              # 8
    "Vencimento",         # 9
    "Texto",              # 10
    "Tipo",               # 11
    "Nome",               # 12 → descartada (mas é o que identifica o Tipo A)
    "Compensaç.",         # 13
    "Moeda",              # 14 → descartada
    "Centro",             # 15 → descartada
]

# (Empresa, Fornecedor, LNeg, Referência, Nº doc, Data doc,
#  Doc. Compensação, Valor, Vencimento, Texto, Tipo, Compensaç.)
#
# Valor no FBL1N: o código faz parse_sap_valor(...) * -1.
# Logo, "1.500,00-" (crédito SAP) vira +1500,00 no relatório final.
LINHAS_FBL1N = [
    ("Santa Cruz", 101234, 1000, "CTE-2025-1042", 1900012341, "02.10.2025", 5100000101, "1.500,00-", "10.10.2025", "FRETE CTE 1042 - GUTO EXPRESS", "RE", "09.10.2025"),
    ("Santa Cruz", 101234, 1000, "CTE-2025-1043", 1900012342, "02.10.2025", 5100000101, "2.380,50-", "10.10.2025", "FRETE CTE 1043 - GUTO EXPRESS", "RE", "09.10.2025"),
    ("Santa Cruz", 101234, 1000, "CTE-2025-1044", 1900012343, "05.10.2025", "", "980,00-", "20.10.2025", "FRETE CTE 1044 - GUTO EXPRESS", "RE", ""),
    ("Santa Cruz", 101987, 2000, "CTE-2025-2011", 1900012351, "07.10.2025", 5100000118, "4.120,00-", "15.10.2025", "FRETE CTE 2011 - GUTO LOG FILIAL", "RE", "14.10.2025"),
    ("Santa Cruz", 101987, 2000, "CTE-2025-2012", 1900012352, "07.10.2025", 5100000118, "1.205,75-", "15.10.2025", "FRETE CTE 2012 - GUTO LOG FILIAL", "RE", "14.10.2025"),
    # Confissão de dívida (KT) — débito/estorno, aparece em vermelho no Excel
    ("Santa Cruz", 101234, 1000, "KT-2025-0007", 1900012360, "08.10.2025", "", "350,00", "31.10.2025", "CONFISSAO DIVIDA - AVARIA CTE 1042", "KT", ""),
    # Nota fiscal da seguradora (RF) — reembolso
    ("Santa Cruz", 102450, 3001, "RF-2025-0301", 1900012370, "09.10.2025", 5100000125, "620,00-", "25.10.2025", "REEMBOLSO SEGURO - SINISTRO 0301", "RF", "24.10.2025"),
    # Fatura (KL) — deve ser DESCARTADA pelo filtro de tipos
    ("Santa Cruz", 101234, 1000, "KL-2025-9001", 1900012399, "10.10.2025", "", "7.890,00-", "30.10.2025", "FATURA KL - NAO ENTRA NO RELATORIO", "KL", ""),

    ("Panpharma", 101234, 2000, "CTE-2025-1055", 1900012380, "03.10.2025", 5100000130, "2.750,00-", "13.10.2025", "FRETE CTE 1055 - GUTO EXPRESS", "RE", "12.10.2025"),
    ("Panpharma", 101234, 2000, "CTE-2025-1056", 1900012381, "03.10.2025", 5100000130, "1.840,30-", "13.10.2025", "FRETE CTE 1056 - GUTO EXPRESS", "RE", "12.10.2025"),
    ("Panpharma", 101987, 3001, "CTE-2025-2020", 1900012385, "11.10.2025", "", "5.300,00-", "27.10.2025", "FRETE CTE 2020 - LOTE PANPHARMA", "RE", ""),
    ("Panpharma", 101987, 3001, "KT-2025-0009", 1900012390, "12.10.2025", "", "1.100,00", "31.10.2025", "CONFISSAO DIVIDA - ESTORNO CTE 2020", "KT", ""),
    ("Panpharma", 102450, 1000, "RF-2025-0305", 1900012392, "13.10.2025", 5100000140, "410,90-", "28.10.2025", "REEMBOLSO SEGURO - SINISTRO 0305", "RF", "27.10.2025"),

    ("Custos SC", 101234, 3001, "CTE-2025-1070", 1900012400, "14.10.2025", 5100000150, "3.215,60-", "24.10.2025", "FRETE CTE 1070 - GUTO EXPRESS", "RE", "23.10.2025"),
    ("Custos SC", 101234, 3001, "CTE-2025-1071", 1900012401, "14.10.2025", 5100000150, "760,00-", "24.10.2025", "FRETE CTE 1071 - GUTO EXPRESS", "RE", "23.10.2025"),
    ("Custos SC", 101987, 4000, "CTE-2025-2030", 1900012410, "16.10.2025", "", "1.980,45-", "30.10.2025", "FRETE CTE 2030 - GUTO LOG FILIAL", "RE", ""),
    ("Custos SC", 101987, 4000, "CTE-2025-2031", 1900012411, "16.10.2025", "", "2.410,00-", "30.10.2025", "FRETE CTE 2031 - GUTO LOG FILIAL", "RE", ""),
    ("Custos SC", 102450, 2000, "RF-2025-0310", 1900012415, "17.10.2025", 5100000160, "890,25-", "31.10.2025", "REEMBOLSO SEGURO - SINISTRO 0310", "RF", "30.10.2025"),
]

# ──────────────────────────────────────────────────────────────────────────────
# REL_LOG — 16 colunas no arquivo; o código descarta 15, 14, 13 e 8.
# Depois do descarte, as 12 restantes são renomeadas POR POSIÇÃO:
#   0 Empresa | 1 LNeg | 2 Fornecedor | 3 Nº documento | 4 Data doc.
#   5 Referência | 6 Vencimento | 7 Tipo | 9 Valor | 10 Texto
#   11 Doc. Compensação | 12 Compensaç.
# ──────────────────────────────────────────────────────────────────────────────
CABECALHO_REL_LOG = [
    "Empresa",            # 0
    "LNeg",               # 1
    "Fornecedor",         # 2
    "Nº documento",       # 3
    "Data doc.",          # 4
    "Referência",         # 5
    "Vencimento",         # 6
    "Tipo",               # 7
    "Moeda",              # 8  → descartada
    "Valor",              # 9
    "Texto",              # 10
    "Doc. Compensação",   # 11
    "Compensaç.",         # 12
    "Banco",              # 13 → descartada
    "Data baixa",         # 14 → descartada
    "Forma pgto",         # 15 → descartada
]

# Valor no REL_LOG: parse_sap_valor() é aplicado SEM inversão de sinal.
# (Empresa, LNeg, Fornecedor, Nº doc, Data doc, Referência, Vencimento,
#  Tipo, Valor, Texto, Doc. Compensação, Compensaç.)
LINHAS_REL_LOG = [
    # Documento que TAMBÉM existe no FBL1N (mesma empresa + LNeg): serve para
    # exercitar o drop_duplicates de ope.py — a linha do log é descartada.
    ("Santa Cruz", 1000, 101234, 1900012341, "02.10.2025", "CTE-2025-1042", "10.10.2025", "RE", "1.500,00", "PGTO FRETE CTE 1042", 5100000101, "09.10.2025"),

    # Documentos exclusivos do log de pagamentos
    ("Santa Cruz", 1000, 101234, 1900012450, "18.10.2025", "CTE-2025-1045", "28.10.2025", "RE", "1.240,00", "PGTO FRETE CTE 1045", 5100000170, "27.10.2025"),
    ("Santa Cruz", 1000, 101234, 1900012451, "18.10.2025", "CTE-2025-1046", "28.10.2025", "RE", "3.050,00", "PGTO FRETE CTE 1046", 5100000170, "27.10.2025"),
    ("Santa Cruz", 2000, 101987, 1900012455, "19.10.2025", "CTE-2025-2013", "29.10.2025", "RE", "2.115,40", "PGTO FRETE CTE 2013", 5100000175, "28.10.2025"),
    ("Panpharma", 2000, 101234, 1900012460, "20.10.2025", "CTE-2025-1060", "30.10.2025", "RE", "1.600,00", "PGTO FRETE CTE 1060", "", ""),
    ("Panpharma", 3001, 101987, 1900012465, "21.10.2025", "CTE-2025-2021", "31.10.2025", "RE", "4.480,00", "PGTO FRETE CTE 2021", "", ""),
    ("Custos SC", 3001, 101234, 1900012470, "22.10.2025", "CTE-2025-1073", "31.10.2025", "RE", "1.120,00", "PGTO FRETE CTE 1073", 5100000180, "30.10.2025"),
    ("Custos SC", 4000, 101987, 1900012475, "23.10.2025", "CTE-2025-2032", "31.10.2025", "RE", "2.890,75", "PGTO FRETE CTE 2032", "", ""),
    # Desconto/abatimento registrado no log → valor negativo (sinal no fim)
    ("Custos SC", 3001, 101234, 1900012478, "24.10.2025", "CTE-2025-1074", "31.10.2025", "RE", "135,00-", "DESCONTO AVARIA CTE 1074", "", ""),
]


def escrever_xls(caminho: Path, preambulo: list[str], cabecalho: list[str], linhas: list[list]) -> None:
    """Grava texto TAB + UTF-16 (BOM), exatamente como a exportação do SAP."""
    conteudo = [*preambulo, "\t".join(cabecalho)]
    conteudo += ["\t".join("" if c is None else str(c) for c in linha) for linha in linhas]

    # newline='' evita a tradução automática de \n, mantendo CRLF puro do SAP
    with open(caminho, "w", encoding="utf-16", newline="") as arquivo:
        arquivo.write("\r\n".join(conteudo) + "\r\n")


def gerar() -> list[Path]:
    AQUI.mkdir(parents=True, exist_ok=True)

    # 8 linhas de preâmbulo → cabeçalho na linha 9. A palavra "Nome" na linha 3
    # é o que faz detectar_relat() classificar o arquivo como Tipo A (FBL1N).
    preambulo_fbl1n = [
        "Extrato de Fornecedor - FBL1N",
        "Empresa: Todas as empresas",
        f"Nome: {TRANSPORTADORA}",
        f"CNPJ: {CNPJ}",
        "Período: 01.10.2025 até 31.10.2025",
        "Moeda: BRL",
        "Usuário: PAGFLOW",
        "",
    ]

    # 3 linhas de preâmbulo → cabeçalho na linha 4. Nenhuma pode conter "Nome",
    # senão o arquivo seria lido como FBL1N.
    preambulo_rel_log = [
        "Log de Pagamentos - REL_LOG",
        "Empresa: Todas as empresas | Período: 01.10.2025 a 31.10.2025",
        f"Fornecedor: 101234 / 101987 / 102450 - {TRANSPORTADORA}",
    ]

    # FBL1N: insere o sequencial (0), 'Nome' (12) e as colunas 14/15 no fim
    linhas_fbl1n = [
        [seq, empresa, fornecedor, lneg, referencia, documento, data_doc,
         doc_comp, valor, vencimento, texto, tipo, TRANSPORTADORA, compensacao,
         "BRL", "SC01"]
        for seq, (empresa, fornecedor, lneg, referencia, documento, data_doc,
                  doc_comp, valor, vencimento, texto, tipo, compensacao)
        in enumerate(LINHAS_FBL1N, start=1)
    ]

    linhas_rel_log = [
        [empresa, lneg, fornecedor, documento, data_doc, referencia, vencimento,
         tipo, "BRL", valor, texto, doc_comp, compensacao, "341", data_doc, "TED"]
        for (empresa, lneg, fornecedor, documento, data_doc, referencia, vencimento,
             tipo, valor, texto, doc_comp, compensacao) in LINHAS_REL_LOG
    ]

    p_fbl1n = AQUI / "GutoLog_FBL1N_2025-10.xls"
    p_rel_log = AQUI / "GutoLog_REL_LOG_2025-10.xls"

    escrever_xls(p_fbl1n, preambulo_fbl1n, CABECALHO_FBL1N, linhas_fbl1n)
    escrever_xls(p_rel_log, preambulo_rel_log, CABECALHO_REL_LOG, linhas_rel_log)

    return [p_fbl1n, p_rel_log]


if __name__ == "__main__":
    for caminho in gerar():
        print(f"gerado: {caminho} ({caminho.stat().st_size} bytes)")
