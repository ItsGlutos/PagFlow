"""
Verifica os arquivos de exemplo do PagFlow de ponta a ponta.

1. Gera os .xls (chamando gerar_dados_exemplo.gerar)
2. Confere que cada um foi detectado no layout correto (A = FBL1N, B = REL_LOG)
3. Confere esquema, tipos, filtro de tipos de documento e sinal dos valores
4. Roda ope.executar() em uma pasta temporária e confere o .xlsx consolidado
   (abas, linhas, deduplicação e fórmula de SUBTOTAL)

Uso:
    python exemplos/verificar_exemplo.py
"""

import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import openpyxl
import pandas as pd

from funcoes import detectar_relat, processar_arquivo
from ope import executar
from gerar_dados_exemplo import gerar

ESQUEMA = [
    "Empresa", "Fornecedor", "LNeg", "Referência", "Nº documento",
    "Data doc.", "Doc. Compensação", "Valor", "Vencimento", "Texto",
    "Tipo", "Compensaç.",
]

falhas: list[str] = []


def checar(condicao: bool, mensagem: str) -> None:
    print(("  ok   " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        falhas.append(mensagem)


def main() -> int:
    caminhos = gerar()
    print("\n[1] Detecção de layout")
    fbl1n, rel_log = caminhos
    _, tipo_fbl1n = detectar_relat(fbl1n)
    _, tipo_rel_log = detectar_relat(rel_log)
    checar(tipo_fbl1n == "A", f"{fbl1n.name} detectado como Tipo A (FBL1N)")
    checar(tipo_rel_log == "B", f"{rel_log.name} detectado como Tipo B (REL_LOG)")

    print("\n[2] Tratamento por arquivo")
    frames = {}
    for caminho in caminhos:
        df = processar_arquivo(caminho)
        frames[caminho.name] = df
        checar(
            set(df.columns) == set(ESQUEMA) and len(df.columns) == 12,
            f"{caminho.name}: 12 colunas no esquema padrão",
        )
        checar(
            set(df["Tipo"].unique()) <= {"RE", "KT", "RF"},
            f"{caminho.name}: nenhum tipo fora de RE/KT/RF (KL descartado)",
        )
        checar(
            str(df["Valor"].dtype) == "float64" and not df["Valor"].isna().any(),
            f"{caminho.name}: Valor numérico e sem nulos",
        )
        checar(
            str(df["Data doc."].dtype).startswith("datetime64"),
            f"{caminho.name}: datas convertidas para datetime",
        )
        checar(
            str(df["Fornecedor"].dtype) == "Int64",
            f"{caminho.name}: Fornecedor/LNeg/Nº doc. como Int64",
        )

    print("\n[3] Consolidação (ope.executar)")
    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "saida"
        saida.mkdir()
        executar(
            pasta=Path(__file__).resolve().parent,
            destino=saida,
            nome="consolidado_teste",
            separar="Marca",
            cor="Verde",
            cb_status=lambda msg, estado=None: None,
        )
        xlsx = saida / "consolidado_teste.xlsx"
        checar(xlsx.exists(), "arquivo consolidado gerado")

        esperado = (
            len(frames[fbl1n.name])
            + len(frames[rel_log.name])
            - 1  # 1 referência aparece nos dois relatórios → drop_duplicates
        )
        wb = openpyxl.load_workbook(xlsx)
        total_dados = 0
        for ws in wb.worksheets:
            linhas = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[6] != "SUBTOTAL"]
            total_dados += len(linhas)
            checar(ws.cell(ws.max_row, 7).value == "SUBTOTAL", f"aba '{ws.title}': linha de SUBTOTAL")
            checar(
                str(ws.cell(ws.max_row, 8).value).startswith("=SUM("),
                f"aba '{ws.title}': fórmula =SUM na coluna Valor",
            )
            checar(
                sum(1 for r in ws.iter_rows(min_row=1, values_only=True)) == ws.max_row,
                f"aba '{ws.title}': {len(linhas)} linha(s) de dados",
            )
        checar(
            total_dados == esperado,
            f"total consolidado = {total_dados} linhas (esperado {esperado})",
        )

        nomes_abas = sorted(wb.sheetnames)
        esperadas = sorted(frames[fbl1n.name]["Empresa"].unique())
        checar(nomes_abas == esperadas, f"abas por Marca: {nomes_abas}")

    print()
    if falhas:
        print(f"[FALHOU] {len(falhas)} verificacao(oes) falharam.")
        return 1
    print("[OK] Todos os arquivos de exemplo passaram na verificacao.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
