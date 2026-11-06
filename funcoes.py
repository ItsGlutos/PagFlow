from pathlib import Path


# Paletas baseadas nos estilos nativos do Excel "Formatar como Tabela"
# (TableStyleMedium) com conformidade WCAG AA (contraste ≥ 4.5:1).
# Estrutura: (cabeçalho, linha ímpar, linha par)
#   • Cabeçalho: cor sólida escura + texto branco (#FFFFFF) → contraste alto
#   • Linhas: alternância clara/branca + texto preto (#000000) → máximo legível
#
#  Referência Excel:
#   Azul    → TableStyleMedium2  (#4472C4 / #D9E1F2 / #FFFFFF)
#   Verde   → TableStyleMedium7  (#70AD47 / #E2EFDA / #FFFFFF)
#   Roxo    → TableStyleMedium13 (#7030A0 / #E4DFEC / #FFFFFF)
#   Vermelho→ TableStyleMedium10 (#C00000 / #FFC7CE / #FFFFFF)
PALETAS_RELATORIO = {
    'Azul':     ('4472C4', 'D9E1F2', 'FFFFFF'),
    'Verde':    ('375623', 'E2EFDA', 'FFFFFF'),
    'Roxo':     ('7030A0', 'E4DFEC', 'FFFFFF'),
    'Vermelho': ('C00000', 'FFC7CE', 'FFFFFF'),
}

# Mapeia o label da UI para o nome real da coluna no DataFrame
MAPA_COLUNAS_RELATORIO = {
    'Marca':      'Empresa',
    'LNeg':       'LNeg',
    'Fornecedor': 'Fornecedor',
}


def _montar_abas(df_final, separar):
    """Monta a lista de (nome_aba, DataFrame) conforme a separação escolhida."""
    if separar == 'Não Separar':
        return [('Dados', df_final)]
    coluna = MAPA_COLUNAS_RELATORIO[separar]
    return [
        (str(valor)[:31], df_final[df_final[coluna] == valor])
        for valor in sorted(df_final[coluna].dropna().unique())
    ]


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: detectar_relat
# Objetivo: Abrir o arquivo .xls (salvo como texto separado por tab, UTF-16)
#           e identificar de qual relatório SAP se trata lendo as primeiras
#           linhas do cabeçalho.
#
#   • Relatório A (FBL1N)  → contém a palavra 'Nome' nas 7 primeiras linhas
#                            → cabeçalho real começa na linha 9 (skiprows=8)
#   • Relatório B (REL_LOG) → não contém 'Nome'
#                            → cabeçalho real começa na linha 4 (skiprows=3)
#
# Retorna:
#   df         – DataFrame bruto já lido do arquivo
#   tipo_relat – 'A' para FBL1N  |  'B' para REL_LOG
# ──────────────────────────────────────────────────────────────────────────────
def detectar_relat(caminho_arquivo):

    # Lê apenas as 7 primeiras linhas para inspecionar o cabeçalho SAP
    with open(caminho_arquivo, 'r', encoding='utf-16') as arquivo:
        linhas_iniciais = [arquivo.readline() for _ in range(7)]
        amostra_texto = ''.join(linhas_iniciais)

    # A presença de 'Nome' no cabeçalho indica o layout do FBL1N
    if 'Nome' in amostra_texto:
        pular_linhas = 8       # FBL1N tem 8 linhas de cabeçalho antes dos dados
        tipo_relat = 'A'
    else:
        pular_linhas = 3       # REL_LOG tem 3 linhas de cabeçalho
        tipo_relat = 'B'

    import pandas as pd
    
    # Lê o arquivo completo já pulando as linhas de cabeçalho SAP
    # index_col=False evita que a primeira coluna vire índice (importante no REL_LOG)
    df = pd.read_csv(
        caminho_arquivo,
        encoding='utf-16',
        skiprows=pular_linhas,
        sep='\t',
        index_col=False
    )

    return df, tipo_relat


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: parse_sap_valor
# Objetivo: Tratar de forma robusta os valores monetários do SAP.
# O SAP costuma exportar créditos com o sinal de menos no final (ex: "1.500,00-")
# o que quebra o conversor nativo do Pandas.
# ──────────────────────────────────────────────────────────────────────────────
def parse_sap_valor(val):
    import pandas as pd
    
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip()
    if not val_str:
        return 0.0
        
    is_negative = False
    if val_str.endswith('-'):
        is_negative = True
        val_str = val_str[:-1]
    elif val_str.startswith('-'):
        is_negative = True
        val_str = val_str[1:]
        
    val_str = val_str.replace('.', '').replace(',', '.')
    
    try:
        num = float(val_str)
        if is_negative:
            num = num * -1
        
        return num
    except ValueError:
        return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: localizar_coluna_bloqueio
