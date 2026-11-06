"""Lógica de envio dos relatórios PagFlow por fornecedor (via Outlook).

Este módulo é independente da interface gráfica e do Outlook na importação:
a automação COM do Outlook só acontece quando um envio real é executado.

Fluxo principal:

1. :func:`ler_contatos` lê a planilha de contatos (``Transportadora`` +
   ``Fornecedor`` + ``E-mail(s)``) e consolida cada fornecedor com o *Nome
   Simples* informado em ``Transportadora``. As demais colunas são ignoradas;
2. :func:`localizar_relatorios` varre a pasta e, para cada ``.xlsx``, localiza
   a coluna ``Fornecedor`` em **todas** as abas;
3. :func:`montar_plano` cruza os dois lados usando o **código do fornecedor**
   como chave (o *procv* código → Transportadora) e monta um
   :class:`PlanoEnvios` (um grupo por arquivo — logo, um arquivo não pode
   conter dois fornecedores diferentes nesta etapa);
4. :func:`enviar_plano` envia os grupos selecionados, um e-mail por arquivo,
   com o relatório anexado.

O corpo de cada e-mail recebe automaticamente os avisos de documentos
bloqueados (coluna ``BlP``/``BIP`` = ``B``) e do valor total de CFD
(documentos ``KT``), quando existirem.

O envio real usa o Outlook Desktop via ``pywin32``. Para testes,
:func:`enviar_plano` aceita um ``sender_factory`` que devolve qualquer objeto
com ``enviar(grupo)`` e ``fechar()``.
"""

from __future__ import annotations

import html as _html
import posixpath
import re
import time
import unicodedata
import xml.parsers.expat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence
from xml.etree import ElementTree as ET

import pandas as pd

__all__ = [
    "DEFAULT_ASSUNTO",
    "DEFAULT_CORPO",
    "Contato",
    "EnvioError",
    "EnvioResultado",
    "GrupoEnvio",
    "OutlookSender",
    "PlanoEnvios",
    "RelatorioInfo",
    "corpo_para_html",
    "dividir_emails",
    "enviar_plano",
    "formatar_moeda",
    "formatar_quantidade",
    "ler_contatos",
    "localizar_relatorios",
    "montar_plano",
    "normalizar_chave",
    "normalizar_fornecedor",
    "renderizar_template",
    "validar_email",
]


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
DEFAULT_ASSUNTO = "{fornecedor} — Relatório de pagamento"

DEFAULT_CORPO = """Olá, {fornecedor}!

Segue em anexo o relatório de pagamento referente ao último pagamento realizado.

Em caso de dúvidas, permanecemos à disposição.

Atenciosamente,
Time Fretes - Distribuição Farma"""

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SEPARADORES_RE = re.compile(r"[;,\s]+")
_ESPACOS_RE = re.compile(r"\s+")
_NUM_RE = re.compile(r"^(\d+)(?:[.,]0+)?$")
# Mesma limpeza usada pelo openpyxl para decidir se um formato é de data.
_STRIP_FORMATO_RE = re.compile(r'.*?"|\[(?!hh?\]|mm?\]|ss?\])[^\]]*\]')
_FORMATO_DATA_RE = re.compile(r"(?<![_\\])[dmhysDMHYS]")
# IDs de formato nativo do Excel que representam data/hora. A lista é a mesma
# que o openpyxl reconhece em BUILTIN_FORMATS (14-22, 45-47).
_FORMATOS_DATA_EMBUTIDOS = frozenset(
    {14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47}
)


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------
class EnvioError(Exception):
    """Erro esperado, com mensagem pronta para ser mostrada ao usuário."""


# ---------------------------------------------------------------------------
# Normalização e validação
# ---------------------------------------------------------------------------
def normalizar_chave(texto: object) -> str:
    """Padroniza nomes para o cruzamento entre arquivos e contatos.

    Remove acentos, ignora caixa e colapsa espaços — assim ``" Ála  Uber "``
    e ``"ALA UBER"`` viram a mesma chave.
    """
    decomposto = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(
        caractere
        for caractere in decomposto
        if not unicodedata.combining(caractere)
    )
    return _ESPACOS_RE.sub(" ", sem_acento).strip().lower()


def normalizar_fornecedor(valor: object) -> str:
    """Normaliza o código de fornecedor vindo do relatório ou dos contatos.

    Códigos numéricos (``10001234``, ``10001234.0``, ``"0010001234"``) viram a
    mesma chave ``"10001234"``. Valores textuais caem em :func:`normalizar_chave`.
    """
    if _vazio(valor):
        return ""
    texto = str(valor).strip()
    if not texto:
        return ""
    match = _NUM_RE.match(texto)
    if match:
        return match.group(1).lstrip("0") or "0"
    return normalizar_chave(texto)


def _vazio(valor: object) -> bool:
    """Diz se um valor de célula está vazio (``None``/NaN/string em branco)."""
    if valor is None:
        return True
    if isinstance(valor, float) and pd.isna(valor):
        return True
    if isinstance(valor, str) and not valor.strip():
        return True
    return False


def validar_email(email: object) -> bool:
    """Diz se um endereço tem o formato mínimo aceito pelo Outlook.

    Além do formato básico, rejeita pontos no início/fim da parte local ou do
    domínio e pontos consecutivos, que são erros comuns de digitação.
    """
    texto = str(email).strip().strip(";, ")
    if not texto or ".." in texto:
        return False
    if not _EMAIL_RE.match(texto):
        return False
    local, separador, dominio = texto.partition("@")
    if not separador or not local or not dominio:
        return False
    if local.startswith(".") or local.endswith("."):
        return False
    if dominio.startswith(".") or dominio.endswith(".") or "." not in dominio:
        return False
    return True


