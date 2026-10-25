"""Página de detalhes de um imóvel: dados, negociações ativas (contratos)
e mídia (fotos e vídeos)."""

import os
import customtkinter as ctk
import dao
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED, GREEN, GREEN_D,
                     AMBER, RED, TEAL_L, BLUE, PURPLE,
                     btn_primary, btn_secondary, btn_danger,
                     confirmar, fmt_brl, fmt_date, font)

# status do imóvel -> cor/estilo
STATUS_BG = {
    "disponivel":     ("#1f3d2e", "#9FE1CB"),
    "em negociacao":  ("#4a3613", "#FAC775"),
    "alugado":        ("#0C447C", "#E6F1FB"),
    "vendido":        ("#3a2459", "#cbb0f0"),
}
# situação do contrato -> cor
CONT_BG = {
    "ativo":     ("#1f3d2e", "#9FE1CB"),
    "em espera": ("#4a3613", "#FAC775"),
    "encerrado": ("#34373d", "#9aa0a8"),
}

VIDEO_EXTS = (".mp4", ".webm", ".avi", ".mov", ".mkv", ".m4v")


class ImovelDetalhe(ctk.CTkToplevel):
    """Janela (top-level) com os detalhes completos do imóvel."""

    def __init__(self, master, imovel_id, toast, **kw):
        """Inicializa ImovelDetalhe e prepara seu estado e interface."""
        super().__init__(master)
        self._imovel_id = imovel_id
        self.toast = toast
        self._imgs = []          # mantém referências vivas das imagens
        self.title("Detalhes do imóvel")
        self.geometry("920x680")
        self.minsize(760, 560)
        self.configure(fg_color=BG)

        # barra superior
        top = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)
        self._lbl_titulo = ctk.CTkLabel(top, text="", font=font(18, "bold"),
                                        text_color=TEXT)
        self._lbl_titulo.pack(side="left", padx=18)
        ctk.CTkButton(top, text="✏  Editar", width=110, height=32,
                      fg_color=BG3, hover_color=BORDER, border_width=1,
                      border_color=BORDER, text_color=TEXT, font=font(13),
                      command=self._editar).pack(side="right", padx=(0, 10))
        btn_secondary(top, "Fechar", self.destroy, width=100).pack(side="right", padx=10)

        # corpo com scroll
        body = ctk.CTkScrollableFrame(self, fg_color=BG,
                                      scrollbar_button_color=BORDER)
        body.pack(fill="both", expand=True, padx=0, pady=0)
        self._body = body

        self._carregar()

    # ── carregamento ──
    def _carregar(self):
        """Carrega no formulário os dados do registro que será editado."""
        row, props = dao.get_imovel(self._imovel_id)
        if not row:
            ctk.CTkLabel(self._body, text="Imóvel não encontrado.",
                         text_color=RED, font=font(14)).pack(pady=30)
            return

        codigo = row["codigo"]
        self._lbl_titulo.configure(text=f"{codigo}  —  {row['categoria']} · {row['subtipo']}")

        # ── MÍDIA: carrossel no topo (em vez de grade lá embaixo) ──
        try:
            todas = dao.get_fotos(row["id"])
        except Exception:
            todas = []
        fotos = [x for x in todas
                 if not x["caminho"].lower().endswith(VIDEO_EXTS)]
        videos = [x for x in todas
                  if x["caminho"].lower().endswith(VIDEO_EXTS)]
        if fotos or videos:
            self._montar_carrossel(fotos, videos)
        else:
            ctk.CTkLabel(self._body, text="Sem imagens/vídeos cadastrados.",
                         text_color=MUTED, font=font(12)).pack(padx=18, pady=(8, 0))

        # ── linha de cabeçalho: status + valores ──
        head = ctk.CTkFrame(self._body, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 8))

        st_bg, st_fg = STATUS_BG.get(row["status"], (BG3, MUTED))
        ctk.CTkLabel(head, text=row["status"].upper(), fg_color=st_bg,
                     text_color=st_fg, font=font(12, "bold"),
                     corner_radius=6, padx=10, pady=4).pack(side="left", padx=(0, 10))

        if row["finalidade"] == "venda":
            val = fmt_brl(row["preco_venda"])
        elif row["finalidade"] == "aluguel":
            val = fmt_brl(row["preco_aluguel"]) + " /mês"
        else:
            pv = fmt_brl(row["preco_venda"]) if row["preco_venda"] else "—"
            pa = (fmt_brl(row["preco_aluguel"]) + "/mês") if row["preco_aluguel"] else "—"
            val = f"{pv}  |  {pa}"
        ctk.CTkLabel(head, text=val, font=font(16, "bold"),
                     text_color=TEAL_L).pack(side="left")

        # ── grid de informações ──
        self._info_block("Informações", [
            ("Código", row["codigo"]),
            ("Categoria", row["categoria"]),
            ("Subtipo", row["subtipo"]),
            ("Finalidade", row["finalidade"]),
            ("Área", f"{row['area']} m²"),
            ("Endereço", f"{row['rua']}" + (f", {row['numero']}" if row['numero'] else "")),
            ("Bairro", row["bairro"]),
            ("Cidade", row["cidade"]),
        ])

        # ── proprietários ──
        prop_lines = []
        for p in props:
            prop_lines.append((p["nome"], f"{p['percentual']}% de posse"))
        if prop_lines:
            self._info_block("Proprietários", prop_lines)
        else:
            self._info_block("Proprietários", [("—", "nenhum proprietário")])

        # ── negociações (contratos) ──
        self._bloco_contratos(row["id"])

    # ── carrossel de mídia ──
    def _montar_carrossel(self, fotos, videos):
        """Monta o carrossel com as fotos disponíveis do imóvel."""
        Carrossel(self._body, self.toast, fotos, videos).pack(
            fill="x", padx=18, pady=(12, 4))

    # ── helper: bloco de info em 2 colunas ──
    def _info_block(self, titulo, pares):
        """Cria um bloco rotulado para exibir uma informação do imóvel."""
        f = ctk.CTkFrame(self._body, fg_color=BG2, corner_radius=10)
        f.pack(fill="x", padx=18, pady=8)
        ctk.CTkLabel(f, text=titulo, font=font(14, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 4))
        sep = ctk.CTkFrame(f, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=14, pady=(0, 6))

        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 12))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        for i, (k, v) in enumerate(pares):
            r, c = divmod(i, 2)
            rowf = ctk.CTkFrame(grid, fg_color="transparent")
            rowf.grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 16, ), pady=3)
            ctk.CTkLabel(rowf, text=f"{k}:", text_color=MUTED,
                         font=font(12), width=96, anchor="w").pack(side="left")
            ctk.CTkLabel(rowf, text=str(v), text_color=TEXT,
                         font=font(12, "bold"), anchor="w").pack(side="left")

    # ── helper: contratos / negociações ──
    def _bloco_contratos(self, imovel_id):
        """Monta o bloco com os contratos vinculados ao imóvel."""
        f = ctk.CTkFrame(self._body, fg_color=BG2, corner_radius=10)
        f.pack(fill="x", padx=18, pady=8)
        ativos = 0
        try:
            contratos = dao.contratos_por_imovel(imovel_id)
        except Exception:
            contratos = []
        for ct in contratos:
            if ct["situacao"] in ("ativo", "em espera"):
                ativos += 1
        titulo = f"Negociações / Contratos  ({len(contratos)} · {ativos} ativa(s))"
        ctk.CTkLabel(f, text=titulo, font=font(14, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 4))
        sep = ctk.CTkFrame(f, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=14, pady=(0, 6))

        if not contratos:
            ctk.CTkLabel(f, text="Nenhuma negociação registrada para este imóvel.",
                         text_color=MUTED, font=font(12)).pack(anchor="w",
                                                               padx=14, pady=(4, 14))
            return

        for ct in contratos:
            self._linha_contrato(f, ct)

    def _linha_contrato(self, parent, ct):
        """Cria uma linha visual com o resumo de um contrato."""
        row_f = ctk.CTkFrame(parent, fg_color=BG3, corner_radius=8)
        row_f.pack(fill="x", padx=14, pady=5)

        tipo_cor = ("#0C447C", "#E6F1FB") if ct["tipo"] == "venda" else ("#085041", "#E1F5EE")
        ctk.CTkLabel(row_f, text=ct["tipo"].upper(), fg_color=tipo_cor[0],
                     text_color=tipo_cor[1], font=font(9, "bold"),
                     corner_radius=4, width=50).pack(side="left", padx=(10, 8), pady=8)

        info = ctk.CTkFrame(row_f, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=6)
        ctk.CTkLabel(info, text=f"{ct['codigo']}  ·  {fmt_brl(ct['valor'])}",
                     font=font(12, "bold"), text_color=TEXT, anchor="w").pack(anchor="w")
        adqs = (ct["adquirentes"] or "").replace("|", ", ")
        ctk.CTkLabel(info, text=f"Adquirentes: {adqs or '—'}",
                     font=font(11), text_color=MUTED, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=f"Assinatura: {fmt_date(ct['data_assinatura'])}",
                     font=font(11), text_color=MUTED, anchor="w").pack(anchor="w")

        st_bg, st_fg = CONT_BG.get(ct["situacao"], (BG3, MUTED))
        ctk.CTkLabel(row_f, text=ct["situacao"], fg_color=st_bg, text_color=st_fg,
                     font=font(9, "bold"), corner_radius=4, padx=8, pady=3
                     ).pack(side="right", padx=12)

    # ── editar ──
    def _editar(self):
        """Abre para edição o registro atualmente selecionado."""
        try:
            from views.imoveis import FormImovel
        except Exception:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from views.imoveis import FormImovel
        # fecha e reabre a janela de detalhe após salvar
        janela = self

        def _apos_salvar():
            """Atualiza a tela de detalhes depois que uma edição é salva."""
            try:
                janela.destroy()
            except Exception:
                pass
            # reabre a mesma janela de detalhe
            ImovelDetalhe(self.master, self._imovel_id, self.toast)

        FormImovel(self, self.toast, id_=self._imovel_id, on_save=_apos_salvar)


