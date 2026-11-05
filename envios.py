"""Lógica de envio dos relatórios PagFlow por fornecedor (via Outlook).

Este módulo é independente da interface gráfica e do Outlook na importação:
a automação COM do Outlook só acontece quando um envio real é executado.

Fluxo principal:

1. :func:`ler_contatos` lê a planilha de contatos (``Fornecedor`` + ``Nome`` +
   ``E-mail(s)``) e consolida cada fornecedor com seu *Nome Simples*;
2. :func:`localizar_relatorios` varre a pasta e, para cada ``.xlsx``, localiza
   a coluna ``Fornecedor`` em **todas** as abas;
3. :func:`montar_plano` cruza os dois lados e monta um :class:`PlanoEnvios`
   (um grupo por arquivo — logo, um arquivo não pode conter dois fornecedores
   diferentes nesta etapa);
4. :func:`enviar_plano` envia os grupos selecionados, um e-mail por arquivo,
   com o relatório anexado.

O envio real usa o Outlook Desktop via ``pywin32``. Para testes,
:func:`enviar_plano` aceita um ``sender_factory`` que devolve qualquer objeto
com ``enviar(grupo)`` e ``fechar()``.
"""

from __future__ import annotations

import html as _html
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

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
Equipe Financeira"""

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SEPARADORES_RE = re.compile(r"[;,\s]+")
_ESPACOS_RE = re.compile(r"\s+")
_NUM_RE = re.compile(r"^(\d+)(?:[.,]0+)?$")


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
    """Contato consolidado de um fornecedor (Nome Simples + e-mails)."""

    nome: str
    emails: tuple[str, ...]
    emails_invalidos: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelatorioInfo:
    """Um ``.xlsx`` encontrado na pasta e os fornecedores que ele contém."""

    caminho: Path
    fornecedores: tuple[str, ...]


def ler_contatos(caminho: str | Path) -> dict[str, Contato]:
    """Lê a planilha de contatos e consolida por código de fornecedor.

    Aceita variações de caixa e sinônimos nas colunas (``Fornecedor``, ``Nome``,
    ``E-mail``/``E-mails``). E-mails repetidos são removidos e os inválidos
    ficam separados para que a interface possa avisar sem bloquear os bons.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        raise EnvioError(
            f"Planilha de contatos não encontrada:\n{caminho}\n\n"
            "Escolha o arquivo .xlsx com as colunas 'Fornecedor', 'Nome' e "
            "'E-mail(s)'."
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
        colunas, "fornecedor", excluir=("nome",)
    )
    coluna_nome = _achar_coluna(colunas, "nome", excluir=("fornecedor",))
    coluna_email = _achar_coluna_email(colunas)

    if coluna_fornecedor is None or coluna_nome is None or coluna_email is None:
        encontradas = ", ".join(str(c) for c in dataframe.columns)
        raise EnvioError(
            "A planilha de contatos precisa das colunas 'Fornecedor', 'Nome' e "
            "'E-mail(s)'.\n\n"
            f"Colunas encontradas: {encontradas or '(nenhuma)'}"
        )

    contatos: dict[str, Contato] = {}
    for _, linha in dataframe.iterrows():
        codigo = normalizar_fornecedor(linha[coluna_fornecedor])
        if not codigo:
            continue
        nome_bruto = linha[coluna_nome]
        if _vazio(nome_bruto):
            continue
        nome = str(nome_bruto).strip()

        emails = dividir_emails(linha[coluna_email])
        validos = tuple(email for email in emails if validar_email(email))
        invalidos = tuple(email for email in emails if not validar_email(email))

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
        relatorios.append(
            RelatorioInfo(
                caminho=caminho,
                fornecedores=_fornecedores_do_arquivo(caminho),
            )
        )
    return relatorios


def _fornecedores_do_arquivo(caminho: Path) -> tuple[str, ...]:
    """Lê todas as abas do ``.xlsx`` e devolve os códigos de fornecedor únicos.

    A coluna ``Fornecedor`` é procurada pelo cabeçalho (linha 1) de cada aba;
    linhas em branco (como a de SUBTOTAL) são ignoradas.
    """
    try:
        abas = pd.read_excel(caminho, sheet_name=None, dtype=object)
    except Exception as erro:  # noqa: BLE001 - mensagem amigável
        raise EnvioError(
            f"Não foi possível ler o relatório:\n{caminho}\n\n"
            f"Detalhe técnico: {erro}"
        ) from erro

    encontrados: set[str] = set()
    for _nome_aba, df in (abas or {}).items():
        if df is None or df.empty:
            continue
        coluna = next(
            (
                col
                for col in df.columns
                if normalizar_chave(col) == "fornecedor"
            ),
            None,
        )
        if coluna is None:
            continue
        for valor in df[coluna]:
            codigo = normalizar_fornecedor(valor)
            if codigo:
                encontrados.add(codigo)
    return tuple(sorted(encontrados))