def dividir_emails(texto: object) -> list[str]:
    """Divide uma célula/lista em e-mails únicos, preservando a ordem."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return []
    partes = _SEPARADORES_RE.split(str(texto).strip())
    vistos: set[str] = set()
    resultado: list[str] = []
    for parte in partes:
        email = parte.strip().strip(",;")
        if not email:
            continue
        chave = email.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(email)
    return resultado


def renderizar_template(texto: str, nome_fornecedor: str) -> str:
    """Troca ``{fornecedor}`` (ou ``{nome}``) pelo Nome Simples do grupo."""
    resultado = str(texto)
    resultado = resultado.replace("{fornecedor}", nome_fornecedor)
    resultado = resultado.replace("{nome}", nome_fornecedor)
    return resultado


def formatar_moeda(valor: float) -> str:
    """Formata um número no padrão brasileiro: ``R$ 1.234,56``."""
    texto = f"{abs(float(valor)):,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_quantidade(valor: int) -> str:
    """Formata uma contagem no padrão brasileiro: ``1.234``."""
    return f"{int(valor):,}".replace(",", ".")


def _bloqueado(valor: object) -> bool:
    """Diz se o indicador de bloqueio da linha representa um bloqueio ativo.

    Na coluna ``BlP``/``BIP`` o SAP marca o documento bloqueado com ``B``.
    Os demais valores (``S``, ``N``, branco) são tratados como sem bloqueio —
    por isso não basta olhar se a célula está preenchida.
    """
    if _vazio(valor):
        return False
    texto = normalizar_chave(valor)
    return texto in {"b", "bloqueado", "bloqueada", "bloq", "bloqueio"}


def corpo_para_html(corpo: str) -> str:
    """Converte o corpo (texto puro) em HTML seguro para o ``HTMLBody``.

    O conteúdo é escapado para evitar que um nome com ``<``/``&`` quebre o
    e-mail, e quebras de linha viram ``<br>``.
    """
    seguro = _html.escape(str(corpo))
    com_quebras = seguro.replace("\r\n", "\n").replace("\n", "<br>")
    return (
        '<div style="font-family:Calibri, Arial, sans-serif; '
        f'font-size:11pt;">{com_quebras}</div>'
    )


# ---------------------------------------------------------------------------
# Leitura das fontes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Contato:
    """Contato consolidado de um fornecedor (Transportadora + e-mails)."""

    nome: str
    emails: tuple[str, ...]
    emails_invalidos: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelatorioInfo:
    """Um ``.xlsx`` encontrado na pasta e os dados que ele contém."""

    caminho: Path
    fornecedores: tuple[str, ...]
    documentos_bloqueados: int = 0
    valor_bloqueado: float = 0.0
    documentos_cfd: int = 0
    valor_cfd: float = 0.0

    @property
    def tem_avisos(self) -> bool:
        """Indica se o arquivo tem bloqueio e/ou documento KT (CFD)."""
        return self.documentos_bloqueados > 0 or self.documentos_cfd > 0

    def resumo_avisos(self) -> str:
        """Resumo curto dos avisos, para a interface e para os logs."""
        partes: list[str] = []
        if self.documentos_bloqueados:
            partes.append(
                f"{formatar_quantidade(self.documentos_bloqueados)} bloqueio(s) — "
                f"{formatar_moeda(self.valor_bloqueado)}"
            )
        if self.documentos_cfd:
            partes.append(
                f"CFD — {formatar_moeda(self.valor_cfd)} "
                f"({formatar_quantidade(self.documentos_cfd)} KT)"
            )
        return " · ".join(partes)


def ler_contatos(caminho: str | Path) -> dict[str, Contato]:
    """Lê a planilha de contatos e consolida por código de fornecedor.

    A planilha deve ter as colunas ``Transportadora`` (Nome Simples),
    ``Fornecedor`` (código) e ``E-mail(s)``. Quaisquer outras colunas são
    ignoradas. O código é a chave do *procv* que localiza a Transportadora e
    os e-mails de cada envio. E-mails repetidos são removidos e os inválidos
    ficam separados para que a interface possa avisar sem bloquear os bons.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        raise EnvioError(
            f"Planilha de contatos não encontrada:\n{caminho}\n\n"
            "Escolha o arquivo .xlsx com as colunas 'Transportadora', "
            "'Fornecedor' e 'E-mail(s)'."
        )

    try:
        dataframe = pd.read_excel(caminho, dtype=object)
    except Exception as erro:  # noqa: BLE001 - mensagem amigável
        raise EnvioError(
            f"Não foi possível ler a planilha de contatos:\n{caminho}\n\n"
            f"Detalhe técnico: {erro}"
        ) from erro

    colunas = {
        normalizar_chave(coluna): coluna for coluna in dataframe.columns
    }
    coluna_fornecedor = _achar_coluna(
        colunas, "fornecedor", excluir=("transportadora", "nome")
    )
    coluna_nome = _achar_coluna_transportadora(colunas)
    coluna_email = _achar_coluna_email(colunas)

    if coluna_fornecedor is None or coluna_nome is None or coluna_email is None:
        encontradas = ", ".join(str(c) for c in dataframe.columns)
        raise EnvioError(
            "A planilha de contatos precisa das colunas 'Transportadora', "
            "'Fornecedor' e 'E-mail(s)'.\n\n"
            f"Colunas encontradas: {encontradas or '(nenhuma)'}"
        )

    contatos: dict[str, Contato] = {}
    # Iterar pelas colunas é bem mais rápido que iterrows(): evita criar uma
    # Series por linha, mantendo a mesma ordem e os mesmos valores.
    for bruto_codigo, nome_bruto, email_bruto in zip(
        dataframe[coluna_fornecedor],
        dataframe[coluna_nome],
        dataframe[coluna_email],
    ):
        codigo = normalizar_fornecedor(bruto_codigo)
        if not codigo:
            continue
        if _vazio(nome_bruto):
            continue
        nome = str(nome_bruto).strip()

        emails = dividir_emails(email_bruto)
        validos_lista: list[str] = []
        invalidos_lista: list[str] = []
        for email in emails:
            if validar_email(email):
                validos_lista.append(email)
            else:
                invalidos_lista.append(email)
        validos = tuple(validos_lista)
        invalidos = tuple(invalidos_lista)

        existente = contatos.get(codigo)
        if existente is None:
            contatos[codigo] = Contato(
                nome=nome, emails=validos, emails_invalidos=invalidos
            )
            continue
        contatos[codigo] = Contato(
            nome=existente.nome,
            emails=_unir_unicos(existente.emails, validos),
            emails_invalidos=_unir_unicos(
                existente.emails_invalidos, invalidos
            ),
        )
    return contatos