class Carrossel(ctk.CTkFrame):
    """Carrossel de fotos/vídeos do imóvel, exibido no topo dos detalhes.
    - uma imagem por vez (16:9), navegação por setas ◀ ▶
    - legenda + contador (n / total)
    - clique na imagem abre o arquivo original
    - vídeos aparecem com botão ▶ Assistir
    """

    def __init__(self, master, toast, fotos, videos, **kw):
        """Inicializa Carrossel e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG2, corner_radius=10, **kw)
        self.toast = toast
        self._itens = list(fotos) + list(videos)  # fotos primeiro
        self._idx = 0
        self._imgs = []  # mantém referências vivas

        # palco da imagem (proporção ~16:9)
        self._palco = ctk.CTkFrame(self, fg_color=BG, height=300,
                                   corner_radius=8)
        self._palco.pack(fill="x", padx=12, pady=12)
        self._palco.pack_propagate(False)
        self._foto_lbl = ctk.CTkLabel(self._palco, text="", fg_color="transparent",
                                      cursor="hand2")
        self._foto_lbl.pack(expand=True, fill="both", padx=4, pady=4)
        self._foto_lbl.bind("<Button-1>", lambda e: self._abrir_atual())

        # barra inferior: seta esq, contador/legenda, seta dir, botão vídeo
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 10))

        btn_secondary(bar, "◀", self._ant, width=40).pack(side="left", padx=(0, 8))
        self._info = ctk.CTkLabel(bar, text="", text_color=MUTED,
                                  font=font(11), anchor="center")
        self._info.pack(side="left", fill="x", expand=True)
        btn_secondary(bar, "▶", self._prox, width=40).pack(side="left", padx=(8, 0))

        self._btn_video = btn_primary(bar, "▶ Assistir", self._abrir_atual,
                                      width=110)
        # só aparece quando o item atual for vídeo (controlado em _render)

        if self._itens:
            self._render()
        else:
            self._info.configure(text="Sem mídia.")

    def _render(self):
        """Redesenha o componente com os dados e dimensões atuais."""
        if not self._itens:
            return
        i = self._idx % len(self._itens)
        item = self._itens[i]
        caminho = item["caminho"]
        legenda = item["legenda"] or caminho.split("/")[-1]
        is_video = caminho.lower().endswith(VIDEO_EXTS)

        # imagem (ou placeholder de vídeo)
        if is_video:
            self._palco.configure(fg_color=BG)
            try:
                from PIL import Image
                from customtkinter import CTkImage
                ph = Image.new("RGB", (640, 360), _hex_rgb(BG))
                d = ImageDraw.Draw(ph)
                _centered_text(d, ph, "🎬 VÍDEO", 28)
                img = CTkImage(light_image=ph, dark_image=ph, size=(640, 360))
                self._imgs.append(img)
                self._foto_lbl.configure(image=img, text="")
            except Exception:
                self._foto_lbl.configure(image=None, text="🎬 VÍDEO")
        else:
            try:
                from PIL import Image
                from customtkinter import CTkImage
                im = Image.open(caminho).convert("RGB")
                im = _fit(im, 640, 360)
                img = CTkImage(light_image=im, dark_image=im, size=im.size)
                self._imgs.append(img)
                self._foto_lbl.configure(image=img, text="")
            except Exception:
                self._foto_lbl.configure(image=None, text="[imagem não encontrada]")

        self._info.configure(text=f"{i+1} / {len(self._itens)}   ·   {legenda}")
        if is_video:
            self._btn_video.pack(side="right", padx=(12, 0))
        else:
            self._btn_video.pack_forget()

    def _prox(self):
        """Avança para a próxima foto do carrossel."""
        if len(self._itens) > 1:
            self._idx = (self._idx + 1) % len(self._itens)
            self._render()

    def _ant(self):
        """Retorna para a foto anterior do carrossel."""
        if len(self._itens) > 1:
            self._idx = (self._idx - 1) % len(self._itens)
            self._render()

    def _abrir_atual(self):
        """Abre em tamanho original a foto atualmente exibida."""
        if not self._itens:
            return
        item = self._itens[self._idx % len(self._itens)]
        try:
            os.startfile(item["caminho"])
        except Exception as e:
            self.toast.show(f"Não foi possível abrir: {e}", error=True)


# ── helpers de imagem p/ o carrossel ──
from PIL import Image, ImageDraw

def _hex_rgb(hexcor):
    """Converte uma cor hexadecimal em uma tupla de componentes RGB."""
    h = (hexcor or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (150, 150, 150)

def _fit(im, w, h):
    """Redimensiona mantendo proporção (cabe dentro de w x h)."""
    im = im.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    return im

def _centered_text(draw, img, text, size):
    """Desenha um texto centralizado na área informada da imagem."""
    try:
        from widgets import _font
        fnt = _font(size, bold=True)
    except Exception:
        fnt = ImageDraw.load_default()
    W, H = img.size
    draw.text((W / 2, H / 2), text, fill=_hex_rgb(MUTED), font=fnt, anchor="mm")
