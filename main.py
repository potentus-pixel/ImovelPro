import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))


def _excepthook(tipo, valor, tb):
    # Captura QUALQUER erro nao tratado (inclusive nos imports) num arquivo,
    # ja que o pythonw nao tem console para exibir o traceback.
    """Registra exceções não tratadas e apresenta o erro ao usuário."""
    import traceback
    texto = "".join(traceback.format_exception(tipo, valor, tb))
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "erro_inicio.txt"), "w", encoding="utf-8") as _f:
            _f.write(texto)
    except Exception:
        pass
    # Mostra um popup com o erro (tkinter nao precisa de customtkinter)
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        _tk.Tk().withdraw()
        _mb.showerror("Erro ao iniciar o ImóvelPro", texto)
    except Exception:
        pass


sys.excepthook = _excepthook

import customtkinter as ctk
from database import init_db
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED,
                     GREEN, GREEN_D, TEAL_L, Toast, font,
                     atualizar_tema_tabelas)

from views.dashboard  import Dashboard
from views.clientes   import Clientes
from views.corretores import Corretores
from views.imoveis    import Imoveis
from views.imovel_detalhe import ImovelDetalhe
from views.contratos  import Contratos
from views.boletos    import Boletos

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config.json")


def _carregar_tema():
    """Carrega das configurações o tema visual salvo pelo usuário."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            tema = json.load(f).get("tema", "dark")
        return tema if tema in ("light", "dark") else "dark"
    except (OSError, ValueError, TypeError):
        return "dark"


ctk.set_appearance_mode(_carregar_tema())
ctk.set_default_color_theme("green")

NAV_ITEMS = [
    ("dashboard",  "🏠  Dashboard"),
    ("imoveis",    "🏢  Imóveis"),
    ("clientes",   "👥  Clientes"),
    ("corretores", "🪪  Corretores"),
    ("contratos",  "📄  Contratos"),
    ("boletos",    "🧾  Boletos"),
]


class App(ctk.CTk):
    def __init__(self):
        """Inicializa App e prepara seu estado e interface."""
        super().__init__()
        self.title("ImóvelPro — Sistema de Gestão Imobiliária")
        self.geometry("1280x760")
        self.minsize(920, 600)
        self.configure(fg_color=BG)

        # Ícone da janela / barra de tarefas (não usar o ícone padrão do Python)
        _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "app_icon.ico")
        try:
            self.iconbitmap(_ico)
        except Exception:
            pass

        self._toast  = Toast(self)
        self._pages  = {}
        self._btns   = {}
        self._current = None
        self._dashboard_job = None
        self._theme_job = None

        self._build_sidebar()
        self._build_main()
        self._navigate("dashboard")

    # ── SIDEBAR ─────────────────────────────────────────────
    def _build_sidebar(self):
        """Monta a barra lateral com a marca e as opções de navegação."""
        sb = ctk.CTkFrame(self, width=200, fg_color=BG2,
                          corner_radius=0, border_width=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Logo
        logo_f = ctk.CTkFrame(sb, fg_color="transparent", height=64)
        logo_f.pack(fill="x")
        logo_f.pack_propagate(False)
        ctk.CTkLabel(logo_f, text="Imóvel", font=("Segoe UI", 18, "bold"),
                     text_color=TEXT).place(relx=0.12, rely=0.5, anchor="w")
        ctk.CTkLabel(logo_f, text="Pro", font=("Segoe UI", 18, "bold"),
                     text_color=GREEN).place(relx=0.52, rely=0.5, anchor="w")

        sep = ctk.CTkFrame(sb, fg_color=BORDER, height=1)
        sep.pack(fill="x")

        # Itens de navegação
        nav_f = ctk.CTkFrame(sb, fg_color="transparent")
        nav_f.pack(fill="both", expand=True, padx=10, pady=12)

        for key, label in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_f, text=label, anchor="w",
                font=font(15),
                height=46, corner_radius=8,
                fg_color="transparent", hover_color=BG3,
                text_color=MUTED,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=2)
            self._btns[key] = btn

        # Rodapé sidebar
        sep2 = ctk.CTkFrame(sb, fg_color=BORDER, height=1)
        sep2.pack(fill="x", side="bottom", pady=(0, 0))
        foot = ctk.CTkFrame(sb, fg_color="transparent", height=98)
        foot.pack(side="bottom", fill="x")
        foot.pack_propagate(False)
        ctk.CTkLabel(foot, text="Gestão imobiliária", wraplength=175,
                     font=font(10), text_color=MUTED).pack(pady=(8, 1))
        ctk.CTkLabel(foot, text="v1.1  •  SQLite",
                     font=("Segoe UI", 10), text_color=MUTED
                     ).pack(pady=(1, 0))

        tema_f = ctk.CTkFrame(sb, fg_color="transparent")
        tema_f.pack(side="bottom", fill="x", padx=12, pady=(6, 8))
        ctk.CTkLabel(tema_f, text="Aparência", font=font(11),
                     text_color=MUTED).pack(anchor="w", pady=(0, 4))
        self._tema = ctk.CTkSegmentedButton(
            tema_f, values=["Claro", "Escuro"], height=30,
            fg_color=BG3, selected_color=GREEN,
            selected_hover_color=GREEN_D, unselected_color=BG3,
            unselected_hover_color=BORDER, text_color=TEXT,
            command=self._trocar_tema)
        self._tema.pack(fill="x")
        self._tema.set(
            "Escuro" if ctk.get_appearance_mode() == "Dark" else "Claro")

    def _trocar_tema(self, escolha):
        """Alterna o tema visual, salva a preferência e atualiza a interface."""
        tema = "light" if escolha == "Claro" else "dark"
        ctk.set_appearance_mode(tema)
        if self._theme_job is not None:
            self.after_cancel(self._theme_job)

        def finalizar_tema():
            """Aplica o tema aos componentes após a montagem da janela."""
            self._theme_job = None
            atualizar_tema_tabelas()
            try:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump({"tema": tema}, f, ensure_ascii=False, indent=2)
            except OSError:
                pass

        self._theme_job = self.after_idle(finalizar_tema)

    # ── CONTEÚDO PRINCIPAL ──────────────────────────────────
    def _build_main(self):
        """Monta a área principal e instancia as telas da aplicação."""
        self._container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._container.pack(side="left", fill="both", expand=True)

        # Instancia todas as views
        self._pages["dashboard"]  = Dashboard(self._container,
                                              on_open_imovel=self._open_imovel)
        self._pages["imoveis"]    = Imoveis(self._container, self._toast,
                                            on_open=self._open_imovel)
        self._pages["clientes"]   = Clientes(self._container, self._toast)
        self._pages["corretores"] = Corretores(self._container, self._toast)
        self._pages["contratos"]  = Contratos(self._container, self._toast)
        self._pages["boletos"]    = Boletos(self._container, self._toast)

        for page in self._pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            page.lower()

    # ── NAVEGAÇÃO ───────────────────────────────────────────
    def _open_imovel(self, imovel_id):
        """Abre a tela de detalhes do imóvel identificado pelo código recebido."""
        if not imovel_id:
            return
        ImovelDetalhe(self, imovel_id, self._toast)

    def _navigate(self, key):
        """Exibe a tela solicitada e atualiza o estado visual da navegação."""
        if self._dashboard_job is not None:
            self.after_cancel(self._dashboard_job)
            self._dashboard_job = None
        if self._current:
            self._pages[self._current].lower()
            self._btns[self._current].configure(
                fg_color="transparent", text_color=MUTED)

        self._current = key
        page = self._pages[key]
        page.lift()

        self._btns[key].configure(
            fg_color=BG3, text_color=TEXT)

        # Atualiza dados da página
        if hasattr(page, "atualizar"):
            if key == "dashboard":
                # Exibe primeiro o conteúdo em cache e só então verifica se
                # uma reconstrução dos cartões e gráficos é necessária.
                def atualizar_dashboard():
                    """Solicita a atualização dos indicadores exibidos no painel."""
                    self._dashboard_job = None
                    if self._current == "dashboard":
                        page.atualizar()
                self._dashboard_job = self.after(30, atualizar_dashboard)
            else:
                page.atualizar()


if __name__ == "__main__":
    try:
        init_db()
        app = App()
        app.mainloop()
    except Exception as exc:  # sem console: mostra erro em tela em vez de sumir
        import traceback
        tb = traceback.format_exc()
        try:
            import tkinter as _tk
            _tk.Tk().withdraw()
            from tkinter import messagebox as _mb
            _mb.showerror("Erro ao iniciar o ImóvelPro", f"{exc}\n\n{tb}")
        except Exception:
            with open(os.path.join(os.path.dirname(__file__), "erro_inicio.txt"),
                      "w", encoding="utf-8") as _f:
                _f.write(f"{exc}\n\n{tb}")