def localizar_relatorios(
    pasta: str | Path, ignorar: Iterable[str | Path] | None = None
) -> list[RelatorioInfo]:
    """Lista os ``.xlsx`` da pasta com os códigos de fornecedor encontrados.

    Ignora temporários do Excel (``~$``), arquivos que não sejam ``.xlsx`` e os
    caminhos passados em ``ignorar`` (útil para não confundir a planilha de
    contatos com um relatório quando ela está na mesma pasta).
    """
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise EnvioError(
            f"Pasta de relatórios não encontrada:\n{pasta}\n\n"
            "Escolha a pasta que contém os arquivos gerados pelo PagFlow."
        )

    ignorados = {Path(caminho).resolve() for caminho in (ignorar or [])}
    relatorios: list[RelatorioInfo] = []
    for caminho in sorted(pasta.iterdir(), key=lambda p: p.name.lower()):
        if not caminho.is_file():
            continue
        if caminho.name.startswith("~$"):
            continue
        if caminho.suffix.lower() != ".xlsx":
            continue
        if caminho.resolve() in ignorados:
            continue
        relatorios.append(_ler_relatorio(caminho))
    return relatorios


# [gerado] Namespaces internos do formato .xlsx (Office Open XML).
_XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_XLSX_REL_NS = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
)


class _LeituraRapidaInvalida(Exception):
    """Arquivo fora do padrão simples: a leitura volta para o pandas."""


# ---------------------------------------------------------------------------
# Leitura rápida dos relatórios gerados pelo PagFlow
# ---------------------------------------------------------------------------
# O caminho antigo (pandas.read_excel) monta um DataFrame completo de todas as
# abas. Como o envio só precisa de quatro colunas (Fornecedor, Valor, Bloqueio
# e Tipo), a leitura rápida percorre o XML da planilha com o expat e monta
# apenas essas colunas. Qualquer construção não prevista (data ISO, número com
# formato de data, tipo de célula desconhecido, aba que não seja worksheet)
# cancela o caminho rápido e refaz a leitura pelo pandas — o resultado é o
# mesmo, apenas mais lento para arquivos atípicos.

def _coluna_da_referencia(ref: str) -> int:
    """Converte ``"H12"`` no índice zero-based da coluna (``7``)."""
    coluna = 0
    for caractere in ref:
        if "A" <= caractere <= "Z":
            coluna = coluna * 26 + (ord(caractere) - 64)
        elif "a" <= caractere <= "z":
            coluna = coluna * 26 + (ord(caractere) - 96)
        else:
            return coluna - 1
    raise _LeituraRapidaInvalida("referência de célula sem número de linha")


def _texto_do_xml(elemento) -> str:
    """Junta o texto visível de um ``<si>``/``<is>``, ignorando fonética.

    O openpyxl usa ``Text.from_tree(...).content``, que considera apenas o
    texto simples e os blocos formatados; ``<rPh>`` (leitura fonética) fica de
    fora. Repetimos a mesma regra para os valores baterem exatamente.
    """
    partes: list[str] = []
    for filho in elemento:
        if filho.tag == _XLSX_NS + "rPh":
            continue
        if filho.tag == _XLSX_NS + "t":
            if filho.text:
                partes.append(filho.text)
        elif filho.tag == _XLSX_NS + "r":
            for neto in filho:
                if neto.tag == _XLSX_NS + "t" and neto.text:
                    partes.append(neto.text)
    return "".join(partes)


def _indice_da_coluna(nomes, aliases: tuple[str, ...]) -> int | None:
    """Repete a busca de :func:`_coluna_por_nome` sobre cabeçalhos do XML."""
    for coluna, nome in nomes:
        if normalizar_chave(nome) in aliases:
            return coluna
    for coluna, nome in nomes:
        chave = normalizar_chave(nome)
        if any(alias in chave for alias in aliases):
            return coluna
    return None


def _formato_eh_data(codigo: str) -> bool:
    """Equivalente local de ``openpyxl.styles.numbers.is_date_format``."""
    if not codigo:
        return False
    codigo = codigo.split(";")[0]
    codigo = _STRIP_FORMATO_RE.sub("", codigo)
    return _FORMATO_DATA_RE.search(codigo) is not None


def _estilos_com_formato_de_data(arquivo_zip: zipfile.ZipFile) -> set[int]:
    """Índices de estilo (``cellXfs``) que exibem números como data.

    A leitura rápida não converte números em data; se alguma das colunas que
    interessam usar um desses estilos, o caminho rápido é abandonado para não
    alterar os totais.
    """
    try:
        raiz = ET.fromstring(arquivo_zip.read("xl/styles.xml"))
    except KeyError:
        return set()

    formatos: dict[int, str] = {}
    lista_formatos = raiz.find(_XLSX_NS + "numFmts")
    if lista_formatos is not None:
        for formato in lista_formatos:
            formatos[int(formato.get("numFmtId"))] = (
                formato.get("formatCode") or ""
            )

    estilos: set[int] = set()
    lista_estilos = raiz.find(_XLSX_NS + "cellXfs")
    if lista_estilos is not None:
        for indice, estilo in enumerate(lista_estilos):
            numero = int(estilo.get("numFmtId") or 0)
            codigo = formatos.get(numero) or ""
            if codigo:
                if _formato_eh_data(codigo):
                    estilos.add(indice)
            elif numero in _FORMATOS_DATA_EMBUTIDOS:
                estilos.add(indice)
    return estilos


def _numero_da_celula(texto: str):
    """Mesma distinção int/float usada pelo openpyxl para células numéricas."""
    if "." in texto or "e" in texto.lower():
        try:
            return float(texto)
        except ValueError as erro:
            raise _LeituraRapidaInvalida("número inválido") from erro
    try:
        return int(texto)
    except ValueError as erro:
        raise _LeituraRapidaInvalida("número inválido") from erro


