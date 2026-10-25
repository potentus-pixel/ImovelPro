import tkinter as tk
import customtkinter as ctk
import weakref

# ── PALETA ───────────────────────────────────────────────────
GREEN   = ("#16805f", "#1D9E75")
GREEN_D = ("#0F6E56", "#0F6E56")
BG      = ("#f4f6f8", "#16181d")
BG2     = ("#ffffff", "#20242c")
BG3     = ("#e8edf1", "#2b303a")
BORDER  = ("#cbd3da", "#3a4150")
TEXT    = ("#17202a", "#f4f2ee")
MUTED   = ("#5f6b76", "#b3ada3")
AMBER   = ("#a76708", "#FAC775")
RED     = ("#b83232", "#F09595")
TEAL_L  = ("#087f67", "#9FE1CB")
BLUE    = ("#2476ad", "#4A9ED9")
PURPLE  = ("#7650a5", "#A77FD8")


_RENDER_MODE = None


def resolve_color(color):
    """Resolve uma cor adaptativa para widgets Tk/PIL que não entendem tuplas."""
    if isinstance(color, (tuple, list)):
        modo = _RENDER_MODE or ctk.get_appearance_mode()
        return color[1] if modo == "Dark" else color[0]
    return color


_TABELAS = weakref.WeakSet()

STATUS_COLORS = {
    "ativo":      ("#1f3d2e", "#9FE1CB"),
    "em espera":  ("#4a3613", "#FAC775"),
    "encerrado":  ("#34373d", "#9aa0a8"),
    "pendente":   ("#4a3613", "#FAC775"),
    "pago":       ("#1f3d2e", "#9FE1CB"),
    "vencido":    ("#4d1f1f", "#F09595"),
}

TIPO_COLORS = {
    "venda":   ("#163a5e", "#9ed0fc"),
    "aluguel": ("#123f33", "#9fe1cb"),
    "ambos":   ("#3a2459", "#cbb0f0"),
}

FONT = "Segoe UI"
FONT_SIZE = 13   # base maior (era 12/11 em vários lugares)
FONT_SIZE_SM = 12
FONT_SIZE_LG = 15

def font(size=FONT_SIZE, weight="normal"):
    """Monta a configuração de fonte usando a família e o tamanho do tema atual."""
    return (FONT, size, weight)


def fmt_brl(v):
    """Formata um valor numérico como moeda brasileira."""
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_date(d):
    """Converte uma data armazenada no sistema para o formato de exibição."""
    if not d:
        return "—"
    try:
        y, m, dd = str(d).split("-")
        return f"{dd}/{m}/{y}"
    except Exception:
        return str(d)


