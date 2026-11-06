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

A troca de tema preserva geometria, proporções e estados: só os tokens mudam.
"""

from __future__ import annotations

import math
import os
import random
import threading
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve, QElapsedTimer, QEvent, QPoint, QPointF, QPropertyAnimation,
    QRect, QRectF, QSettings, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QIcon, QLinearGradient,
    QPainter, QPainterPath, QPalette, QPen, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QAbstractButton, QAbstractItemView, QApplication, QButtonGroup, QDialog,
    QFileDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

TAU = math.tau


# ══════════════════════════════════════════════════════════════════════════════
#  TOKENS DE TEMA
# ══════════════════════════════════════════════════════════════════════════════
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
)

THEMES = {"dark": DARK, "light": LIGHT}


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
      tracking: float = 0.0, family: str = "Segoe UI") -> QFont:
    """Fonte em pixels — evita o descompasso entre pt e px do QSS."""
    font = QFont(family)
    font.setPixelSize(px)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
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


def make_app_icon(theme: Theme) -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, C(theme.primary_from))
        grad.setColorAt(1.0, C(theme.primary_pressed_to))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), size * 0.24, size * 0.24)
        glyph = size * 0.46
        draw_sheet(p, QRectF((size - glyph * 0.86) / 2, (size - glyph) / 2,
                             glyph * 0.86, glyph),
                   C(theme.on_accent), max(1.0, size * 0.035))
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
    mark = C("#062338") if theme.key == "dark" else C("#FFFFFF")
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
        finally:
            p.end()

        self._bg_cache = pixmap
        return pixmap

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

        fill = C(t.surface, int(t.surface_alpha * 255))
        p.setPen(QPen(C(t.border), 1))
        p.setBrush(fill)
        p.drawRoundedRect(rect, self._radius, self._radius)


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

        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, C(t.primary_from))
        grad.setColorAt(1.0, C(t.accent_pressed))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, 9, 9)

        # brilho superior sutil
        sheen = QLinearGradient(0, 0, 0, self.height())
        sheen.setColorAt(0.0, C("#FFFFFF", 40))
        sheen.setColorAt(0.55, C("#FFFFFF", 0))
        p.setBrush(QBrush(sheen))
        p.drawRoundedRect(rect, 9, 9)

        draw_sheet(p, QRectF(8, 7.5, 14, 15), C(t.on_accent), 1.3)


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

            fg = C(t.on_accent, 255 if enabled else 120)
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

        font = F(self.font_px, QFont.Weight.DemiBold
                 if self.variant == "primary" else QFont.Weight.Medium)
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
            x += icon_w + gap

        p.setPen(fg)
        p.drawText(QRectF(x, 0, text_w + 2, self.height()),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)


class IconButton(QAbstractButton):
    """Botão de ícone (selecionar pasta)."""

    def __init__(self, glyph: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = DARK
        self.glyph = glyph
        self._hover = False
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
        p.setPen(QPen(stroke, 1))
        p.setBrush(fill)
        p.drawRoundedRect(rect, 10, 10)

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(C(t.accent), 1.5))
            p.drawRoundedRect(rect.adjusted(2.2, 2.2, -2.2, -2.2), 8, 8)

        color = C(t.accent if self._hover else t.text_secondary)
        glyph_rect = QRectF(11, 9.5, 14, 13)
        if self.glyph == "file":
            draw_file(p, glyph_rect, color, 1.4)
        elif self.glyph == "mail":
            draw_mail(p, glyph_rect, color, 1.4)
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
        target = 1.0 if theme.key == "light" else 0.0
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
            if inside and target != self._theme.key:
                self.theme_requested.emit(target)
        self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.theme_requested.emit("light" if self._theme.key == "dark" else "dark")
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
        grad.setColorAt(0.0, C(t.accent_hover))
        grad.setColorAt(1.0, C(t.accent))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(knob_rect)

        # ícones
        moon_color = C(t.on_accent) if self._pos < 0.5 else C(t.text_muted)
        sun_color = C(t.on_accent) if self._pos >= 0.5 else C(t.text_muted)
        draw_moon(p, QPointF(x + knob / 2 + 0.6, self.height() / 2), 5.4, moon_color)
        draw_sun(p, QPointF(2 + (self.width() - 4) - knob / 2 - 0.6, self.height() / 2),
                 5.0, sun_color)

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
            color = t.on_accent if checked else t.text_secondary
            weight = QFont.Weight.DemiBold if checked else QFont.Weight.Normal
            button.setFont(F(11, weight))
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
        grad = QLinearGradient(0, pill.top(), 0, pill.bottom())
        grad.setColorAt(0.0, C(t.primary_from))
        grad.setColorAt(1.0, C(t.primary_to))
        p.setPen(Qt.PenStyle.NoPen)
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

        shadow = QColor(6, 18, 32, 70 if t.key == "dark" else 30)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawRoundedRect(panel.adjusted(0, 2, 0, 4), 11, 11)

        p.setPen(QPen(C(t.border), 1))
        p.setBrush(C(t.surface_alt, 252))
        p.drawRoundedRect(panel, 10, 10)

        p.setFont(F(11))
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
                           C(t.accent_soft_text if t.key == "light" else t.accent), 1.5)
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

        font = F(11)
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
        if self._state == "ok":
            return C(t.ok_bg), C(t.ok_fg), False
        if self._state == "erro":
            return C(t.err_bg), C(t.err_fg), False
        if self._state == "aviso":
            return C(t.warn_bg), C(t.warn_fg), False
        return C(t.surface_alt, 190), C(t.text_secondary), True

    def paintEvent(self, event) -> None:
        t = self._theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg, fg, bordered = self._colors()

        p.setPen(QPen(C(t.border), 1) if bordered else Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, 10, 10)

        cy = self.height() / 2
        dot_color = fg if not bordered else C(t.accent)
        halo = QColor(dot_color)
        halo.setAlpha(30)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(14, cy), 5.6, 5.6)
        p.setBrush(dot_color)
        p.drawEllipse(QPointF(14, cy), 3.1, 3.1)

        font = F(11)
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
                color = t.accent_soft_text
                weight = QFont.Weight.DemiBold
            elif index == self._hover:
                color = t.text
                weight = QFont.Weight.Medium
            else:
                color = t.text_secondary
                weight = QFont.Weight.Medium
            button.setFont(F(11, weight))
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
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(C(t.accent, 22))
        p.drawRoundedRect(thumb.adjusted(-2.0, -1.0, 2.0, 1.0),
                          thumb.height() / 2 + 1, thumb.height() / 2 + 1)
        p.setPen(QPen(C(t.accent, 135), 1))
        p.setBrush(C(t.accent_soft, 255))
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
#  FOLHA DE ESTILO
# ══════════════════════════════════════════════════════════════════════════════
def build_qss(t: Theme) -> str:
    return f"""
