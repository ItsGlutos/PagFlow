"""
PagFlow · interface gráfica (PyQt6)
────────────────────────────────────────────────────────────────────────────────
Camada puramente visual. O fluxo operacional continua em ope.py / funcoes.py e
é acionado exatamente como antes (executar(pasta, destino, nome, separar, cor,
cb_status)) — nada de regra de negócio mora neste arquivo.

Dois temas completos:
  • escuro  → céu noturno azul-marinho com estrelinhas azuis que crescem e
              diminuem (campo de estrelas animado, pintado à mão em QPainter)
  • claro   → céu diurno, mesma estrutura, destaque em azul-celeste

Quatro temas secretos, ativados por código (uma palavra cada) na aba
“Inserir código” das Configurações. Eles não têm variante clara/escura: são
uma direção visual única. O botão “Restaurar padrão” devolve o PagFlow
original (escuro), com o alternador escuro↔claro de volta.

A troca de tema preserva geometria, proporções e estados: só os tokens mudam.
"""

from __future__ import annotations

import math
import os
import random
import sys
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve, QElapsedTimer, QEvent, QPoint, QPointF, QPropertyAnimation,
    QRect, QRectF, QSettings, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontDatabase, QFontMetrics, QGuiApplication, QIcon,
    QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QAbstractButton, QAbstractItemView, QApplication, QButtonGroup, QDialog,
    QFileDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QStackedWidget, QTableWidget,
    QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from temas_extra import EXTRA_THEMES as _EXTRA_THEME_DATA

TAU = math.tau


# ══════════════════════════════════════════════════════════════════════════════
#  TOKENS DE TEMA
# ══════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class ThemeArt:
    """A “película” visual que não cabe nos tokens de cor.

    Fontes, motivos do logo, padrão de fundo, gradientes de estado e as
    transformações tipográficas (caixa alta, tracking). Tudo opcional: os
    campos vazios caem nos tokens do próprio ``Theme``.
    """

    is_light: bool = False
    secret_code: str = ""
    aliases: tuple[str, ...] = ()

    # tipografia
    display_font: str = "Segoe UI"
    ui_font: str = "Segoe UI"
    mono_font: str = "Consolas"
    section_font: str = ""
    button_font: str = ""
    status_font: str = ""
    status_size: int = 11
    status_transform: str = "none"       # none | uppercase
    status_tracking: float = 0.0         # em

    # marca
    brand_label: str = "PagFlow"
    brand_suffix: str = ""
    brand_suffix_style: str = "normal"   # normal | italic
    brand_suffix_color: str = ""
    brand_transform: str = "none"
    brand_tracking: float = 0.0
    brand_size: int = 16
    brand_dy: int = 0                    # respiro superior do título, em px

    # títulos de seção
    section_transform: str = "none"
    section_tracking: float = 0.0
    section_size: int = 11

    # botões
    button_transform: str = "none"
    button_tracking: float = 0.0
    button_size: int = 12

    # logo
    logo_motif: str = "sheet"            # sheet | flower | bolt | cherry | berry
    logo_from: str = ""
    logo_to: str = ""
    logo_mid: str = ""
    logo_mid_pos: float = 0.56
    logo_fg: str = ""
    logo_border: str = ""

    # fundo
    pattern: str = "plain"               # plain | stars | clouds | grain | paper | dotgrid

    # superfícies específicas
    primary_text: str = ""
    card_from: str = ""
    card_to: str = ""
    card_edge_from: str = ""
    card_edge_to: str = ""
    card_edge_height: int = 0
    card_alpha: float = 0.0
    card_edge_alpha: int = 255

    chip_from: str = ""
    chip_to: str = ""
    chip_fg: str = ""

    badge_bg: str = ""
    badge_fg: str = ""
    badge_border: str = ""
    badge_font: str = ""
    badge_transform: str = "none"
    badge_tracking: float = 0.0

    meta_font: str = ""
    meta_transform: str = "none"
    meta_tracking: float = 0.0

    status_bg: str = ""
    status_border: str = ""
    status_fg: str = ""
    status_dot: str = ""

    view_active_from: str = ""
    view_active_to: str = ""
    view_active_fg: str = ""
    view_active_border: str = ""

    seg_active_from: str = ""
    seg_active_to: str = ""
    seg_active_fg: str = ""
    seg_active_border: str = ""

    dialog_title_size: int = 23
    description: str = ""


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    # fundo
    bg_top: str
    bg_bottom: str
    glow: str
    glow_alpha: int
    # superfícies
    surface: str
    surface_alpha: float
    surface_alt: str
    border: str
    border_strong: str
    # texto
    text: str
    text_secondary: str
    text_muted: str
    # destaque
    accent: str
    accent_hover: str
    accent_pressed: str
    on_accent: str
    accent_soft: str
    accent_soft_text: str
    # campos
    field_bg: str
    field_focus: str
    field_border: str
    placeholder: str
    # estados da barra de status
    ok_bg: str
    ok_fg: str
    err_bg: str
    err_fg: str
    warn_bg: str
    warn_fg: str
    info_bg: str
    info_fg: str
    # botão primário (gradiente)
    primary_from: str
    primary_to: str
    primary_hover_from: str
    primary_hover_to: str
    primary_pressed_from: str
    primary_pressed_to: str
    # céu estrelado / sombras
    stars: bool
    shadow_alpha: int
    # película visual (fontes, motivos, padrões)
    art: ThemeArt = field(default_factory=ThemeArt)


DARK = Theme(
    key="dark",
    label="Escuro",
    bg_top="#091522",
    bg_bottom="#11263E",
    glow="#2D7DD2",
    glow_alpha=32,
    surface="#112236",
    surface_alpha=0.88,
    surface_alt="#162B44",
    border="#1B3A5C",
    border_strong="#2A567F",
    text="#E8F0FE",
    text_secondary="#94B4D4",
    text_muted="#6F8CAB",
    accent="#2C77C6",
    accent_hover="#3A89DA",
    accent_pressed="#22609C",
    on_accent="#FFFFFF",
    accent_soft="#16324F",
    accent_soft_text="#9CC7FF",
    field_bg="#0A1828",
    field_focus="#0C1E33",
    field_border="#1B3A5C",
    placeholder="#7694B4",
    ok_bg="#12331F",
    ok_fg="#7EE2A8",
    err_bg="#3A1618",
    err_fg="#FF9E9E",
    warn_bg="#3A2E12",
    warn_fg="#FFD479",
    info_bg="#14273D",
    info_fg="#B7CFEA",
    primary_from="#2C77C6",
    primary_to="#23629F",
    primary_hover_from="#3585D8",
    primary_hover_to="#2A6FBA",
    primary_pressed_from="#23629F",
    primary_pressed_to="#1D5590",
    stars=True,
    shadow_alpha=0,
    art=ThemeArt(pattern="stars"),
)

LIGHT = Theme(
    key="light",
    label="Claro",
    bg_top="#E7F2FD",
    bg_bottom="#FBFDFF",
    glow="#FFFFFF",
    glow_alpha=150,
    surface="#FFFFFF",
    surface_alpha=0.96,
    surface_alt="#F1F8FE",
    border="#D9E8F6",
    border_strong="#BED8EC",
    text="#0B2540",
    text_secondary="#4B6A87",
    text_muted="#6F8CA6",
    accent="#0EA5E9",
    accent_hover="#38BDF8",
    accent_pressed="#0284C7",
    on_accent="#062338",
    accent_soft="#E0F2FE",
    accent_soft_text="#0369A1",
    field_bg="#FFFFFF",
    field_focus="#FFFFFF",
    field_border="#D5E5F5",
    placeholder="#8AA6BF",
    ok_bg="#E7F8EF",
    ok_fg="#0E7A44",
    err_bg="#FDEBEB",
    err_fg="#B42318",
    warn_bg="#FFF6E4",
    warn_fg="#8A5A00",
    info_bg="#EAF4FD",
    info_fg="#1F5C8B",
    primary_from="#38BDF8",
    primary_to="#0EA5E9",
    primary_hover_from="#4EC5FA",
    primary_hover_to="#22A9E8",
    primary_pressed_from="#0EA5E9",
    primary_pressed_to="#0284C7",
    stars=False,
    shadow_alpha=26,
    art=ThemeArt(pattern="plain", is_light=True),
)

EXTRA_THEMES: dict[str, Theme] = {
    item["key"]: Theme(**item["theme"], art=ThemeArt(**item["art"]))
    for item in _EXTRA_THEME_DATA
}

CORE_THEME_KEYS = ("dark", "light")
THEME_ORDER = ("dark", "light", "graduation", "ozzy", "lana", "acai")
THEMES: dict[str, Theme] = {"dark": DARK, "light": LIGHT, **EXTRA_THEMES}

UNLOCKED_SETTING = "temas_desbloqueados"
ANIMATIONS_SETTING = "reduzir_animacoes"
APP_VERSION = "2.0"


# ── códigos secretos ────────────────────────────────────────────────────────
def normalize_code(text: str) -> str:
    """Ignora maiúsculas, acentos, espaços e pontuação."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in text.lower() if ch.isalnum())


CODE_TO_THEME: dict[str, str] = {}
for _key, _theme in EXTRA_THEMES.items():
    for _code in (_theme.art.secret_code, *_theme.art.aliases):
        if _code:
            CODE_TO_THEME[normalize_code(_code)] = _key


# ── persistência ────────────────────────────────────────────────────────────
def unlocked_keys(settings: QSettings) -> set[str]:
    raw = str(settings.value(UNLOCKED_SETTING, "") or "")
    return {key for key in raw.split(",") if key in EXTRA_THEMES}


def save_unlocked(settings: QSettings, keys: set[str]) -> None:
    settings.setValue(UNLOCKED_SETTING, ",".join(sorted(keys)))


def available_themes(settings: QSettings) -> dict[str, Theme]:
    """Temas principais + os secretos já desbloqueados (nunca os bloqueados)."""
    unlocked = unlocked_keys(settings)
    ordered = [
        key for key in THEME_ORDER
        if key in CORE_THEME_KEYS or key in unlocked
    ]
    ordered += [key for key in sorted(unlocked) if key not in THEME_ORDER]
    return {key: THEMES[key] for key in ordered}


# ── fontes ──────────────────────────────────────────────────────────────────
_FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_FONT_FAMILIES: set[str] = set()
_UI_FONT = "Segoe UI"

# ── arte ────────────────────────────────────────────────────────────────────
_IMAGES_DIR = Path(__file__).resolve().parent / "assets" / "images"
_IMAGE_CACHE: dict[str, QPixmap | None] = {}

# capa de fundo por tema: (arquivo, lado em px @1280, opacidade)
_THEME_COVERS: dict[str, tuple[str, float, float]] = {
    "graduation": ("theme-art-01.jpg", 560.0, 0.40),
    "ozzy": ("theme-art-02.jpg", 540.0, 0.55),
}


def theme_cover(filename: str) -> QPixmap | None:
    """Capa de um tema, carregada uma vez. Sem o arquivo, o tema segue sem ela."""
    if filename in _IMAGE_CACHE:
        return _IMAGE_CACHE[filename]
    base = _IMAGES_DIR
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "assets" / "images"
    pixmap: QPixmap | None = None
    path = base / filename
    if path.is_file():
        loaded = QPixmap(str(path))
        if not loaded.isNull():
            pixmap = loaded
    _IMAGE_CACHE[filename] = pixmap
    return pixmap


def load_theme_fonts() -> None:
    """Carrega as TTFs do kit de temas. Sem elas, tudo cai para Segoe UI."""
    global _FONT_FAMILIES
    base = _FONTS_DIR
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "assets" / "fonts"
    if base.is_dir():
        for path in sorted(base.glob("*.ttf")):
            QFontDatabase.addApplicationFont(str(path))
    _FONT_FAMILIES = set(QFontDatabase.families())


def resolve_family(name: str) -> str:
    if not name:
        return "Segoe UI"
    families = _FONT_FAMILIES or set(QFontDatabase.families())
    return name if name in families else "Segoe UI"


def tracking_px(em: float, size: int) -> float:
    """O design expressa tracking em em; o QFont usa pixels absolutos."""
    return max(0.0, float(em) * float(size))


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def C(hex_color: str, alpha: int | None = None) -> QColor:
    """QColor a partir de HEX, com alfa opcional (0-255)."""
    color = QColor(hex_color)
    if alpha is not None:
        color.setAlpha(alpha)
    return color


def F(px: int, weight: QFont.Weight = QFont.Weight.Normal,
      tracking: float = 0.0, family: str | None = None,
      caps: bool = False, italic: bool = False) -> QFont:
    """Fonte em pixels — evita o descompasso entre pt e px do QSS.

    ``family`` vazio usa a fonte de interface do tema ativo (``_UI_FONT``);
    ``tracking`` é em pixels; ``caps`` aplica caixa alta na renderização sem
    alterar o texto real do widget (importante para o SegmentedControl).
    """
    font = QFont(family or _UI_FONT)
    font.setPixelSize(px)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if italic:
        font.setItalic(True)
    if caps:
        font.setCapitalization(QFont.Capitalization.AllUppercase)
    if tracking:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
    return font


def draw_folder(p: QPainter, rect: QRectF, color: QColor, width: float = 1.4) -> None:
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    path = QPainterPath()
    path.moveTo(x + w * 0.04, y + h * 0.16)
    path.lineTo(x + w * 0.36, y + h * 0.16)
    path.lineTo(x + w * 0.48, y + h * 0.34)
    path.lineTo(x + w * 0.96, y + h * 0.34)
    path.lineTo(x + w * 0.96, y + h * 0.86)
    path.lineTo(x + w * 0.04, y + h * 0.86)
    path.closeSubpath()
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def draw_play(p: QPainter, rect: QRectF, color: QColor) -> None:
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    path = QPainterPath()
    path.moveTo(x + w * 0.16, y + h * 0.08)
    path.lineTo(x + w * 0.92, y + h * 0.50)
    path.lineTo(x + w * 0.16, y + h * 0.92)
    path.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(path)


def draw_chevron(p: QPainter, cx: float, cy: float, size: float, color: QColor,
                 width: float = 1.5, up: bool = False) -> None:
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    if up:
        path.moveTo(cx - size, cy + size * 0.42)
        path.lineTo(cx, cy - size * 0.42)
        path.lineTo(cx + size, cy + size * 0.42)
    else:
        path.moveTo(cx - size, cy - size * 0.42)
        path.lineTo(cx, cy + size * 0.42)
        path.lineTo(cx + size, cy - size * 0.42)
    p.drawPath(path)


def draw_check(p: QPainter, rect: QRectF, color: QColor, width: float = 1.6) -> None:
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(x + w * 0.12, y + h * 0.54)
    path.lineTo(x + w * 0.40, y + h * 0.80)
    path.lineTo(x + w * 0.90, y + h * 0.20)
    p.drawPath(path)


def draw_moon(p: QPainter, center: QPointF, radius: float, color: QColor) -> None:
    outer = QPainterPath()
    outer.addEllipse(center, radius, radius)
    cut = QPainterPath()
    cut.addEllipse(QPointF(center.x() + radius * 0.62, center.y() - radius * 0.52),
                   radius * 0.94, radius * 0.94)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(outer.subtracted(cut))


def draw_sun(p: QPainter, center: QPointF, radius: float, color: QColor) -> None:
    p.setPen(QPen(color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(center, radius * 0.52, radius * 0.52)
    for i in range(8):
        angle = math.radians(i * 45)
        dx, dy = math.cos(angle), math.sin(angle)
        p.drawLine(QPointF(center.x() + dx * radius * 0.84, center.y() + dy * radius * 0.84),
                   QPointF(center.x() + dx * radius * 1.14, center.y() + dy * radius * 1.14))


def draw_sheet(p: QPainter, rect: QRectF, color: QColor, width: float = 1.25) -> None:
    """Marca do app: mini planilha (cabeçalho + colunas)."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    radius = w * 0.18
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRect(QRectF(x + width, y + width, w - width * 2, h * 0.26))
    p.setPen(QPen(color, width * 0.9))
    p.drawLine(QPointF(x + w * 0.5, y + h * 0.34), QPointF(x + w * 0.5, y + h - width))


def draw_file(p: QPainter, rect: QRectF, color: QColor, width: float = 1.3) -> None:
    """Ícone de arquivo/documento com a ponta dobrada (seletor de arquivo)."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    fold = w * 0.28
    path = QPainterPath()
    path.moveTo(x, y)
    path.lineTo(x + w - fold, y)
    path.lineTo(x + w, y + fold)
    path.lineTo(x + w, y + h)
    path.lineTo(x, y + h)
    path.closeSubpath()
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    p.drawLine(QPointF(x + w - fold, y), QPointF(x + w - fold, y + fold))
    p.drawLine(QPointF(x + w - fold, y + fold), QPointF(x + w, y + fold))
    p.setPen(QPen(color, width * 0.85))
    for i in range(3):
        ly = y + h * (0.42 + i * 0.2)
        p.drawLine(QPointF(x + w * 0.16, ly), QPointF(x + w * 0.70, ly))


def draw_mail(p: QPainter, rect: QRectF, color: QColor, width: float = 1.4) -> None:
    """Ícone de envelope (envio de e-mail)."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(x, y + h * 0.16)
    path.lineTo(x, y + h * 0.86)
    path.lineTo(x + w, y + h * 0.86)
    path.lineTo(x + w, y + h * 0.16)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(x, y + h * 0.16), QPointF(x + w * 0.5, y + h * 0.52))
    p.drawLine(QPointF(x + w, y + h * 0.16), QPointF(x + w * 0.5, y + h * 0.52))


def draw_motif(p: QPainter, rect: QRectF, motif: str, color: QColor,
               width: float = 1.3) -> None:
    """Desenha o motivo do logo do tema dentro de ``rect`` (sem imagens).

    Coordenadas normalizadas: o desenho acompanha qualquer tamanho (30×30 no
    cartão de marca, 64×64 no ícone da janela) sem deformar.
    """
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    cx, cy = x + w / 2, y + h / 2
    s = min(w, h)

    def pt(px: float, py: float) -> QPointF:
        return QPointF(x + px * w, y + py * h)

    pen = QPen(color, width, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    if motif == "flower":
        # seis pétalas em volta de um miolo cheio
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(6):
            angle = math.radians(-90 + i * 60)
            px = cx + math.cos(angle) * s * 0.27
            py = cy + math.sin(angle) * s * 0.27
            p.drawEllipse(QPointF(px, py), s * 0.105, s * 0.105)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(cx, cy), s * 0.085, s * 0.085)

    elif motif == "bolt":
        # raio de palco: ponta fina em cima, base larga embaixo
        path = QPainterPath()
        path.moveTo(pt(0.58, 0.06))
        path.lineTo(pt(0.20, 0.56))
        path.lineTo(pt(0.46, 0.56))
        path.lineTo(pt(0.40, 0.94))
        path.lineTo(pt(0.80, 0.42))
        path.lineTo(pt(0.53, 0.42))
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)

    elif motif == "cherry":
        # duas cerejas com cabinho e folha
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        stem = QPainterPath()
        stem.moveTo(pt(0.38, 0.74))
        stem.cubicTo(pt(0.40, 0.44), pt(0.46, 0.30), pt(0.54, 0.26))
        stem.cubicTo(pt(0.60, 0.30), pt(0.64, 0.40), pt(0.66, 0.48))
        p.drawPath(stem)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(pt(0.38, 0.76), s * 0.145, s * 0.145)
        p.drawEllipse(pt(0.68, 0.80), s * 0.125, s * 0.125)
        leaf = QPainterPath()
        leaf.moveTo(pt(0.54, 0.27))
        leaf.quadTo(pt(0.72, 0.10), pt(0.80, 0.22))
        leaf.quadTo(pt(0.70, 0.30), pt(0.54, 0.27))
        p.drawPath(leaf)

    elif motif == "berry":
        # cacho de açaí com folha
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(pt(0.50, 0.62), pt(0.56, 0.30))
        p.drawLine(pt(0.56, 0.30), pt(0.66, 0.22))
        leaf = QPainterPath()
        leaf.moveTo(pt(0.58, 0.28))
        leaf.quadTo(pt(0.74, 0.10), pt(0.82, 0.20))
        leaf.quadTo(pt(0.72, 0.30), pt(0.58, 0.28))
        p.drawPath(leaf)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        for px, py, r in (
            (0.50, 0.66, 0.105), (0.66, 0.68, 0.100), (0.58, 0.80, 0.100),
            (0.40, 0.78, 0.082), (0.74, 0.80, 0.078), (0.50, 0.90, 0.070),
        ):
            p.drawEllipse(pt(px, py), s * r, s * r)

    else:  # sheet — motivo original
        draw_sheet(p, QRectF(x + w * 0.18, y + h * 0.16, w * 0.64, h * 0.68),
                   color, width)