# ── TABELA CUSTOMIZADA ───────────────────────────────────────
class Tabela(ctk.CTkFrame):
    """Tabela com Treeview estilizada, listras alternadas e scroll."""

    def __init__(self, master, colunas, larguras, on_select=None, on_open=None, **kw):
        """Inicializa Tabela e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG2, corner_radius=10, **kw)
        self.on_select = on_select
        self.on_open = on_open
        _TABELAS.add(self)

        import tkinter.ttk as ttk

        style = ttk.Style()
        style.theme_use("default")
        self._style = style
        self._aplicar_tema()
        style.layout("IP.Treeview", [("IP.Treeview.treearea", {"sticky": "nswe"})])

        # listras alternadas para leitura mais fácil
        self.tree = ttk.Treeview(self, columns=colunas, show="headings",
                                 style="IP.Treeview", selectmode="browse")
        self.tree.tag_configure("odd",  background=resolve_color(BG2))
        self.tree.tag_configure("even", background=resolve_color(BG3))

        for col, larg in zip(colunas, larguras):
            self.tree.heading(col, text=col)
            # stretch=False: a coluna mantém sua largura e, quando a soma
            # passa da área visível, aparece a barra de rolagem HORIZONTAL
            # (em vez de espremar/desalinhar as colunas).
            self.tree.column(col, width=larg, minwidth=larg,
                             stretch=True, anchor="w")

        sb = ctk.CTkScrollbar(self, command=self.tree.yview, fg_color=BG2,
                               button_color=BORDER, button_hover_color=MUTED)
        self.tree.configure(yscrollcommand=sb.set)

        # scroll horizontal (aparece quando as colunas somam mais que a area)
        self.tree.configure(xscrollcommand=self._on_xscroll)
        self._xsb = ctk.CTkScrollbar(self, orientation="horizontal",
                                      command=self.tree.xview, fg_color=BG2,
                                      button_color=BORDER,
                                      button_hover_color=MUTED)
        self._xsb_visible = False

        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=8)

        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: on_select(self.selected_id()))
        if on_open:
            self.tree.bind("<Double-1>", lambda e: on_open(self.selected_id()))

        self._id_map = {}
        self._row_map = {}  # guarda a tupla COMPLETA (com id) por linha

    def _aplicar_tema(self):
        """Aplica ao componente as cores e fontes do tema atual."""
        self._style.configure(
            "IP.Treeview", background=resolve_color(BG2),
            foreground=resolve_color(TEXT), fieldbackground=resolve_color(BG2),
            borderwidth=0, rowheight=44, font=font(13))
        self._style.configure(
            "IP.Treeview.Heading", background=resolve_color(BG3),
            foreground=resolve_color(MUTED), borderwidth=0,
            relief="flat", font=font(13, "bold"))
        self._style.map(
            "IP.Treeview", background=[("selected", resolve_color(GREEN_D))],
            foreground=[("selected", "#ffffff")])
        if hasattr(self, "tree"):
            self.tree.tag_configure("odd", background=resolve_color(BG2))
            self.tree.tag_configure("even", background=resolve_color(BG3))


    def _on_xscroll(self, first, last):
        # mostra a scrollbar horizontal somente quando necessario
        """Sincroniza a rolagem horizontal dos elementos da tabela."""
        try:
            f, l = float(first), float(last)
        except ValueError:
            return
        if l - f < 0.999:
            if not self._xsb_visible:
                self._xsb.pack(side="bottom", fill="x",
                               padx=(8, 4), pady=(0, 4))
                self._xsb_visible = True
        else:
            if self._xsb_visible:
                self._xsb.pack_forget()
                self._xsb_visible = False

    def preencher(self, rows, id_col=0):
        """Substitui o conteúdo da tabela pelos registros recebidos."""
        self.tree.delete(*self.tree.get_children())
        self._id_map = {}
        self._row_map = {}
        for idx, row in enumerate(rows):
            # exibe TODAS as colunas EXCETO a do id (id_col), que é
            # valor oculto usado apenas para seleção/carregar registro.
            disp = [str(v) if v is not None else "—"
                    for i, v in enumerate(row) if i != id_col]
            tag = "odd" if idx % 2 else "even"
            iid = self.tree.insert("", "end", values=disp, tags=(tag,))
            self._id_map[iid] = row[id_col]
            self._row_map[iid] = tuple(row)

    def selected_id(self):
        """Devolve o identificador do registro selecionado na tabela."""
        sel = self.tree.selection()
        if not sel:
            return None
        return self._id_map.get(sel[0])

    def selected_row(self):
        """Devolve os valores da linha atualmente selecionada."""
        sel = self.tree.selection()
        if not sel:
            return None
        return self._row_map.get(sel[0])


# ── CAMPO DE FORMULÁRIO ──────────────────────────────────────
def atualizar_tema_tabelas():
    """Atualiza os estilos compartilhados das tabelas conforme o tema ativo."""
    for tabela in list(_TABELAS):
        tabela._aplicar_tema()


class Campo(ctk.CTkFrame):
    def __init__(self, master, label, widget_class=ctk.CTkEntry,
                 width=220, values=None, **kw):
        """Inicializa Campo e prepara seu estado e interface."""
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=label, text_color=MUTED,
                     font=font(13)).pack(anchor="w")
        if widget_class == ctk.CTkOptionMenu:
            self.w = ctk.CTkOptionMenu(self, values=values or [], width=width,
                                       fg_color=BG3, button_color=GREEN,
                                       button_hover_color=GREEN_D,
                                       dropdown_fg_color=BG3,
                                       text_color=TEXT, **kw)
        else:
            self.w = widget_class(self, width=width, fg_color=BG3,
                                  border_color=BORDER, text_color=TEXT,
                                  placeholder_text_color=MUTED, **kw)
        self.w.pack(fill="x", pady=(2, 0))

    def get(self):
        """Devolve o valor atual armazenado pelo componente."""
        return self.w.get()

    def set(self, v):
        """Define o valor do componente e atualiza sua apresentação."""
        if isinstance(self.w, ctk.CTkOptionMenu):
            self.w.set(v)
        elif isinstance(self.w, ctk.CTkEntry):
            self.w.delete(0, "end")
            self.w.insert(0, str(v) if v is not None else "")

    def configure(self, **kw):
        """Atualiza as opções configuráveis e reaplica o estado visual."""
        self.w.configure(**kw)


# ── BOTÕES ───────────────────────────────────────────────────
def btn_primary(master, text, cmd, width=120):
    """Cria um botão com o estilo visual de ação principal."""
    return ctk.CTkButton(master, text=text, command=cmd, width=width,
                         height=38, fg_color=GREEN, hover_color=GREEN_D,
                         font=font(14, "bold"))


def btn_secondary(master, text, cmd, width=100):
    """Cria um botão com o estilo visual de ação secundária."""
    return ctk.CTkButton(master, text=text, command=cmd, width=width,
                         height=38, fg_color=BG3, hover_color=BORDER,
                         border_width=1, border_color=BORDER,
                         text_color=TEXT, font=font(14))


def btn_danger(master, text, cmd, width=100):
    """Cria um botão com o estilo visual reservado a ações destrutivas."""
    return ctk.CTkButton(master, text=text, command=cmd, width=width,
                         height=38, fg_color="#5a1a1a", hover_color="#7a2a2a",
                         text_color=RED, font=font(14))


# ── DIÁLOGO DE CONFIRMAÇÃO ───────────────────────────────────
def confirmar(master, titulo, mensagem):
    """Exibe uma confirmação antes de permitir a continuação da ação."""
    result = [False]
    dlg = ctk.CTkToplevel(master)
    dlg.title(titulo)
    dlg.geometry("400x180")
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.configure(fg_color=BG2)

    ctk.CTkLabel(dlg, text=mensagem, wraplength=360,
                 text_color=TEXT, font=font(13)).pack(pady=(28, 16), padx=24)

    row = ctk.CTkFrame(dlg, fg_color="transparent")
    row.pack()

    def ok():
        """Valida a entrada da caixa de diálogo e confirma seu fechamento."""
        result[0] = True
        dlg.destroy()

    btn_danger(row, "Confirmar", ok).pack(side="left", padx=6)
    btn_secondary(row, "Cancelar", dlg.destroy).pack(side="left", padx=6)
    dlg.wait_window()
    return result[0]


# ── TOAST / NOTIFICAÇÃO ──────────────────────────────────────
class Toast:
    def __init__(self, root):
        """Inicializa Toast e prepara seu estado e interface."""
        self.root = root
        self._job = None

    def show(self, msg, error=False):
        """Exibe temporariamente a mensagem informativa do componente."""
        color = "#5a1a1a" if error else "#1a3d2e"
        txt_color = RED if error else TEAL_L

        if hasattr(self, "_win") and self._win.winfo_exists():
            self._win.destroy()

        self._win = ctk.CTkToplevel(self.root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.configure(fg_color=color)

        ctk.CTkLabel(self._win, text=msg, text_color=txt_color,
                     font=font(13), padx=16, pady=10).pack()

        self._win.update_idletasks()
        w = self._win.winfo_width()
        h = self._win.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self._win.geometry(f"+{sw - w - 30}+{sh - h - 60}")

        if self._job:
            self.root.after_cancel(self._job)
        self._job = self.root.after(2800, self._hide)

    def _hide(self):
        """Oculta a mensagem temporária exibida pelo componente."""
        if hasattr(self, "_win") and self._win.winfo_exists():
            self._win.destroy()


# ── FILTRO BAR ───────────────────────────────────────────────
class FiltroBar(ctk.CTkFrame):
    def __init__(self, master, on_search, placeholder="Buscar...",
                 filtros=None, btn_label="+ Novo", btn_cmd=None, **kw):
        """Inicializa FiltroBar e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG2, corner_radius=0, **kw)
        self.on_search = on_search
        self._vars = {}

        self._entry = ctk.CTkEntry(self, placeholder_text=placeholder,
                                   width=300, fg_color=BG3,
                                   border_color=BORDER, text_color=TEXT,
                                   placeholder_text_color=MUTED,
                                   font=font(12))
        self._entry.pack(side="left", padx=(12, 6), pady=10)
        self._entry.bind("<KeyRelease>", lambda e: on_search())

        if filtros:
            for label, opts in filtros:
                var = ctk.StringVar(value="")
                self._vars[label] = var
                om = ctk.CTkOptionMenu(self, values=[""] + opts,
                                       variable=var, width=150,
                                       fg_color=BG3, button_color=GREEN,
                                       button_hover_color=GREEN_D,
                                       dropdown_fg_color=BG3,
                                       text_color=TEXT, font=font(12),
                                       command=lambda _: on_search())
                om.pack(side="left", padx=4, pady=10)

        if btn_cmd:
            btn_primary(self, btn_label, btn_cmd, width=150).pack(
                side="right", padx=12, pady=10)

    def get_query(self):
        """Devolve o texto digitado no campo de pesquisa."""
        return self._entry.get().strip()

    def get_filtro(self, label):
        """Devolve o filtro selecionado no controle de pesquisa."""
        return self._vars.get(label, ctk.StringVar()).get()


