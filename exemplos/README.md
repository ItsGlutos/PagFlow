# Dados de exemplo — GutoLog Express Ltda.

Arquivos `.xls` fictícios no **mesmo formato que o PagFlow lê**, prontos para
parametrizar e testar o sistema sem nenhum dado real.

| Arquivo | Layout | Detectado como |
|---|---|---|
| `GutoLog_FBL1N_2025-10.xls` | Extrato de fornecedor | Tipo **A** (`skiprows=8`) |
| `GutoLog_REL_LOG_2025-10.xls` | Log de pagamentos | Tipo **B** (`skiprows=3`) |

Os dois podem ficar na mesma pasta: o PagFlow identifica o layout sozinho e
consolida tudo em um único `.xlsx`.

## Como usar

1. Abra o PagFlow (`python main.py` ou o executável).
2. **Pasta de origem** → aponte para esta pasta `exemplos/`.
3. **Separar abas por** → `Marca`, `LNeg`, `Fornecedor` ou `Não Separar`.
4. **Cor do relatório** → qualquer uma das quatro.
5. **Pasta de destino** → onde salvar o `.xlsx`.
6. **Nome do arquivo** → ex.: `GutoLog_consolidado`.
7. Clique em **Gerar Excel**.

Resultado esperado com `Marca` + `Verde`: 3 abas (`Custos SC`, `Panpharma`,
`Santa Cruz`), 25 linhas de dados, 2 linhas `KT` destacadas em vermelho e uma
linha de `SUBTOTAL` com fórmula `=SUM` em cada aba.

## Formato do arquivo (importante)

Estes `.xls` **não são planilhas binárias**. São exatamente o que o SAP exporta
neste contexto e o que `funcoes.detectar_relat()` espera:

- texto com separador **TAB**
- codificação **UTF-16** com BOM (`FF FE`)
- quebras de linha **CRLF**
- extensão `.xls`
- datas em `dd.mm.yyyy`
- valores em `1.234,56`, com o sinal de menos **no fim** quando negativo
  (`1.234,56-`), conforme o padrão SAP

Abrir esses arquivos no Excel mostra tudo em uma única coluna — é o
comportamento normal desse formato.

## Layout das colunas

`funcoes.py` descarta colunas **por posição** e depois renomeia as 12 restantes.
Por isso a ordem posicional não pode mudar, mesmo em colunas que são descartadas.
A coluna de bloqueio (`BlP`/`BIP`) também é descartada do esquema fixo, mas é
capturada pelo cabeçalho e devolvida ao final como **`Bloqueio`**.

### FBL1N (Tipo A) — 16 colunas no arquivo

O código descarta os índices **0, 12, 14 e 15**:

| Índice | Coluna no arquivo | Vira |
|---:|---|---|
| 0 | `Seq` | descartada |
| 1 | `Empresa` | `Empresa` |
| 2 | `Fornecedor` | `Fornecedor` |
| 3 | `LNeg` | `LNeg` |
| 4 | `Referência` | `Referência` |
| 5 | `Nº documento` | `Nº documento` |
| 6 | `Data doc.` | `Data doc.` |
| 7 | `Doc. Compensação` | `Doc. Compensação` |
| 8 | `Valor` | `Valor` |
| 9 | `Vencimento` | `Vencimento` |
| 10 | `Texto` | `Texto` |
| 11 | `Tipo` | `Tipo` |
| 12 | `Nome` | descartada |
| 13 | `Compensaç.` | `Compensaç.` |
| 14 | `BlP` | descartada do esquema fixo, mas vira `Bloqueio` |
| 15 | `Moeda` | descartada |

No FBL1N o valor é multiplicado por **-1** após o parse, então `1.500,00-`
(crédito SAP) aparece como **+1500,00** no relatório.

### REL_LOG (Tipo B) — 16 colunas no arquivo

O código descarta os índices **15, 14, 13 e 8** e renomeia o restante **por
posição** (os nomes do cabeçalho são ignorados):

| Índice | Coluna no arquivo | Vira (posição após descarte) |
|---:|---|---|
| 0 | `Empresa` | `Empresa` (0) |
| 1 | `LNeg` | `LNeg` (1) |
| 2 | `Fornecedor` | `Fornecedor` (2) |
| 3 | `Nº documento` | `Nº documento` (3) |
| 4 | `Data doc.` | `Data doc.` (4) |
| 5 | `Referência` | `Referência` (5) |
| 6 | `Vencimento` | `Vencimento` (6) |
| 7 | `Tipo` | `Tipo` (7) |
| 8 | `BIP` | descartada do esquema fixo, mas vira `Bloqueio` |
| 9 | `Valor` | `Valor` (8) |
| 10 | `Texto` | `Texto` (9) |
| 11 | `Doc. Compensação` | `Doc. Compensação` (10) |
| 12 | `Compensaç.` | `Compensaç.` (11) |
| 13 | `Banco` | descartada |
| 14 | `Data baixa` | descartada |
| 15 | `Forma pgto` | descartada |

No REL_LOG o valor é usado **sem** inversão de sinal.

## O que os dados exercitam

O conjunto foi montado para cobrir os caminhos reais do código:

- **3 marcas** (`Santa Cruz`, `Panpharma`, `Custos SC`) e **4 locais de negócio**
  (`1000`, `2000`, `3001`, `4000`)
- **3 códigos de fornecedor** (`101234`, `101987`, `102450`) — testa a separação
  de abas por `Fornecedor`
- **25 linhas finais**: 17 do FBL1N + 9 do REL_LOG − 1 duplicata
- **2 linhas `KT`** (confissão de dívida) → destaque vermelho no Excel
- **6 linhas com bloqueio** (`BlP`/`BIP` = `B`) → exercita a coluna `Bloqueio`
  e os avisos de valor bloqueado no e-mail

> Na coluna de bloqueio, `B` = bloqueado; `S` = sem bloqueio (linhas `RE`);
> os demais tipos ficam em branco, como no extrato real.
- **3 linhas `RF`** (nota fiscal da seguradora) → reembolsos
- **1 linha `KL`** (fatura) → propositalmente descartada pelo filtro de tipos
- **1 referência repetida** entre os dois relatórios (`CTE-2025-1042`) →
  exercita o `drop_duplicates` de `ope.py`
- **1 valor negativo** vindo do log (`135,00-`) → testa o sinal no fim da string

Totais resultantes da consolidação:

| Marca | Linhas | Soma de `Valor` |
|---|---:|---:|
| Santa Cruz | 10 | 16.861,65 |
| Panpharma | 7 | 15.281,20 |
| Custos SC | 8 | 13.132,05 |
| **Total** | **25** | **45.274,90** |

## Regenerar ou personalizar

```bash
python exemplos/gerar_dados_exemplo.py    # regrava os dois .xls
python exemplos/verificar_exemplo.py      # valida tudo de ponta a ponta
```

Para adaptar a outra transportadora, edite as constantes `TRANSPORTADORA`,
`CNPJ` e as listas `LINHAS_FBL1N` / `LINHAS_REL_LOG` em
`gerar_dados_exemplo.py` e rode o gerador novamente.

> Todos os nomes, CNPJs, documentos e valores são fictícios. Os nomes de marca
> usados nas abas (`Santa Cruz`, `Panpharma`, `Custos SC`) são apenas rótulos de
> exemplo.