def draw_gear(p: QPainter, rect: QRectF, color: QColor, width: float = 1.3) -> None:
    """Engrenagem compacta para a barra superior (24×24).

    Dentes preenchidos em volta de um anel: em 11 px, raios finos viram um
    sol; blocos curtos leem como engrenagem.
    """
    c = rect.center()
    r = min(rect.width(), rect.height()) * 0.27
    dente_l, dente_c = max(1.6, r * 0.62), max(2.0, r * 0.86)
    p.save()
    p.translate(c)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    for i in range(8):
        p.save()
        p.rotate(i * 45)
        p.drawRoundedRect(
            QRectF(-dente_l / 2, -r - dente_c * 0.72, dente_l, dente_c),
            dente_l * 0.32, dente_l * 0.32,
        )
        p.restore()
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(0, 0), r, r)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(0, 0), max(0.9, r * 0.34), max(0.9, r * 0.34))
    p.restore()


def draw_key(p: QPainter, rect: QRectF, color: QColor, width: float = 1.5) -> None:
    """Chave pequena: argola à esquerda, haste na diagonal e dois dentes."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    centro = QPointF(x + w * 0.26, y + h * 0.72)
    raio = min(w, h) * 0.16
    p.drawEllipse(centro, raio, raio)
    ponta = QPointF(x + w * 0.88, y + h * 0.12)
    p.drawLine(QPointF(centro.x() + raio * 0.72, centro.y() - raio * 0.72), ponta)
    p.drawLine(QPointF(x + w * 0.66, y + h * 0.34), QPointF(x + w * 0.78, y + h * 0.46))
    p.drawLine(QPointF(x + w * 0.78, y + h * 0.22), QPointF(x + w * 0.90, y + h * 0.34))


def make_app_icon(theme: Theme) -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        art = theme.art
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, C(art.logo_from or theme.primary_from))
        if art.logo_mid:
            grad.setColorAt(art.logo_mid_pos, C(art.logo_mid))
        grad.setColorAt(1.0, C(art.logo_to or theme.primary_pressed_to))
        p.setPen(QPen(C(art.logo_border), max(1.0, size * 0.012))
                 if art.logo_border else Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), size * 0.24, size * 0.24)
        if art.logo_motif == "sheet":
            glyph = size * 0.46
            draw_sheet(p, QRectF((size - glyph * 0.86) / 2, (size - glyph) / 2,
                                 glyph * 0.86, glyph),
                       C(theme.on_accent), max(1.0, size * 0.035))
        else:
            glyph = size * 0.56
            draw_motif(p, QRectF((size - glyph) / 2, (size - glyph) / 2,
                                 glyph, glyph),
                       art.logo_motif, C(art.logo_fg or theme.on_accent),
                       max(1.0, size * 0.035))
        p.end()
        icon.addPixmap(pm)
    return icon


def make_success_pixmap(theme: Theme, size: int = 44) -> QPixmap:
    """Ícone do diálogo de sucesso, no mesmo vocabulário visual do app."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fill = C(theme.ok_fg)
    mark = C("#062338") if theme.art.is_light else C("#FFFFFF")
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(fill)
    p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    draw_check(p, QRectF(size * 0.28, size * 0.31, size * 0.42, size * 0.38), mark, 2.2)
    p.end()
    return pm


# ══════════════════════════════════════════════════════════════════════════════
#  CÉU ESTRELADO
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Star:
    x: float          # posição relativa 0-1
    y: float
    radius: float
    base_alpha: int
    period: float     # segundos por ciclo de cintilação
    phase: float
    color: str
    halo: bool