# ── LISTA COM TAGS (proprietários, partes, corretores) ────────
class ListaTag(ctk.CTkScrollableFrame):
    def __init__(self, master, altura=120, on_change=None, **kw):
        """Inicializa ListaTag e prepara seu estado e interface."""
        super().__init__(master, height=altura, fg_color=BG3,
                         scrollbar_button_color=BORDER, **kw)
        self._items = []  # lista de dicts
        self._on_change = on_change

    def adicionar(self, item: dict):
        """Adiciona um item à coleção exibida pelo componente."""
        self._items.append(item)
        self._render()
        if self._on_change:
            self._on_change()

    def remover(self, idx):
        """Remove o item selecionado da coleção exibida pelo componente."""
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._render()
            if self._on_change:
                self._on_change()

    def _render(self):
        """Redesenha o componente com os dados e dimensões atuais."""
        for w in self.winfo_children():
            w.destroy()
        for i, item in enumerate(self._items):
            row = ctk.CTkFrame(self, fg_color=BG2, corner_radius=6)
            row.pack(fill="x", pady=2, padx=4)
            ctk.CTkLabel(row, text=item.get("label", ""),
                         text_color=TEXT, font=font(12),
                         anchor="w").pack(side="left", padx=8, pady=4)
            if "sub" in item:
                ctk.CTkLabel(row, text=item["sub"], text_color=MUTED,
                             font=font(11)).pack(side="left", padx=2)
            idx = i
            ctk.CTkButton(row, text="✕", width=28, height=24,
                          fg_color="transparent", hover_color=BG3,
                          text_color=RED,
                          command=lambda ix=idx: self.remover(ix)
                          ).pack(side="right", padx=4)

    def get_items(self):
        """Devolve uma cópia dos itens mantidos pelo componente."""
        return list(self._items)

    def clear(self):
        """Remove todos os itens atualmente mantidos pelo componente."""
        self._items = []
        self._render()

    def set_items(self, items):
        """Substitui a coleção atual pelos itens recebidos."""
        self._items = list(items)
        self._render()