class _AbaXlsx:
    """Callbacks do expat que extraem as quatro colunas de uma aba."""

    def __init__(
        self, shared: list[str], estilos_data: set[int]
    ) -> None:
        self.shared = shared
        self.estilos_data = estilos_data
        self.cabecalho_lido = False
        self.indices = [None, None, None, None]
        self.slots: dict[int, int] = {}
        self.listas: list[list] = [[], [], [], []]
        self.celulas_cabecalho: list[tuple[int, object]] = []
        self.valores_linha: list = []
        self.numero_linha: str | None = None
        self.coluna_celula: int | None = None
        self.tipo_celula: str | None = None
        self.estilo_celula: str | None = None
        self.valor_celula: str | None = None
        self.partes_texto: list[str] = []
        self.texto: list[str] = []
        self.dentro_de_valor = False
        self.dentro_de_string = False
        self.dentro_de_texto = False
        self.dentro_de_rph = False
        self.ignorar_celula = False

    # ── callbacks do expat ─────────────────────────────────────────────────
    def start(self, nome: str, atributos: dict) -> None:
        if nome == "row":
            # Estilo herdado da linha poderia transformar número em data sem
            # que a célula tivesse o atributo "s"; nesse caso, caminho seguro.
            if "s" in atributos or atributos.get("customFormat") == "1":
                raise _LeituraRapidaInvalida("estilo herdado da linha")
            self.numero_linha = atributos.get("r")
            if self.cabecalho_lido:
                self.valores_linha = [None, None, None, None]
            else:
                self.celulas_cabecalho = []
        elif nome == "col":
            # Mesmo raciocínio para estilo herdado da coluna.
            if "style" in atributos:
                raise _LeituraRapidaInvalida("estilo herdado da coluna")
        elif nome == "c":
            referencia = atributos.get("r")
            if not referencia:
                raise _LeituraRapidaInvalida("célula sem referência")
            self.coluna_celula = _coluna_da_referencia(referencia)
            # Depois do cabeçalho, células de outras colunas não precisam ser
            # convertidas: a leitura do XML continua, mas o valor é descartado.
            self.ignorar_celula = (
                self.cabecalho_lido and self.coluna_celula not in self.slots
            )
            self.tipo_celula = atributos.get("t")
            self.estilo_celula = atributos.get("s")
            self.valor_celula = None
            self.partes_texto = []
            self.texto = []
            self.dentro_de_valor = False
            self.dentro_de_string = False
            self.dentro_de_texto = False
            self.dentro_de_rph = False
        elif nome == "v":
            if not self.ignorar_celula:
                self.dentro_de_valor = True
                self.texto = []
        elif nome == "is":
            if not self.ignorar_celula:
                self.dentro_de_string = True
        elif nome == "rPh":
            self.dentro_de_rph = True
        elif nome == "t":
            if (
                self.dentro_de_string
                and not self.ignorar_celula
                and not self.dentro_de_rph
            ):
                self.dentro_de_texto = True
                self.texto = []

    def dados(self, texto: str) -> None:
        if (
            not self.ignorar_celula
            and not self.dentro_de_rph
            and (self.dentro_de_valor or self.dentro_de_texto)
        ):
            self.texto.append(texto)

    def end(self, nome: str) -> None:
        if nome == "v":
            if not self.ignorar_celula and self.dentro_de_valor:
                self.valor_celula = "".join(self.texto)
                self.dentro_de_valor = False
                self.texto = []
        elif nome == "t":
            if not self.ignorar_celula and self.dentro_de_texto:
                self.partes_texto.append("".join(self.texto))
                self.dentro_de_texto = False
                self.texto = []
        elif nome == "rPh":
            self.dentro_de_rph = False
        elif nome == "is":
            self.dentro_de_string = False
        elif nome == "c":
            self._fechar_celula()
        elif nome == "row":
            self._fechar_linha()

    # ── conversão de valores ───────────────────────────────────────────────
    def _converter(self):
        tipo = self.tipo_celula
        if tipo == "inlineStr":
            return "".join(self.partes_texto) if self.partes_texto else None

        texto = self.valor_celula
        if texto is None:
            return None
        if tipo == "s":
            try:
                return self.shared[int(texto)]
            except (ValueError, IndexError) as erro:
                raise _LeituraRapidaInvalida("sharedString inválida") from erro
        if tipo == "b":
            try:
                return bool(int(texto))
            except ValueError as erro:
                raise _LeituraRapidaInvalida("booleano inválido") from erro
        if tipo in ("e", "str"):
            return texto
        if tipo == "d":
            raise _LeituraRapidaInvalida("data ISO")
        if tipo not in (None, "n"):
            raise _LeituraRapidaInvalida(f"tipo de célula: {tipo}")
        if texto == "":
            return None
        if self.estilo_celula is not None:
            if int(self.estilo_celula) in self.estilos_data:
                raise _LeituraRapidaInvalida("número formatado como data")
        return _numero_da_celula(texto)

    def _fechar_celula(self) -> None:
        if self.ignorar_celula:
            self.coluna_celula = None
            self.ignorar_celula = False
            return
        if not self.cabecalho_lido:
            # No cabeçalho é preciso ler todas as células para localizar as
            # colunas que interessam.
            self.celulas_cabecalho.append(
                (self.coluna_celula, self._converter())
            )
        else:
            # Nas linhas de dados só as quatro colunas escolhidas são lidas.
            slot = self.slots.get(self.coluna_celula)
            if slot is not None:
                self.valores_linha[slot] = self._converter()
        self.coluna_celula = None

    def _fechar_linha(self) -> None:
        if not self.cabecalho_lido:
            if self.numero_linha not in (None, "1"):
                raise _LeituraRapidaInvalida("primeira linha não é a 1")
            nomes = sorted(
                (coluna, valor)
                for coluna, valor in self.celulas_cabecalho
                if valor is not None
            )
            self.indices[0] = _indice_da_coluna(nomes, ("fornecedor",))
            self.indices[1] = _indice_da_coluna(nomes, ("valor",))
            self.indices[2] = _indice_da_coluna(
                nomes,
                ("bloqueio", "bloqueio de pagamento", "blp", "bip", "bloq"),
            )
            self.indices[3] = _indice_da_coluna(nomes, ("tipo",))
            self.slots = {
                coluna: slot
                for slot, coluna in enumerate(self.indices)
                if coluna is not None
            }
            self.cabecalho_lido = True
            self.celulas_cabecalho = []
        else:
            for slot in self.slots.values():
                self.listas[slot].append(self.valores_linha[slot])
            self.valores_linha = []
        self.numero_linha = None

    def resultado(self) -> dict[str, list]:
        if not self.cabecalho_lido:
            return {}
        return {
            nome: self.listas[slot]
            for slot, nome in enumerate(
                ("Fornecedor", "Valor", "Bloqueio", "Tipo")
            )
            if self.indices[slot] is not None
        }


