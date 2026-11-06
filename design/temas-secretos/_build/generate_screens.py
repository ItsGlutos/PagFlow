"""Gera as telas estáticas do kit de temas secretos do PagFlow.

Sem JavaScript, sem lógica de aplicativo: só HTML + CSS. As telas reproduzem a
geometria real do PagFlow (1280x960, 5 passos, barra de status) e aplicam a
linguagem visual de cada tema.
"""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "screens"

ICON = {
    "gear": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>""",
    "moon": """<svg class="t-icon moon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.2 14.6A8.7 8.7 0 0 1 9.4 3.8 8.7 8.7 0 1 0 20.2 14.6Z"/></svg>""",
    "sun": """<svg class="t-icon sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3.4"/><path d="M12 2.2v2.1M12 19.7v2.1M2.2 12h2.1M19.7 12h2.1M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/></svg>""",
    "folder": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7.2a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8.6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>""",
    "chevron": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>""",
    "play": """<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.2v13.6L19 12z"/></svg>""",
    "key": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="15.5" r="3.8"/><path d="m10.8 12.7 8.2-8.2M15.8 4.1l3.7 3.7M17.6 6l1.9 1.9"/></svg>""",
    "check": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.2 4.2L19 6.8"/></svg>""",
    "alert": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7.6v5.2M12 16.4v.2"/></svg>""",
    "lock": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>""",
    "close": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>""",
    "flower": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" aria-hidden="true"><circle cx="12" cy="5.2" r="2.05"/><circle cx="17.4" cy="8.3" r="2.05"/><circle cx="17.4" cy="15.7" r="2.05"/><circle cx="12" cy="18.8" r="2.05"/><circle cx="6.6" cy="15.7" r="2.05"/><circle cx="6.6" cy="8.3" r="2.05"/><circle cx="12" cy="12" r="1.9" fill="currentColor" stroke="none"/></svg>""",
    "bolt": """<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.2 2 4.4 14.1h5.5L9 22l8.9-12.2h-5.5z"/></svg>""",
    "cherry": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.8 13.4c0-4.4 4.3-6.4 7.6-7.3M16.2 14.4c0-3.4 1.8-5.2 3.7-6"/><circle cx="7.6" cy="16.3" r="3.1"/><circle cx="16.2" cy="17.2" r="3.1"/><path d="M11.2 6.9C12.6 5.2 14.3 4.3 16.3 4"/></svg>""",
    "berry": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8.9" cy="14" r="2.9"/><circle cx="15.1" cy="14" r="2.9"/><circle cx="12" cy="18.1" r="2.5"/><path d="M12 11c0-3.8 2.8-6 6.8-6-.2 3.8-2.8 6-6.8 6Z"/></svg>""",
}