class StarField(QWidget):
    """Fundo do app: gradiente + (no tema escuro) estrelas que pulsam."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._reduced = os.environ.get("PAGFLOW_REDUCED_MOTION", "") == "1"
        rng = random.Random(20261104)
        self._stars = self._make_stars(rng)
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(40)          # ~25 fps: suficiente p/ cintilar
        self._timer.timeout.connect(self._tick)
        # O gradiente de fundo é estático: fica em cache para não ser
        # reconstruído a cada quadro da animação.
        self._bg_cache: QPixmap | None = None
        # Regiões máximas de cada estrela: a animação repinta só esses
        # retângulos em vez da janela inteira a cada quadro.
        self._star_boxes: list[QRect] = []

    @staticmethod
    def _make_stars(rng: random.Random) -> list[Star]:
        palette = ("#6FA8F0", "#8FC2FF", "#5B8FC9", "#A9CCFF", "#4E7FB8")
        stars: list[Star] = []
        # poeira fina
        for _ in range(62):
            stars.append(Star(
                x=rng.uniform(0.015, 0.985), y=rng.uniform(0.01, 0.99),
                radius=rng.uniform(0.8, 1.7),
                base_alpha=rng.randint(70, 205),
                period=rng.uniform(2.8, 8.4), phase=rng.random(),
                color=rng.choice(palette), halo=False,
            ))
        # poucas estrelas maiores, com halo suave
        for _ in range(5):
            stars.append(Star(
                x=rng.uniform(0.10, 0.90), y=rng.uniform(0.07, 0.92),
                radius=rng.uniform(1.5, 2.0),
                base_alpha=rng.randint(170, 220),
                period=rng.uniform(4.5, 9.5), phase=rng.random(),
                color="#9CC7FF", halo=True,
            ))
        return stars

    # ── tema ────────────────────────────────────────────────────────────────
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._bg_cache = None
        self._sync_timer()
        self.update()

    def _sync_timer(self) -> None:
        should_run = self._theme.stars and not self._reduced and self.isVisible()
        if should_run and not self._timer.isActive():
            self._timer.start()
        elif not should_run and self._timer.isActive():
            self._timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_star_boxes()
        self._sync_timer()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._sync_timer()

    def resizeEvent(self, event) -> None:
        self._bg_cache = None
        self._sync_star_boxes()
        super().resizeEvent(event)

    def _sync_star_boxes(self) -> None:
        """Calcula o retângulo máximo de cada estrela na escala atual."""
        w, h = float(self.width()), float(self.height())
        if w <= 0 or h <= 0:
            self._star_boxes = []
            return
        caixas: list[QRect] = []
        for star in self._stars:
            raio = star.radius * 1.3          # maior raio possível da onda
            if star.halo:
                raio *= 4.2                   # alcance do halo
            raio += 2                          # folga do antialiasing
            cx, cy = star.x * w, star.y * h
            lado = int(raio * 2) + 1
            caixas.append(
                QRect(int(cx - raio), int(cy - raio), lado, lado)
            )
        self._star_boxes = caixas

    def _tick(self) -> None:
        """Repinta apenas as regiões das estrelas, não a janela inteira."""
        if not self._star_boxes:
            self.update()
            return
        for caixa in self._star_boxes:
            self.update(caixa)

    # ── pintura ─────────────────────────────────────────────────────────────
    def _background(self) -> QPixmap:
        """Devolve o gradiente de fundo em cache, recriando só se necessário."""
        largura = max(1, self.width())
        altura = max(1, self.height())
        dpr = self.devicePixelRatioF() or 1.0
        largura_fisica = int(round(largura * dpr))
        altura_fisica = int(round(altura * dpr))

        cache = self._bg_cache
        if (
            cache is not None
            and cache.devicePixelRatio() == dpr
            and cache.width() == largura_fisica
            and cache.height() == altura_fisica
        ):
            return cache

        pixmap = QPixmap(largura_fisica, altura_fisica)
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)

        theme = self._theme
        w, h = float(largura), float(altura)
        p = QPainter(pixmap)
        try:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, C(theme.bg_top))
            grad.setColorAt(1.0, C(theme.bg_bottom))
            p.fillRect(QRectF(0, 0, w, h), QBrush(grad))
            pattern = theme.art.pattern or ("stars" if theme.stars else "plain")
            if pattern == "clouds":
                self._paint_clouds(p, w, h)
            elif pattern == "grain":
                self._paint_grain(p, w, h)
            elif pattern == "paper":
                self._paint_paper(p, w, h)
            elif pattern == "dotgrid":
                self._paint_dotgrid(p, w, h)
            else:
                self._paint_atmosphere(p, w, h, theme)
            if theme.key in _THEME_COVERS:
                self._paint_theme_cover(p, w, h, theme.key)
        finally:
            p.end()

        self._bg_cache = pixmap
        return pixmap

    def _paint_theme_cover(self, p: QPainter, w: float, h: float,
                           key: str) -> None:
        """Capa do tema saindo do cabeçalho, como camada de fundo.

        Fica atrás de todo o conteúdo (o cartão e os campos são translúcidos),
        com a opacidade do tema e máscara que dissolve as laterais e o pé.
        """
        spec = _THEME_COVERS.get(key)
        if spec is None:
            return
        filename, base_size, opacity = spec
        cover = theme_cover(filename)
        if cover is None:
            return
        size = min(base_size, w * (base_size / 1280.0))
        if size < 100.0:
            return

        dpr = self.devicePixelRatioF() or 1.0
        layer = QPixmap(int(round(size * dpr)), int(round(size * dpr)))
        layer.setDevicePixelRatio(dpr)
        layer.fill(Qt.GlobalColor.transparent)

        lp = QPainter(layer)
        try:
            lp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            lp.setOpacity(opacity)
            lp.drawPixmap(QRectF(0, 0, size, size), cover,
                          QRectF(cover.rect()))

            lp.setOpacity(1.0)
            lp.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_DestinationIn)
            vertical = QLinearGradient(0, 0, 0, size)
            vertical.setColorAt(0.00, QColor(255, 255, 255, 255))
            vertical.setColorAt(0.55, QColor(255, 255, 255, 235))
            vertical.setColorAt(0.82, QColor(255, 255, 255, 120))
            vertical.setColorAt(1.00, QColor(255, 255, 255, 0))
            lp.fillRect(QRectF(0, 0, size, size), vertical)

            horizontal = QLinearGradient(0, 0, size, 0)
            horizontal.setColorAt(0.00, QColor(255, 255, 255, 0))
            horizontal.setColorAt(0.28, QColor(255, 255, 255, 210))
            horizontal.setColorAt(0.93, QColor(255, 255, 255, 255))
            horizontal.setColorAt(1.00, QColor(255, 255, 255, 0))
            lp.fillRect(QRectF(0, 0, size, size), horizontal)
        finally:
            lp.end()

        # encostada na borda direita do conteúdo e no topo do cabeçalho
        p.drawPixmap(QPointF(w - 20.0 - size, 44.0), layer)

    # ── padrões de fundo dos temas secretos ─────────────────────────────────
    @staticmethod
    def _blob(p: QPainter, cx: float, cy: float, rx: float, ry: float,
              color: str, alpha: int, stop: float = 0.7) -> None:
        """Mancha elíptica com a mesma leitura do gradiente radial do CSS."""
        if alpha <= 0 or rx <= 0 or ry <= 0:
            return
        p.save()
        p.translate(cx, cy)
        if abs(rx - ry) > 0.5:
            p.scale(rx / ry, 1.0)
        inner = QColor(color)
        inner.setAlpha(alpha)
        outer = QColor(color)
        outer.setAlpha(0)
        grad = QRadialGradient(QPointF(0, 0), ry)
        grad.setColorAt(0.0, inner)
        grad.setColorAt(stop, outer)
        grad.setColorAt(1.0, outer)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(0, 0), ry, ry)
        p.restore()

    @staticmethod
    def _radial(p: QPainter, cx: float, cy: float, radius: float,
                color: str, alpha: int) -> None:
        """Mancha radial suave (o “blur” do CSS, sem filtro caro)."""
        if alpha <= 0 or radius <= 0:
            return
        inner = QColor(color)
        inner.setAlpha(alpha)
        outer = QColor(color)
        outer.setAlpha(0)
        grad = QRadialGradient(QPointF(cx, cy), radius)
        grad.setColorAt(0.0, inner)
        grad.setColorAt(1.0, outer)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), radius, radius)

    def _paint_atmosphere(self, p: QPainter, w: float, h: float,
                          theme: Theme) -> None:
        if theme.glow_alpha:
            glow = QColor(theme.glow)
            glow.setAlpha(theme.glow_alpha)
            radial = QRadialGradient(
                QPointF(w * 0.84, h * 0.01), max(w, h) * 0.9
            )
            radial.setColorAt(0.0, glow)
            transparent = QColor(theme.glow)
            transparent.setAlpha(0)
            radial.setColorAt(1.0, transparent)
            p.fillRect(QRectF(0, 0, w, h), QBrush(radial))

    def _paint_clouds(self, p: QPainter, w: float, h: float) -> None:
        """Graduation: céu pastel, nuvens brancas e poeira de verão.

        Camadas na mesma ordem do CSS: base do céu, lavagem pastel, nuvens e
        orbes, e por fim a poeira branca.
        """
        # Lavagem lavanda no topo, depois os três brilhos que dão o clima
        # (rosa à esquerda, azul-lavanda à direita, creme embaixo à direita).
        self._blob(p, w * 0.55, -h * 0.08, w * 0.85, h * 0.44, "#C9B6F2", 120, 0.85)
        self._blob(p, w * 0.68, h * 0.04, w * 0.25, h * 0.3125, "#F07BC0", 55, 0.80)
        self._blob(p, w * 0.02, h * 0.02, w * 0.422, h * 0.542, "#E23E9E", 135, 0.72)
        self._blob(p, w * 0.99, h * 0.00, w * 0.4375, h * 0.4896, "#8FA6F2", 170, 0.72)
        self._blob(p, w * 0.72, h * 0.98, w * 0.367, h * 0.4375, "#FFC96B", 108, 0.72)
        self._blob(p, w * 0.42, h * 0.30, w * 0.297, h * 0.229, "#FFFFFF", 70, 0.85)
        rng = random.Random(7)
        step = 118.0
        p.setPen(Qt.PenStyle.NoPen)
        y = 0.0
        while y < h:
            x = 0.0
            while x < w:
                for _ in range(3):
                    px = x + rng.uniform(0, step)
                    py = y + rng.uniform(0, step)
                    p.setBrush(C("#FFFFFF", rng.randint(70, 150)))
                    raio = rng.uniform(0.5, 1.1)
                    p.drawEllipse(QPointF(px, py), raio, raio)
                x += step
            y += step

    def _paint_grain(self, p: QPainter, w: float, h: float) -> None:
        """Ozzy: palco preto, sangramento vermelho, morcego e scanlines."""
        # .sky — base
        self._blob(p, w * 0.84, -h * 0.12, 560, 400, "#920703", 120, 0.68)
        self._blob(p, -w * 0.04, h * 0.24, 380, 280, "#920703", 41, 0.66)
        self._blob(p, w * 0.12, h * 1.12, 380, 260, "#FBE500", 13, 0.68)
        # .sky::before
        self._blob(p, w * 0.12, h * 0.08, w * 0.42, h * 0.42, "#920703", 85, 0.70)
        self._blob(p, w * 0.92, h * 0.74, w * 0.40, h * 0.40, "#920703", 58, 0.70)
        self._blob(p, w * 0.55, h * 1.10, w * 0.40, h * 0.35, "#FBE500", 20, 0.70)
        # orbes
        self._blob(p, -w * 0.20, -h * 0.25, 390, 310, "#920703", 70, 0.68)
        self._blob(p, w * 0.69, h * 0.75, 310, 260, "#920703", 50, 0.68)
        self._blob(p, w * 0.73, -h * 0.19, 230, 180, "#FBE500", 15, 0.70)

        # morcego: silhueta abstrata, quase invisível, atrás do conteúdo
        p.save()
        p.translate(w - 120, 120)
        p.rotate(-6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(C("#920703", 33))
        asa = QPainterPath()
        asa.moveTo(320, 85)
        asa.cubicTo(268, 40, 166, 15, 12, 45)
        asa.lineTo(64, 75)
        asa.lineTo(26, 85)
        asa.lineTo(90, 105)
        asa.lineTo(51, 120)
        asa.lineTo(141, 130)
        asa.lineTo(115, 150)
        asa.lineTo(218, 145)
        asa.lineTo(230, 175)
        asa.lineTo(320, 150)
        asa.lineTo(410, 175)
        asa.lineTo(422, 145)
        asa.lineTo(525, 150)
        asa.lineTo(499, 130)
        asa.lineTo(589, 120)
        asa.lineTo(550, 105)
        asa.lineTo(614, 85)
        asa.lineTo(576, 75)
        asa.lineTo(628, 45)
        asa.cubicTo(474, 15, 372, 40, 320, 85)
        asa.closeSubpath()
        p.drawPath(asa)
        p.restore()

        # scanlines de 1 px a cada 3 px
        p.setPen(QPen(C("#FFFFFF", 7), 1))
        y = 0.0
        while y < h:
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += 3.0
        edge = QLinearGradient(0, 0, w, 0)
        edge.setColorAt(0.0, C("#920703", 140))
        edge.setColorAt(0.58, C("#FBE500", 140))
        edge.setColorAt(1.0, C("#920703", 140))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(edge))
        p.drawRect(QRectF(0, 0, w, 2))

    def _paint_paper(self, p: QPainter, w: float, h: float) -> None:
        """Lana: papel marfim, blush e o disco de vinil ao fundo."""
        # .sky — base
        self._blob(p, w * 0.84, -h * 0.12, 450, 310, "#FFB1C1", 82, 0.68)
        self._blob(p, w * 0.12, h * 1.12, 380, 260, "#FFDAD9", 97, 0.68)
        # .sky::before
        self._blob(p, w * 0.20, h * 0.12, w * 0.45, h * 0.45, "#FFB1C1", 85, 0.70)
        self._blob(p, w * 0.86, h * 0.58, w * 0.42, h * 0.42, "#C81D3B", 26, 0.70)
        self._blob(p, w * 0.30, h * 0.96, w * 0.45, h * 0.40, "#FFDAD9", 95, 0.70)
        # véu morno que tira o branco do topo (papel envelhecido)
        self._blob(p, w * 0.50, -h * 0.05, w * 0.95, h * 0.40, "#C9A8A8", 75, 0.85)
        # orbes
        self._blob(p, -w * 0.19, -h * 0.23, 340, 270, "#FFB1C1", 107, 0.68)
        self._blob(p, w * 1.00, h * 0.62, w * 0.42, h * 0.42, "#C81D3B", 26, 0.78)
        self._blob(p, w * 0.44, h * 0.31, 210, 190, "#FFDAD9", 112, 0.70)

        # grão de papel: tile de 6 px repetido (barato e sem moiré)
        dpr = p.device().devicePixelRatioF()
        lado = max(1, int(round(6 * dpr)))
        tile = QPixmap(lado, lado)
        tile.setDevicePixelRatio(dpr)
        tile.fill(Qt.GlobalColor.transparent)
        tp = QPainter(tile)
        tp.setRenderHint(QPainter.RenderHint.Antialiasing)
        tp.setPen(Qt.PenStyle.NoPen)
        tp.setBrush(C("#5B4040", 20))
        tp.drawEllipse(QPointF(3, 3), 0.6, 0.6)
        tp.end()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(tile))
        p.drawRect(QRectF(0, 0, w, h))

        # disco: anéis concêntricos + selo central
        centro = QPointF(w * 0.906, h * 0.50)
        externo = w * 0.226
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(C("#A10028", 18), 1))
        raio = 22.0
        while raio < externo:
            p.drawEllipse(centro, raio, raio)
            raio += 6.0
        p.setPen(QPen(C("#A10028", 42), 1))
        p.drawEllipse(centro, externo, externo)
        p.setPen(QPen(C("#A10028", 40), 1))
        p.drawEllipse(centro, externo * 0.252, externo * 0.252)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(C("#A10028", 10))
        p.drawEllipse(centro, externo * 0.252, externo * 0.252)

    def _paint_dotgrid(self, p: QPainter, w: float, h: float) -> None:
        """Açaí: roxo profundo, grade de pontos e anel dourado."""
        # .sky — base
        self._blob(p, w * 0.84, -h * 0.12, 450, 310, "#7E22CE", 102, 0.68)
        self._blob(p, -w * 0.04, h * 0.24, 380, 280, "#F59E0B", 23, 0.66)
        self._blob(p, w * 0.12, h * 1.12, 380, 260, "#581C87", 77, 0.68)
        # .sky::before
        self._blob(p, w * 0.12, h * 0.10, w * 0.45, h * 0.45, "#7E22CE", 78, 0.70)
        self._blob(p, w * 0.96, h * 0.12, w * 0.40, h * 0.40, "#F59E0B", 10, 0.70)
        self._blob(p, w * 0.62, h * 1.08, w * 0.45, h * 0.40, "#581C87", 95, 0.70)
        # orbes
        self._blob(p, -w * 0.20, -h * 0.25, 380, 300, "#7E22CE", 107, 0.68)
        self._blob(p, w * 0.70, h * 0.02, 260, 260, "#F59E0B", 36, 0.68)
        self._blob(p, w * 0.07, h * 0.77, 310, 260, "#581C87", 55, 0.68)

        # grade de pontos
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(C("#D8B4FE", 36))
        step = 26.0
        y = 13.0
        while y < h:
            x = 13.0
            while x < w:
                p.drawEllipse(QPointF(x, y), 0.55, 0.55)
                x += step
            y += step
        # anéis dourados
        centro = QPointF(w * 0.902, h * 0.353)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(C("#F59E0B", 46), 1))
        p.drawEllipse(centro, w * 0.184, w * 0.184)
        p.setPen(QPen(C("#C084FC", 23), 1))
        p.drawEllipse(centro, w * 0.129, w * 0.129)

    def set_reduced(self, reduced: bool) -> None:
        """Liga/desliga a animação (preferência de acessibilidade)."""
        self._reduced = bool(reduced)
        self._sync_timer()
        self.update()

    def paintEvent(self, event) -> None:
        theme = self._theme
        p = QPainter(self)
        p.drawPixmap(0, 0, self._background())

        if not theme.stars:
            return

        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        now = self._clock.elapsed() / 1000.0
        p.setPen(Qt.PenStyle.NoPen)
        for star in self._stars:
            wave = 0.5 + 0.5 * math.sin(TAU * (now / star.period + star.phase))
            wave = wave * wave * (3 - 2 * wave)          # smoothstep: sobe/desce macio
            alpha = int(star.base_alpha * (0.35 + 0.65 * wave))
            if alpha <= 3:
                continue
            radius = star.radius * (0.68 + 0.62 * wave)
            color = C(star.color, alpha)
            p.setBrush(color)
            p.drawEllipse(QPointF(star.x * w, star.y * h), radius, radius)
            if star.halo:
                halo = QRadialGradient(QPointF(star.x * w, star.y * h), radius * 4.2)
                inner = C(star.color, int(alpha * 0.26))
                halo.setColorAt(0.0, inner)
                halo.setColorAt(1.0, C(star.color, 0))
                p.setBrush(QBrush(halo))
                p.drawEllipse(QPointF(star.x * w, star.y * h), radius * 4.2, radius * 4.2)


# ══════════════════════════════════════════════════════════════════════════════
#  PEÇAS DE SUPERFÍCIE
# ══════════════════════════════════════════════════════════════════════════════
class Card(QFrame):
    """Superfície arredondada, translúcida no escuro para o céu aparecer."""

    def __init__(self, parent: QWidget | None = None, radius: int = 12) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def set_shadow(self, alpha: int) -> None:
        """Sombra macia via efeito gráfico (o desenho manual ficava em faixas)."""
        if alpha <= 0:
            self.setGraphicsEffect(None)
            return
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(15, 40, 70, alpha))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        art = t.art
        alpha = int((art.card_alpha or t.surface_alpha) * 255)
        if art.card_from:
            grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
            grad.setColorAt(0.0, C(art.card_from, alpha))
            grad.setColorAt(1.0, C(art.card_to or art.card_from, alpha))
            fill = QBrush(grad)
        else:
            fill = C(t.surface, alpha)
        p.setPen(QPen(C(t.border), 1))
        p.setBrush(fill)
        p.drawRoundedRect(rect, self._radius, self._radius)

        if art.card_edge_height and art.card_edge_from:
            edge = QLinearGradient(rect.left(), 0, rect.right(), 0)
            edge.setColorAt(0.0, C(art.card_edge_from, art.card_edge_alpha))
            edge.setColorAt(0.58, C(art.card_edge_to or art.card_edge_from,
                                    art.card_edge_alpha))
            edge.setColorAt(1.0, C(art.card_edge_from, art.card_edge_alpha))
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(rect, self._radius, self._radius)
            p.setClipPath(clip)
            p.fillRect(
                QRectF(rect.left(), rect.top(), rect.width(),
                       float(art.card_edge_height)),
                QBrush(edge),
            )
            p.restore()


class Divider(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self.setFixedHeight(1)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, C(self._theme.border, 0))
        grad.setColorAt(0.18, C(self._theme.border))
        grad.setColorAt(0.82, C(self._theme.border))
        grad.setColorAt(1.0, C(self._theme.border, 0))
        p.fillRect(self.rect(), QBrush(grad))


class LogoMark(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self.setFixedSize(30, 30)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)

        art = t.art
        from_color = art.logo_from or t.primary_from
        to_color = art.logo_to or t.accent_pressed
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, C(from_color))
        if art.logo_mid:
            grad.setColorAt(art.logo_mid_pos, C(art.logo_mid))
        grad.setColorAt(1.0, C(to_color))
        if art.logo_border:
            p.setPen(QPen(C(art.logo_border), 1))
        else:
            p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, 9, 9)

        # brilho superior sutil (mais discreto nos logos escuros)
        brilho = (40 if art.is_light else 18) if art.logo_from else 40
        sheen = QLinearGradient(0, 0, 0, self.height())
        sheen.setColorAt(0.0, C("#FFFFFF", brilho))
        sheen.setColorAt(0.55, C("#FFFFFF", 0))
        p.setBrush(QBrush(sheen))
        p.drawRoundedRect(rect, 9, 9)

        if art.logo_motif == "sheet":
            draw_sheet(p, QRectF(8, 7.5, 14, 15), C(t.on_accent), 1.3)
        else:
            draw_motif(p, QRectF(6.5, 5.8, 17.0, 18.4), art.logo_motif,
                       C(art.logo_fg or t.on_accent), 1.25)


# ══════════════════════════════════════════════════════════════════════════════
#  BOTÕES
# ══════════════════════════════════════════════════════════════════════════════
class PillButton(QAbstractButton):
    """Botão primário (gradiente) / secundário (superfície + borda)."""

    def __init__(self, text: str, variant: str = "secondary", glyph: str | None = None,
                 width: int | None = None, height: int = 36,
                 parent: QWidget | None = None, font_px: int = 12) -> None:
        super().__init__(parent)
        self._theme = DARK
        self.variant = variant
        self.glyph = glyph
        self.font_px = font_px
        self._hover = False
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(text)
        if width:
            self.setFixedWidth(width)
        self.setFixedHeight(height)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        art = t.art
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 10
        enabled = self.isEnabled()

        if self.variant == "primary":
            if not enabled:
                top, bottom = C(t.border_strong), C(t.border)
            elif self.isDown():
                top, bottom = C(t.primary_pressed_from), C(t.primary_pressed_to)
            elif self._hover:
                top, bottom = C(t.primary_hover_from), C(t.primary_hover_to)
            else:
                top, bottom = C(t.primary_from), C(t.primary_to)
            grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
            grad.setColorAt(0.0, top)
            grad.setColorAt(1.0, bottom)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(rect, radius, radius)

            sheen = QLinearGradient(0, rect.top(), 0, rect.bottom())
            sheen.setColorAt(0.0, C("#FFFFFF", 46 if enabled else 14))
            sheen.setColorAt(0.6, C("#FFFFFF", 0))
            p.setBrush(QBrush(sheen))
            p.drawRoundedRect(rect, radius, radius)

            fg = C(art.primary_text or t.on_accent, 255 if enabled else 120)
        else:
            if not enabled:
                fill, stroke, fg = C(t.surface_alt), C(t.border), C(t.text_muted, 140)
            else:
                fill = C(t.surface_alt if self._hover else t.surface, 235)
                stroke = C(t.accent if self._hover else t.border)
                fg = C(t.text if self._hover else t.text_secondary)
            p.setPen(QPen(stroke, 1))
            p.setBrush(fill)
            p.drawRoundedRect(rect, radius, radius)

        if self.hasFocus():
            ring = C(t.on_accent if self.variant == "primary" else t.accent)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ring, 1.5))
            p.drawRoundedRect(rect.adjusted(2.2, 2.2, -2.2, -2.2), radius - 2, radius - 2)

        familia = art.button_font or art.ui_font
        font = F(
            self.font_px,
            QFont.Weight.DemiBold if self.variant == "primary" else QFont.Weight.Medium,
            tracking=tracking_px(art.button_tracking, self.font_px),
            family=familia,
            caps=art.button_transform == "uppercase",
        )
        p.setFont(font)
        fm = QFontMetrics(font)
        text = self.text()
        text_w = fm.horizontalAdvance(text)
        icon_w = 11 if self.glyph else 0
        gap = 8 if self.glyph else 0
        total = icon_w + gap + text_w
        x = (self.width() - total) / 2

        if self.glyph:
            icon_rect = QRectF(x, (self.height() - 12) / 2, 11, 12)
            if self.glyph == "play":
                draw_play(p, icon_rect, fg)
            elif self.glyph == "mail":
                draw_mail(p, icon_rect, fg, 1.3)
            elif self.glyph == "key":
                draw_key(p, icon_rect, fg, 1.3)
            x += icon_w + gap

        p.setPen(fg)
        p.drawText(QRectF(x, 0, text_w + 2, self.height()),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)


class IconButton(QAbstractButton):
    """Botão de ícone (selecionar pasta)."""

    def __init__(self, glyph: str, tooltip: str, parent: QWidget | None = None,
                 compact: bool = False) -> None:
        super().__init__(parent)
        self._theme = DARK
        self.glyph = glyph
        self.compact = compact
        self._hover = False
        if compact:
            self.setFixedSize(24, 24)
        else:
            self.setFixedSize(36, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        if self.isDown():
            fill, stroke = C(t.surface_alt), C(t.accent)
        elif self._hover:
            fill, stroke = C(t.surface_alt), C(t.accent)
        else:
            fill, stroke = C(t.surface, 235), C(t.border)
        raio = 7 if self.compact else 10
        if self.compact and not (self._hover or self.isDown()):
            # fantasma: só o glifo, como na referência
            pass
        else:
            p.setPen(QPen(stroke, 1))
            p.setBrush(fill)
            p.drawRoundedRect(rect, raio, raio)

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.5))
            p.drawRoundedRect(rect.adjusted(2.2, 2.2, -2.2, -2.2),
                              max(3, raio - 2), max(3, raio - 2))

        color = C(t.accent if self._hover else t.text_secondary)
        if self.compact:
            glyph_rect = QRectF(6.5, 6.5, 11, 11)
            if self.glyph == "gear":
                draw_gear(p, glyph_rect, color, 1.25)
            elif self.glyph == "file":
                draw_file(p, glyph_rect, color, 1.25)
            elif self.glyph == "mail":
                draw_mail(p, glyph_rect, color, 1.25)
            else:
                draw_folder(p, glyph_rect, color, 1.25)
            return

        glyph_rect = QRectF(11, 9.5, 14, 13)
        if self.glyph == "file":
            draw_file(p, glyph_rect, color, 1.4)
        elif self.glyph == "mail":
            draw_mail(p, glyph_rect, color, 1.4)
        elif self.glyph == "gear":
            draw_gear(p, glyph_rect, color, 1.4)
        else:
            draw_folder(p, glyph_rect, color, 1.4)


# ══════════════════════════════════════════════════════════════════════════════
#  ALTERNADOR DE TEMA
# ══════════════════════════════════════════════════════════════════════════════
class ThemeToggle(QAbstractButton):
    """Pílula com lua/sol e botão deslizante — alterna escuro ↔ claro."""

    theme_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._pos = 0.0            # 0 = escuro, 1 = claro
        self._hover = False
        self._pending: str | None = None
        self.setFixedSize(58, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Alternar entre tema escuro e claro")
        self.setAccessibleName("Alternar tema")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        target = 1.0 if theme.art.is_light else 0.0
        if not self.isVisible() or self._pos == target:
            self._pos = target
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(float(self._pos))
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_anim(self, value) -> None:
        self._pos = float(value)
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.update()
        super().focusOutEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pending = "dark" if event.position().x() < self.width() / 2 else "light"
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._pending:
            inside = self.rect().contains(event.position().toPoint())
            target = self._pending
            self._pending = None
            # Compara com o MODO atual, não com a key: um tema secreto tem key
            # própria (graduation, ozzy…), mas pertence a um dos dois lados.
            current_mode = "light" if self._theme.art.is_light else "dark"
            if inside and target != current_mode:
                self.theme_requested.emit(target)
        self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.theme_requested.emit(
                "dark" if self._theme.art.is_light else "light"
            )
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(C(t.accent if self._hover else t.border), 1))
        p.setBrush(C(t.surface_alt, 220))
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        # botão deslizante
        knob = 22.0
        x = 2 + self._pos * (self.width() - knob - 4)
        knob_rect = QRectF(x, 2, knob, knob)
        grad = QLinearGradient(0, knob_rect.top(), 0, knob_rect.bottom())
        grad.setColorAt(0.0, C(t.primary_from))
        grad.setColorAt(1.0, C(t.primary_to))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(knob_rect)

        # ícones em posições fixas: a lua mora à esquerda, o sol à direita;
        # só a cor muda com o lado ativo (antes eles seguiam o botão e a lua
        # sumia no tema claro).
        ativo = C(t.art.primary_text or t.on_accent)
        inativo = C(t.text_muted)
        centro_knob = x + knob / 2
        if self._pos < 0.5:
            # lua viaja com o botão; sol fica apagado no lugar dele
            draw_moon(p, QPointF(centro_knob + 0.6, self.height() / 2), 5.4, ativo)
            draw_sun(p, QPointF(self.width() - 2 - knob / 2 - 0.6,
                                self.height() / 2), 5.0, inativo)
        else:
            draw_moon(p, QPointF(2 + knob / 2 + 0.6, self.height() / 2), 5.4, inativo)
            draw_sun(p, QPointF(centro_knob - 0.6, self.height() / 2), 5.0, ativo)

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.5))
            p.drawRoundedRect(track.adjusted(-1, -1, 1, 1), track.height() / 2 + 1,
                              track.height() / 2 + 1)


# ══════════════════════════════════════════════════════════════════════════════
#  CONTROLE SEGMENTADO
# ══════════════════════════════════════════════════════════════════════════════
class SegmentedControl(QWidget):
    def __init__(self, options: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._hover_index = -1
        self._pos = 0.0
        self.setFixedHeight(32)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        for index, option in enumerate(options):
            button = QPushButton(option, self)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setFlat(True)
            button.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            button.installEventFilter(self)
            self._group.addButton(button, index)
            layout.addWidget(button, 1)
            self._buttons.append(button)
        self._buttons[-1].setChecked(True)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._group.buttonClicked.connect(self._on_clicked)

    # ── API ─────────────────────────────────────────────────────────────────
    def value(self) -> str:
        button = self._group.checkedButton()
        return button.text() if button else ""

    def set_value(self, text: str) -> None:
        for button in self._buttons:
            if button.text() == text:
                button.setChecked(True)
                self._sync_buttons()
                self._snap_pill()
                break

    def _snap_pill(self) -> None:
        checked = self._group.checkedButton()
        self._pos = float(self._buttons.index(checked)) if checked in self._buttons else 0.0
        self.update()

    def _on_clicked(self, button: QPushButton) -> None:
        index = self._buttons.index(button)
        self._sync_buttons()          # texto do item ativo acompanha a seleção
        self._anim.stop()
        self._anim.setStartValue(float(self._pos))
        self._anim.setEndValue(float(index))
        self._anim.start()

    def _on_anim(self, value) -> None:
        self._pos = float(value)
        self.update()

    def eventFilter(self, obj, event) -> bool:
        if obj in self._buttons:
            if event.type() == QEvent.Type.Enter:
                self._hover_index = self._buttons.index(obj)
                self.update()
            elif event.type() == QEvent.Type.Leave:
                if self._hover_index == self._buttons.index(obj):
                    self._hover_index = -1
                    self.update()
            elif event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
                self.update()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._snap_pill()

    # ── tema ────────────────────────────────────────────────────────────────
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._sync_buttons()
        self.update()

    def _sync_buttons(self) -> None:
        t = self._theme
        for button in self._buttons:
            checked = button.isChecked()
            color = (t.art.seg_active_fg or t.on_accent) if checked else t.text_secondary
            weight = QFont.Weight.DemiBold if checked else QFont.Weight.Normal
            button.setFont(F(11, weight, family=t.art.ui_font))
            button.setStyleSheet(
                "QPushButton { background: transparent; border: none;"
                f" color: {color}; padding: 0px; }}"
                "QPushButton:focus { outline: none; }"
            )

    def _segment_rect(self, index: int) -> QRectF:
        count = max(1, len(self._buttons))
        width = (self.width() - 4) / count
        return QRectF(2 + index * width, 2, width, self.height() - 4)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(C(t.field_border), 1))
        p.setBrush(C(t.field_bg))
        p.drawRoundedRect(track, 9, 9)

        if self._hover_index >= 0 and not self._buttons[self._hover_index].isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(C(t.accent, 26))
            p.drawRoundedRect(self._segment_rect(self._hover_index).adjusted(2, 1, -2, -1),
                              7, 7)

        # pílula do item selecionado (desliza entre as opções)
        count = max(1, len(self._buttons))
        seg_w = (self.width() - 4) / count
        x = 2 + self._pos * seg_w
        pill = QRectF(x + 1, 2, seg_w - 2, self.height() - 4)
        art = t.art
        topo = art.seg_active_from or t.primary_from
        base = art.seg_active_to or t.primary_to
        grad = QLinearGradient(0, pill.top(), 0, pill.bottom())
        grad.setColorAt(0.0, C(topo))
        grad.setColorAt(1.0, C(base))
        p.setPen(QPen(C(art.seg_active_border or topo), 1))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(pill, 7, 7)

        # anel de foco no item focado
        focused = next((b for b in self._buttons if b.hasFocus()), None)
        if focused is not None:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent_soft_text if focused.isChecked() else t.accent), 1.4))
            p.drawRoundedRect(self._segment_rect(self._buttons.index(focused)).adjusted(2, 1, -2, -1),
                              7, 7)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._snap_pill()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self._sync_buttons()


# ══════════════════════════════════════════════════════════════════════════════
#  CAMPO DE SELEÇÃO (substitui o option menu)
# ══════════════════════════════════════════════════════════════════════════════
class OptionPopup(QWidget):
    chosen = pyqtSignal(str)

    def __init__(self, options: list[str], current: str, theme: Theme,
                 parent: QWidget) -> None:
        super().__init__(parent, Qt.WindowType.Popup
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self._theme = theme
        self._options = options
        self._current = current
        self._hover = max(0, options.index(current)) if current in options else 0
        self._row_h = 30
        self._inset = 6
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(parent.width() + self._inset * 2,
                          len(options) * self._row_h + 8 + self._inset * 2)

    def fade_in(self) -> None:
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(120)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._fade = anim

    def _panel(self) -> QRectF:
        return QRectF(self._inset, self._inset,
                      self.width() - self._inset * 2,
                      self.height() - self._inset * 2)

    def _row_rect(self, index: int) -> QRectF:
        panel = self._panel()
        return QRectF(panel.left() + 4, panel.top() + 4 + index * self._row_h,
                      panel.width() - 8, self._row_h)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = self._panel()

        shadow = QColor(6, 18, 32, 30 if t.art.is_light else 70)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawRoundedRect(panel.adjusted(0, 2, 0, 4), 11, 11)

        p.setPen(QPen(C(t.border), 1))
        p.setBrush(C(t.surface_alt, 252))
        p.drawRoundedRect(panel, 10, 10)

        p.setFont(F(11, family=t.art.ui_font))
        for index, option in enumerate(self._options):
            row = self._row_rect(index)
            if index == self._hover:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(C(t.accent, 30))
                p.drawRoundedRect(row, 7, 7)
            if option == self._current:
                p.setPen(QPen(C(t.accent), 1.4, Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(row.adjusted(0.7, 0.7, -0.7, -0.7), 7, 7)
                draw_check(p, QRectF(row.right() - 22, row.center().y() - 6, 11, 12),
                           C(t.accent_soft_text if t.art.is_light else t.accent), 1.5)
            p.setPen(C(t.text if index == self._hover else t.text_secondary))
            p.drawText(row.adjusted(12, 0, -26, 0),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), option)

    def _index_at(self, y: float) -> int:
        panel = self._panel()
        if y < panel.top() + 4:
            return 0
        index = int((y - panel.top() - 4) // self._row_h)
        return max(0, min(len(self._options) - 1, index))

    def mouseMoveEvent(self, event) -> None:
        index = self._index_at(event.position().y())
        if index != self._hover:
            self._hover = index
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._choose(self._hover)

    def _choose(self, index: int) -> None:
        self.chosen.emit(self._options[index])
        self.close()
        self.deleteLater()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Down:
            self._hover = min(len(self._options) - 1, self._hover + 1)
            self.update()
        elif key == Qt.Key.Key_Up:
            self._hover = max(0, self._hover - 1)
            self.update()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._choose(self._hover)
        elif key == Qt.Key.Key_Escape:
            self.close()
            self.deleteLater()
        else:
            super().keyPressEvent(event)


class SelectField(QAbstractButton):
    """Campo que abre o popup de opções (cor da tabela)."""

    def __init__(self, options: list[str], value: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._options = options
        self._value = value
        self._hover = False
        self._popup: OptionPopup | None = None
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Cor do relatório")

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def value(self) -> str:
        return self._value

    def set_value(self, value: str) -> None:
        self._value = value
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        active = self._hover or self.hasFocus() or self._popup is not None
        p.setPen(QPen(C(t.accent if active else t.field_border), 1))
        p.setBrush(C(t.field_focus if active else t.field_bg))
        p.drawRoundedRect(rect, 10, 10)

        font = F(11, family=t.art.ui_font)
        p.setFont(font)
        fm = QFontMetrics(font)
        text = fm.elidedText(self._value, Qt.TextElideMode.ElideRight,
                             int(self.width() - 44))
        p.setPen(C(t.text))
        p.drawText(QRectF(11, 0, self.width() - 42, self.height()),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
        draw_chevron(p, self.width() - 17, self.height() / 2, 4.2,
                     C(t.accent if active else t.text_secondary), 1.5)

    def _open_popup(self) -> None:
        if self._popup is not None:
            return
        popup = OptionPopup(self._options, self._value, self._theme, self)
        popup.chosen.connect(self._on_chosen)
        popup.destroyed.connect(self._on_popup_destroyed)
        self._popup = popup

        anchor = self.mapToGlobal(QPoint(-6, self.height() - 4))
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen and anchor.y() + popup.height() > screen.bottom() - 4:
            anchor.setY(self.mapToGlobal(QPoint(0, 0)).y() - popup.height() + 4)
        popup.move(anchor)
        popup.show()
        popup.setFocus()
        popup.fade_in()
        self.update()

    def _on_popup_destroyed(self) -> None:
        self._popup = None
        self.update()

    def _on_chosen(self, value: str) -> None:
        self._value = value
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._popup is None:
            self._open_popup()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Space, Qt.Key.Key_Return,
                           Qt.Key.Key_Enter):
            self._open_popup()
            return
        super().keyPressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
#  BARRA DE STATUS
# ══════════════════════════════════════════════════════════════════════════════
class StatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._message = "Pronto para uso."
        self._state = "idle"
        self._busy = False
        self._angle = 0
        self.setFixedHeight(32)
        self.setFont(F(11))
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._spin)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def set_message(self, message: str, state: str = "idle") -> None:
        self._message = message
        self._state = state
        self.update()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy and not self._timer.isActive():
            self._timer.start()
        elif not busy and self._timer.isActive():
            self._timer.stop()
        self.update()

    def _spin(self) -> None:
        self._angle = (self._angle + 7) % 360
        self.update()

    def _colors(self) -> tuple[QColor, QColor, bool]:
        t = self._theme
        art = t.art
        if self._state == "ok":
            return C(t.ok_bg), C(t.ok_fg), False
        if self._state == "erro":
            return C(t.err_bg), C(t.err_fg), False
        if self._state == "aviso":
            return C(t.warn_bg), C(t.warn_fg), False
        return (
            C(art.status_bg or t.surface_alt, 190),
            C(art.status_fg or t.text_secondary),
            True,
        )

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg, fg, bordered = self._colors()
        art = t.art

        p.setPen(QPen(C(art.status_border or t.border), 1)
                 if bordered else Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, 10, 10)

        cy = self.height() / 2
        dot_color = fg if not bordered else C(art.status_dot or t.accent)
        halo = QColor(dot_color)
        halo.setAlpha(30)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(14, cy), 5.6, 5.6)
        p.setBrush(dot_color)
        p.drawEllipse(QPointF(14, cy), 3.1, 3.1)

        font = F(
            art.status_size,
            family=art.status_font or art.ui_font,
            tracking=tracking_px(art.status_tracking, art.status_size),
            caps=art.status_transform == "uppercase",
        )
        p.setFont(font)
        fm = QFontMetrics(font)
        right_pad = 34 if self._busy else 14
        available = int(self.width() - 26 - right_pad)
        text = fm.elidedText(self._message, Qt.TextElideMode.ElideRight, max(20, available))
        p.setPen(fg)
        p.drawText(QRectF(26, 0, max(20, available), self.height()),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)

        if self._busy:
            spinner = QRectF(self.width() - 24, cy - 6, 12, 12)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(spinner, int(-self._angle * 16), int(280 * 16))


# ══════════════════════════════════════════════════════════════════════════════
#  CHECKBOX DESENHADO À MÃO
# ══════════════════════════════════════════════════════════════════════════════
class CheckBox(QAbstractButton):
    """Checkbox no vocabulário visual do app (caixa arredondada + check)."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._hover = False
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(1, (self.height() - 16) / 2, 16, 16)
        checked = self.isChecked()
        enabled = self.isEnabled()

        if checked:
            p.setPen(QPen(C(t.accent), 1.2))
            p.setBrush(C(t.accent))
        else:
            p.setPen(QPen(C(t.accent if self._hover else t.border_strong), 1.2))
            p.setBrush(C(t.field_bg))
        p.drawRoundedRect(box, 4.5, 4.5)

        if checked:
            draw_check(
                p,
                QRectF(box.left() + 3.4, box.top() + 3.6,
                       box.width() - 6.8, box.height() - 7.2),
                C(t.on_accent),
                1.7,
            )

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.3))
            p.drawRoundedRect(box.adjusted(-2, -2, 2, 2), 6, 6)

        if self.text():
            font = F(11)
            p.setFont(font)
            p.setPen(C(t.text if enabled else t.text_muted))
            p.drawText(
                QRectF(24, 0, max(0, self.width() - 26), self.height()),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.text(),
            )

    def sizeHint(self) -> QSize:
        """Tamanho da caixa + texto.

        O ``QAbstractButton`` puro devolve 0×0 para este desenho customizado;
        sem um ``sizeHint`` o checkbox some dentro dos layouts.
        """
        if not self.text():
            return QSize(20, 20)
        largura = 30 + QFontMetrics(F(11)).horizontalAdvance(self.text())
        return QSize(largura, 22)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