def _ler_aba_rapida(
    arquivo, shared: list[str], estilos_data: set[int]
) -> dict[str, list]:
    aba = _AbaXlsx(shared, estilos_data)
    parser = xml.parsers.expat.ParserCreate()
    parser.StartElementHandler = aba.start
    parser.EndElementHandler = aba.end
    parser.CharacterDataHandler = aba.dados
    parser.ParseFile(arquivo)
    return aba.resultado()


def _ler_relatorio_rapido(caminho: Path) -> RelatorioInfo:
    """Lê o ``.xlsx`` sem passar pelo DataFrame completo do pandas."""
    with zipfile.ZipFile(caminho) as arquivo_zip:
        shared: list[str] = []
        try:
            raiz = ET.fromstring(arquivo_zip.read("xl/sharedStrings.xml"))
            shared = [
                _texto_do_xml(item)
                for item in raiz
                if item.tag == _XLSX_NS + "si"
            ]
        except KeyError:
            pass

        estilos_data = _estilos_com_formato_de_data(arquivo_zip)

        workbook = ET.fromstring(arquivo_zip.read("xl/workbook.xml"))
        relacoes = ET.fromstring(
            arquivo_zip.read("xl/_rels/workbook.xml.rels")
        )
        alvo_por_id = {
            relacao.get("Id"): relacao.get("Target") for relacao in relacoes
        }

        folhas: list[str] = []
        for folha in workbook.find(_XLSX_NS + "sheets"):
            alvo = alvo_por_id[folha.get(_XLSX_REL_NS + "id")]
            if alvo.startswith("/"):
                alvo = alvo.lstrip("/")
            else:
                alvo = posixpath.join("xl", alvo)
            alvo = posixpath.normpath(alvo)
            if not alvo.startswith("xl/worksheets/"):
                raise _LeituraRapidaInvalida("aba não é worksheet")
            folhas.append(alvo)

        def abas():
            for alvo in folhas:
                with arquivo_zip.open(alvo) as arquivo_aba:
                    dados = _ler_aba_rapida(
                        arquivo_aba, shared, estilos_data
                    )
                if dados:
                    yield pd.DataFrame(dados, dtype=object)

        return _agregar_abas(abas(), caminho)


def _agregar_abas(
    abas: Iterable[pd.DataFrame], caminho: Path
) -> RelatorioInfo:
    """Agrega fornecedores, bloqueios e CFD a partir das abas já lidas.

    A lógica é a mesma para o caminho rápido e para o pandas: os valores de
    bloqueio e de CFD (documentos ``KT``) são somados em módulo, porque o
    e-mail informa ao transportador a quantia efetiva, sempre positiva.
    """
    encontrados: set[str] = set()
    documentos_bloqueados = 0
    valor_bloqueado = 0.0
    documentos_cfd = 0
    valor_cfd = 0.0

    for df in abas:
        if df is None or df.empty:
            continue

        coluna_fornecedor = _coluna_por_nome(df, ("fornecedor",))
        if coluna_fornecedor is not None:
            for valor in df[coluna_fornecedor]:
                codigo = normalizar_fornecedor(valor)
                if codigo:
                    encontrados.add(codigo)

        coluna_valor = _coluna_por_nome(df, ("valor",))
        if coluna_valor is not None:
            valores = (
                pd.to_numeric(df[coluna_valor], errors="coerce")
                .fillna(0.0)
                .abs()
            )
        else:
            valores = pd.Series(0.0, index=df.index)

        coluna_bloqueio = _coluna_por_nome(
            df, ("bloqueio", "bloqueio de pagamento", "blp", "bip", "bloq")
        )
        if coluna_bloqueio is not None:
            mascara_bloqueio = df[coluna_bloqueio].map(_bloqueado)
            documentos_bloqueados += int(mascara_bloqueio.sum())
            valor_bloqueado += float(valores[mascara_bloqueio].sum())

        coluna_tipo = _coluna_por_nome(df, ("tipo",))
        if coluna_tipo is not None:
            mascara_kt = (
                df[coluna_tipo].astype(str).str.strip().str.upper().eq("KT")
            )
            documentos_cfd += int(mascara_kt.sum())
            valor_cfd += float(valores[mascara_kt].sum())

    return RelatorioInfo(
        caminho=caminho,
        fornecedores=tuple(sorted(encontrados)),
        documentos_bloqueados=documentos_bloqueados,
        valor_bloqueado=valor_bloqueado,
        documentos_cfd=documentos_cfd,
        valor_cfd=valor_cfd,
    )


def _ler_relatorio(caminho: Path) -> RelatorioInfo:
    """Lê todas as abas do ``.xlsx`` e agrega fornecedores, bloqueios e CFD.

    A coluna ``Fornecedor`` é procurada pelo cabeçalho (linha 1) de cada aba;
    linhas em branco (como a de SUBTOTAL) são ignoradas. O caminho rápido é
    tentado primeiro; se o arquivo tiver qualquer estrutura não prevista, a
    leitura é refeita pelo pandas, exatamente como antes.
    """
    try:
        return _ler_relatorio_rapido(caminho)
    except Exception:  # noqa: BLE001 - qualquer desvio volta ao caminho seguro
        pass

    try:
        abas = pd.read_excel(caminho, sheet_name=None, dtype=object)
    except Exception as erro:  # noqa: BLE001 - mensagem amigável
        raise EnvioError(
            f"Não foi possível ler o relatório:\n{caminho}\n\n"
            f"Detalhe técnico: {erro}"
        ) from erro

    return _agregar_abas((abas or {}).values(), caminho)