# ---------------------------------------------------------------------------
# Plano de envios
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GrupoEnvio:
    """Um e-mail que será montado para um arquivo/fornecedor."""

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

    @property
    def chave(self) -> str:
        """Chave única do grupo (o caminho do arquivo)."""
        return str(self.arquivo)

    @property
    def pronto(self) -> bool:
        """Indica se o grupo tem um único fornecedor e destinatário válido."""
        return self.status == "pronto" and bool(self.para)

    @property
    def rotulo_status(self) -> str:
        """Texto amigável da situação do grupo."""
        return {
            "pronto": "Pronto para envio",
            "sem_contato": "Fornecedor sem contato",
            "sem_email": "Contato sem e-mail",
            "email_invalido": "E-mail inválido",
            "sem_fornecedor": "Sem fornecedor no arquivo",
            "multi_fornecedor": "Múltiplos fornecedores",
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
    "multi_fornecedor": "com múltiplos fornecedores",
}


def montar_plano(
    contatos_path: str | Path,
    pasta_relatorios: str | Path,
    assunto: str | None = None,
    corpo: str | None = None,
) -> PlanoEnvios:
    """Cruza contatos e arquivos e devolve todos os grupos de envio.

    Um arquivo deve conter exatamente **um** fornecedor para poder ser enviado;
    arquivos com zero ou múltiplos fornecedores entram como grupos bloqueados
    (``sem_fornecedor``/``multi_fornecedor``).
    """
    assunto_template = DEFAULT_ASSUNTO if not assunto else assunto
    corpo_template = DEFAULT_CORPO if not corpo else corpo

    contatos = ler_contatos(contatos_path)
    relatorios = localizar_relatorios(pasta_relatorios, ignorar=[contatos_path])

    grupos: list[GrupoEnvio] = []
    for relatorio in relatorios:
        quantidade = len(relatorio.fornecedores)
        if quantidade == 0:
            status = "sem_fornecedor"
            chave = ""
            para: tuple[str, ...] = ()
            invalidos: tuple[str, ...] = ()
            nome = ""
            detalhe = (
                "Nenhuma coluna 'Fornecedor' com dados foi encontrada nas abas."
            )
        elif quantidade > 1:
            status = "multi_fornecedor"
            chave = ""
            para = ()
            invalidos = ()
            nome = ""
            detalhe = (
                "Fornecedores encontrados: " + ", ".join(relatorio.fornecedores)
                + " — não pode haver dois fornecedores diferentes num mesmo "
                "arquivo nesta etapa de envio."
            )
        else:
            chave = relatorio.fornecedores[0]
            contato = contatos.get(chave)
            if contato is None:
                status = "sem_contato"
                para = ()
                invalidos = ()
                nome = ""
                detalhe = (
                    f"Fornecedor {chave} não encontrado na planilha de contatos."
                )
            elif contato.emails:
                status = "pronto"
                para = contato.emails
                invalidos = contato.emails_invalidos
                nome = contato.nome
                detalhe = ""
                if invalidos:
                    detalhe = "E-mails inválidos ignorados: " + ", ".join(invalidos)
            elif contato.emails_invalidos:
                status = "email_invalido"
                para = ()
                invalidos = contato.emails_invalidos
                nome = contato.nome
                detalhe = (
                    "Nenhum e-mail válido no cadastro: " + ", ".join(invalidos)
                )
            else:
                status = "sem_email"
                para = ()
                invalidos = ()
                nome = contato.nome
                detalhe = "O fornecedor está cadastrado, mas sem e-mail."

        grupos.append(
            GrupoEnvio(
                arquivo=relatorio.caminho,
                fornecedores=relatorio.fornecedores,
                fornecedor_chave=chave,
                nome=nome,
                para=para,
                assunto=renderizar_template(assunto_template, nome),
                corpo=renderizar_template(corpo_template, nome),
                status=status,
                detalhe=detalhe,
                emails_invalidos=invalidos,
            )
        )

    plano = PlanoEnvios(grupos=grupos)
    if not grupos:
        plano.avisos.append(
            "Nenhum arquivo .xlsx foi encontrado na pasta selecionada."
        )
    return plano


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