# ══════════════════════════════════════════════════════════════════════════════
#  SELETOR DE JANELAS
# ══════════════════════════════════════════════════════════════════════════════
class ViewSwitch(QWidget):
    """Seletor mínimo de telas: duas palavras e uma pílula que desliza.

    É o antigo fichário reduzido ao essencial — sem lombo, sem abas
    trapezoidais, sem sobreposição. O peso visual fica todo no conteúdo.
    """

    tab_changed = pyqtSignal(int)

    HEIGHT = 30
    PAD = 3.0

    def __init__(self, labels: list[str], width: int = 268,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._current = 0
        self._hover = -1
        self._pos = 0.0
        self.setFixedSize(width, self.HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)
        for index, label in enumerate(labels):
            button = QPushButton(label, self)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setFlat(True)
            button.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            button.installEventFilter(self)
            self._group.addButton(button, index)
            layout.addWidget(button, 1)
            self._buttons.append(button)
        self._buttons[0].setChecked(True)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._group.buttonClicked.connect(self._on_clicked)

    # ── API ─────────────────────────────────────────────────────────────────
    def current_index(self) -> int:
        return self._current

    def set_current(self, index: int) -> None:
        index = max(0, min(len(self._buttons) - 1, index))
        self._current = index
        self._pos = float(index)
        self._buttons[index].setChecked(True)
        self._sync_buttons()
        self.update()

    # ── eventos ─────────────────────────────────────────────────────────────
    def _on_clicked(self, button: QPushButton) -> None:
        index = self._buttons.index(button)
        if index == self._current:
            return
        self._current = index
        self._sync_buttons()
        self._anim.stop()
        self._anim.setStartValue(float(self._pos))
        self._anim.setEndValue(float(index))
        self._anim.start()
        self.tab_changed.emit(index)

    def _on_anim(self, value) -> None:
        self._pos = float(value)
        self.update()

    def eventFilter(self, obj, event) -> bool:
        if obj in self._buttons:
            index = self._buttons.index(obj)
            if event.type() == QEvent.Type.Enter:
                self._hover = index
                self._sync_buttons()
            elif event.type() == QEvent.Type.Leave:
                if self._hover == index:
                    self._hover = -1
                    self._sync_buttons()
            elif event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
                self.update()
        return super().eventFilter(obj, event)

    # ── tema e pintura ──────────────────────────────────────────────────────
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self._sync_buttons()
        self.update()

    def _sync_buttons(self) -> None:
        t = self._theme
        for index, button in enumerate(self._buttons):
            if button.isChecked():
                color = t.art.view_active_fg or t.accent_soft_text
                weight = QFont.Weight.DemiBold
            elif index == self._hover:
                color = t.text
                weight = QFont.Weight.Medium
            else:
                color = t.text_secondary
                weight = QFont.Weight.Medium
            button.setFont(F(11, weight, family=t.art.ui_font))
            button.setStyleSheet(
                "QPushButton { background: transparent; border: none;"
                f" color: {color}; padding: 0px; }}"
                "QPushButton:focus { outline: none; }"
            )

    def _segment_rect(self, position: float) -> QRectF:
        count = max(1, len(self._buttons))
        seg_w = (self.width() - self.PAD * 2) / count
        return QRectF(
            self.PAD + position * seg_w + 1.0,
            self.PAD,
            seg_w - 2.0,
            self.height() - self.PAD * 2,
        )

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # trilho: quase transparente, só um fio para delimitar a área
        radius = (self.height() - 1) / 2
        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(C(t.field_border, 150), 1))
        p.setBrush(C(t.field_bg, 135))
        p.drawRoundedRect(track, radius, radius)

        # polegar da tela ativa: mancha de acento, desliza entre as opções
        thumb = self._segment_rect(self._pos)
        art = t.art
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(C(art.view_active_from or t.accent, 22))
        p.drawRoundedRect(thumb.adjusted(-2.0, -1.0, 2.0, 1.0),
                          thumb.height() / 2 + 1, thumb.height() / 2 + 1)
        if art.view_active_from:
            grad = QLinearGradient(thumb.topLeft(), thumb.bottomRight())
            grad.setColorAt(0.0, C(art.view_active_from))
            grad.setColorAt(1.0, C(art.view_active_to or art.view_active_from))
            brush = QBrush(grad)
        else:
            brush = C(t.accent_soft, 255)
        borda_vs = C(art.view_active_border or t.accent,
                     255 if art.view_active_border else 135)
        p.setPen(QPen(borda_vs, 1))
        p.setBrush(brush)
        p.drawRoundedRect(thumb, thumb.height() / 2, thumb.height() / 2)

        # foco por teclado: um anel discreto na opção que está com o foco
        for index, button in enumerate(self._buttons):
            if not button.hasFocus():
                continue
            ring = self._segment_rect(float(index)).adjusted(1.0, 1.0, -1.0, -1.0)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent, 170), 1.2))
            p.drawRoundedRect(ring, ring.height() / 2, ring.height() / 2)