# Objetivo: Encontrar a coluna de bloqueio no extrato bruto, sem depender da
#           posição em que ela aparece em cada layout.
#
#   • FBL1N  → cabeçalho "BlP"
#   • REL_LOG → cabeçalho "BIP"
#
# Também aceita "Bloqueio", "Bloq." e variações, para não quebrar se o SAP
# mudar o rótulo. Retorna None quando o relatório não traz essa informação.
# ──────────────────────────────────────────────────────────────────────────────
def localizar_coluna_bloqueio(df):
    import re
    import unicodedata

    def chave(nome):
        decomposto = unicodedata.normalize('NFKD', str(nome))
        sem_acento = ''.join(
            caractere for caractere in decomposto
            if not unicodedata.combining(caractere)
        )
        return re.sub(r'[^a-z0-9]+', ' ', sem_acento.lower()).strip()

    aliases = {
        'blp', 'bip', 'bloq', 'bloqueio',
        'bloqueio de pagamento', 'bloqueio pagamento',
        'bloqueio de pgto', 'bloqueio pgto',
        'bloqueio do pagamento',
    }

    # Primeiro tenta o nome exato (evita falsos positivos)
    for coluna in df.columns:
        if chave(coluna) in aliases:
            return coluna

    # Depois aceita variações que comecem/containham o termo
    for coluna in df.columns:
        nome = chave(coluna)
        if nome.startswith(('blp', 'bip')) or 'bloqueio' in nome:
            return coluna

    return None


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: _inserir_bloqueio
# Objetivo: Acrescentar a coluna "Bloqueio" ao DataFrame tratado, preservando
#           o valor original do SAP (ex.: "B" para bloqueado, "S" para livre).
#           Ela entra ao final para não deslocar as colunas já existentes.
#           Quando o relatório não possui a coluna, ela entra vazia para que
#           todos os arquivos tenham o mesmo esquema na consolidação.
# ──────────────────────────────────────────────────────────────────────────────
def _inserir_bloqueio(df, serie_bloqueio):
    import pandas as pd

    df = df.copy()

    if serie_bloqueio is None:
        valores = pd.Series('', index=df.index, dtype=object)
    else:
        valores = serie_bloqueio.reindex(df.index)
        valores = valores.map(
            lambda valor: '' if pd.isna(valor) else str(valor).strip()
        )

    # [gerado] Anexa ao final para não deslocar as colunas já existentes —
    # a exportação e os totais continuam usando as mesmas posições de antes.
    df['Bloqueio'] = valores
    return df


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: tratamento_fbl1n
# Objetivo: Limpar e padronizar o DataFrame do relatório FBL1N (Tipo A).
#
# Passos:
#   1. Remove colunas 'Unnamed' (geradas pelo Excel/SAP que exporta colunas vazias)
#   2. Remove colunas desnecessárias pelos índices posicionais [0, 12, 14, 15]
#   3. Renomeia as colunas restantes para nomes amigáveis
#   4. Converte 'Valor' de forma robusta lidando com sinal negativo e multiplicando por -1
#   5. Converte colunas de texto, inteiro e data para os tipos corretos
#   6. Filtra apenas os tipos de documento relevantes: RE, KT, RF
#
# Recebe: df – DataFrame bruto retornado por detectar_relat()
# Retorna: df_filtrado – DataFrame limpo e filtrado
# ──────────────────────────────────────────────────────────────────────────────
def tratamento_fbl1n(df):
    import pandas as pd

    # Tipos de documento que interessam para a conciliação de pagamentos
    puxar_apenas = ['RE', 'KT', 'RF']

    colunas_texto = ['Empresa', 'Referência', 'Texto', 'Tipo']
    colunas_int   = ['LNeg', 'Fornecedor', 'Nº documento', 'Doc. Compensação']
    colunas_data  = ['Data doc.', 'Vencimento', 'Compensaç.']

    # Passo 1 – Remove qualquer coluna cujo nome comece com 'Unnamed'
    df_limpo = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # [gerado] Guarda a coluna de bloqueio (BlP/BIP) antes dos descartes
    # posicionais — no FBL1N ela costuma cair justamente entre as descartadas.
    coluna_bloqueio = localizar_coluna_bloqueio(df)
    serie_bloqueio = df[coluna_bloqueio] if coluna_bloqueio is not None else None

    # Passo 2 – Remove colunas posicionais que não são usadas neste relatório
    df_limpo = df_limpo.drop(df_limpo.columns[[0, 12, 14, 15]], axis=1)

    # Passo 3 – Renomeia as colunas restantes para um padrão único entre relatórios
    colunas_desejadas = [
        'Empresa', 'Fornecedor', 'LNeg', 'Referência', 'Nº documento',
        'Data doc.', 'Doc. Compensação', 'Valor', 'Vencimento', 'Texto',
        'Tipo', 'Compensaç.'
    ]
    df_limpo.columns = colunas_desejadas

    # Passo 4 – Trata o campo 'Valor' com a função robusta
    df_limpo['Valor'] = df_limpo['Valor'].apply(parse_sap_valor) * -1

    # Passo 5 – Converte tipos de cada grupo de colunas
    df_limpo[colunas_texto] = df_limpo[colunas_texto].astype(str)
    df_limpo[colunas_int]   = df_limpo[colunas_int].astype('Int64')

    for coluna in colunas_data:
        df_limpo[coluna] = df_limpo[coluna].astype(str).str.replace('.', '/', regex=False)
        df_limpo[coluna] = pd.to_datetime(df_limpo[coluna], format='%d/%m/%Y', errors='coerce')

    # Passo 6 – Filtra apenas os tipos de documento relevantes
    df_filtrado = df_limpo[df_limpo['Tipo'].isin(puxar_apenas)].copy()

    # [gerado] Recoloca o bloqueio no esquema final do relatório
    df_filtrado = _inserir_bloqueio(df_filtrado, serie_bloqueio)

    return df_filtrado


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: tratamento_log
# Objetivo: Limpar e padronizar o DataFrame do relatório REL_LOG (Tipo B).
#
# A lógica é análoga ao tratamento_fbl1n, mas o layout do REL_LOG é diferente:
#   • Colunas a remover: índices [15, 14, 13, 8] (remoção de trás para frente
#     evita que o shift de índices afete as posições seguintes)
#   • O mapa de renomeação é feito por posição (dicionário índice → nome)
#     pois as colunas do REL_LOG não têm nomes limpos como o FBL1N
#
# Recebe: df – DataFrame bruto retornado por detectar_relat()
# Retorna: df_filtrado – DataFrame limpo e filtrado
# ──────────────────────────────────────────────────────────────────────────────
def tratamento_log(df):
    import pandas as pd

    puxar_apenas = ['RE', 'KT', 'RF']

    colunas_texto = ['Empresa', 'Referência', 'Texto', 'Tipo']
    colunas_int   = ['LNeg', 'Fornecedor', 'Nº documento', 'Doc. Compensação']
    colunas_data  = ['Data doc.', 'Vencimento', 'Compensaç.']

    # Passo 1 – Remove colunas 'Unnamed'
    df_limpo = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # [gerado] Guarda a coluna de bloqueio (BlP/BIP) antes dos descartes
    # posicionais — no REL_LOG o "BIP" é o índice 8, que atualmente é removido.
    coluna_bloqueio = localizar_coluna_bloqueio(df)
    serie_bloqueio = df[coluna_bloqueio] if coluna_bloqueio is not None else None

    # Passo 2 – Remove colunas desnecessárias do layout REL_LOG
    # Os índices são removidos do maior para o menor para não deslocar as posições
    df_limpo = df_limpo.drop(df_limpo.columns[[15, 14, 13, 8]], axis=1)

    # Passo 3 – Renomeia por posição (REL_LOG exporta nomes de coluna diferentes)
    colunas_desejadas = {
        0:  'Empresa',
        1:  'LNeg',
        2:  'Fornecedor',
        3:  'Nº documento',
        4:  'Data doc.',
        5:  'Referência',
        6:  'Vencimento',
        7:  'Tipo',
        8:  'Valor',
        9:  'Texto',
        10: 'Doc. Compensação',
        11: 'Compensaç.'
    }
    dicionario_traduzido = {
        df_limpo.columns[pos]: novo_nome
        for pos, novo_nome in colunas_desejadas.items()
    }
    df_limpo = df_limpo.rename(columns=dicionario_traduzido)

    # Passo 4 – Trata o campo 'Valor' com a função robusta
    df_limpo['Valor'] = df_limpo['Valor'].apply(parse_sap_valor)

    # Passo 5 – Converte tipos
    df_limpo[colunas_texto] = df_limpo[colunas_texto].astype(str)
    df_limpo[colunas_int]   = df_limpo[colunas_int].astype('Int64')

    for coluna in colunas_data:
        df_limpo[coluna] = df_limpo[coluna].astype(str).str.replace('.', '/', regex=False)
        df_limpo[coluna] = pd.to_datetime(df_limpo[coluna], format='%d/%m/%Y', errors='coerce')

    # Passo 6 – Filtra tipos de documento relevantes
    df_filtrado = df_limpo[df_limpo['Tipo'].isin(puxar_apenas)].copy()

    # [gerado] Recoloca o bloqueio no esquema final do relatório
    df_filtrado = _inserir_bloqueio(df_filtrado, serie_bloqueio)

    return df_filtrado


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: processar_arquivo  ← ponto de entrada chamado pelo ope.py
# Objetivo: Orquestrar a detecção + tratamento de um único arquivo.
#
#   1. Chama detectar_relat() para identificar o tipo e obter o df bruto
#   2. Direciona para a função de tratamento correta (A → fbl1n | B → log)
#
# Recebe: caminho_arquivo – objeto Path ou str com o caminho do .xls
# Retorna: DataFrame tratado e filtrado
# ──────────────────────────────────────────────────────────────────────────────
def processar_arquivo(caminho_arquivo):

    # Detecta o tipo de relatório e carrega o df bruto em uma única chamada
    df, tipo_relat = detectar_relat(caminho_arquivo)

    if tipo_relat == 'A':
        # Arquivo FBL1N → tratamento específico do layout de extrato de fornecedor
        return tratamento_fbl1n(df)
    else:
        # Arquivo REL_LOG → tratamento do layout de log de pagamentos
        return tratamento_log(df)


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: exportar_excel  [gerado]
# Objetivo: Salvar o df_final em um arquivo .xlsx, criando abas separadas
#           de acordo com a escolha feita pelo usuário na interface, e aplicar
#           formatação visual completa: tabela colorida com zebrado, subtotal
#           de Valor e destaque vermelho para linhas do tipo KT.
#
# Mapeamento de opções da interface → coluna do DataFrame:
#   'Marca'       → coluna 'Empresa'     (nome exibido na UI é diferente do df)
#   'LNeg'        → coluna 'LNeg'
#   'Fornecedor'  → coluna 'Fornecedor'
#   'Não Separar' → sem separação, tudo numa aba 'Dados'
#
# Paletas disponíveis (cor escolhida na interface):
#   Cabeçalho: cor forte  |  Linha ímpar: levemente mais clara  |  Linha par: ainda mais clara
#
# Parâmetros:
#   df_final  – DataFrame consolidado vindo do ope.py
#   separar   – string com a opção escolhida na interface
#   destino   – Path ou str com a pasta de destino
#   nome      – nome base do arquivo (sem extensão)
#   cor       – cor de personalização escolhida na interface: 'Verde' | 'Azul' | 'Roxo' | 'Vermelho'
#
# Retorna: caminho_arquivo (Path) do .xlsx gerado
# ──────────────────────────────────────────────────────────────────────────────
def _exportar_excel_openpyxl(df_final, separar, destino, nome, cor='Azul'):
    import pandas as pd
    from copy import copy
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import datetime
    import tempfile
    import shutil
    import os

    # [gerado] Seleciona a paleta escolhida; cai em Azul se a cor não for reconhecida
    header_hex, row1_hex, row2_hex = PALETAS_RELATORIO.get(
        cor, PALETAS_RELATORIO['Azul']
    )

    fill_header = PatternFill('solid', fgColor=header_hex)
    fill_row1   = PatternFill('solid', fgColor=row1_hex)
    fill_row2   = PatternFill('solid', fgColor=row2_hex)
    fill_kt     = PatternFill('solid', fgColor='FF0000')  # [gerado] KT → vermelho puro

    font_header  = Font(bold=True, color='FFFFFF', size=11)
    font_normal  = Font(color='000000', size=10)
    font_kt      = Font(color='FFFFFF', bold=True, size=10)  # [gerado] texto branco sobre vermelho
    font_subtotal = Font(bold=True, color='FFFFFF', size=10)

    align_center = Alignment(horizontal='center', vertical='center')
    align_left   = Alignment(horizontal='left',   vertical='center')
    align_right  = Alignment(horizontal='right',  vertical='center')

    # [gerado] Bordas brancas para simplicidade visual
    lado_branco = Side(style='thin', color='FFFFFF')
    borda_fina = Border(
        left=lado_branco, right=lado_branco,
        top=lado_branco, bottom=lado_branco,
    )

    # [gerado] Índice posicional da coluna 'Valor' no DataFrame (base 1 para o Excel)
    col_valor_idx = list(df_final.columns).index('Valor') + 1

    # [gerado] Garante que o destino seja um objeto Path
    caminho_arquivo = Path(destino) / f'{nome}.xlsx'

    # [gerado] Cria um arquivo temporário oculto
    fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    # [gerado] Monta a lista de (nome_aba, DataFrame) para iterar de forma uniforme
    # independente de estar separando por coluna ou não
    abas = _montar_abas(df_final, separar)

    # [gerado] Cache de estilos: a primeira célula de cada variante registra o
    # estilo pela API pública do openpyxl; as demais apenas copiam o StyleArray
    # já registrado. O resultado visual é idêntico, mas evita que o openpyxl
    # recalcule hash/índice de fonte, fundo, borda e alinhamento em cada célula.
    estilos = {}

    def aplicar_estilo(celula, chave, preencher, fonte, alinhamento, numero=None):
        estilo = estilos.get(chave)
        if estilo is None:
            celula.fill = preencher
            celula.font = fonte
            celula.border = borda_fina
            if alinhamento is not None:
                celula.alignment = alinhamento
            if numero is not None:
                celula.number_format = numero
            # Se uma versão futura do openpyxl não expuser o StyleArray,
            # marca a variante para continuar pela via pública (sem quebrar).
            interno = getattr(celula, '_style', None)
            estilos[chave] = copy(interno) if interno is not None else False
        elif estilo is False:
            celula.fill = preencher
            celula.font = fonte
            celula.border = borda_fina
            if alinhamento is not None:
                celula.alignment = alinhamento
            if numero is not None:
                celula.number_format = numero
        else:
            celula._style = copy(estilo)

    # [gerado] Passamos str(caminho_arquivo) em vez do objeto Path.
    # Quando o pandas recebe um Path, em algumas versões ele cria um file-handle 
    # e o openpyxl pode não finalizar/fechar o arquivo ZIP (XLSX) corretamente
    # ao final, gerando o erro de "extensão inválida" ou arquivo corrompido.
    # [gerado] Adicionamos formatação nativa de datetime para garantir dd/mm/yyyy no excel
    with pd.ExcelWriter(
        str(temp_path),
        engine='openpyxl',
        datetime_format='dd/mm/yyyy',
        date_format='dd/mm/yyyy'
    ) as writer:

        for nome_aba, df_aba in abas:

            # [gerado] Grava os dados sem índice; a formatação será aplicada depois
            df_aba.to_excel(writer, sheet_name=nome_aba, index=False)
            ws = writer.sheets[nome_aba]
            n_cols = len(df_aba.columns)

            # [gerado] A largura de cada coluna é medida na mesma passada em que
            # as células recebem estilo, evitando uma segunda varredura completa.
            larguras = [0] * (n_cols + 1)

            # ── Formatar cabeçalho (linha 1) ─────────────────────────────────
            for col_idx in range(1, n_cols + 1):
                cell = ws.cell(row=1, column=col_idx)
                aplicar_estilo(
                    cell, 'cabecalho', fill_header, font_header, align_center
                )
                comprimento = len(str(cell.value or ''))
                if comprimento > larguras[col_idx]:
                    larguras[col_idx] = comprimento

            # [gerado] Máscara KT calculada de uma vez (antes era uma conversão
            # de string por linha).
            if len(df_aba):
                mascara_kt = (
                    df_aba['Tipo']
                    .astype(str).str.strip().str.upper().eq('KT')
                    .to_numpy()
                )
            else:
                mascara_kt = ()

            # ── Formatar linhas de dados (a partir da linha 2) ────────────────
            subtotal_row = ws.max_row + 1

            if subtotal_row > 2:
                linhas = ws.iter_rows(
                    min_row=2, max_row=subtotal_row - 1, max_col=n_cols
                )
                for row_idx, row_cells in enumerate(linhas, start=2):

                    # [gerado] Verifica se o tipo da linha é KT para pintar de vermelho
                    is_kt = bool(mascara_kt[row_idx - 2])

                    # [gerado] Zebrado: linhas ímpares e pares recebem tons diferentes
                    if row_idx % 2 != 0:
                        fill_linha, sufixo_linha = fill_row1, 'impar'
                    else:
                        fill_linha, sufixo_linha = fill_row2, 'par'

                    for col_idx, cell in enumerate(row_cells, start=1):
                        if col_idx == col_valor_idx:
                            if is_kt:
                                # [gerado] Célula de Valor em linha KT: fundo vermelho + fonte branca
                                aplicar_estilo(
                                    cell, f'kt_{sufixo_linha}',
                                    fill_kt, font_kt, align_right,
                                )
                            else:
                                aplicar_estilo(
                                    cell, f'dados_{sufixo_linha}_valor',
                                    fill_linha, font_normal, align_right,
                                )
                        else:
                            aplicar_estilo(
                                cell, f'dados_{sufixo_linha}_texto',
                                fill_linha, font_normal, align_left,
                            )

                        # [gerado] Força a formatação visual brasileira nas datas (dd/mm/yyyy)
                        if isinstance(cell.value, datetime.datetime):
                            cell.number_format = 'dd/mm/yyyy'

                        comprimento = len(str(cell.value or ''))
                        if comprimento > larguras[col_idx]:
                            larguras[col_idx] = comprimento

            # ── Linha de subtotal de Valor ────────────────────────────────────
            lbl_col = col_valor_idx - 1 if col_valor_idx > 1 else 1  # coluna ao lado esquerdo

            for col_idx in range(1, n_cols + 1):
                cell = ws.cell(row=subtotal_row, column=col_idx)

                if col_idx == lbl_col:
                    cell.value = 'SUBTOTAL'
                    aplicar_estilo(
                        cell, 'subtotal_rotulo',
                        fill_header, font_subtotal, align_right,
                    )
                elif col_idx == col_valor_idx:
                    cell.value = f'=SUM({get_column_letter(col_valor_idx)}2:' \
                                 f'{get_column_letter(col_valor_idx)}{subtotal_row - 1})'
                    aplicar_estilo(
                        cell, 'subtotal_valor',
                        fill_header, font_subtotal, align_right,
                        numero='#,##0.00',
                    )
                else:
                    aplicar_estilo(
                        cell, 'subtotal_outro',
                        fill_header, font_subtotal, None,
                    )

                comprimento = len(str(cell.value or ''))
                if comprimento > larguras[col_idx]:
                    larguras[col_idx] = comprimento

            # ── Ajuste automático da largura das colunas ──────────────────────
            for col_idx in range(1, n_cols + 1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = min(
                    larguras[col_idx] + 4, 40
                )

    # [gerado] Move atomicamente o temporário completo para o destino final
    # Isso faz o arquivo "nascer" na pasta destino no exato milissegundo em que 
    # fica completamente pronto, sincronizando 100% com o popup da interface.
    shutil.move(temp_path, str(caminho_arquivo))

    return caminho_arquivo


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: _exportar_excel_xlsxwriter  [gerado]
# Objetivo: Caminho rápido opcional para a mesma exportação. O XlsxWriter é
#           bem mais veloz que o openpyxl em volumes grandes; o wrapper público
#           só o usa quando o pacote está instalado e consegue concluir.
# ──────────────────────────────────────────────────────────────────────────────
class _ExportacaoRapidaIndisponivel(Exception):
    """Dado fora do conjunto suportado pelo caminho rápido."""


def _escrever_celula(ws, linha, coluna, valor, formato, formato_data):
    """Grava uma célula preservando o tipo do valor.

    O openpyxl (caminho padrão) decide o tipo sozinho; aqui a decisão é
    explícita para que números, textos, booleanos, datas e vazios cheguem ao
    arquivo exatamente como chegariam pelo pandas/openpyxl. Os tipos mais
    comuns (texto, inteiro, float e data) são testados primeiro, sem passar
    pelo ``pd.isna``, que é caro quando repetido em cada célula.
    """
    import datetime
    import math

    import numpy as np
    import pandas as pd

    if valor is None:
        ws.write_blank(linha, coluna, None, formato)
        return
    if isinstance(valor, str):
        # O openpyxl transforma texto que começa com "=" em fórmula; repetimos
        # a mesma regra para o arquivo ficar idêntico ao caminho antigo.
        if len(valor) > 1 and valor.startswith('='):
            ws.write_formula(linha, coluna, valor, formato)
        else:
            ws.write_string(linha, coluna, valor, formato)
        return
    if isinstance(valor, bool):
        ws.write_boolean(linha, coluna, valor, formato)
        return
    if isinstance(valor, np.bool_):
        ws.write_boolean(linha, coluna, bool(valor), formato)
        return
    if isinstance(valor, np.integer):
        ws.write_number(linha, coluna, int(valor), formato)
        return
    if isinstance(valor, np.floating):
        numero = float(valor)
        if math.isnan(numero):
            ws.write_blank(linha, coluna, None, formato)
        else:
            ws.write_number(linha, coluna, numero, formato)
        return
    if isinstance(valor, int):
        ws.write_number(linha, coluna, valor, formato)
        return
    if isinstance(valor, float):
        if math.isnan(valor):
            ws.write_blank(linha, coluna, None, formato)
        else:
            ws.write_number(linha, coluna, valor, formato)
        return

    # NaT é subclasse de datetime, mas representa vazio.
    if valor is pd.NaT:
        ws.write_blank(linha, coluna, None, formato)
        return

    if isinstance(valor, (pd.Timestamp, datetime.datetime, datetime.date)):
        if getattr(valor, 'tzinfo', None) is not None:
            raise _ExportacaoRapidaIndisponivel('data com fuso horário')
        ws.write_datetime(linha, coluna, valor, formato_data)
        return

    # time/timedelta têm regras de formato próprias no openpyxl; nesses casos
    # o caminho rápido delega para o caminho seguro.
    if isinstance(valor, (datetime.time, datetime.timedelta, pd.Timedelta)):
        raise _ExportacaoRapidaIndisponivel('hora/intervalo de tempo')

    # pd.NA, NaN de tipos exóticos e escalares não previstos.
    try:
        vazio = pd.isna(valor)
    except (TypeError, ValueError):
        vazio = False
    if isinstance(vazio, bool) and vazio:
        ws.write_blank(linha, coluna, None, formato)
        return

    # Escalares do NumPy que não caíram nos testes acima.
    if hasattr(valor, 'item'):
        convertido = valor.item()
        if type(convertido) is not type(valor):
            _escrever_celula(
                ws, linha, coluna, convertido, formato, formato_data
            )
            return

    raise _ExportacaoRapidaIndisponivel(f'tipo não suportado: {type(valor)}')


def _maior_comprimento_coluna(serie) -> int:
    """Maior ``len(str(valor or ''))`` da coluna, como a medição antiga.

    Datas são medidas pelo ``str`` do objeto (ex.: ``2025-10-02 00:00:00``),
    e não pelo formato curto do ``astype(str)``; por isso a coluna de data usa
    ``map``. Para os demais tipos o cálculo vetorizado é equivalente.
    """
    import pandas as pd
    from pandas.api.types import is_datetime64_any_dtype

    if len(serie) == 0:
        return 0

    if (
        is_datetime64_any_dtype(serie.dtype)
        or serie.dtype == object
        or isinstance(serie.dtype, pd.CategoricalDtype)
    ):
        validos = serie.notna()
        comprimentos = serie.map(lambda valor: len(str(valor or '')))
        comprimentos = comprimentos.where(validos, 0)
        return int(comprimentos.max())

    comprimentos = serie.astype(str).str.len()
    vazio = serie.isna()
    try:
        zero = serie.eq(0) | serie.eq(False)
    except (TypeError, ValueError):
        zero = False
    if hasattr(zero, "fillna"):
        zero = zero.fillna(False)
    comprimentos = comprimentos.mask(vazio | zero, 0)
    return int(comprimentos.max()) if len(comprimentos) else 0


def _exportar_excel_xlsxwriter(df_final, separar, destino, nome, cor='Azul'):
    import datetime
    import os
    import shutil
    import tempfile

    import pandas as pd
    import xlsxwriter
    from xlsxwriter.utility import xl_col_to_name

    header_hex, row1_hex, row2_hex = PALETAS_RELATORIO.get(
        cor, PALETAS_RELATORIO['Azul']
    )

    abas = _montar_abas(df_final, separar)
    colunas = list(df_final.columns)
    col_valor_idx = colunas.index('Valor')  # base 0 no XlsxWriter

    caminho_arquivo = Path(destino) / f'{nome}.xlsx'
    fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(fd)

    # Base comum a todas as células de dados, igual aos Font/Alignment/Border
    # do caminho openpyxl.
    base = {
        'font_name': 'Calibri', 'font_size': 10, 'font_color': '#000000',
        'border': 1, 'border_color': '#FFFFFF', 'valign': 'vcenter',
    }

    wb = None

    def novo_formato(**extra):
        return wb.add_format({**base, **extra})

    try:
        # in_memory evita arquivos temporários internos do XlsxWriter e é um
        # pouco mais rápido; o custo de memória é semelhante ao do openpyxl.
        wb = xlsxwriter.Workbook(str(temp_path), {'in_memory': True})

        formato_cabecalho = wb.add_format({
            'font_name': 'Calibri', 'font_size': 11, 'bold': True,
            'font_color': '#FFFFFF', 'bg_color': '#' + header_hex,
            'pattern': 1, 'border': 1, 'border_color': '#FFFFFF',
            'align': 'center', 'valign': 'vcenter',
        })
        formato_kt = wb.add_format({
            'font_name': 'Calibri', 'font_size': 10, 'bold': True,
            'font_color': '#FFFFFF', 'bg_color': '#FF0000', 'pattern': 1,
            'border': 1, 'border_color': '#FFFFFF',
            'align': 'right', 'valign': 'vcenter',
        })
        formato_kt_data = wb.add_format({
            'font_name': 'Calibri', 'font_size': 10, 'bold': True,
            'font_color': '#FFFFFF', 'bg_color': '#FF0000', 'pattern': 1,
            'border': 1, 'border_color': '#FFFFFF',
            'align': 'right', 'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy',
        })
        formato_subtotal_rotulo = wb.add_format({
            'font_name': 'Calibri', 'font_size': 10, 'bold': True,
            'font_color': '#FFFFFF', 'bg_color': '#' + header_hex,
            'pattern': 1, 'border': 1, 'border_color': '#FFFFFF',
            'align': 'right', 'valign': 'vcenter',
        })
        formato_subtotal_valor = wb.add_format({
            'font_name': 'Calibri', 'font_size': 10, 'bold': True,
            'font_color': '#FFFFFF', 'bg_color': '#' + header_hex,
            'pattern': 1, 'border': 1, 'border_color': '#FFFFFF',
            'align': 'right', 'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        formato_subtotal_outro = wb.add_format({
            'font_name': 'Calibri', 'font_size': 10, 'bold': True,
            'font_color': '#FFFFFF', 'bg_color': '#' + header_hex,
            'pattern': 1, 'border': 1, 'border_color': '#FFFFFF',
        })

        # [True = linha de Excel ímpar (tom row1); False = par (row2)]
        formatos_esq = {
            True: novo_formato(bg_color='#' + row1_hex, pattern=1,
                               align='left'),
            False: novo_formato(bg_color='#' + row2_hex, pattern=1,
                                align='left'),
        }
        formatos_dir = {
            True: novo_formato(bg_color='#' + row1_hex, pattern=1,
                               align='right'),
            False: novo_formato(bg_color='#' + row2_hex, pattern=1,
                                align='right'),
        }
        formatos_esq_data = {
            True: novo_formato(bg_color='#' + row1_hex, pattern=1,
                               align='left', num_format='dd/mm/yyyy'),
            False: novo_formato(bg_color='#' + row2_hex, pattern=1,
                                align='left', num_format='dd/mm/yyyy'),
        }
        formatos_dir_data = {
            True: novo_formato(bg_color='#' + row1_hex, pattern=1,
                               align='right', num_format='dd/mm/yyyy'),
            False: novo_formato(bg_color='#' + row2_hex, pattern=1,
                                align='right', num_format='dd/mm/yyyy'),
        }

        for nome_aba, df_aba in abas:
            ws = wb.add_worksheet(nome_aba)
            n_cols = len(colunas)
            subtotal = len(df_aba) + 1  # base 0 no XlsxWriter
            rotulo = col_valor_idx - 1 if col_valor_idx > 0 else 0
            letra_valor = xl_col_to_name(col_valor_idx)
            formula_valor = f'=SUM({letra_valor}2:{letra_valor}{subtotal})'

            # [gerado] As larguras são medidas por coluna (vetorizado), e não
            # célula a célula: mesmo resultado do openpyxl, bem mais rápido.
            larguras: list[int] = []
            for indice, coluna in enumerate(colunas):
                if isinstance(
                    coluna, (pd.Timestamp, datetime.datetime, datetime.date)
                ):
                    raise _ExportacaoRapidaIndisponivel('cabeçalho de data')
                maior = len(str(coluna or ''))
                if len(df_aba):
                    maior = max(
                        maior,
                        _maior_comprimento_coluna(
                            df_aba.iloc[:, indice]
                        ),
                    )
                if indice == rotulo:
                    maior = max(maior, len('SUBTOTAL'))
                elif indice == col_valor_idx:
                    maior = max(maior, len(formula_valor))
                larguras.append(maior)

            for indice, coluna in enumerate(colunas):
                _escrever_celula(
                    ws, 0, indice, coluna,
                    formato_cabecalho, formato_cabecalho,
                )

            if len(df_aba):
                mascara_kt = (
                    df_aba['Tipo']
                    .astype(str).str.strip().str.upper().eq('KT')
                    .tolist()
                )
            else:
                mascara_kt = []

            for linha, valores in enumerate(
                df_aba.itertuples(index=False, name=None)
            ):
                excel_row = linha + 2  # 1 = cabeçalho
                usa_row1 = excel_row % 2 != 0
                for indice, valor in enumerate(valores):
                    eh_kt = mascara_kt[linha] and indice == col_valor_idx
                    if eh_kt:
                        _escrever_celula(
                            ws, linha + 1, indice, valor,
                            formato_kt, formato_kt_data,
                        )
                    elif indice == col_valor_idx:
                        _escrever_celula(
                            ws, linha + 1, indice, valor,
                            formatos_dir[usa_row1],
                            formatos_dir_data[usa_row1],
                        )
                    else:
                        _escrever_celula(
                            ws, linha + 1, indice, valor,
                            formatos_esq[usa_row1],
                            formatos_esq_data[usa_row1],
                        )

            for indice in range(n_cols):
                if indice == rotulo:
                    ws.write_string(
                        subtotal, indice, 'SUBTOTAL',
                        formato_subtotal_rotulo,
                    )
                elif indice == col_valor_idx:
                    ws.write_formula(
                        subtotal, indice, formula_valor,
                        formato_subtotal_valor,
                    )
                else:
                    ws.write_blank(
                        subtotal, indice, None, formato_subtotal_outro
                    )

            for indice, largura in enumerate(larguras):
                # O XlsxWriter soma 0.7109375 ao valor gravado; descontamos
                # para o arquivo ficar com a mesma largura do openpyxl.
                ws.set_column(
                    indice, indice, min(largura + 4, 40) - 0.7109375
                )

        wb.close()
        wb = None
    except Exception:
        if wb is not None:
            try:
                wb.close()
            except Exception:  # noqa: BLE001 - melhor esforço
                pass
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

    # [gerado] Mesmo nascimento atômico do caminho openpyxl.
    shutil.move(temp_path, str(caminho_arquivo))
    return caminho_arquivo


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO: exportar_excel
# Objetivo: Ponto de entrada da exportação. Usa o XlsxWriter quando disponível
#           e, em qualquer falha ou ambiente sem o pacote, refaz pelo openpyxl
#           — que é o caminho antigo, preservado integralmente.
# ──────────────────────────────────────────────────────────────────────────────
def exportar_excel(df_final, separar, destino, nome, cor='Azul'):
    try:
        return _exportar_excel_xlsxwriter(
            df_final, separar, destino, nome, cor
        )
    except Exception:  # noqa: BLE001 - qualquer desvio usa o caminho seguro
        return _exportar_excel_openpyxl(
            df_final, separar, destino, nome, cor
        )