# ---------------------------------------------------------------------------
# Plano de envios
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GrupoEnvio:
    """Um e-mail que será montado para um arquivo/transportadora."""

    arquivo: Path
    fornecedores: tuple[str, ...]
    fornecedor_chave: str
    nome: str
    para: tuple[str, ...]
    assunto: str
    corpo: str
    status: str
    detalhe: str = ""
    emails_invalidos: tuple[str, ...] = ()
    documentos_bloqueados: int = 0
    valor_bloqueado: float = 0.0
    documentos_cfd: int = 0
    valor_cfd: float = 0.0

    @property
    def chave(self) -> str:
        """Chave única do grupo (o caminho do arquivo)."""
        return str(self.arquivo)

    @property
    def pronto(self) -> bool:
        """Indica se o grupo tem uma única transportadora e destinatário válido."""
        return self.status == "pronto" and bool(self.para)

    @property
    def tem_avisos(self) -> bool:
        """Indica se o e-mail levará aviso de bloqueio e/ou de CFD."""
        return self.documentos_bloqueados > 0 or self.documentos_cfd > 0

    @property
    def resumo_avisos(self) -> str:
        """Resumo dos avisos para a tabela de revisão antes do envio."""
        partes: list[str] = []
        if self.documentos_bloqueados:
            partes.append(
                f"{formatar_quantidade(self.documentos_bloqueados)} bloqueio(s) — "
                f"{formatar_moeda(self.valor_bloqueado)}"
            )
        if self.documentos_cfd:
            partes.append(
                f"CFD — {formatar_moeda(self.valor_cfd)} "
                f"({formatar_quantidade(self.documentos_cfd)} KT)"
            )
        return " · ".join(partes)

    @property
    def rotulo_status(self) -> str:
        """Texto amigável da situação do grupo."""
        return {
            "pronto": "Pronto para envio",
            "sem_contato": "Fornecedor sem contato",
            "sem_email": "Contato sem e-mail",
            "email_invalido": "E-mail inválido",
            "sem_fornecedor": "Sem fornecedor no arquivo",
            "multi_fornecedor": "Transportadoras diferentes",
        }.get(self.status, self.status)


@dataclass
class PlanoEnvios:
    """Resultado do cruzamento entre contatos, arquivos e modelos."""

    grupos: list[GrupoEnvio] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def prontos(self) -> list[GrupoEnvio]:
        """Grupos que podem ser enviados agora."""
        return [grupo for grupo in self.grupos if grupo.pronto]

    @property
    def nao_encontrados(self) -> list[GrupoEnvio]:
        """Grupos que não podem ser enviados, por qualquer motivo."""
        return [grupo for grupo in self.grupos if not grupo.pronto]

    def resumo(self) -> str:
        """Resumo curto para a interface."""
        por_status: dict[str, int] = {}
        for grupo in self.grupos:
            por_status[grupo.status] = por_status.get(grupo.status, 0) + 1
        partes = [f"{len(self.grupos)} arquivo(s)"]
        partes.append(f"{len(self.prontos)} pronto(s)")
        for status in (
            "sem_contato",
            "sem_email",
            "email_invalido",
            "sem_fornecedor",
            "multi_fornecedor",
        ):
            total = por_status.get(status, 0)
            if total:
                partes.append(f"{total} {_ROTULO_RESUMO.get(status, status)}")
        return " · ".join(partes)


_ROTULO_RESUMO = {
    "sem_contato": "sem contato",
    "sem_email": "sem e-mail",
    "email_invalido": "com e-mail inválido",
    "sem_fornecedor": "sem fornecedor",
    "multi_fornecedor": "com transportadoras diferentes",
}


def montar_plano(
    contatos_path: str | Path,
    pasta_relatorios: str | Path,
    assunto: str | None = None,
    corpo: str | None = None,
) -> PlanoEnvios:
    """Cruza contatos e arquivos e devolve todos os grupos de envio.

    Um mesmo transportador pode ter **vários** códigos de fornecedor. O arquivo
    pode conter todos esses códigos; o que não pode é reunir códigos de
    transportadoras diferentes. Arquivos sem código ou com mais de uma
    transportadora entram como grupos bloqueados
    (``sem_fornecedor``/``multi_fornecedor``).
    """
    assunto_template = DEFAULT_ASSUNTO if not assunto else assunto
    corpo_template = DEFAULT_CORPO if not corpo else corpo

    contatos = ler_contatos(contatos_path)
    por_transportadora = _contatos_por_transportadora(contatos)
    relatorios = localizar_relatorios(pasta_relatorios, ignorar=[contatos_path])

    grupos: list[GrupoEnvio] = []
    for relatorio in relatorios:
        codigos = relatorio.fornecedores
        if not codigos:
            status = "sem_fornecedor"
            chave = ""
            para: tuple[str, ...] = ()
            invalidos: tuple[str, ...] = ()
            nome = ""
            detalhe = (
                "Nenhuma coluna 'Fornecedor' com dados foi encontrada nas abas."
            )
            grupos.append(
                _novo_grupo(
                    relatorio, chave, nome, para, invalidos, status, detalhe,
                    assunto_template, corpo_template,
                )
            )
            continue

        # Procv código → Transportadora para cada código presente no arquivo.
        faltantes: list[str] = []
        nomes: dict[str, str] = {}
        for codigo in codigos:
            contato = contatos.get(codigo)
            if contato is None:
                faltantes.append(codigo)
                continue
            nomes.setdefault(normalizar_chave(contato.nome), contato.nome)

        if faltantes:
            status = "sem_contato"
            para = ()
            invalidos = ()
            nome = next(iter(nomes.values())) if len(nomes) == 1 else ""
            detalhe = (
                "Fornecedor(es) não encontrado(s) na planilha de contatos: "
                + ", ".join(faltantes)
            )
        elif len(nomes) > 1:
            status = "multi_fornecedor"
            para = ()
            invalidos = ()
            nome = ""
            detalhe = (
                "Transportadoras encontradas: "
                + ", ".join(sorted(nomes.values()))
                + " — um mesmo arquivo não pode reunir transportadoras "
                "diferentes nesta etapa de envio."
            )
        else:
            nome = next(iter(nomes.values()))
            contato = por_transportadora.get(normalizar_chave(nome))
            if contato is None:
                # Não deve ocorrer (o código veio de um contato), mas evita
                # quebrar o plano caso a Transportadora esteja vazia.
                status = "sem_contato"
                para = ()
                invalidos = ()
                detalhe = (
                    f"Transportadora do(s) fornecedor(es) {', '.join(codigos)} "
                    "não encontrada na planilha de contatos."
                )
            elif contato.emails:
                status = "pronto"
                para = contato.emails
                invalidos = contato.emails_invalidos
                detalhe = ""
                if invalidos:
                    detalhe = "E-mails inválidos ignorados: " + ", ".join(invalidos)
            elif contato.emails_invalidos:
                status = "email_invalido"
                para = ()
                invalidos = contato.emails_invalidos
                detalhe = (
                    "Nenhum e-mail válido no cadastro: " + ", ".join(invalidos)
                )
            else:
                status = "sem_email"
                para = ()
                invalidos = ()
                detalhe = "A transportadora está cadastrada, mas sem e-mail."

        chave = codigos[0] if len(codigos) == 1 else ", ".join(codigos)
        grupos.append(
            _novo_grupo(
                relatorio, chave, nome, para, invalidos, status, detalhe,
                assunto_template, corpo_template,
            )
        )

    plano = PlanoEnvios(grupos=grupos)
    if not grupos:
        plano.avisos.append(
            "Nenhum arquivo .xlsx foi encontrado na pasta selecionada."
        )
    return plano