QWidget {{
    font-family: "Segoe UI";
    color: {t.text};
}}
QLabel {{ background: transparent; }}
QLabel#Meta {{
    color: {t.text_muted};
    font-size: 9px;
    font-weight: 600;
}}
QLabel#BrandTitle {{
    color: {t.text};
    font-size: 16px;
    font-weight: 600;
}}
QLabel#BrandSub {{
    color: {t.text_secondary};
    font-size: 9px;
}}
QLabel#Badge {{
    background: {t.accent_soft};
    color: {t.accent_soft_text};
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 9px;
    font-weight: 600;
}}
QLabel#Chip {{
    background: {t.accent};
    color: {t.on_accent};
    border-radius: 10px;
    font-size: 9px;
    font-weight: 700;
}}
QLabel#SectionTitle {{
    color: {t.text};
    font-size: 11px;
    font-weight: 600;
}}
QLineEdit#Field {{
    background: {t.field_bg};
    border: 1px solid {t.field_border};
    border-radius: 10px;
    padding: 0px 11px;
    color: {t.text};
    selection-background-color: {t.accent};
    selection-color: {t.on_accent};
    font-size: 11px;
}}
QLineEdit#Field:hover {{ border-color: {t.border_strong}; }}
QLineEdit#Field:focus {{ border-color: {t.accent}; background: {t.field_focus}; }}
QToolTip {{
    background: {t.surface_alt};
    color: {t.text};
    border: 1px solid {t.border};
    padding: 5px 8px;
    font-size: 10px;
}}
QMessageBox {{ background: {t.surface_alt}; }}
QMessageBox QLabel {{ color: {t.text}; font-size: 11px; }}
QMessageBox QPushButton {{
    background: {t.accent};
    color: {t.on_accent};
    border: none;
    border-radius: 8px;
    padding: 6px 20px;
    min-width: 64px;
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
        saved = str(self._settings.value("tema", "dark"))
        self._theme_key = saved if saved in THEMES else "dark"
        self.theme = THEMES[self._theme_key]
        self._busy = False
        self._themed: list = []
        self._overlay: QLabel | None = None
        self._fade_anim: QPropertyAnimation | None = None

        self._build()
        self.status_requested.connect(self._set_status)
        self.thread_finished.connect(self._on_finished)
        self._apply_theme()
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
        self._themed = [self.header, self.logo, self.toggle, self.switch,
                        self.seg, self.select, self.btn_pasta, self.btn_destino,
                        self.divider, self.btn_limpar, self.btn_gerar,
                        self.status, self.envio]

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
        overlay = None
        if self.isVisible() and not self.isMinimized():
            overlay = self._snapshot()
        self._theme_key = key
        self.theme = THEMES[key]
        self._apply_theme()
        self._settings.setValue("tema", key)
        if overlay is not None:
            self._fade_out(overlay)

    def _apply_theme(self) -> None:
        t = self.theme
        self.setStyleSheet(build_qss(t))
        self.set_theme(t)                       # StarField
        for widget in self._themed:
            widget.set_theme(t)
        self.lbl_author.setFont(F(9, QFont.Weight.DemiBold, 1.1))
        self.setWindowIcon(make_app_icon(t))

        for entry in (self.entry_nome, self.entry_pasta, self.entry_destino):
            palette = entry.palette()
            palette.setColor(QPalette.ColorRole.PlaceholderText, C(t.placeholder))
            entry.setPalette(palette)

        self._sync_primary_shadow(t)
        self.header.set_shadow(t.shadow_alpha)

    def _sync_primary_shadow(self, t: Theme) -> None:
        glow = QColor(t.accent)
        if t.key == "dark":
            glow.setAlpha(95)
            blur, offset = 26, 0
        else:
            glow.setAlpha(70)
            blur, offset = 20, 4
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
    app.setStyle("Fusion")
    app.setApplicationName("PagFlow")
    app.setApplicationDisplayName("PagFlow Excel")
    app.setFont(F(11))

    window = App()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