THEMES = [
    {
        "slug": "graduation",
        "name": "Graduation",
        "label": "Graduation",
        "mode": "light",
        "logo": "flower",
        "brand_before": "PagFlow",
        "brand_suffix": "Graduation",
        "file": "good_morning_relatorio_outubro",
        "folder": "C:/KanyeWest/GraduationTour/SAP_Pagamentos_RAW/",
        "select": "Graduation (Nuvens Pastel, Céu Claro & Rosa Choque)",
        "dest": "C:/KanyeWest/GraduationTour/Planilhas_Consolidadas/",
        "code_input": "graduation",
        "code_state": "success",
        "code_title": "Tema Graduation ativado.",
        "code_text": "O tema foi aplicado e será lembrado na próxima abertura.",
        "current": "Graduation",
        "mood": "Nuvens pastel, choque de rosa e azul, brilho de verão.",
    },
    {
        "slug": "ozzy",
        "name": "Ozzy",
        "label": "Ozzy",
        "mode": "dark",
        "logo": "bolt",
        "brand_before": "PAGFLOW",
        "brand_suffix": "OZZY",
        "file": "blizzard_of_ozz_relatorio_outubro",
        "folder": r"C:\OZZY_STAGE_DATA\SAP_PAYMENTS_1996\OCTOBER_PARANOID",
        "select": "Ozzy Osbourne (No More Tours — Preto, Vermelho & Amarelo)",
        "dest": r"C:\OZZY_STAGE_DATA\CONSOLIDATED_FINAL_EXCELS",
        "code_input": "ozzy osbourne tour",
        "code_state": "error",
        "code_title": "Código não reconhecido.",
        "code_text": "Confira o nome do tema e tente novamente. Nada foi alterado.",
        "current": "Ozzy",
        "mood": "Palco preto, vermelho sangue e amarelo de high gain.",
    },
    {
        "slug": "lana",
        "name": "Lana Del Rey",
        "label": "Lana Del Rey",
        "mode": "light",
        "logo": "cherry",
        "brand_before": "PagFlow",
        "brand_suffix": "Lana Del Rey",
        "file": "relatorio_summertime_outubro",
        "folder": "C:/Users/Gustavo/Financial/SAP_Exports/2024_Q4",
        "select": "Lana Del Rey (Cereja Vintage, Rosa Blush & Marfim)",
        "dest": "C:/Users/Gustavo/Desktop/Relatorios_Finalizados",
        "code_input": "lana del rey",
        "code_state": "success",
        "code_title": "Tema Lana Del Rey ativado.",
        "code_text": "O tema foi aplicado e será lembrado na próxima abertura.",
        "current": "Lana Del Rey",
        "mood": "Papel marfim, cereja vintage e melancolia editorial.",
    },
    {
        "slug": "acai",
        "name": "Açaí",
        "label": "Açaí",
        "mode": "dark",
        "logo": "berry",
        "brand_before": "PagFlow",
        "brand_suffix": "Premium",
        "file": "relatorio_acai_outubro",
        "folder": "C:/PagFlow/SAP_Exports/2026_10",
        "select": "Açaí Especial (Roxo Intenso & Dourado)",
        "dest": "C:/PagFlow/Relatorios_Consolidados",
        "code_input": "açaí",
        "code_state": "success",
        "code_title": "Tema Açaí ativado.",
        "code_text": "O tema foi aplicado e será lembrado na próxima abertura.",
        "current": "Açaí",
        "mood": "Roxo profundo, dourado e acabamento premium.",
    },
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def logo_mark(theme: dict) -> str:
    return ICON[theme["logo"]]


def theme_toggle(theme: dict) -> str:
    mode = "is-light" if theme["mode"] == "light" else "is-dark"
    return (
        f'<div class="theme-toggle {mode}" role="img" '
        f'aria-label="Alternador de tema {theme["label"]}">'
        f'<span class="knob"></span>{ICON["moon"]}{ICON["sun"]}</div>'
    )


def app_markup(theme: dict, *, settings_open: bool = False) -> str:
    gear_class = "top-icon is-active" if settings_open else "top-icon"
    suffix = (
        f' <span class="suffix">{esc(theme["brand_suffix"])}</span>'
        if theme["brand_suffix"]
        else ""
    )
    return f"""
    <div class="app">
      <header class="topbar">
        <span class="meta">FEITO POR GUSTAVO PINHEIRO</span>
        <div class="topbar-actions">
          <button class="{gear_class}" type="button" title="Configurações" aria-label="Configurações">{ICON["gear"]}</button>
          {theme_toggle(theme)}
        </div>
      </header>

      <section class="brand-card" aria-label="Identidade do PagFlow">
        <div class="logo" aria-hidden="true">{logo_mark(theme)}</div>
        <div class="brand-copy">
          <h1 class="brand-title">{esc(theme["brand_before"])}{suffix}</h1>
          <p class="brand-sub">Consolidação de pagamentos SAP</p>
        </div>
        <span class="badge">XLS → XLSX</span>
      </section>

      <nav class="view-switch" aria-label="Telas do PagFlow">
        <button type="button" class="active">Gerar Excel</button>
        <button type="button">Envio de e-mails</button>
      </nav>

      <main class="form">
        <section class="step">
          <div class="step-row">
            <span class="chip">1</span>
            <span class="step-title">Nome do arquivo de saída</span>
          </div>
          <div class="step-body">
            <div class="field"><span class="value">{esc(theme["file"])}</span></div>
          </div>
        </section>

        <section class="step">
          <div class="step-row">
            <span class="chip">2</span>
            <span class="step-title">Pasta com os arquivos de entrada</span>
          </div>
          <div class="step-body">
            <div class="row">
              <div class="field"><span class="value">{esc(theme["folder"])}</span></div>
              <button class="icon-field" type="button" title="Selecionar pasta de entrada" aria-label="Selecionar pasta de entrada">{ICON["folder"]}</button>
            </div>
          </div>
        </section>

        <section class="step">
          <div class="step-row">
            <span class="chip">3</span>
            <span class="step-title">Separação das abas</span>
          </div>
          <div class="step-body">
            <div class="segmented" role="group" aria-label="Separação das abas">
              <button class="seg" type="button">Marca</button>
              <button class="seg" type="button">LNeg</button>
              <button class="seg" type="button">Fornecedor</button>
              <button class="seg active" type="button">Não Separar</button>
            </div>
          </div>
        </section>

        <section class="step">
          <div class="step-row">
            <span class="chip">4</span>
            <span class="step-title">Personalização</span>
          </div>
          <div class="step-body">
            <div class="select">
              <span>{esc(theme["select"])}</span>
              {ICON["chevron"]}
            </div>
          </div>
        </section>

        <section class="step">
          <div class="step-row">
            <span class="chip">5</span>
            <span class="step-title">Destino do arquivo final</span>
          </div>
          <div class="step-body">
            <div class="row">
              <div class="field"><span class="value">{esc(theme["dest"])}</span></div>
              <button class="icon-field" type="button" title="Selecionar pasta de destino" aria-label="Selecionar pasta de destino">{ICON["folder"]}</button>
            </div>
          </div>
        </section>

        <div class="form-spacer"></div>
        <div class="divider"></div>

        <div class="actions">
          <button class="btn secondary" type="button">Limpar campos</button>
          <span class="spacer"></span>
          <button class="btn primary" type="button">{ICON["play"]} Gerar Excel</button>
        </div>
      </main>

      <div class="statusbar" role="status">
        <span class="status-dot"></span>
        <span>Pronto para uso.</span>
      </div>
    </div>
    """


def background_markup(theme: dict) -> str:
    bat = ""
    if theme["slug"] == "ozzy":
        bat = """
      <svg class="bat-bg" viewBox="0 0 240 90" aria-hidden="true">
        <path d="M120 35c-8-11-21-17-39-16 6 9 6 20-2 29 10-3 21-1 31 7 4-7 7-11 10-13 3 2 6 6 10 13 10-8 21-10 31-7-8-9-8-20-2-29-18-1-31 5-39 16Z"/>
        <path d="M112 30c-2-8-5-14-10-20 6 0 11 3 14 8 1-6 2-11 4-15 2 4 3 9 4 15 3-5 8-8 14-8-5 6-8 12-10 20Z"/>
      </svg>"""
    return f"""
    <div class="sky"></div>
    <div class="decor">
      <span class="orb o1"></span>
      <span class="orb o2"></span>
      <span class="orb o3"></span>{bat}
    </div>
    """


def settings_markup(theme: dict) -> str:
    state = theme["code_state"]
    state_icon = ICON["check"] if state == "success" else ICON["alert"]
    field_class = "is-success" if state == "success" else "is-error"
    return f"""
    <div class="scrim"></div>
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <header class="dialog-head">
        <div>
          <p class="dialog-eyebrow">PAGFLOW · AJUSTES</p>
          <h2 class="dialog-title" id="settings-title">Configurações</h2>
          <p class="dialog-sub">Ajustes do aplicativo</p>
        </div>
        <button class="dialog-close" type="button" title="Fechar" aria-label="Fechar">{ICON["close"]}</button>
      </header>

      <nav class="dialog-tabs" aria-label="Seções das configurações">
        <button class="dialog-tab" type="button">Geral</button>
        <button class="dialog-tab" type="button">Aparência</button>
        <button class="dialog-tab active" type="button">{ICON["key"]} Inserir código</button>
        <button class="dialog-tab" type="button">Sobre</button>
      </nav>

      <div class="dialog-body">
        <section class="code-card">
          <div class="code-head">
            <div class="key-badge" aria-hidden="true">{ICON["key"]}</div>
            <div>
              <p class="code-eyebrow">ACESSO RESTRITO</p>
              <h3 class="code-title">Ativar um tema pelo código</h3>
            </div>
          </div>

          <p class="code-copy">Digite o nome de um tema para desbloqueá-lo e aplicá-lo agora. Os códigos não aparecem em nenhuma lista.</p>

          <div class="code-label">CÓDIGO DO TEMA</div>
          <div class="code-row">
            <div class="code-field {field_class}">
              <span class="value">{esc(theme["code_input"])}</span>
              <span class="kbd">↵</span>
            </div>
            <button class="btn-activate" type="button">{ICON["key"]} Ativar tema</button>
          </div>

          <div class="feedback {state}" role="status">
            {state_icon}
            <div>
              <strong>{esc(theme["code_title"])}</strong>
              {esc(theme["code_text"])}
            </div>
          </div>

          <div class="current-theme">
            <span class="label">TEMA ATUAL</span>
            <span class="theme-pill"><span class="dot"></span>{esc(theme["current"])}</span>
          </div>
        </section>

        <aside class="code-aside">
          <p class="aside-title">COMO FUNCIONA</p>
          <ul class="aside-list">
            <li>Maiúsculas, acentos e espaços são ignorados.</li>
            <li>O tema fica salvo e volta na próxima abertura.</li>
            <li>Os códigos não aparecem em nenhuma lista.</li>
          </ul>
          <div class="aside-lock">
            {ICON["lock"]}
            <span>Feature quase secreta. Nenhum tema é listado antes de ser ativado.</span>
          </div>
        </aside>
      </div>

      <footer class="dialog-foot">
        <span class="foot-note">As alterações são aplicadas na hora.</span>
        <button class="btn secondary" type="button">Fechar</button>
      </footer>
    </section>
    """


def page(theme: dict, *, settings: bool) -> str:
    suffix = "-configuracoes" if settings else "-principal"
    title = f"{theme['name']} · {'Configurações' if settings else 'Tela principal'} · PagFlow"
    settings_css = '<link rel="stylesheet" href="_shared/settings.css">' if settings else ""
    body = app_markup(theme, settings_open=settings)
    if settings:
        body += settings_markup(theme)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1280">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="_shared/fonts.css">
  <link rel="stylesheet" href="_shared/base.css">
  {settings_css}
  <link rel="stylesheet" href="{theme['slug']}.css">
</head>
<body class="theme-{theme['slug']}">
  <div class="artboard">
    {background_markup(theme)}
    {body}
  </div>
</body>
</html>
"""


def index_page() -> str:
    cards = []
    for index, theme in enumerate(THEMES, start=1):
        cards.append(
            f"""
        <article class="card">
          <a class="shot" href="{index:02d}-{theme['slug']}-principal.html">
            <img src="../exports/{index:02d}-{theme['slug']}-principal.png" alt="Tela principal do tema {esc(theme['name'])}">
          </a>
          <div class="card-body">
            <div class="card-top">
              <span class="num">{index:02d}</span>
              <span class="code">{esc(theme['label'])}</span>
            </div>
            <h2>{esc(theme['name'])}</h2>
            <p>{esc(theme['mood'])}</p>
            <div class="links">
              <a href="{index:02d}-{theme['slug']}-principal.html">Tela principal</a>
              <a href="{index:02d}-{theme['slug']}-configuracoes.html">Configurações</a>
            </div>
          </div>
        </article>"""
        )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Temas secretos · PagFlow</title>
  <link rel="stylesheet" href="_shared/fonts.css">
  <style>
    :root {{
      color-scheme: dark;
      --bg: #08090c;
      --panel: #101116;
      --line: #23252c;
      --text: #f5f3f7;
      --muted: #8d8f99;
      --accent: #f4c542;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(900px 520px at 12% -8%, rgba(126, 34, 206, .18), transparent 65%),
        radial-gradient(800px 520px at 92% 8%, rgba(244, 197, 66, .08), transparent 60%),
        var(--bg);
      color: var(--text);
      font-family: "Space Grotesk", "Segoe UI", sans-serif;
    }}
    .wrap {{ width: min(1180px, calc(100% - 64px)); margin: 0 auto; padding: 64px 0 72px; }}
    .eyebrow {{ margin: 0 0 12px; font-size: 11px; font-weight: 700; letter-spacing: .16em; color: var(--accent); text-transform: uppercase; }}
    h1 {{ margin: 0; max-width: 820px; font-family: "Outfit", "Segoe UI", sans-serif; font-size: clamp(40px, 5vw, 64px); font-weight: 600; line-height: .98; letter-spacing: -.025em; }}
    .lede {{ max-width: 680px; margin: 20px 0 0; font-size: 15px; line-height: 1.6; color: #b9bbc4; }}
    .notice {{ margin: 28px 0 0; padding: 13px 16px; border: 1px solid rgba(244, 197, 66, .22); border-radius: 10px; background: rgba(244, 197, 66, .06); color: #e8d48d; font-size: 12px; line-height: 1.5; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; margin-top: 34px; }}
    .card {{ overflow: hidden; border: 1px solid var(--line); border-radius: 16px; background: var(--panel); }}
    .shot {{ display: block; overflow: hidden; border-bottom: 1px solid var(--line); background: #0b0c10; }}
    .shot img {{ display: block; width: 100%; height: auto; }}
    .shot:hover img {{ opacity: .88; }}
    .card-body {{ padding: 18px 20px 20px; }}
    .card-top {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }}
    .num {{ font-size: 11px; font-weight: 700; letter-spacing: .12em; color: var(--muted); }}
    .code {{ padding: 4px 8px; border: 1px solid #33363f; border-radius: 6px; background: #171920; color: #cfd1d8; font-family: "JetBrains Mono", Consolas, monospace; font-size: 10px; letter-spacing: .04em; }}
    h2 {{ margin: 0; font-family: "Outfit", "Segoe UI", sans-serif; font-size: 24px; font-weight: 600; }}
    .card p {{ margin: 7px 0 0; font-size: 12px; line-height: 1.5; color: var(--muted); }}
    .links {{ display: flex; gap: 16px; margin-top: 14px; }}
    .links a {{ color: var(--accent); font-size: 11px; font-weight: 600; text-decoration: none; }}
    .links a:hover {{ text-decoration: underline; }}
    .foot {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; line-height: 1.5; }}
    @media (max-width: 860px) {{
      .wrap {{ width: min(100% - 36px, 680px); padding-top: 40px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .foot {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <p class="eyebrow">Temas secretos · PagFlow</p>
    <h1>Quatro direções para o mesmo fluxo.</h1>
    <p class="lede">Uma coleção de telas estáticas que traduzem as quatro linguagens visuais do arquivo <em>temas pagflow.figcraft</em> para a estrutura real do PagFlow: cinco passos, campos de 32 px, cartões de 12 px e a mesma barra de status.</p>
    <p class="notice"><strong>Design only.</strong> Nada aqui está integrado ao aplicativo. As telas são referências visuais, sem JavaScript e sem regra de negócio. O guia de implementação está em <strong>GUIA_PARA_AGENTE.md</strong>.</p>

    <div class="grid">{''.join(cards)}
    </div>

    <footer class="foot">
      <span>PagFlow · kit de design para temas secretos</span>
      <span>Fonte: <em>temas pagflow.figcraft</em> · estrutura preservada do app atual</span>
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    SCREENS.mkdir(parents=True, exist_ok=True)
    for index, theme in enumerate(THEMES, start=1):
        main_path = SCREENS / f"{index:02d}-{theme['slug']}-principal.html"
        config_path = SCREENS / f"{index:02d}-{theme['slug']}-configuracoes.html"
        main_path.write_text(page(theme, settings=False), encoding="utf-8")
        config_path.write_text(page(theme, settings=True), encoding="utf-8")
        print(main_path.name)
        print(config_path.name)
    index_path = SCREENS / "index.html"
    index_path.write_text(index_page(), encoding="utf-8")
    print(index_path.name)


if __name__ == "__main__":
    main()