def _novo_grupo(
    relatorio: RelatorioInfo,
    chave: str,
    nome: str,
    para: tuple[str, ...],
    invalidos: tuple[str, ...],
    status: str,
    detalhe: str,
    assunto_template: str,
    corpo_template: str,
) -> GrupoEnvio:
    """Monta um :class:`GrupoEnvio` já com assunto/corpo renderizados."""
    corpo = renderizar_template(corpo_template, nome)
    corpo = _aplicar_avisos(corpo, relatorio)
    return GrupoEnvio(
        arquivo=relatorio.caminho,
        fornecedores=relatorio.fornecedores,
        fornecedor_chave=chave,
        nome=nome,
        para=para,
        assunto=renderizar_template(assunto_template, nome),
        corpo=corpo,
        status=status,
        detalhe=detalhe,
        emails_invalidos=invalidos,
        documentos_bloqueados=relatorio.documentos_bloqueados,
        valor_bloqueado=relatorio.valor_bloqueado,
        documentos_cfd=relatorio.documentos_cfd,
        valor_cfd=relatorio.valor_cfd,
    )


def _aplicar_avisos(corpo: str, relatorio: RelatorioInfo) -> str:
    """Insere os avisos de bloqueio/CFD antes da despedida do e-mail.

    O corpo padrão (ou o corpo editado pelo usuário) é preservado; apenas
    ganha um parágrafo extra quando o arquivo tem documento bloqueado e/ou
    documento ``KT``. A inserção acontece antes de "Atenciosamente"/"Att.".
    """
    avisos: list[str] = []

    if relatorio.documentos_bloqueados:
        valor = formatar_moeda(relatorio.valor_bloqueado)
        if relatorio.documentos_bloqueados == 1:
            avisos.append(
                f"Informamos que 1 documento está com bloqueio, "
                f"no valor de {valor}."
            )
        else:
            avisos.append(
                f"Informamos que "
                f"{formatar_quantidade(relatorio.documentos_bloqueados)} "
                f"documentos estão com bloqueio, totalizando {valor}."
            )

    if relatorio.documentos_cfd:
        valor = formatar_moeda(relatorio.valor_cfd)
        if relatorio.documentos_cfd == 1:
            avisos.append(
                f"O valor total de CFD (Confissão de Dívida) é de {valor}, "
                f"referente a 1 documento do tipo KT."
            )
        else:
            avisos.append(
                f"O valor total de CFD (Confissão de Dívida) é de {valor}, "
                f"referente a "
                f"{formatar_quantidade(relatorio.documentos_cfd)} "
                f"documentos do tipo KT."
            )

    if not avisos:
        return corpo

    bloco = "\n\n".join(avisos)
    despedida = re.search(
        r"(?im)^[ \t]*(atenciosamente|cordialmente|att\.?|abraços|abracos|"
        r"obrigado)[ \t]*,?[ \t]*$",
        corpo,
    )
    if despedida is not None:
        inicio = despedida.start()
        return f"{corpo[:inicio].rstrip()}\n\n{bloco}\n\n{corpo[inicio:]}"
    return f"{corpo.rstrip()}\n\n{bloco}"


def _contatos_por_transportadora(
    contatos: dict[str, Contato],
) -> dict[str, Contato]:
    """Consolida os contatos pela Transportadora (vários códigos → um nome).

    Como um transportador pode ter vários códigos de fornecedor, os e-mails de
    todas as linhas com o mesmo Nome Simples são unidos. A chave do dicionário
    é a versão normalizada do nome.
    """
    agrupados: dict[str, Contato] = {}
    for contato in contatos.values():
        chave = normalizar_chave(contato.nome)
        if not chave:
            continue
        existente = agrupados.get(chave)
        if existente is None:
            agrupados[chave] = contato
            continue
        agrupados[chave] = Contato(
            nome=existente.nome,
            emails=_unir_unicos(existente.emails, contato.emails),
            emails_invalidos=_unir_unicos(
                existente.emails_invalidos, contato.emails_invalidos
            ),
        )
    return agrupados


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------
@dataclass
class EnvioResultado:
    """Resultado de uma rodada de envios."""

    enviados: list[GrupoEnvio] = field(default_factory=list)
    falhos: list[GrupoEnvio] = field(default_factory=list)
    nao_encontrados: list[GrupoEnvio] = field(default_factory=list)
    ignorados: list[GrupoEnvio] = field(default_factory=list)
    cancelado: bool = False
    duracao_segundos: float = 0.0

    @property
    def total(self) -> int:
        """Quantidade de grupos considerados na rodada."""
        return (
            len(self.enviados)
            + len(self.falhos)
            + len(self.nao_encontrados)
            + len(self.ignorados)
        )


SenderFactory = Callable[[], object]