# ── GRÁFICOS (PIL + CTkImage: alta resolução, nítidos em HiDPI) ──
import math
from PIL import Image, ImageDraw, ImageFont

def _hex_rgb(hexcor):
    """Converte uma cor hexadecimal em uma tupla de componentes RGB."""
    hexcor = resolve_color(hexcor)
    h = (hexcor or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (150, 150, 150)

def _dim(rgb, f=0.8):
    """Calcula uma variação mais escura da cor informada."""
    return tuple(int(c * f) for c in rgb)

def _font(size, bold=False):
    """Carrega a fonte usada para desenhar textos no componente."""
    if bold:
        paths = ["C:/Windows/Fonts/segoeuib.ttf",
                 "C:/Windows/Fonts/segoeuiz.ttf",
                 "C:/Windows/Fonts/segoeui.ttf"]
    else:
        paths = ["C:/Windows/Fonts/segoeui.ttf"]
    paths += ["C:/Windows/Fonts/arial.ttf",
              "C:/Windows/Fonts/arialbd.ttf"]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _bg2_rgb():
    """Obtém em RGB a cor secundária de fundo do tema atual."""
    return _hex_rgb(BG2)


def _render_nos_dois_temas(render):
    """Gera imagens adaptativas sem alternar o tema global da aplicação."""
    global _RENDER_MODE
    try:
        _RENDER_MODE = "Light"
        clara = render()
        _RENDER_MODE = "Dark"
        escura = render()
        return clara, escura
    finally:
        _RENDER_MODE = None


class DonutChart(ctk.CTkFrame):
    """Gráfico de rosca (PIL + CTkImage): data=[(label,valor,cor),...].
    - render em alta resolução (supersampling) => nítido em telas HiDPI
    - desenho completo e imediato (sem animação incompleta / arco aberto)
    - hover destaca o segmento e mostra tooltip
    """

    def __init__(self, master, titulo, largura=250, altura=185, **kw):
        """Inicializa DonutChart e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG2, corner_radius=10, **kw)
        self._titulo = titulo
        self._dw, self._dh = int(largura), int(altura)
        self._scale = 2
        self._data = []
        self._segs = []
        self._hover = None
        self._ctk_img = None
        ctk.CTkLabel(self, text=titulo, font=font(14, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 0))
        self._img = ctk.CTkLabel(self, text="", fg_color="transparent")
        self._img.pack(padx=10, pady=(2, 12))
        self._img.bind("<Motion>", self._on_move)
        self._img.bind("<Leave>", self._on_leave)
        self._tip = None
        self._render()

    def set_data(self, data):
        """Substitui os dados do gráfico e solicita uma nova renderização."""
        nova = [(l, v, c) for (l, v, c) in data if v and v > 0]
        if nova == self._data:
            return
        self._data = nova
        self._segs = []
        self._hover = None
        self._render()

    # ── render puro (testável sem GUI) ──
    def render_pil(self, hover=None, prog=1.0):
        """Desenha o gráfico em uma imagem PIL e devolve o resultado."""
        S = self._scale
        W, H = self._dw * S, self._dh * S
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if not self._data:
            f = _font(int(H * 0.10))
            d.text((W / 2, H / 2), "Sem dados", fill=_hex_rgb(MUTED),
                   font=f, anchor="mm")
            return img.resize((self._dw, self._dh), Image.LANCZOS)
        total = sum(v for _, v, _ in self._data) or 1
        cx, cy = W * 0.31, H * 0.5
        r_out = min(W * 0.25, H * 0.42)
        t = int(r_out * 0.34)
        r_in = r_out - t
        bg = _bg2_rgb()
        ang = 270.0
        self._segs = []
        for idx, (label, val, color) in enumerate(self._data):
            sweep = val / total * 360.0 * prog
            rgb = _hex_rgb(color)
            if hover is not None and idx != hover:
                rgb = _dim(rgb, 0.78)
            wseg = t + (S * 3 if idx == hover else 0)
            bbox = [cx - r_out, cy - r_out, cx + r_out, cy + r_out]
            d.arc(bbox, start=ang, end=ang + sweep, fill=rgb, width=wseg)
            self._segs.append((ang, ang + sweep, color, label, val))
            ang += sweep
        # furo central (cor do card)
        d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=bg)
        # texto central
        if hover is not None and 0 <= hover < len(self._data):
            lbl, val, _ = self._data[hover]
            d.text((cx, cy - H * 0.05), str(val), fill=_hex_rgb(TEXT),
                   font=_font(int(H * 0.13), bold=True), anchor="mm")
            d.text((cx, cy + H * 0.09), lbl, fill=_hex_rgb(MUTED),
                   font=_font(int(H * 0.06)), anchor="mm")
        else:
            d.text((cx, cy - H * 0.05), str(total), fill=_hex_rgb(TEXT),
                   font=_font(int(H * 0.14), bold=True), anchor="mm")
            d.text((cx, cy + H * 0.09), "total", fill=_hex_rgb(MUTED),
                   font=_font(int(H * 0.06)), anchor="mm")
        # legenda à direita
        lx = W * 0.60
        ly = H * 0.16
        lh = H * 0.17
        for idx, (label, val, color) in enumerate(self._data):
            pct = val / total * 100
            fg = _hex_rgb(TEXT) if (hover is None or idx == hover) else _hex_rgb(MUTED)
            d.rectangle([lx, ly + 2 * S, lx + 12 * S, ly + 14 * S], fill=_hex_rgb(color))
            d.text((lx + 18 * S, ly), label, fill=fg, font=_font(int(H * 0.058)))
            d.text((lx + 18 * S, ly + H * 0.075), f"{val}  ({pct:.0f}%)",
                   fill=fg, font=_font(int(H * 0.05)))
            ly += lh
        return img.resize((self._dw, self._dh), Image.LANCZOS)

    def _render(self):
        """Redesenha o componente com os dados e dimensões atuais."""
        clara, escura = _render_nos_dois_temas(
            lambda: self.render_pil(hover=self._hover))
        self._ctk_img = ctk.CTkImage(light_image=clara, dark_image=escura,
                                     size=(self._dw, self._dh))
        self._img.configure(image=self._ctk_img, text="")

    # ── hit-test (coords do label -> segmento) ──
    def _hit(self, x, y):
        """Identifica o elemento gráfico localizado sob as coordenadas informadas."""
        S = self._scale
        W, H = self._dw * S, self._dh * S
        cx, cy = W * 0.31, H * 0.5
        r_out = min(W * 0.25, H * 0.42)
        t = int(r_out * 0.34)
        r_in = r_out - t
        dx, dy = x * S - cx, y * S - cy
        dist = math.hypot(dx, dy)
        if dist < r_in or dist > r_out + 8 * S:
            return None
        a = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        rel = (a - 270) % 360
        tot = sum(v for _, v, _ in self._data) or 1
        acc = 0.0
        for idx, (label, val, color) in enumerate(self._data):
            ext = val / tot * 360.0
            if acc <= rel < acc + ext:
                return idx
            acc += ext
        return None

    def _on_move(self, ev):
        """Trata o movimento do ponteiro e exibe detalhes do elemento apontado."""
        idx = self._hit(ev.x, ev.y)
        if idx != self._hover:
            self._hover = idx
            self._render()
            self._show_tip(ev, idx)

    def _on_leave(self, ev):
        """Oculta os detalhes quando o ponteiro deixa a área do gráfico."""
        if self._hover is not None:
            self._hover = None
            self._render()
        self._hide_tip()

    def _show_tip(self, ev, idx):
        """Exibe a dica com os dados do elemento gráfico apontado."""
        self._hide_tip()
        if idx is None or idx >= len(self._data):
            return
        label, val, color = self._data[idx]
        total = sum(v for _, v, _ in self._data) or 1
        pct = val / total * 100
        tip = ctk.CTkToplevel(self)
        tip.wm_overrideredirect(True)
        tip.configure(fg_color=BG3)
        ctk.CTkLabel(tip, text=f"{label}:  {val}  ({pct:.1f}%)",
                     font=font(12), text_color=TEXT, padx=10, pady=5).pack()
        x = self.winfo_rootx() + ev.x + 14
        y = self.winfo_rooty() + ev.y + 14
        tip.geometry(f"+{x}+{y}")
        self._tip = tip

    def _hide_tip(self):
        """Oculta a dica de dados do gráfico."""
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


class BarChart(ctk.CTkFrame):
    """Gráfico de barras verticais (PIL + CTkImage). data=[(label,valor,cor),...]."""

    def __init__(self, master, titulo, largura=250, altura=160, **kw):
        """Inicializa BarChart e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG2, corner_radius=10, **kw)
        self._titulo = titulo
        self._dw, self._dh = int(largura), int(altura)
        self._scale = 2
        self._data = []
        self._hover = None
        self._ctk_img = None
        ctk.CTkLabel(self, text=titulo, font=font(14, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 0))
        self._img = ctk.CTkLabel(self, text="", fg_color="transparent")
        self._img.pack(padx=10, pady=(2, 12))
        self._img.bind("<Motion>", self._on_move)
        self._img.bind("<Leave>", self._on_leave)
        self._tip = None
        self._render()

    def set_data(self, data):
        """Substitui os dados do gráfico e solicita uma nova renderização."""
        nova = [(l, v, c) for (l, v, c) in data if v and v > 0]
        if nova == self._data:
            return
        self._data = nova
        self._hover = None
        self._render()

    def render_pil(self, hover=None, prog=1.0):
        """Desenha o gráfico em uma imagem PIL e devolve o resultado."""
        S = self._scale
        W, H = self._dw * S, self._dh * S
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if not self._data:
            f = _font(int(H * 0.10))
            d.text((W / 2, H / 2), "Sem dados", fill=_hex_rgb(MUTED),
                   font=f, anchor="mm")
            return img.resize((self._dw, self._dh), Image.LANCZOS)
        pad = 22 * S
        baseY = H - 34 * S
        top = 16 * S
        n = len(self._data)
        gap = (W - 2 * pad) / n
        bw = min(gap * 0.55, 54 * S)
        maxv = max(v for _, v, _ in self._data) or 1
        border = _hex_rgb(BORDER)
        for i, (label, val, color) in enumerate(self._data):
            x = pad + gap * i + (gap - bw) / 2
            bh = (val / maxv) * (baseY - top) * prog
            y = baseY - bh
            rgb = _hex_rgb(color)
            if hover is not None and i != hover:
                rgb = _dim(rgb, 0.72)
            d.rectangle([x, y, x + bw, baseY], fill=rgb)
            vcol = _hex_rgb(TEXT) if i == hover else _hex_rgb(MUTED)
            d.text((x + bw / 2, y - 9 * S), str(val), fill=vcol,
                   font=_font(int(H * 0.075), bold=(i == hover)), anchor="mm")
            lcol = _hex_rgb(TEXT) if i == hover else _hex_rgb(MUTED)
            d.text((x + bw / 2, baseY + 12 * S), label, fill=lcol,
                   font=_font(int(H * 0.06)), anchor="mm")
        d.line([pad, baseY, W - pad, baseY], fill=border, width=max(1, S))
        return img.resize((self._dw, self._dh), Image.LANCZOS)

    def _render(self):
        """Redesenha o componente com os dados e dimensões atuais."""
        clara, escura = _render_nos_dois_temas(
            lambda: self.render_pil(hover=self._hover))
        self._ctk_img = ctk.CTkImage(light_image=clara, dark_image=escura,
                                     size=(self._dw, self._dh))
        self._img.configure(image=self._ctk_img, text="")

    def _hit(self, x, y):
        """Identifica o elemento gráfico localizado sob as coordenadas informadas."""
        S = self._scale
        W, H = self._dw * S, self._dh * S
        pad = 22 * S
        baseY = H - 34 * S
        n = len(self._data) or 1
        gap = (W - 2 * pad) / n
        bw = min(gap * 0.55, 54 * S)
        for i, (label, val, color) in enumerate(self._data):
            x0 = pad + gap * i + (gap - bw) / 2
            x1 = x0 + bw
            if x0 - 6 * S <= x * S <= x1 + 6 * S:
                return i
        return None

    def _on_move(self, ev):
        """Trata o movimento do ponteiro e exibe detalhes do elemento apontado."""
        idx = self._hit(ev.x, ev.y)
        if idx != self._hover:
            self._hover = idx
            self._render()
            self._show_tip(ev, idx)

    def _on_leave(self, ev):
        """Oculta os detalhes quando o ponteiro deixa a área do gráfico."""
        if self._hover is not None:
            self._hover = None
            self._render()
        self._hide_tip()

    def _show_tip(self, ev, idx):
        """Exibe a dica com os dados do elemento gráfico apontado."""
        self._hide_tip()
        if idx is None or idx >= len(self._data):
            return
        label, val, color = self._data[idx]
        tip = ctk.CTkToplevel(self)
        tip.wm_overrideredirect(True)
        tip.configure(fg_color=BG3)
        ctk.CTkLabel(tip, text=f"{label}:  {val}", font=font(12),
                     text_color=TEXT, padx=10, pady=5).pack()
        x = self.winfo_rootx() + ev.x + 14
        y = self.winfo_rooty() + ev.y + 14
        tip.geometry(f"+{x}+{y}")
        self._tip = tip

    def _hide_tip(self):
        """Oculta a dica de dados do gráfico."""
        if self._tip is not None:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


def _escurecer(hexcor):
    """Mantido p/ compatibilidade (não usado nos novos gráficos)."""
    try:
        r, g, b = _hex_rgb(hexcor)
        f = 0.72
        return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"
    except Exception:
        return hexcor