class PageSwap(QWidget):
    """Troca de tela como troca de janela: uma dissolve na outra.

    As duas páginas ocupam exatamente o mesmo retângulo e têm o mesmo tamanho.
    A que sai é fotografada e a foto se apaga sobre a nova — nada desliza, nada
    reflui e a janela não muda de tamanho, então o conteúdo não dá a sensação
    de rolagem.
    """

    DURATION = 240

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pages: list[QWidget] = []
        self._current = -1
        self._transition: QPropertyAnimation | None = None
        self._overlay: QLabel | None = None
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ── API ─────────────────────────────────────────────────────────────────
    def add_page(self, page: QWidget) -> None:
        page.setParent(self)
        page.setGeometry(self.rect())
        page.hide()
        self._pages.append(page)

    def current_index(self) -> int:
        return self._current

    def finish(self) -> None:
        """Encerra a dissolução em andamento (antes de fotografar a tela)."""
        self._finish_now()

    def set_current(self, index: int, animate: bool = True) -> None:
        if not self._pages:
            return
        index = max(0, min(len(self._pages) - 1, index))
        if index == self._current:
            return
        self._finish_now()
        if self._current < 0:
            self._settle(index)
            return

        old = self._pages[self._current]
        new = self._pages[index]
        self._current = index

        if not animate or not self.isVisible() or self.height() < 24:
            self._settle(index)
            return
        self._dissolve(old, new)

    # ── transição ───────────────────────────────────────────────────────────
    def _capture(self) -> QPixmap:
        """Foto da área das telas, já com o céu atrás (nada de retângulo opaco)."""
        window = self.window()
        origin = self.mapTo(window, QPoint(0, 0))
        return window.grab(QRect(origin, self.size()))

    def _dissolve(self, old: QWidget, new: QWidget) -> None:
        # A foto da tela que sai dissolve sobre a nova. Nenhum widget vivo
        # recebe efeito de opacidade — o texto continua nítido até sumir e a
        # troca não mexe em layout, posição ou tamanho de coisa alguma.
        foto = self._capture()

        overlay = QLabel(self)
        overlay.setObjectName("SwapFrame")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        overlay.setStyleSheet("background: transparent; border: none;")
        overlay.setPixmap(foto)
        overlay.setGeometry(self.rect())

        new.setGeometry(self.rect())
        new.move(0, 0)
        new.show()
        new.raise_()
        old.hide()

        overlay.show()
        overlay.raise_()

        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(1.0)
        overlay.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(self.DURATION)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self._finish(anim, overlay))

        self._transition = anim
        self._overlay = overlay
        anim.start()

    def _finish(self, anim: QPropertyAnimation, overlay: QLabel) -> None:
        if anim is not self._transition:
            return
        self._transition = None
        self._overlay = None
        overlay.deleteLater()
        anim.deleteLater()
        self._settle(self._current)

    def _finish_now(self) -> None:
        anim, self._transition = self._transition, None
        overlay, self._overlay = self._overlay, None
        if anim is not None:
            anim.stop()
            anim.deleteLater()
        if overlay is not None:
            overlay.hide()
            overlay.deleteLater()
        if self._current >= 0:
            self._settle(self._current)

    def _settle(self, index: int) -> None:
        self._current = index
        for i, page in enumerate(self._pages):
            page.setGeometry(self.rect())
            page.move(0, 0)
            page.setVisible(i == index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._transition is None:
            for page in self._pages:
                page.setGeometry(self.rect())


# ══════════════════════════════════════════════════════════════════════════════
#  ABA DE ENVIO DE E-MAILS
# ══════════════════════════════════════════════════════════════════════════════
ENVIO_ASSUNTO_PADRAO = "{fornecedor} — Relatório de pagamento"
ENVIO_CORPO_PADRAO = (
    "Olá, {fornecedor}!\n\n"
    "Segue em anexo o relatório de pagamento referente ao último pagamento "
    "realizado.\n\n"
    "Em caso de dúvidas, permanecemos à disposição.\n\n"
    "Atenciosamente,\n"
    "Time Fretes - Distribuição Farma"
)


class ConfirmarEnvioDialog(QDialog):
    """Tabela de revisão: cada arquivo xlsx ↔ Transportadora, antes do disparo."""

    _COLUNAS = ["", "Arquivo", "Fornecedor", "Transportadora", "E-mails", "Situação", "Avisos"]

    def __init__(self, plano, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plano = plano
        self._theme = theme
        self._groups = list(plano.grupos)
        self._checks: list[CheckBox] = []
        self._building = True

        self.setWindowTitle("Confirmar envio dos relatórios")
        self.setModal(True)
        self.setMinimumSize(760, 480)
        self.resize(1040, 660)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._populate()
        self._sync_theme()
        self._building = False
        self._update_selection()
        self.table.setFocus()

    # ── construção ──────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(8)

        eyebrow = QLabel("REVISÃO • DISPARO REAL", self)
        eyebrow.setObjectName("CardEyebrow")
        layout.addWidget(eyebrow)

        title = QLabel("Confirme os e-mails antes de enviar", self)
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Cada linha é um arquivo do PagFlow relacionado à sua Transportadora "
            "na planilha de contatos. Ao confirmar, os e-mails marcados serão "
            "enviados imediatamente pelo Outlook Desktop, com o arquivo anexado. "
            "Bloqueios e documentos KT (CFD) entram automaticamente no corpo.",
            self,
        )
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.question = QLabel("Tem certeza que deseja enviar 0 e-mail(s)?", self)
        self.question.setObjectName("DialogQuestion")
        self.question.setWordWrap(True)
        layout.addWidget(self.question)

        topo = QHBoxLayout()
        topo.setSpacing(10)
        self.stats = QLabel(self._plano.resumo(), self)
        self.stats.setObjectName("Hint")
        self.stats.setWordWrap(True)
        topo.addWidget(self.stats, 1)
        layout.addLayout(topo)

        # [gerado] Seleção em massa, em linha própria acima da tabela
        linha_selecao = QHBoxLayout()
        linha_selecao.setSpacing(10)

        self.select_all = CheckBox("Selecionar todos", self)
        self.select_all.setToolTip(
            "Marcar ou desmarcar todos os grupos prontos para envio"
        )
        self.select_all.setChecked(True)
        self.select_all.toggled.connect(self._toggle_all)
        linha_selecao.addWidget(self.select_all, 0)

        dica_selecao = QLabel(
            "Inclui todos os grupos prontos; os grupos com pendência "
            "continuam bloqueados.",
            self,
        )
        dica_selecao.setObjectName("Hint")
        dica_selecao.setWordWrap(True)
        linha_selecao.addWidget(dica_selecao, 1)
        layout.addLayout(linha_selecao)

        self.table = QTableWidget(0, len(self._COLUNAS), self)
        self.table.setObjectName("confirmTable")
        self.table.setHorizontalHeaderLabels(self._COLUNAS)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(34)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(40)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 42)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(5, 160)
        self.table.setColumnWidth(6, 210)
        layout.addWidget(self.table, 1)

        rodape = QHBoxLayout()
        rodape.setSpacing(10)
        self.selection_label = QLabel("", self)
        self.selection_label.setObjectName("SelectionLabel")
        rodape.addWidget(self.selection_label, 1)

        self.cancel_button = PillButton("Cancelar", "secondary", width=110, parent=self)
        self.cancel_button.clicked.connect(self.reject)
        rodape.addWidget(self.cancel_button, 0)

        self.confirm_button = PillButton("Confirmar envio", "primary", width=180, parent=self)
        self.confirm_button.clicked.connect(self._on_confirm)
        rodape.addWidget(self.confirm_button, 0)
        layout.addLayout(rodape)

    def showEvent(self, event) -> None:
        """Limita o diálogo à área útil da tela (telas baixas/DPI alto)."""
        super().showEvent(event)
        screen = self.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        max_w = max(self.minimumWidth(), area.width() - 40)
        max_h = max(self.minimumHeight(), area.height() - 40)
        self.resize(min(self.width(), max_w), min(self.height(), max_h))
        self.move(area.center().x() - self.width() // 2,
                  area.center().y() - self.height() // 2)

    def _populate(self) -> None:
        self.table.setRowCount(len(self._groups))
        for linha, grupo in enumerate(self._groups):
            self._fill_row(linha, grupo)

    def _sync_theme(self) -> None:
        """Propaga o tema para os controles desenhados à mão no diálogo."""
        for check in self.findChildren(CheckBox):
            check.set_theme(self._theme)
        for botao in self.findChildren(PillButton):
            botao.set_theme(self._theme)

    def _fill_row(self, linha: int, grupo) -> None:
        container = QWidget(self.table)
        cl = QHBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        check = CheckBox("", container)
        check.setChecked(grupo.pronto)
        check.setEnabled(grupo.pronto)
        check.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        check.setToolTip(
            f"Incluir {grupo.nome} no envio" if grupo.pronto
            else (grupo.detalhe or grupo.rotulo_status)
        )
        check.toggled.connect(self._update_selection)
        cl.addWidget(check)
        self.table.setCellWidget(linha, 0, container)
        self._checks.append(check)

        arquivo = QTableWidgetItem(grupo.arquivo.name)
        arquivo.setToolTip(str(grupo.arquivo))
        self.table.setItem(linha, 1, arquivo)

        fornecedor = QTableWidgetItem(
            ", ".join(grupo.fornecedores) if grupo.fornecedores else "—"
        )
        fornecedor.setToolTip(
            "Código(s) de fornecedor encontrados no arquivo "
            "(uma transportadora pode ter vários)"
        )
        self.table.setItem(linha, 2, fornecedor)

        nome = QTableWidgetItem(grupo.nome or "—")
        fonte = QFont(nome.font())
        fonte.setBold(True)
        nome.setFont(fonte)
        nome.setToolTip(grupo.nome or grupo.rotulo_status)
        self.table.setItem(linha, 3, nome)

        para = QTableWidgetItem("; ".join(grupo.para) if grupo.para else "—")
        para.setToolTip("\n".join(grupo.para))
        para.setForeground(
            QBrush(C(self._theme.ok_fg)) if grupo.para
            else QBrush(C(self._theme.text_muted))
        )
        self.table.setItem(linha, 4, para)

        situacao = QTableWidgetItem(grupo.rotulo_status)
        situacao.setForeground(
            QBrush(C(self._theme.ok_fg)) if grupo.pronto
            else QBrush(C(self._theme.err_fg))
        )
        situacao.setToolTip(grupo.detalhe or grupo.rotulo_status)
        self.table.setItem(linha, 5, situacao)

        avisos = QTableWidgetItem(grupo.resumo_avisos or "—")
        avisos.setForeground(
            QBrush(C(self._theme.warn_fg)) if grupo.tem_avisos
            else QBrush(C(self._theme.text_muted))
        )
        avisos.setToolTip(
            "Avisos incluídos automaticamente no corpo do e-mail."
            if grupo.tem_avisos
            else "Sem bloqueios e sem documentos KT (CFD) neste arquivo."
        )
        self.table.setItem(linha, 6, avisos)

    # ── seleção ─────────────────────────────────────────────────────────────
    def selected_keys(self) -> list[str]:
        chaves: list[str] = []
        for indice, grupo in enumerate(self._groups):
            if not grupo.pronto:
                continue
            if indice < len(self._checks) and self._checks[indice].isChecked():
                chaves.append(grupo.chave)
        return chaves

    def _toggle_all(self, marcado: bool) -> None:
        if self._building:
            return
        for indice, grupo in enumerate(self._groups):
            if not grupo.pronto:
                continue
            check = self._checks[indice]
            check.blockSignals(True)
            check.setChecked(marcado)
            check.blockSignals(False)
        self._update_selection()

    def _update_selection(self, *_: object) -> None:
        if self._building:
            return
        selecionados = len(self.selected_keys())
        prontos = len(self._plano.prontos)
        self.selection_label.setText(
            f"{selecionados} de {prontos} grupo(s) pronto(s) selecionado(s)"
        )
        self.question.setText(
            f"Tem certeza que deseja enviar {selecionados} e-mail(s)?"
        )
        self.confirm_button.setEnabled(selecionados > 0)
        self.confirm_button.setText(
            f"Confirmar envio ({selecionados})" if selecionados else "Confirmar envio"
        )

        self.select_all.blockSignals(True)
        self.select_all.setChecked(selecionados == prontos and prontos > 0)
        self.select_all.blockSignals(False)

    def _on_confirm(self) -> None:
        if not self.selected_keys():
            return
        self.accept()


class EnvioPage(QWidget):
    """Conteúdo da aba 'Envio de e-mails'."""

    status_requested = pyqtSignal(str, object)
    _plan_finished = pyqtSignal(object)
    _send_finished = pyqtSignal(object)
    _failed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._settings = QSettings("PagFlow", "PagFlow")
        self._running = False
        self._plano = None

        self._build_ui()
        self._restore_settings()

        self._plan_finished.connect(self._handle_plan)
        self._send_finished.connect(self._handle_send_result)
        self._failed.connect(self._handle_error)

    # ── construção ──────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 1 · planilha de contatos ───────────────────────────────────────
        self._section(root, "1", "Planilha de contatos")
        row1 = QWidget(self)
        row1_lay = QHBoxLayout(row1)
        row1_lay.setContentsMargins(0, 0, 0, 0)
        row1_lay.setSpacing(8)
        self.entry_contatos = self._entry(
            "Transportadora · Fornecedor · E-mails (arquivo .xlsx)"
        )
        self.btn_contatos = IconButton("file", "Selecionar planilha de contatos", row1)
        self.btn_contatos.clicked.connect(self._browse_contatos)
        row1_lay.addWidget(self.entry_contatos, 1)
        row1_lay.addWidget(self.btn_contatos, 0)
        root.addWidget(row1)
        root.addSpacing(9)

        # ── 2 · pasta dos relatórios ───────────────────────────────────────
        self._section(root, "2", "Pasta com os relatórios gerados")
        row2 = QWidget(self)
        row2_lay = QHBoxLayout(row2)
        row2_lay.setContentsMargins(0, 0, 0, 0)
        row2_lay.setSpacing(8)
        self.entry_pasta = self._entry("Selecione a pasta...")
        self.btn_pasta = IconButton("folder", "Selecionar pasta com os relatórios", row2)
        self.btn_pasta.clicked.connect(self._browse_pasta)
        row2_lay.addWidget(self.entry_pasta, 1)
        row2_lay.addWidget(self.btn_pasta, 0)
        root.addWidget(row2)
        root.addSpacing(5)

        aviso = QLabel(
            "Um arquivo pode conter vários códigos de fornecedor, desde que "
            "todos sejam da mesma transportadora.",
            self,
        )
        aviso.setObjectName("Hint")
        aviso.setWordWrap(True)
        root.addWidget(aviso)
        root.addSpacing(8)

        # ── 3 · mensagem ───────────────────────────────────────────────────
        self._section(root, "3", "Mensagem")
        caption_assunto = QLabel("ASSUNTO", self)
        caption_assunto.setObjectName("FieldCaption")
        root.addWidget(caption_assunto)
        self.entry_assunto = self._entry("ex.: {fornecedor} — Relatório de pagamento")
        root.addWidget(self.entry_assunto)
        root.addSpacing(6)

        # legenda do corpo e atalhos dividem a mesma linha: o editor ganha altura
        row_corpo = QWidget(self)
        corpo_lay = QHBoxLayout(row_corpo)
        corpo_lay.setContentsMargins(0, 0, 0, 0)
        corpo_lay.setSpacing(7)

        caption_corpo = QLabel("CORPO", row_corpo)
        caption_corpo.setObjectName("FieldCaption")
        corpo_lay.addWidget(caption_corpo, 0, Qt.AlignmentFlag.AlignVCenter)

        dica_corpo = QLabel("{fornecedor} → Transportadora (Nome Simples)", row_corpo)
        dica_corpo.setObjectName("FieldCaption")
        dica_corpo.setToolTip(
            "A variável {fornecedor} é substituída pela Transportadora "
            "(Nome Simples) localizada pelo código na planilha de contatos."
        )
        corpo_lay.addWidget(dica_corpo, 0, Qt.AlignmentFlag.AlignVCenter)
        corpo_lay.addStretch(1)

        self.btn_inserir = PillButton("Inserir {fornecedor}", "secondary",
                                      width=126, height=24, font_px=10,
                                      parent=row_corpo)
        self.btn_inserir.clicked.connect(self._insert_placeholder)
        corpo_lay.addWidget(self.btn_inserir, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_restaurar = PillButton("Restaurar", "secondary",
                                        width=82, height=24, font_px=10,
                                        parent=row_corpo)
        self.btn_restaurar.setToolTip("Voltar ao assunto e ao corpo padrão")
        self.btn_restaurar.clicked.connect(self._restore_defaults)
        corpo_lay.addWidget(self.btn_restaurar, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(row_corpo)
        root.addSpacing(4)

        self.body = QTextEdit(self)
        self.body.setObjectName("Body")
        self.body.setAcceptRichText(False)
        # Piso baixo para caber em telas pequenas/DPI alto; em telas normais o
        # editor recebe todo o espaço vertical restante (stretch).
        self.body.setMinimumHeight(100)
        self.body.setPlaceholderText("Escreva o corpo do e-mail…")
        root.addWidget(self.body, 1)

        root.addSpacing(4)
        self.divider = Divider(self)
        root.addWidget(self.divider)
        root.addSpacing(8)

        # ── ações ──────────────────────────────────────────────────────────
        row_actions = QWidget(self)
        actions = QHBoxLayout(row_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)
        self.lbl_resumo = QLabel("Pronto para preparar os envios.", row_actions)
        self.lbl_resumo.setObjectName("Hint")
        self.lbl_resumo.setWordWrap(True)
        actions.addWidget(self.lbl_resumo, 1)
        self.btn_preparar = PillButton("Preparar envios", "primary", glyph="mail",
                                       width=170, parent=row_actions)
        self.btn_preparar.clicked.connect(self._preparar)
        actions.addWidget(self.btn_preparar, 0)
        root.addWidget(row_actions)

        self._themed = [
            self.btn_contatos, self.btn_pasta, self.btn_inserir,
            self.btn_restaurar, self.btn_preparar, self.divider,
        ]

    def _section(self, layout: QVBoxLayout, number: str, title: str) -> None:
        row = QWidget(self)
        row.setFixedHeight(20)
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(8)

        chip = QLabel(number, row)
        chip.setObjectName("Chip")
        chip.setFixedSize(20, 20)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(title, row)
        label.setObjectName("SectionTitle")

        row_lay.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
        row_lay.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
        row_lay.addStretch(1)

        layout.addWidget(row)
        layout.addSpacing(3)

    def _entry(self, placeholder: str) -> QLineEdit:
        entry = QLineEdit(self)
        entry.setObjectName("Field")
        entry.setFixedHeight(32)
        entry.setPlaceholderText(placeholder)
        return entry

    # ── tema ────────────────────────────────────────────────────────────────
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        for widget in self._themed:
            widget.set_theme(theme)
        for entry in (self.entry_contatos, self.entry_pasta, self.entry_assunto):
            pal = entry.palette()
            pal.setColor(QPalette.ColorRole.PlaceholderText, C(theme.placeholder))
            entry.setPalette(pal)

    # ── navegação de arquivos ───────────────────────────────────────────────
    def _browse_contatos(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar planilha de contatos", "",
            "Planilhas do Excel (*.xlsx *.xlsm)",
        )
        if path:
            self.entry_contatos.setText(path)
            self._save_settings()
            self.status_requested.emit(
                f"Planilha de contatos: {os.path.basename(path)}", "idle"
            )

    def _browse_pasta(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta com os relatórios"
        )
        if path:
            self.entry_pasta.setText(path)
            self._save_settings()
            self.status_requested.emit(
                f"Pasta de relatórios: {os.path.basename(path)}", "idle"
            )

    # ── editor de corpo ─────────────────────────────────────────────────────
    def _insert_placeholder(self) -> None:
        self.body.insertPlainText("{fornecedor}")
        self.body.setFocus()

    def _restore_defaults(self) -> None:
        resposta = QMessageBox.question(
            self, "Restaurar padrão",
            "Substituir o assunto e o corpo atuais pelo texto padrão?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self.entry_assunto.setText(ENVIO_ASSUNTO_PADRAO)
        self.body.setPlainText(ENVIO_CORPO_PADRAO)

    # ── fluxo de envio ──────────────────────────────────────────────────────
    def _preparar(self) -> None:
        if self._running:
            return
        contatos = self.entry_contatos.text().strip()
        pasta = self.entry_pasta.text().strip()
        assunto = self.entry_assunto.text().strip()
        corpo = self.body.toPlainText().strip()

        faltando: list[str] = []
        if not contatos:
            faltando.append("Selecione a planilha de contatos.")
        if not pasta:
            faltando.append("Selecione a pasta com os relatórios.")
        if not assunto:
            faltando.append("Escreva o assunto do e-mail.")
        if not corpo:
            faltando.append("Escreva o corpo do e-mail.")
        if faltando:
            self._show_error("Configuração incompleta", "\n\n".join(faltando))
            return

        self._save_settings()
        self._set_running(True)
        self.lbl_resumo.setText("Preparando os grupos de envio…")
        self.status_requested.emit("Preparando envios…", "idle")

        def rodar() -> None:
            try:
                from envios import montar_plano
                plano = montar_plano(contatos, pasta, assunto=assunto, corpo=corpo)
                self._plan_finished.emit(plano)
            except Exception as erro:  # noqa: BLE001
                self._failed.emit(str(erro))

        threading.Thread(target=rodar, daemon=True).start()

    def _handle_plan(self, plano) -> None:
        self._set_running(False)
        self._plano = plano
        self.lbl_resumo.setText(plano.resumo())
        self.status_requested.emit("Plano pronto — confirme o envio", "idle")

        dialogo = ConfirmarEnvioDialog(plano, self._theme, self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            self.status_requested.emit("Envio cancelado antes do disparo", "aviso")
            return

        chaves = dialogo.selected_keys()
        if not chaves:
            self.status_requested.emit("Nenhum grupo selecionado", "aviso")
            return
        self._enviar(plano, chaves)

    def _enviar(self, plano, chaves: list[str]) -> None:
        self._set_running(True)
        total = len(chaves)
        self.status_requested.emit(f"Enviando {total} e-mail(s)…", "idle")

        def rodar() -> None:
            try:
                from envios import enviar_plano
                resultado = enviar_plano(plano, chaves, on_progress=self._on_progress)
                self._send_finished.emit(resultado)
            except Exception as erro:  # noqa: BLE001
                self._failed.emit(str(erro))

        threading.Thread(target=rodar, daemon=True).start()

    def _on_progress(self, atual: int, total: int, nome: str) -> None:
        self.status_requested.emit(f"Enviando {atual} de {total} — {nome}", "idle")

    def _handle_send_result(self, resultado) -> None:
        self._set_running(False)
        resumo = (
            f"{len(resultado.enviados)} enviado(s) · "
            f"{len(resultado.falhos)} falha(s) · "
            f"{len(resultado.nao_encontrados)} não encontrado(s)"
        )
        if resultado.cancelado:
            resumo += " · cancelado"
        self.lbl_resumo.setText(resumo)

        estado = "aviso" if (resultado.falhos or resultado.cancelado) else "idle"
        self.status_requested.emit(resumo, estado)

        icone = (
            QMessageBox.Icon.Warning
            if (resultado.falhos or resultado.cancelado)
            else QMessageBox.Icon.Information
        )
        caixa = QMessageBox(self)
        caixa.setIcon(icone)
        caixa.setWindowTitle("Envios PagFlow")
        caixa.setText("Envio finalizado.\n\n" + resumo)
        caixa.exec()

    def _handle_error(self, mensagem: str) -> None:
        self._set_running(False)
        self.status_requested.emit("Falha ao preparar/enviar os e-mails", "erro")
        self._show_error("Envios PagFlow", mensagem)

    def _set_running(self, running: bool) -> None:
        self._running = running
        for control in (
            self.entry_contatos, self.entry_pasta, self.entry_assunto, self.body,
            self.btn_contatos, self.btn_pasta, self.btn_inserir, self.btn_restaurar,
            self.btn_preparar,
        ):
            control.setEnabled(not running)

    # ── persistência ────────────────────────────────────────────────────────
    def _save_settings(self) -> None:
        self._settings.setValue("envios/contatos", self.entry_contatos.text().strip())
        self._settings.setValue("envios/pasta", self.entry_pasta.text().strip())
        self._settings.setValue("envios/assunto", self.entry_assunto.text())
        self._settings.setValue("envios/corpo", self.body.toPlainText())

    def _restore_settings(self) -> None:
        contatos = str(self._settings.value("envios/contatos", "") or "")
        pasta = str(self._settings.value("envios/pasta", "") or "")
        assunto = str(self._settings.value("envios/assunto", "") or "")
        corpo = str(self._settings.value("envios/corpo", "") or "")
        # [gerado] Migra a assinatura antiga salva nas preferências do usuário
        if "Equipe Financeira" in corpo:
            corpo = corpo.replace(
                "Equipe Financeira", "Time Fretes - Distribuição Farma"
            )
        if contatos:
            self.entry_contatos.setText(contatos)
        if pasta:
            self.entry_pasta.setText(pasta)
        self.entry_assunto.setText(assunto or ENVIO_ASSUNTO_PADRAO)
        self.body.setPlainText(corpo or ENVIO_CORPO_PADRAO)

    # ── utilitários ─────────────────────────────────────────────────────────
    def _show_error(self, titulo: str, mensagem: str) -> None:
        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Icon.Warning)
        caixa.setWindowTitle(titulo)
        caixa.setText(mensagem)
        caixa.setStandardButtons(QMessageBox.StandardButton.Ok)
        caixa.exec()


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
class GlyphBadge(QWidget):
    """Quadrado com o glifo de chave (cabeçalho da aba de código)."""

    def __init__(self, parent: QWidget | None = None, size: int = 38) -> None:
        super().__init__(parent)
        self._theme = DARK
        self.setFixedSize(size, size)

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        t = self._theme
        art = t.art
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(C(art.badge_border or t.border), 1))
        p.setBrush(C(art.badge_bg or t.accent_soft))
        p.drawRoundedRect(rect, 12, 12)
        draw_key(p, QRectF(self.width() * 0.24, self.height() * 0.24,
                           self.width() * 0.52, self.height() * 0.52),
                 C(art.badge_fg or t.accent_soft_text), 1.4)


class CloseButton(QAbstractButton):
    """Botão de fechar desenhado (sem depender de fonte/emoji)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self._hover = False
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Fechar")
        self.setAccessibleName("Fechar")

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return,
                           Qt.Key.Key_Enter):
            self.click()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(C(t.accent if self._hover else t.border), 1))
        p.setBrush(C(t.surface_alt if self._hover else t.surface))
        p.drawRoundedRect(rect, 8, 8)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.4))
            p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
        p.setPen(QPen(C(t.text if self._hover else t.text_secondary), 1.6,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        w, h = self.width(), self.height()
        p.drawLine(QPointF(w * 0.36, h * 0.36), QPointF(w * 0.64, h * 0.64))
        p.drawLine(QPointF(w * 0.64, h * 0.36), QPointF(w * 0.36, h * 0.64))


class ThemeCard(QAbstractButton):
    """Cartão de tema na aba Aparência (desenhado, não QSS)."""

    def __init__(self, theme: Theme, active: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._active = active
        self._hover = False
        self.setFixedHeight(74)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"Tema {theme.label}")

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        t = self._theme
        art = t.art
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        destaque = self._active or self._hover
        p.setPen(QPen(C(t.accent if destaque else t.border), 1))
        p.setBrush(C(t.accent_soft if self._active else t.bg_top))
        p.drawRoundedRect(rect, 12, 12)

        # barra de acento à esquerda quando ativo
        if self._active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(C(t.accent))
            p.drawRoundedRect(QRectF(rect.left() + 1, rect.top() + 14, 3,
                                     rect.height() - 28), 1.5, 1.5)

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.4))
            p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)

        nome_font = F(14, QFont.Weight.DemiBold, family=art.ui_font)
        p.setFont(nome_font)
        p.setPen(C(t.text))
        nome = QFontMetrics(nome_font).elidedText(
            self._theme.label, Qt.TextElideMode.ElideRight,
            int(rect.width() - 92))
        p.drawText(QRectF(rect.left() + 15, rect.top() + 7, rect.width() - 88, 21),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                       | Qt.TextFlag.TextDontClip),
                   nome)

        descricao = art.description or {
            "dark": "Céu noturno azul-marinho, com estrelas que respiram.",
            "light": "Céu diurno, com destaque em azul-celeste.",
        }.get(self._theme.key, "")
        p.setFont(F(9, family=art.ui_font))
        p.setPen(C(t.text_secondary))
        p.drawText(QRectF(rect.left() + 17, rect.top() + 31, rect.width() - 34,
                          rect.height() - 39),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                       | Qt.TextFlag.TextWordWrap),
                   descricao)

        if self._active:
            pill_font = F(8, QFont.Weight.Bold, tracking=0.7, family=art.ui_font)
            fm = QFontMetrics(pill_font)
            largura = fm.horizontalAdvance("ATIVO") + 16
            pill = QRectF(rect.right() - largura - 12, rect.top() + 8, largura, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(C(t.accent))
            p.drawRoundedRect(pill, 9, 9)
            p.setFont(pill_font)
            p.setPen(C(t.on_accent))
            p.drawText(pill, int(Qt.AlignmentFlag.AlignCenter), "ATIVO")


class DragBar(QWidget):
    """Cabeçalho arrastável de uma janela sem moldura."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._offset: QPoint | None = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._offset = None
        event.accept()


class SettingsDialog(QDialog):
    """Configurações do app: Geral, Aparência, Inserir código e Sobre."""

    theme_selected = pyqtSignal(str)
    theme_unlocked = pyqtSignal(str)
    reduced_changed = pyqtSignal(bool)
    forget_requested = pyqtSignal()

    def __init__(self, theme: Theme, settings: QSettings,
                 unlocked: set[str], reduced: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._settings = settings
        self._unlocked = set(unlocked)
        self._reduced = bool(reduced)
        self._cards: list[ThemeCard] = []

        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Configurações")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(720, 560)
        self.resize(760, 600)

        self._build()
        self.set_theme(theme)
        self._refresh_cards()

    # ── construção ──────────────────────────────────────────────────────────
    def _build(self) -> None:
        externo = QVBoxLayout(self)
        externo.setContentsMargins(12, 12, 12, 12)
        externo.setSpacing(0)

        self.shell = QFrame(self)
        self.shell.setObjectName("SettingsShell")
        externo.addWidget(self.shell)
        sombra = QGraphicsDropShadowEffect(self.shell)
        sombra.setBlurRadius(48)
        sombra.setOffset(0, 18)
        sombra.setColor(QColor(0, 0, 0, 120))
        self.shell.setGraphicsEffect(sombra)

        corpo = QVBoxLayout(self.shell)
        corpo.setContentsMargins(24, 18, 24, 16)
        corpo.setSpacing(0)

        # cabeçalho
        self.head = DragBar(self.shell)
        self.head.setFixedHeight(74)
        head_lay = QHBoxLayout(self.head)
        head_lay.setContentsMargins(0, 0, 0, 0)
        head_lay.setSpacing(12)

        titulos = QVBoxLayout()
        titulos.setContentsMargins(0, 0, 0, 0)
        titulos.setSpacing(2)
        self.lbl_eyebrow = QLabel("PAGFLOW · AJUSTES", self.head)
        self.lbl_eyebrow.setObjectName("SettingsEyebrow")
        self.lbl_title = QLabel("Configurações", self.head)
        self.lbl_title.setObjectName("SettingsTitle")
        self.lbl_sub = QLabel("Ajustes do aplicativo", self.head)
        self.lbl_sub.setObjectName("SettingsSub")
        titulos.addWidget(self.lbl_eyebrow)
        titulos.addWidget(self.lbl_title)
        titulos.addWidget(self.lbl_sub)
        head_lay.addLayout(titulos, 1)

        self.btn_close = CloseButton(self.head)
        self.btn_close.clicked.connect(self.reject)
        head_lay.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignTop)
        corpo.addWidget(self.head)
        corpo.addSpacing(8)

        # abas
        abas = QWidget(self.shell)
        abas.setFixedHeight(34)
        abas_lay = QHBoxLayout(abas)
        abas_lay.setContentsMargins(0, 0, 0, 4)
        abas_lay.setSpacing(6)
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tabs: list[QPushButton] = []
        for indice, texto in enumerate(("Geral", "Aparência", "Inserir código", "Sobre")):
            botao = QPushButton(texto, abas)
            botao.setObjectName("SettingsTab")
            botao.setCheckable(True)
            botao.setCursor(Qt.CursorShape.PointingHandCursor)
            botao.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            botao.setFlat(True)
            self._tab_group.addButton(botao, indice)
            abas_lay.addWidget(botao, 0)
            self._tabs.append(botao)
        abas_lay.addStretch(1)
        self._tabs[2].setChecked(True)
        corpo.addWidget(abas)

        # páginas
        self.pages = QStackedWidget(self.shell)
        self.pages.addWidget(self._page_geral())
        self.pages.addWidget(self._page_aparencia())
        self.pages.addWidget(self._page_codigo())
        self.pages.addWidget(self._page_sobre())
        self.pages.setCurrentIndex(2)
        self._tab_group.idClicked.connect(self.pages.setCurrentIndex)
        corpo.addWidget(self.pages, 1)

        # rodapé
        corpo.addSpacing(8)
        self.footer_divider = Divider(self.shell)
        corpo.addWidget(self.footer_divider)
        corpo.addSpacing(8)
        rodape = QHBoxLayout()
        rodape.setContentsMargins(0, 0, 0, 0)
        rodape.setSpacing(10)
        nota = QLabel("As alterações são aplicadas na hora.", self.shell)
        nota.setObjectName("Hint")
        rodape.addWidget(nota, 0)
        rodape.addStretch(1)
        self.btn_fechar = PillButton("Fechar", "secondary", width=108,
                                     parent=self.shell)
        self.btn_fechar.clicked.connect(self.accept)
        rodape.addWidget(self.btn_fechar, 0)
        corpo.addLayout(rodape)

    # ── páginas ─────────────────────────────────────────────────────────────
    def _page_geral(self) -> QWidget:
        pagina = QWidget(self.shell)
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(10)

        self._eyebrow_geral = self._eyebrow("PREFERÊNCIAS", pagina)
        lay.addWidget(self._eyebrow_geral)
        self._title_geral = self._titulo("Geral", pagina)
        lay.addWidget(self._title_geral)
        lay.addWidget(self._copy(
            "Preferências básicas do aplicativo. Nada aqui altera o "
            "processamento dos relatórios.", pagina))

        card = QFrame(pagina)
        card.setObjectName("SettingsCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        linha = QHBoxLayout()
        linha.setSpacing(10)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        nome = QLabel("Animações", card)
        nome.setObjectName("SelectionLabel")
        nome.setFont(F(11, QFont.Weight.DemiBold))
        detalhe = QLabel("As estrelas do tema escuro ficam estáticas.", card)
        detalhe.setObjectName("Hint")
        textos.addWidget(nome)
        textos.addWidget(detalhe)
        linha.addLayout(textos, 1)
        self.check_reduzir = CheckBox("Reduzir animações", card)
        self.check_reduzir.setChecked(self._reduced)
        self.check_reduzir.toggled.connect(self._on_reduced)
        linha.addWidget(self.check_reduzir, 0)
        card_lay.addLayout(linha)

        divisor = QFrame(card)
        divisor.setObjectName("CodeDivider")
        divisor.setFixedHeight(1)
        card_lay.addWidget(divisor)

        versao = QLabel(f"PagFlow Excel · versão {APP_VERSION}", card)
        versao.setObjectName("Hint")
        card_lay.addWidget(versao)

        lay.addWidget(card)
        lay.addStretch(1)
        return pagina

    def _page_aparencia(self) -> QWidget:
        pagina = QWidget(self.shell)
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(8)

        self._eyebrow_ap = self._eyebrow("APARÊNCIA", pagina)
        lay.addWidget(self._eyebrow_ap)
        self._title_ap = self._titulo("Temas", pagina)
        lay.addWidget(self._title_ap)
        lay.addWidget(self._copy(
            "Escuro e claro são os temas principais. Os temas secretos "
            "aparecem aqui só depois de desbloqueados por código.", pagina))

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)

        # A grade rola quando a tela é baixa (o diálogo pode encolher até 560).
        rolagem = QScrollArea(pagina)
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QFrame.Shape.NoFrame)
        rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rolagem.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        interno = QWidget(rolagem)
        interno_lay = QVBoxLayout(interno)
        interno_lay.setContentsMargins(0, 0, 0, 0)
        interno_lay.setSpacing(0)
        interno_lay.addLayout(self.grid)
        interno_lay.addStretch(1)
        rolagem.setWidget(interno)
        lay.addWidget(rolagem, 1)

        lay.addSpacing(4)
        rodape = QHBoxLayout()
        rodape.setSpacing(10)
        self.btn_restaurar = PillButton("Restaurar padrão PagFlow", "primary",
                                        width=230, parent=pagina)
        self.btn_restaurar.setToolTip("Voltar ao tema escuro original do PagFlow")
        self.btn_restaurar.clicked.connect(lambda: self.theme_selected.emit("dark"))
        rodape.addWidget(self.btn_restaurar, 0)
        dica = QLabel("Devolve o visual original. Os temas desbloqueados continuam "
                      "disponíveis.", pagina)
        dica.setObjectName("Hint")
        dica.setWordWrap(True)
        rodape.addWidget(dica, 1)
        lay.addLayout(rodape)
        return pagina

    def _page_codigo(self) -> QWidget:
        pagina = QWidget(self.shell)
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(0)

        colunas = QHBoxLayout()
        colunas.setContentsMargins(0, 0, 0, 0)
        colunas.setSpacing(16)

        card = QFrame(pagina)
        card.setObjectName("SettingsCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(18, 16, 18, 16)
        card_lay.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(12)
        self.badge = GlyphBadge(card)
        head.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        titulos = QVBoxLayout()
        titulos.setSpacing(1)
        self.lbl_code_eyebrow = QLabel("ACESSO RESTRITO", card)
        self.lbl_code_eyebrow.setObjectName("CodeEyebrow")
        self.lbl_code_title = QLabel("Ativar um tema pelo código", card)
        self.lbl_code_title.setObjectName("CodeTitle")
        self.lbl_code_title.setWordWrap(True)
        titulos.addWidget(self.lbl_code_eyebrow)
        titulos.addWidget(self.lbl_code_title)
        head.addLayout(titulos, 1)
        card_lay.addLayout(head)
        card_lay.addSpacing(10)

        self.lbl_code_copy = QLabel(
            "Digite o nome de um tema para desbloqueá-lo e aplicá-lo agora. "
            "Os códigos não aparecem em nenhuma lista.", card)
        self.lbl_code_copy.setObjectName("CodeCopy")
        self.lbl_code_copy.setWordWrap(True)
        card_lay.addWidget(self.lbl_code_copy)
        card_lay.addSpacing(14)

        self.lbl_code_label = QLabel("CÓDIGO DO TEMA", card)
        self.lbl_code_label.setObjectName("CodeLabel")
        card_lay.addWidget(self.lbl_code_label)
        card_lay.addSpacing(6)

        linha = QHBoxLayout()
        linha.setSpacing(8)
        self.code_input = QLineEdit(card)
        self.code_input.setObjectName("Field")
        self.code_input.setFixedHeight(36)
        self.code_input.setPlaceholderText("Digite o nome do tema")
        self.code_input.setAccessibleName("Código do tema")
        self.code_input.returnPressed.connect(self._activate_code)
        linha.addWidget(self.code_input, 1)
        self.btn_ativar = PillButton("Ativar tema", "primary", glyph="key",
                                     width=142, height=36, parent=card)
        self.btn_ativar.clicked.connect(self._activate_code)
        linha.addWidget(self.btn_ativar, 0)
        card_lay.addLayout(linha)
        card_lay.addSpacing(10)

        self.feedback = QLabel(card)
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.RichText)
        self.feedback.setVisible(False)
        card_lay.addWidget(self.feedback)

        card_lay.addStretch(1)

        atual = QHBoxLayout()
        atual.setSpacing(8)
        self.lbl_current = QLabel("TEMA ATUAL", card)
        self.lbl_current.setObjectName("CurrentLabel")
        self.pill_current = QLabel(card)
        self.pill_current.setObjectName("ThemePill")
        atual.addWidget(self.lbl_current, 0)
        atual.addStretch(1)
        atual.addWidget(self.pill_current, 0)
        card_lay.addLayout(atual)

        colunas.addWidget(card, 148)

        aside = QFrame(pagina)
        aside.setObjectName("SettingsAside")
        aside_lay = QVBoxLayout(aside)
        aside_lay.setContentsMargins(16, 16, 16, 16)
        aside_lay.setSpacing(8)
        self.lbl_aside_title = QLabel("COMO FUNCIONA", aside)
        self.lbl_aside_title.setObjectName("AsideTitle")
        aside_lay.addWidget(self.lbl_aside_title)
        for texto in (
            "Maiúsculas, acentos e espaços são ignorados.",
            "O tema fica salvo e volta na próxima abertura.",
            "Os códigos não aparecem em nenhuma lista.",
        ):
            item = QLabel(f"•  {texto}", aside)
            item.setObjectName("AsideItem")
            item.setWordWrap(True)
            aside_lay.addWidget(item)
        aside_lay.addStretch(1)
        self.lbl_aside_note = QLabel(
            "Feature quase secreta. Nenhum tema é listado antes de ser ativado.",
            aside)
        self.lbl_aside_note.setObjectName("AsideNote")
        self.lbl_aside_note.setWordWrap(True)
        aside_lay.addWidget(self.lbl_aside_note)

        colunas.addWidget(aside, 82)
        lay.addLayout(colunas, 1)
        return pagina

    def _page_sobre(self) -> QWidget:
        pagina = QWidget(self.shell)
        lay = QVBoxLayout(pagina)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(10)

        self._eyebrow_sobre = self._eyebrow("SOBRE", pagina)
        lay.addWidget(self._eyebrow_sobre)
        self._title_sobre = self._titulo("PagFlow Excel", pagina)
        lay.addWidget(self._title_sobre)
        lay.addWidget(self._copy(
            "Consolidação de pagamentos SAP. Lê extratos FBL1N e REL_LOG, "
            "gera o .xlsx formatado e envia os relatórios pelo Outlook.", pagina))

        card = QFrame(pagina)
        card.setObjectName("SettingsCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(6)
        for rotulo, valor in (
            ("Versão", APP_VERSION),
            ("Feito por", "Gustavo Pinheiro"),
            ("Tecnologia", "PyQt6 · pandas · openpyxl"),
        ):
            linha = QHBoxLayout()
            nome = QLabel(rotulo, card)
            nome.setObjectName("Hint")
            nome.setFixedWidth(96)
            dado = QLabel(valor, card)
            dado.setObjectName("SelectionLabel")
            linha.addWidget(nome, 0)
            linha.addWidget(dado, 1)
            card_lay.addLayout(linha)
        lay.addWidget(card)
        lay.addStretch(1)

        esquece = QHBoxLayout()
        esquece.setSpacing(10)
        self.btn_esquecer = PillButton("Esquecer temas desbloqueados", "secondary",
                                       width=250, parent=pagina)
        self.btn_esquecer.clicked.connect(self._forget)
        esquece.addWidget(self.btn_esquecer, 0)
        nota = QLabel("Os temas secretos voltam a ficar ocultos. O tema atual "
                      "volta ao escuro.", pagina)
        nota.setObjectName("Hint")
        nota.setWordWrap(True)
        esquece.addWidget(nota, 1)
        lay.addLayout(esquece)
        return pagina

    # ── utilidades de construção ────────────────────────────────────────────
    def _eyebrow(self, texto: str, parent: QWidget) -> QLabel:
        label = QLabel(texto, parent)
        label.setObjectName("CodeEyebrow")
        return label

    def _titulo(self, texto: str, parent: QWidget) -> QLabel:
        label = QLabel(texto, parent)
        label.setObjectName("CodeTitle")
        return label

    def _copy(self, texto: str, parent: QWidget) -> QLabel:
        label = QLabel(texto, parent)
        label.setObjectName("CodeCopy")
        label.setWordWrap(True)
        return label

    # ── tema ────────────────────────────────────────────────────────────────
    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        art = theme.art
        self.lbl_title.setFont(
            F(art.dialog_title_size, QFont.Weight.DemiBold,
              tracking=tracking_px(art.brand_tracking, art.dialog_title_size),
              family=art.display_font))
        self.lbl_eyebrow.setFont(
            F(9, QFont.Weight.Bold, tracking=1.3,
              family=art.meta_font or art.ui_font,
              caps=art.meta_transform == "uppercase"))
        self.lbl_sub.setFont(F(10, family=art.ui_font))

        for label in (self._title_geral, self._title_ap, self._title_sobre):
            label.setFont(F(18, QFont.Weight.DemiBold, family=art.display_font))
        for label in (self._eyebrow_geral, self._eyebrow_ap,
                      self._eyebrow_sobre):
            label.setFont(F(9, QFont.Weight.Bold, tracking=1.3,
                            family=art.meta_font or art.ui_font,
                            caps=art.meta_transform == "uppercase"))

        self.lbl_code_title.setFont(
            F(18, QFont.Weight.DemiBold, family=art.display_font,
              caps=art.brand_transform == "uppercase"))
        for label in (self.lbl_code_eyebrow, self.lbl_code_label,
                      self.lbl_aside_title, self.lbl_current):
            label.setFont(F(9, QFont.Weight.Bold, tracking=1.1,
                            family=art.meta_font or art.ui_font,
                            caps=art.meta_transform == "uppercase"))
        self.lbl_code_copy.setFont(F(10, family=art.ui_font))
        self.lbl_aside_note.setFont(F(10, family=art.ui_font))
        for item in self.findChildren(QLabel, "AsideItem"):
            item.setFont(F(10, family=art.ui_font))
        self.code_input.setFont(F(11, family=art.ui_font))
        self.pill_current.setFont(F(10, QFont.Weight.DemiBold,
                                    family=art.ui_font))
        self.pill_current.setText(theme.label)
        self.badge.set_theme(theme)
        self.btn_close.set_theme(theme)
        self.check_reduzir.set_theme(theme)
        for botao in self.findChildren(PillButton):
            botao.set_theme(theme)
        for divisor in self.findChildren(Divider):
            divisor.set_theme(theme)
        for card in self._cards:
            card.set_theme(theme)

    # ── cartões de tema ─────────────────────────────────────────────────────
    def _refresh_cards(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards = []
        # A lista vem do estado que o App mantém (e não do QSettings no disco):
        # assim o cartão aparece no mesmo instante em que o código é aceito.
        chaves = [k for k in THEME_ORDER if k in CORE_THEME_KEYS or k in self._unlocked]
        chaves += [k for k in sorted(self._unlocked) if k not in THEME_ORDER]
        temas = {k: THEMES[k] for k in chaves}
        for indice, (key, theme) in enumerate(temas.items()):
            card = ThemeCard(theme, active=(key == self._theme.key))
            card.clicked.connect(lambda _=False, k=key: self.theme_selected.emit(k))
            self.grid.addWidget(card, indice // 2, indice % 2)
            self._cards.append(card)

    def set_unlocked(self, unlocked: set[str]) -> None:
        self._unlocked = set(unlocked)
        self._refresh_cards()

    # ── ações ───────────────────────────────────────────────────────────────
    def _on_reduced(self, reduzido: bool) -> None:
        self._reduced = bool(reduzido)
        self.reduced_changed.emit(self._reduced)

    def _show_feedback(self, state: str, title: str, detail: str) -> None:
        self.feedback.setObjectName(
            "FeedbackOk" if state == "success" else "FeedbackErr")
        self.feedback.setText(f"<b>{title}</b><br>{detail}")
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)
        self.feedback.setVisible(True)
        self.feedback.adjustSize()
        self.feedback.setMinimumHeight(
            max(52, self.feedback.sizeHint().height()))

    def _activate_code(self) -> None:
        key = CODE_TO_THEME.get(normalize_code(self.code_input.text()))
        if not key:
            self._show_feedback(
                "error",
                "Código não reconhecido.",
                "Confira o nome do tema e tente novamente. Nada foi alterado.",
            )
            return
        theme = EXTRA_THEMES[key]
        self._show_feedback(
            "success",
            f"Tema {theme.label} ativado.",
            "O tema foi aplicado e será lembrado na próxima abertura.",
        )
        self.pill_current.setText(theme.label)
        self.theme_unlocked.emit(key)

    def _forget(self) -> None:
        resposta = QMessageBox.question(
            self, "Esquecer temas desbloqueados",
            "Remover da memória os temas secretos já desbloqueados?\n\n"
            "Eles voltam a ficar ocultos e o tema atual retorna ao escuro.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            self.forget_requested.emit()

    # ── janela ──────────────────────────────────────────────────────────────
    def showEvent(self, event) -> None:
        super().showEvent(event)
        screen = self.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        largura = min(self.width(), area.width() - 40)
        altura = min(self.height(), area.height() - 40)
        self.resize(max(self.minimumWidth(), largura),
                    max(self.minimumHeight(), altura))
        self.move(area.center().x() - self.width() // 2,
                  area.center().y() - self.height() // 2)
        self.code_input.setFocus()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)



# ══════════════════════════════════════════════════════════════════════════════
#  FOLHA DE ESTILO
# ══════════════════════════════════════════════════════════════════════════════
def build_qss(t: Theme) -> str:
    art = t.art
    ui = art.ui_font
    badge_font = art.badge_font or ui
    chip_top = art.chip_from or t.accent
    chip_bottom = art.chip_to or t.accent
    badge_bg = art.badge_bg or t.accent_soft
    badge_fg = art.badge_fg or t.accent_soft_text
    badge_border = (f"border: 1px solid {art.badge_border};"
                    if art.badge_border else "border: none;")
    return f"""
QWidget {{
    color: {t.text};
}}
QLabel {{ background: transparent; }}
QLabel#Meta {{
    color: {t.text_muted};
}}
QLabel#BrandTitle {{
    color: {t.text};
}}
QLabel#BrandSub {{
    color: {t.text_secondary};
    font-family: "{ui}";
    font-size: 9px;
}}
QLabel#Badge {{
    background: {badge_bg};
    color: {badge_fg};
    {badge_border}
    border-radius: 6px;
    padding: 3px 9px;
}}
QLabel#Chip {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {chip_top}, stop:1 {chip_bottom});
    color: {art.chip_fg or t.on_accent};
    border-radius: 10px;
}}
QLabel#SectionTitle {{
    color: {t.text};
}}
QLineEdit#Field {{
    background: {t.field_bg};
    border: 1px solid {t.field_border};
    border-radius: 10px;
    padding: 0px 11px;
    color: {t.text};
    selection-background-color: {t.accent};
    selection-color: {t.on_accent};
    font-family: "{ui}";
    font-size: 11px;
}}
QLineEdit#Field:hover {{ border-color: {t.border_strong}; }}
QLineEdit#Field:focus {{ border-color: {t.accent}; background: {t.field_focus}; }}
QToolTip {{
    background: {t.surface_alt};
    color: {t.text};
    border: 1px solid {t.border};
    padding: 5px 8px;
    font-family: "{ui}";
    font-size: 10px;
}}
QMessageBox {{ background: {t.surface_alt}; }}
QMessageBox QLabel {{ color: {t.text}; font-family: "{ui}"; font-size: 11px; }}
QMessageBox QPushButton {{
    background: {t.accent};
    color: {t.on_accent};
    border: none;
    border-radius: 8px;
    padding: 6px 20px;
    min-width: 64px;
    font-family: "{ui}";
    font-size: 11px;
    font-weight: 600;
}}
QMessageBox QPushButton:hover {{ background: {t.accent_hover}; }}
QDialog {{ background: {t.surface_alt}; }}
QLabel#CardEyebrow {{
    color: {t.text_muted};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#FieldCaption {{
    color: {t.text_muted};
    font-size: 9px;
    font-weight: 600;
}}
QLabel#Hint {{
    color: {t.text_secondary};
    font-size: 10px;
}}
QLabel#DialogTitle {{
    color: {t.text};
    font-size: 15px;
    font-weight: 600;
}}
QLabel#DialogQuestion {{
    color: {t.text};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#DialogSubtitle {{
    color: {t.text_secondary};
    font-size: 11px;
}}
QLabel#SelectionLabel {{
    color: {t.text_secondary};
    font-size: 11px;
}}
QTextEdit#Body {{
    background: {t.field_bg};
    border: 1px solid {t.field_border};
    border-radius: 10px;
    padding: 8px 10px;
    color: {t.text};
    selection-background-color: {t.accent};
    selection-color: {t.on_accent};
    font-family: "{ui}";
    font-size: 11px;
}}
QTextEdit#Body:focus {{ border-color: {t.accent}; background: {t.field_focus}; }}
QTableWidget {{
    background: {t.field_bg};
    alternate-background-color: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: 10px;
    gridline-color: {t.border};
    color: {t.text};
    font-family: "{ui}";
    font-size: 11px;
}}
QTableWidget::item {{ padding: 3px 6px; }}
QTableWidget::item:selected {{ background: {t.accent_soft}; color: {t.text}; }}
QHeaderView::section {{
    background: {t.surface_alt};
    color: {t.text_secondary};
    border: none;
    border-bottom: 1px solid {t.border_strong};
    padding: 6px 8px;
    font-family: "{ui}";
    font-size: 10px;
    font-weight: 600;
}}
QTableCornerButton::section {{ background: {t.surface_alt}; border: none; }}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border_strong};
    border-radius: 3px;
    min-height: 22px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.accent}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {t.border_strong};
    border-radius: 3px;
    min-width: 22px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t.accent}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ── Configurações ─────────────────────────────────────────────────────── */
QDialog#SettingsDialog {{ background: transparent; }}
QFrame#SettingsShell {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 16px;
}}
QLabel#SettingsEyebrow {{
    color: {t.text_muted};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.3px;
}}
QLabel#SettingsSub {{
    color: {t.text_secondary};
    font-family: "{ui}";
    font-size: 10px;
}}
QPushButton#SettingsClose {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 8px;
    color: {t.text_secondary};
}}
QPushButton#SettingsClose:hover {{
    background: {t.surface_alt};
    border-color: {t.accent};
    color: {t.text};
}}
QPushButton#SettingsTab {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    min-height: 30px;
    padding: 0 14px;
    color: {t.text_secondary};
    font-family: "{ui}";
    font-size: 11px;
    font-weight: 500;
}}
QPushButton#SettingsTab:hover {{
    background: {t.surface};
    color: {t.text};
}}
QPushButton#SettingsTab:checked {{
    background: {t.accent_soft};
    border-color: {t.accent};
    color: {t.accent_soft_text};
    font-weight: 600;
}}
QFrame#SettingsCard {{
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: 12px;
}}
QFrame#SettingsAside {{
    background: {t.bg_top};
    border: 1px solid {t.border};
    border-radius: 12px;
}}
QLabel#FeedbackOk {{
    background: {t.ok_bg};
    border: 1px solid {t.ok_fg};
    border-radius: 9px;
    color: {t.ok_fg};
    padding: 9px 11px;
    font-size: 10px;
}}
QLabel#FeedbackErr {{
    background: {t.err_bg};
    border: 1px solid {t.err_fg};
    border-radius: 9px;
    color: {t.err_fg};
    padding: 9px 11px;
    font-size: 10px;
}}
QLabel#ThemePill {{
    background: {t.accent_soft};
    border: 1px solid {t.accent};
    border-radius: 7px;
    color: {t.accent_soft_text};
    padding: 3px 9px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#CodeEyebrow, QLabel#CodeLabel, QLabel#AsideTitle, QLabel#ThemeLabel {{
    color: {t.text_muted};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.1px;
}}
QLabel#CodeCopy, QLabel#AsideItem, QLabel#AsideNote {{
    color: {t.text_secondary};
    font-size: 10px;
}}
QLabel#CurrentLabel {{
    color: {t.text_muted};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.1px;
}}
QFrame#CodeDivider {{ background: {t.border}; border: none; }}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════════════════
class App(StarField):
    status_requested = pyqtSignal(str, object)   # (mensagem, estado)
    thread_finished = pyqtSignal()

    # Proporção fixa da janela (largura × altura) e teto em monitores grandes.
    _PROPORCAO = (4, 3)
    _TAMANHO_MAX = (1280, 960)
    _FOLGA_TELA = 8           # respiro entre a moldura e a área útil

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PagFlow Excel")
        # Janela de tamanho fixo, mas calculado a partir da tela: 4:3 e sempre
        # dentro da área útil do monitor. Trocar de tela nunca redimensiona —
        # uma página se dissolve na outra, no mesmo retângulo, sem reflow.
        self._current_tab = 0
        self._screen_hooked = False
        self._fit_to_screen()
        self.setWindowIcon(make_app_icon(DARK))

        self._settings = QSettings("PagFlow", "PagFlow")
        self._unlocked = unlocked_keys(self._settings)
        saved = str(self._settings.value("tema", "dark"))
        if saved not in THEMES or (
            saved in EXTRA_THEMES and saved not in self._unlocked
        ):
            saved = "dark"
        self._theme_key = saved
        self.theme = THEMES[self._theme_key]
        self._busy = False
        self._themed: list = []
        self._overlay: QLabel | None = None
        self._fade_anim: QPropertyAnimation | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._scrim: QWidget | None = None
        # preferência de acessibilidade (o env var continua valendo como piso)
        self._env_reduced = self._reduced
        try:
            pref_reduzir = bool(int(self._settings.value(ANIMATIONS_SETTING, 0) or 0))
        except (TypeError, ValueError):
            pref_reduzir = False
        self._reduced_pref = pref_reduzir

        self._build()
        self.status_requested.connect(self._set_status)
        self.thread_finished.connect(self._on_finished)
        self._apply_theme()
        self.set_reduced(self._reduced_pref or self._env_reduced)
        self._center()
        self.entry_nome.setFocus()      # digitação imediata ao abrir

    # ── encaixe na tela ─────────────────────────────────────────────────────
    def _fit_to_screen(self) -> bool:
        """Redimensiona a janela para o maior retângulo 4:3 que caiba na tela.

        Usa a área útil do monitor (já sem a barra de tarefas) e desconta uma
        folga para as bordas. Em monitores grandes o tamanho para no teto, para
        o layout continuar idêntico em qualquer máquina. Devolve ``True`` quando
        o tamanho realmente mudou.
        """
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            largura, altura = self._TAMANHO_MAX
        else:
            area = screen.availableGeometry()
            # A moldura (barra de título) fica fora do tamanho do cliente; sem
            # descontá-la a janela passaria por baixo da barra de tarefas.
            moldura_w = max(0, self.frameGeometry().width() - self.width())
            moldura_h = max(0, self.frameGeometry().height() - self.height())
            if not self.isVisible():
                moldura_w = max(moldura_w, 8)
                moldura_h = max(moldura_h, 32)
            disponivel_w = max(400, area.width() - moldura_w - self._FOLGA_TELA)
            disponivel_h = max(300, area.height() - moldura_h - self._FOLGA_TELA)
            razao = self._PROPORCAO[0] / self._PROPORCAO[1]
            largura = min(disponivel_w, int(disponivel_h * razao))
            if largura > self._TAMANHO_MAX[0]:
                largura = self._TAMANHO_MAX[0]
            # múltiplo de 4 garante a proporção 4:3 exata em pixels inteiros
            largura -= largura % self._PROPORCAO[0]
            altura = largura * self._PROPORCAO[1] // self._PROPORCAO[0]
        if (largura, altura) == (self.width(), self.height()):
            return False
        self.setFixedSize(largura, altura)
        return True

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Ao mover a janela para outro monitor, reencaixa mantendo 4:3.
        handle = self.windowHandle()
        if handle is not None and not self._screen_hooked:
            handle.screenChanged.connect(lambda _screen: self._on_screen_changed())
            self._screen_hooked = True
        if self._fit_to_screen():
            self._center()

    def _on_screen_changed(self) -> None:
        if self._fit_to_screen():
            self._center()

    # ── layout ──────────────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 10)
        root.setSpacing(0)

        # ── faixa superior: crédito + alternador de tema ────────────────────
        top = QWidget(self)
        top.setFixedHeight(24)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(2, 0, 0, 0)
        top_layout.setSpacing(0)

        self.lbl_author = QLabel("FEITO POR GUSTAVO PINHEIRO", top)
        self.lbl_author.setObjectName("Meta")
        self.lbl_author.setFont(F(9, QFont.Weight.DemiBold, 1.1))
        top_layout.addWidget(self.lbl_author, 0, Qt.AlignmentFlag.AlignVCenter)
        top_layout.addStretch(1)

        self.btn_config = IconButton("gear", "Configurações", top, compact=True)
        self.btn_config.clicked.connect(self._open_settings)
        top_layout.addWidget(self.btn_config, 0, Qt.AlignmentFlag.AlignVCenter)
        top_layout.addSpacing(8)

        self.toggle = ThemeToggle(top)
        self.toggle.theme_requested.connect(self._set_theme)
        top_layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(top)
        root.addSpacing(8)

        # ── cartão de marca ─────────────────────────────────────────────────
        self.header = Card(self, radius=12)
        self.header.setFixedHeight(52)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(14, 0, 14, 0)
        header_layout.setSpacing(11)

        self.logo = LogoMark(self.header)
        header_layout.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignVCenter)

        brand = QVBoxLayout()
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(1)
        self.lbl_title = QLabel("PagFlow", self.header)
        self.lbl_title.setObjectName("BrandTitle")
        self.lbl_sub = QLabel("Consolidação de pagamentos SAP", self.header)
        self.lbl_sub.setObjectName("BrandSub")
        brand.addWidget(self.lbl_title)
        brand.addWidget(self.lbl_sub)
        header_layout.addLayout(brand)
        header_layout.addStretch(1)

        self.lbl_badge = QLabel("XLS → XLSX", self.header)
        self.lbl_badge.setObjectName("Badge")
        header_layout.addWidget(self.lbl_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(self.header)
        root.addSpacing(10)

        # ── seletor de telas: pílula mínima, centralizada ──────────────────
        self.switch = ViewSwitch(["Gerar Excel", "Envio de e-mails"], 268, self)
        self.switch.tab_changed.connect(self._switch_tab)
        root.addWidget(self.switch, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addSpacing(10)

        # ── telas: troca por dissolução, as duas ocupam o mesmo lugar ──────
        self.stack = PageSwap(self)
        self.page_gerar = self._build_gerar_page()
        self.envio = EnvioPage(self)
        self.envio.status_requested.connect(self._set_status)
        self.stack.add_page(self.page_gerar)
        self.stack.add_page(self.envio)
        self.stack.set_current(0, animate=False)
        root.addWidget(self.stack, 1)

        # ── status (compartilhado) ─────────────────────────────────────────
        root.addSpacing(8)
        self.status = StatusBar(self)
        self.status.set_message("Pronto para uso.")
        root.addWidget(self.status)

        # widgets que precisam de repintura/tokens
        self._themed = [self.header, self.logo, self.toggle, self.btn_config,
                        self.switch, self.seg, self.select, self.btn_pasta,
                        self.btn_destino, self.divider, self.btn_limpar,
                        self.btn_gerar, self.status, self.envio]

        # ordem de tabulação: formulário → ações
        self.setTabOrder(self.entry_nome, self.entry_pasta)
        self.setTabOrder(self.entry_pasta, self.btn_pasta)
        self.setTabOrder(self.btn_pasta, self.seg._buttons[0])
        self.setTabOrder(self.seg._buttons[0], self.seg._buttons[1])
        self.setTabOrder(self.seg._buttons[1], self.seg._buttons[2])
        self.setTabOrder(self.seg._buttons[2], self.seg._buttons[3])
        self.setTabOrder(self.seg._buttons[3], self.select)
        self.setTabOrder(self.select, self.entry_destino)
        self.setTabOrder(self.entry_destino, self.btn_destino)
        self.setTabOrder(self.btn_destino, self.btn_limpar)
        self.setTabOrder(self.btn_limpar, self.btn_gerar)

    def _build_gerar_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 1 · nome do arquivo ─────────────────────────────────────────────
        self._section(layout, "1", "Nome do arquivo de saída")
        self.entry_nome = self._entry("ex.: relatorio_outubro")
        layout.addWidget(self.entry_nome)
        layout.addSpacing(14)

        # ── 2 · pasta de origem ─────────────────────────────────────────────
        self._section(layout, "2", "Pasta com os arquivos de entrada")
        row_origem = QWidget(page)
        origem_layout = QHBoxLayout(row_origem)
        origem_layout.setContentsMargins(0, 0, 0, 0)
        origem_layout.setSpacing(8)
        self.entry_pasta = self._entry("Selecione a pasta...")
        self.btn_pasta = IconButton("folder", "Selecionar pasta de entrada", row_origem)
        self.btn_pasta.clicked.connect(self._browse_pasta)
        origem_layout.addWidget(self.entry_pasta, 1)
        origem_layout.addWidget(self.btn_pasta, 0)
        layout.addWidget(row_origem)
        layout.addSpacing(14)

        # ── 3 · separação das abas ──────────────────────────────────────────
        self._section(layout, "3", "Separação das abas")
        self.seg = SegmentedControl(["Marca", "LNeg", "Fornecedor", "Não Separar"], page)
        layout.addWidget(self.seg)
        layout.addSpacing(14)

        # ── 4 · personalização ──────────────────────────────────────────────
        self._section(layout, "4", "Personalização")
        self.select = SelectField(["Verde", "Azul", "Roxo", "Vermelho"], "Azul", page)
        layout.addWidget(self.select)
        layout.addSpacing(14)

        # ── 5 · destino ─────────────────────────────────────────────────────
        self._section(layout, "5", "Destino do arquivo final")
        row_destino = QWidget(page)
        destino_layout = QHBoxLayout(row_destino)
        destino_layout.setContentsMargins(0, 0, 0, 0)
        destino_layout.setSpacing(8)
        self.entry_destino = self._entry("Selecione onde salvar...")
        self.btn_destino = IconButton("folder", "Selecionar pasta de destino", row_destino)
        self.btn_destino.clicked.connect(self._browse_destino)
        destino_layout.addWidget(self.entry_destino, 1)
        destino_layout.addWidget(self.btn_destino, 0)
        layout.addWidget(row_destino)

        layout.addStretch(1)

        # ── ações ───────────────────────────────────────────────────────────
        self.divider = Divider(page)
        layout.addWidget(self.divider)
        layout.addSpacing(12)

        row_actions = QWidget(page)
        actions_layout = QHBoxLayout(row_actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        self.btn_limpar = PillButton("Limpar campos", "secondary", width=130,
                                     parent=row_actions)
        self.btn_limpar.clicked.connect(self._limpar)
        self.btn_gerar = PillButton("Gerar Excel", "primary", glyph="play", width=152,
                                    parent=row_actions)
        self.btn_gerar.clicked.connect(self._gerar)
        actions_layout.addWidget(self.btn_limpar, 0)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.btn_gerar, 0)
        layout.addWidget(row_actions)

        return page

    def _section(self, root: QVBoxLayout, number: str, title: str) -> None:
        row = QWidget(self)
        row.setFixedHeight(20)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        chip = QLabel(number, row)
        chip.setObjectName("Chip")
        chip.setFixedSize(20, 20)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(title, row)
        label.setObjectName("SectionTitle")

        layout.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        root.addWidget(row)
        root.addSpacing(5)

    def _entry(self, placeholder: str) -> QLineEdit:
        entry = QLineEdit(self)
        entry.setObjectName("Field")
        entry.setFixedHeight(32)
        entry.setPlaceholderText(placeholder)
        entry.returnPressed.connect(self._gerar)
        return entry

    def _center(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        # move() posiciona a moldura inteira, não só a área de cliente.
        moldura_w = max(0, self.frameGeometry().width() - self.width())
        moldura_h = max(0, self.frameGeometry().height() - self.height())
        total_w = self.width() + moldura_w
        total_h = self.height() + moldura_h
        self.move(area.center().x() - total_w // 2,
                  area.center().y() - total_h // 2)

    # ── troca de tela ───────────────────────────────────────────────────────
    def _switch_tab(self, index: int) -> None:
        if index == self._current_tab:
            return
        self._current_tab = index
        if self.switch.current_index() != index:
            self.switch.set_current(index)
        # Sensação de janela trocada, dentro do programa: a tela atual se
        # dissolve e a outra assume o mesmo lugar. Sem rolagem, sem resize.
        self.stack.set_current(index, animate=True)

    # ── tema ────────────────────────────────────────────────────────────────
    def _set_theme(self, key: str) -> None:
        if key not in THEMES or key == self._theme_key:
            return
        if key in EXTRA_THEMES and key not in self._unlocked:
            return
        overlay = None
        if self.isVisible() and not self.isMinimized() and self._scrim is None:
            overlay = self._snapshot()
        self._theme_key = key
        self.theme = THEMES[key]
        self._apply_theme()
        self._settings.setValue("tema", key)
        self._settings.sync()
        if overlay is not None:
            self._fade_out(overlay)

    def _apply_theme(self) -> None:
        global _UI_FONT
        t = self.theme
        _UI_FONT = t.art.ui_font or "Segoe UI"
        # A fonte da aplicação é a base de tudo que não tem fonte própria.
        # (O QSS não define font-family global: isso sobrescreveria as fontes
        # de display aplicadas com setFont.)
        app = QApplication.instance()
        if app is not None:
            app.setFont(F(11, family=_UI_FONT))
        self.setFont(F(11, family=_UI_FONT))
        self.setStyleSheet(build_qss(t))
        self.set_theme(t)                       # StarField
        for widget in self._themed:
            widget.set_theme(t)
        self._apply_typography(t)
        self.setWindowIcon(make_app_icon(t))

        for entry in (self.entry_nome, self.entry_pasta, self.entry_destino):
            palette = entry.palette()
            palette.setColor(QPalette.ColorRole.PlaceholderText, C(t.placeholder))
            entry.setPalette(palette)

        self._sync_primary_shadow(t)
        self.header.set_shadow(t.shadow_alpha)

        if self._settings_dialog is not None:
            self._settings_dialog.set_theme(t)
            self._settings_dialog._refresh_cards()

    def _apply_typography(self, t: Theme) -> None:
        """Fontes/tracking/caixa alta que o QSS não consegue expressar."""
        art = t.art
        self.lbl_author.setFont(F(
            9, QFont.Weight.Bold,
            tracking=tracking_px(art.meta_tracking, 9) or 1.1,
            family=art.meta_font or art.ui_font,
            caps=art.meta_transform == "uppercase",
        ))

        self.lbl_title.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_title.setText(self._brand_html(t))
        self.lbl_title.setFont(F(
            art.brand_size, QFont.Weight.DemiBold,
            tracking=tracking_px(art.brand_tracking, art.brand_size),
            family=art.display_font,
            caps=art.brand_transform == "uppercase",
        ))
        # display fonts altas (Anton, Playfair) encostam na borda do cartão:
        # o respiro sai da faixa do subtítulo, que tem folga de sobra.
        dy = art.brand_dy
        self.lbl_title.setContentsMargins(0, dy, 0, 0)
        if dy:
            self.lbl_title.setFixedHeight(26 + dy)
            self.lbl_sub.setFixedHeight(25 - dy)
        else:
            self.lbl_title.setMinimumHeight(0)
            self.lbl_title.setMaximumHeight(16_777_215)
            self.lbl_sub.setMinimumHeight(0)
            self.lbl_sub.setMaximumHeight(16_777_215)
        self.lbl_title.updateGeometry()

        self.lbl_badge.setFont(F(
            9, QFont.Weight.Bold,
            tracking=tracking_px(art.badge_tracking, 9) or 0.36,
            family=art.badge_font or art.ui_font,
            caps=art.badge_transform == "uppercase",
        ))

        for label in self.findChildren(QLabel, "SectionTitle"):
            label.setFont(F(
                art.section_size, QFont.Weight.DemiBold,
                tracking=tracking_px(art.section_tracking, art.section_size),
                family=art.section_font or art.ui_font,
                caps=art.section_transform == "uppercase",
            ))
        for chip in self.findChildren(QLabel, "Chip"):
            chip.setFont(F(9, QFont.Weight.Bold, family=art.ui_font))

    def _brand_html(self, t: Theme) -> str:
        art = t.art
        rotulo = art.brand_label or "PagFlow"
        if not art.brand_suffix:
            return rotulo
        cor = art.brand_suffix_color or t.accent
        italico = " font-style:italic;" if art.brand_suffix_style == "italic" else ""
        return (f'{rotulo} <span style="color:{cor};{italico}">'
                f'{art.brand_suffix}</span>')

    def _sync_primary_shadow(self, t: Theme) -> None:
        # o brilho acompanha o gradiente do botão (no Açaí é dourado, não roxo)
        glow = QColor(t.primary_from)
        if t.key == "dark":
            glow.setAlpha(95)
            blur, offset = 26, 0
        elif t.key == "light":
            glow.setAlpha(70)
            blur, offset = 20, 4
        elif t.art.is_light:
            glow.setAlpha(64)
            blur, offset = 20, 4
        else:
            glow.setAlpha(82)
            blur, offset = 24, 0
        shadow = QGraphicsDropShadowEffect(self.btn_gerar)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset)
        shadow.setColor(glow)
        self.btn_gerar.setGraphicsEffect(shadow)

    def _snapshot(self) -> QLabel:
        # se um fade anterior ainda está no ar, encerra antes de fotografar
        previous = self._overlay
        if previous is not None:
            if self._fade_anim is not None:
                self._fade_anim.stop()
            previous.deleteLater()
            self._overlay = None

        # capturar com uma dissolução no ar devolveria o quadro congelado
        self.stack.finish()
        pixmap = self.grab()
        overlay = QLabel(self)
        overlay.setObjectName("Snapshot")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background: transparent; border: none;")
        overlay.setPixmap(pixmap)
        overlay.setGeometry(self.rect())
        overlay.show()
        overlay.raise_()
        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(1.0)
        overlay.setGraphicsEffect(effect)
        self._overlay = overlay
        return overlay

    def _fade_out(self, overlay: QLabel) -> None:
        effect = overlay.graphicsEffect()
        if effect is None:
            overlay.deleteLater()
            return
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(260)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(overlay.deleteLater)
        anim.finished.connect(self._on_fade_done)
        anim.start()
        self._fade_anim = anim

    def _on_fade_done(self) -> None:
        self._overlay = None
        self._fade_anim = None

    # ── configurações ───────────────────────────────────────────────────────
    def _open_settings(self) -> None:
        if self._settings_dialog is not None:
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        self._show_scrim()
        dialog = SettingsDialog(
            self.theme, self._settings, self._unlocked,
            reduced=self._reduced_pref, parent=self,
        )
        dialog.theme_selected.connect(self._set_theme)
        dialog.theme_unlocked.connect(self._on_theme_unlocked)
        dialog.reduced_changed.connect(self._on_reduced_changed)
        dialog.forget_requested.connect(self._forget_unlocked)
        self._settings_dialog = dialog
        dialog.exec()
        self._settings_dialog = None
        self._hide_scrim()

    def _show_scrim(self) -> None:
        if self._scrim is not None:
            return
        scrim = QWidget(self)
        scrim.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scrim.setStyleSheet("background: rgba(0, 0, 0, 96);")
        scrim.setGeometry(self.rect())
        scrim.show()
        scrim.raise_()
        self._scrim = scrim

    def _hide_scrim(self) -> None:
        if self._scrim is not None:
            self._scrim.deleteLater()
            self._scrim = None

    def _on_theme_unlocked(self, key: str) -> None:
        if key not in EXTRA_THEMES:
            return
        self._unlocked.add(key)
        save_unlocked(self._settings, self._unlocked)
        self._settings.sync()
        if self._settings_dialog is not None:
            self._settings_dialog.set_unlocked(self._unlocked)
        self._set_theme(key)

    def _forget_unlocked(self) -> None:
        self._settings.remove(UNLOCKED_SETTING)
        self._settings.sync()
        self._unlocked = set()
        if self._theme_key in EXTRA_THEMES:
            self._set_theme("dark")
        if self._settings_dialog is not None:
            self._settings_dialog.set_unlocked(self._unlocked)

    def _on_reduced_changed(self, reduzido: bool) -> None:
        self._reduced_pref = bool(reduzido)
        self._settings.setValue(ANIMATIONS_SETTING, 1 if reduzido else 0)
        self._settings.sync()
        self.set_reduced(self._reduced_pref or self._env_reduced)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._scrim is not None:
            self._scrim.setGeometry(self.rect())

    # ── callbacks operacionais (mesmo comportamento de antes) ──────────────
    def _browse_pasta(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta de entrada")
        if path:
            self.entry_pasta.setText(path)
            self._set_status(f"Pasta de entrada: {os.path.basename(path)}")

    def _browse_destino(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta de destino")
        if path:
            self.entry_destino.setText(path)
            self._set_status(f"Destino definido: {os.path.basename(path)}")

    def _limpar(self) -> None:
        for entry in (self.entry_nome, self.entry_pasta, self.entry_destino):
            entry.clear()
        self.seg.set_value("Não Separar")
        self.select.set_value("Azul")
        self._set_status("Campos limpos.")

    def _gerar(self) -> None:
        if self._busy:
            return

        nome = self.entry_nome.text().strip()
        pasta = self.entry_pasta.text().strip()
        separar = self.seg.value()
        cor = self.select.value()
        destino = self.entry_destino.text().strip()

        if not nome or not pasta or not destino:
            campos = []
            if not nome:
                campos.append("Nome do arquivo")
            if not pasta:
                campos.append("Pasta de entrada")
            if not destino:
                campos.append("Destino")
            self._set_status(f"Campo(s) não preenchido(s): {', '.join(campos)}",
                             estado="aviso")
            return

        self._set_busy(True)

        def _rodar() -> None:
            self._emit_status(f"Processando... · Separação: {separar}")
            try:
                from ope import executar
                executar(
                    pasta=pasta,
                    destino=destino,
                    nome=nome,
                    separar=separar,
                    cor=cor,
                    cb_status=self._emit_status,
                )
            except Exception as e:  # noqa: BLE001 — mesma rede de segurança de antes
                self._emit_status(f"Erro fatal: {e}", estado="erro")
            finally:
                self.thread_finished.emit()

        threading.Thread(target=_rodar, daemon=True).start()

    def _emit_status(self, msg: str, estado: str | None = None) -> None:
        """Chamado da thread de trabalho — o sinal entrega na thread da GUI."""
        self.status_requested.emit(str(msg), estado)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.btn_gerar.setEnabled(not busy)
        effect = self.btn_gerar.graphicsEffect()
        if effect is not None:
            effect.setEnabled(not busy)
        self.status.set_busy(busy)

    def _on_finished(self) -> None:
        self._set_busy(False)

    def _set_status(self, msg: str, estado: str | None = None,
                    warn: bool = False) -> None:
        if warn and estado is None:
            estado = "aviso"

        message = self._clean_message(msg)

        if estado == "ok":
            box = QMessageBox(self)
            box.setWindowTitle("Sucesso")
            box.setIconPixmap(make_success_pixmap(self.theme))
            box.setTextFormat(Qt.TextFormat.PlainText)
            box.setText(message)
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.exec()
            self.status.set_message("Pronto para uso.", "idle")
            return

        self.status.set_message(message, estado or "idle")

    @staticmethod
    def _clean_message(msg: str) -> str:
        """Os prefixos de ícone do fluxo antigo viram o ponto colorido da barra."""
        text = str(msg)
        for symbol in ("⚠", "✗", "⏳", "✓", "✅", "❌"):
            text = text.replace(symbol, "")
        return " ".join(text.split())


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    app = QApplication.instance() or QApplication([])
    load_theme_fonts()
    app.setStyle("Fusion")
    app.setApplicationName("PagFlow")
    app.setApplicationDisplayName("PagFlow Excel")
    app.setFont(F(11))

    window = App()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