def enviar_plano(
    plano: PlanoEnvios,
    chaves: Sequence[str] | Iterable[str],
    sender_factory: SenderFactory | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
    on_log: Callable[[str, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> EnvioResultado:
    """Envia os grupos selecionados, um e-mail por arquivo.

    Falhas individuais não interrompem os demais envios. Grupos sem um único
    fornecedor/e-mail válido entram em ``nao_encontrados`` e nunca acionam o
    Outlook.
    """
    iniciado = time.monotonic()
    resultado = EnvioResultado()
    selecionadas = {str(chave) for chave in chaves}
    selecionados = [
        grupo for grupo in plano.grupos if grupo.chave in selecionadas
    ]
    prontos = [grupo for grupo in selecionados if grupo.pronto]
    total = len(prontos)

    for grupo in selecionados:
        if not grupo.pronto:
            resultado.nao_encontrados.append(grupo)
            _log(
                on_log,
                f"NÃO ENCONTRADO: {grupo.arquivo.name} — {grupo.rotulo_status}"
                + (f" ({grupo.detalhe})" if grupo.detalhe else ""),
                "warning",
            )

    if not prontos:
        resultado.duracao_segundos = time.monotonic() - iniciado
        _log(
            on_log,
            "Nenhum grupo pronto para envio. Nada foi disparado.",
            "warning",
        )
        return resultado

    fabrica = sender_factory or OutlookSender
    try:
        sender = fabrica()
    except Exception as erro:  # noqa: BLE001 - falha ao abrir o Outlook
        mensagem = _mensagem_sender(erro)
        for grupo in prontos:
            resultado.falhos.append(grupo)
            _log(on_log, f"FALHA: {grupo.arquivo.name} — {mensagem}", "error")
        resultado.duracao_segundos = time.monotonic() - iniciado
        return resultado

    try:
        for indice, grupo in enumerate(prontos, start=1):
            if should_cancel is not None and should_cancel():
                resultado.cancelado = True
                resultado.ignorados.extend(prontos[indice - 1 :])
                _log(
                    on_log,
                    "Envio cancelado pelo usuário. Os e-mails restantes não "
                    "foram disparados.",
                    "warning",
                )
                break

            try:
                sender.enviar(grupo)
            except Exception as erro:  # noqa: BLE001 - continua os demais
                resultado.falhos.append(grupo)
                _log(
                    on_log,
                    f"FALHA: {grupo.arquivo.name} — {_mensagem_sender(erro)}",
                    "error",
                )
            else:
                resultado.enviados.append(grupo)
                _log(
                    on_log,
                    f"ENVIADO: {grupo.nome} — {', '.join(grupo.para)}",
                    "success",
                )

            if on_progress is not None:
                on_progress(indice, total, grupo.nome)

    finally:
        try:
            sender.fechar()
        except Exception:  # noqa: BLE001 - encerramento best-effort
            pass

    resultado.duracao_segundos = time.monotonic() - iniciado
    return resultado


class OutlookSender:
    """Remetente real: cria e dispara cada e-mail pelo Outlook Desktop."""

    def __init__(self) -> None:
        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]
        except Exception as erro:  # noqa: BLE001 - dependência opcional
            raise EnvioError(
                "O Outlook Desktop não está disponível neste computador.\n\n"
                "Instale o Microsoft Outlook e o pacote pywin32 para enviar "
                f"os e-mails.\n\nDetalhe técnico: {erro}"
            ) from erro

        self._pythoncom = pythoncom
        self._win32 = win32com.client
        self._inicializado = False
        try:
            pythoncom.CoInitialize()
            self._inicializado = True
            self._outlook = win32com.client.Dispatch("outlook.application")
        except Exception as erro:  # noqa: BLE001
            if self._inicializado:
                try:
                    pythoncom.CoUninitialize()
                except Exception:  # noqa: BLE001
                    pass
            raise EnvioError(
                "Não foi possível abrir o Outlook Desktop.\n\n"
                "Verifique se o Outlook está instalado, aberto e com o perfil "
                f"de e-mail configurado.\n\nDetalhe técnico: {erro}"
            ) from erro

    def enviar(self, grupo: GrupoEnvio) -> None:
        """Cria o e-mail do grupo, anexa o arquivo e o envia imediatamente."""
        if not grupo.arquivo.is_file():
            raise EnvioError(f"O arquivo anexo não existe mais:\n{grupo.arquivo}")
        item = self._outlook.CreateItem(0)
        item.To = "; ".join(grupo.para)
        item.Subject = grupo.assunto
        item.HTMLBody = corpo_para_html(grupo.corpo)
        item.Attachments.Add(str(grupo.arquivo))
        item.Send()

    def fechar(self) -> None:
        """Encerra o COM do thread atual."""
        if not self._inicializado:
            return
        try:
            self._pythoncom.CoUninitialize()
        finally:
            self._inicializado = False


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def _achar_coluna(
    colunas: dict[str, object], palavra: str, excluir: tuple[str, ...] = ()
) -> object | None:
    """Encontra uma coluna pelo nome normalizado, com sinônimos tolerantes."""
    if palavra in colunas:
        return colunas[palavra]
    for chave in colunas:
        if palavra in chave and not any(ex in chave for ex in excluir):
            return colunas[chave]
    return None


def _coluna_por_nome(df: pd.DataFrame, nomes: tuple[str, ...]) -> object | None:
    """Localiza uma coluna do relatório por nome normalizado.

    Tenta primeiro a igualdade exata (ex.: ``valor``, ``bloqueio``) e, se não
    encontrar, aceita o nome contido no cabeçalho (ex.: ``bloqueio de
    pagamento``). Serve tanto para ``BlP``/``BIP`` quanto para os títulos já
    amigáveis do ``.xlsx`` gerado pelo PagFlow.
    """
    colunas = list(df.columns)

    for coluna in colunas:
        if normalizar_chave(coluna) in nomes:
            return coluna

    for coluna in colunas:
        chave = normalizar_chave(coluna)
        if any(nome in chave for nome in nomes):
            return coluna

    return None


def _achar_coluna_transportadora(colunas: dict[str, object]) -> object | None:
    """Localiza a coluna ``Transportadora`` (que guarda o Nome Simples).

    Aceita também ``Nome Simples`` como sinônimo, mas nunca confunde a coluna
    com ``Fornecedor``/``E-mail``.
    """
    for chave in ("transportadora", "transportadoras", "nome simples"):
        if chave in colunas:
            return colunas[chave]
    for chave in colunas:
        if "transportadora" in chave:
            return colunas[chave]
    return None


def _achar_coluna_email(colunas: dict[str, object]) -> object | None:
    for chave in ("e-mail", "email", "e mail", "e-mails", "emails"):
        if chave in colunas:
            return colunas[chave]
    for chave in colunas:
        if "mail" in chave:
            return colunas[chave]
    return None


def _unir_unicos(existentes: Iterable[str], novos: Iterable[str]) -> tuple[str, ...]:
    vistos = {item.lower() for item in existentes}
    resultado = list(existentes)
    for item in novos:
        if item.lower() in vistos:
            continue
        vistos.add(item.lower())
        resultado.append(item)
    return tuple(resultado)


def _log(
    callback: Callable[[str, str], None] | None, mensagem: str, nivel: str
) -> None:
    if callback is not None:
        callback(mensagem, nivel)


def _mensagem_sender(erro: BaseException) -> str:
    if isinstance(erro, EnvioError):
        return str(erro)
    return f"Erro inesperado: {erro}"
