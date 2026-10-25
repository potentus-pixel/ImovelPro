import customtkinter as ctk
import csv
from tkinter import filedialog
import dao
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED, GREEN, RED,
                     Tabela, FiltroBar, ListaTag, Campo,
                     btn_primary, btn_secondary, btn_danger,
                     confirmar, fmt_brl, font)

SUBTIPOS = {
    "Urbano": ["Apartamento", "Casa", "Terreno"],
    "Rural":  ["Chácara", "Sítio", "Fazenda"],
}


class Imoveis(ctk.CTkFrame):
    def __init__(self, master, toast, on_open=None, **kw):
        """Inicializa Imoveis e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG, **kw)
        self.toast = toast
        self._on_open = on_open
        self._rows_cache = []
        self._build()

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(h, text="Imóveis", font=font(24, "bold"),
                     text_color=TEXT).pack(side="left")

        self._bar = FiltroBar(
            self, on_search=self._pesquisar,
            placeholder="Buscar por código, endereço...",
            filtros=[
                ("Categoria", ["Urbano", "Rural"]),
                ("Finalidade", ["venda", "aluguel"]),
                ("Status", ["Disponível", "Em negociação", "Alugado", "Vendido"]),
                ("Ordenar", ["Mais recentes", "Menor preço", "Maior preço", "Maior área", "Código"]),
            ],
            btn_label="+ Novo imóvel", btn_cmd=self._novo,
        )
        self._bar.pack(fill="x")

        faixa = ctk.CTkFrame(self, fg_color="transparent")
        faixa.pack(fill="x", padx=18, pady=(8, 0))
        ctk.CTkLabel(faixa, text="Cidade", font=font(11), text_color=MUTED).pack(side="left", padx=(0, 5))
        self._cidade = ctk.CTkEntry(faixa, placeholder_text="Todas", width=150)
        self._cidade.pack(side="left", padx=(0, 12))
        self._cidade.bind("<KeyRelease>", lambda _e: self._pesquisar())
        ctk.CTkLabel(faixa, text="Preço de", font=font(11), text_color=MUTED).pack(side="left", padx=(0, 5))
        self._preco_min = ctk.CTkEntry(faixa, placeholder_text="Sem mínimo", width=110)
        self._preco_min.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(faixa, text="até", font=font(11), text_color=MUTED).pack(side="left", padx=4)
        self._preco_max = ctk.CTkEntry(faixa, placeholder_text="Sem máximo", width=110)
        self._preco_max.pack(side="left", padx=(0, 12))
        for campo in (self._preco_min, self._preco_max):
            campo.bind("<KeyRelease>", lambda _e: self._pesquisar())
        btn_secondary(faixa, "Limpar filtros", self._limpar_filtros, width=120).pack(side="left")
        self._resultado = ctk.CTkLabel(faixa, text="", text_color=MUTED, font=font(11))
        self._resultado.pack(side="right", padx=4)

        cols = ["Código", "Tipo", "Endereço", "Área (m²)", "Finalidade",
                "Valor", "Status", "Proprietário(s)"]
        largs = [90, 150, 240, 90, 100, 150, 110, 200]
        self._tabela = Tabela(self, cols, largs,
                              on_select=self._on_select,
                              on_open=self._abrir_detalhe)
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(8, 4))

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(0, 12))
        btn_secondary(brow, "👁  Ver detalhes", self._abrir_detalhe_sel,
                      width=130).pack(side="left", padx=(0, 6))
        btn_secondary(brow, "✏  Editar", self._editar, width=110).pack(side="left", padx=(0, 6))
        btn_secondary(brow, "🗑  Excluir", self._excluir, width=110).pack(side="left")
        btn_secondary(brow, "Exportar CSV", self._exportar, width=120).pack(side="left", padx=6)
        ctk.CTkLabel(brow, text="Dica: clique duas vezes num imóvel para abrir os detalhes.",
                     text_color=MUTED, font=font(11)).pack(side="right")

        self._pesquisar()

    def _pesquisar(self):
        """Aplica os filtros preenchidos e atualiza a listagem da tela."""
        q   = self._bar.get_query()
        cat = self._bar.get_filtro("Categoria")
        fin = self._bar.get_filtro("Finalidade")
        status = {
            "Disponível": "disponivel", "Em negociação": "em negociacao",
            "Alugado": "alugado", "Vendido": "vendido",
        }.get(self._bar.get_filtro("Status"), "")
        order = {
            "Mais recentes": "recentes", "Menor preço": "menor_preco",
            "Maior preço": "maior_preco", "Maior área": "maior_area",
            "Código": "codigo",
        }.get(self._bar.get_filtro("Ordenar"), "codigo")
        def parse_preco(campo):
            valor = campo.get().strip().replace("R$", "").replace(" ", "")
            if not valor:
                return None, True
            try:
                numero = (float(valor.replace(".", "").replace(",", "."))
                          if "," in valor else float(valor))
                return (numero, True) if numero >= 0 else (None, False)
            except ValueError:
                return None, False
        preco_min, min_ok = parse_preco(self._preco_min)
        preco_max, max_ok = parse_preco(self._preco_max)
        if not min_ok or not max_ok:
            self._resultado.configure(text="Informe preços válidos", text_color=RED)
            self._rows_cache = []
            self._tabela.preencher([], id_col=0)
            return
        if preco_min is not None and preco_max is not None and preco_min > preco_max:
            self._resultado.configure(text="O mínimo supera o máximo", text_color=RED)
            self._rows_cache = []
            self._tabela.preencher([], id_col=0)
            return
        rows = dao.listar_imoveis(
            filtro=q, categoria=cat, finalidade=fin, status=status,
            cidade=self._cidade.get().strip(), preco_min=preco_min,
            preco_max=preco_max, ordenar=order)
        self._rows_cache = [dict(row) for row in rows]
        self._resultado.configure(text=f"{len(rows)} imóvel(is)", text_color=MUTED)
        dados = []
        for r in rows:
            if r["finalidade"] == "venda":
                val = fmt_brl(r["preco_venda"])
            elif r["finalidade"] == "aluguel":
                val = fmt_brl(r["preco_aluguel"]) + "/mês"
            else:
                val = fmt_brl(r["preco_venda"]) + " | " + fmt_brl(r["preco_aluguel"]) + "/mês"
            props = (r["proprietarios"] or "—").replace("|", " /")
            endereco = r["rua"]
            if r["numero"]:
                endereco += f", {r['numero']}"
            dados.append((
                r["id"], r["codigo"],
                f"{r['categoria']} — {r['subtipo']}",
                f"{endereco}, {r['bairro']}",
                f"{r['area']}" if r["area"] else "—",
                r["finalidade"],
                val,
                r["status"], props,
            ))
        self._tabela.preencher(dados, id_col=0)

    def _exportar(self):
        """Exporta exatamente os imóveis que atendem aos filtros atuais."""
        if not self._rows_cache:
            self.toast.show("Não há imóveis para exportar.", error=True)
            return
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Exportar imóveis", defaultextension=".csv",
            initialfile="imoveis-filtrados.csv",
            filetypes=[("Planilha CSV", "*.csv")])
        if not caminho:
            return
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.writer(arquivo, delimiter=";")
                writer.writerow(["Código", "Categoria", "Tipo", "Endereço", "Número",
                                 "Bairro", "Cidade", "Área (m²)", "Finalidade",
                                 "Preço de venda", "Preço de aluguel", "Status", "Proprietários"])
                for row in self._rows_cache:
                    writer.writerow([row["codigo"], row["categoria"], row["subtipo"],
                                     row["rua"], row["numero"], row["bairro"],
                                     row["cidade"], row["area"], row["finalidade"],
                                     row["preco_venda"], row["preco_aluguel"],
                                     row["status"], row["proprietarios"]])
            self.toast.show("Lista de imóveis exportada.")
        except OSError as exc:
            self.toast.show(f"Não foi possível exportar: {exc}", error=True)

    def _limpar_filtros(self):
        self._bar._entry.delete(0, "end")
        for var in self._bar._vars.values():
            var.set("")
        self._cidade.delete(0, "end")
        self._preco_min.delete(0, "end")
        self._preco_max.delete(0, "end")
        self._pesquisar()

    def _on_select(self, id_):
        """Atualiza as ações e informações conforme o item selecionado."""
        pass

    def _novo(self):
        """Abre o formulário para cadastrar um novo registro."""
        FormImovel(self, self.toast, on_save=self._pesquisar)

    def _editar(self):
        """Abre para edição o registro atualmente selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um imóvel.", error=True); return
        FormImovel(self, self.toast, id_=id_, on_save=self._pesquisar)

    def _excluir(self):
        """Executa a rotina interna “excluir” deste componente."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um imóvel.", error=True); return
        row = self._tabela.selected_row()
        cod = row[1] if row else "?"
        if confirmar(self, "Excluir imóvel", f"Excluir imóvel '{cod}'?"):
            ok, err = dao.excluir_imovel(id_)
            if ok:
                self.toast.show("Imóvel excluído.")
                self._pesquisar()
            else:
                self.toast.show(f"Erro: {err}", error=True)

    def _abrir_detalhe(self, id_):
        """Abre a visualização detalhada do imóvel informado."""
        if id_ is None:
            return
        if self._on_open:
            self._on_open(id_)
        else:
            ImovelDetalhe(self, id_, self.toast)

    def _abrir_detalhe_sel(self):
        """Abre os detalhes do imóvel atualmente selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um imóvel.", error=True); return
        self._abrir_detalhe(id_)

    def atualizar(self):
        """Recarrega os dados e redesenha as informações exibidas na tela."""
        self._pesquisar()


class FormImovel(ctk.CTkToplevel):
    def __init__(self, master, toast, id_=None, on_save=None):
        """Inicializa FormImovel e prepara seu estado e interface."""
        super().__init__(master)
        self.toast  = toast
        self.id_    = id_
        self.on_save = on_save
        self._foto_imgs = []  # mantém referencias às imagens vivas
        self.title("Editar imóvel" if id_ else "Novo imóvel")
        self.geometry("600x700")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG2)
        self._build()
        if id_:
            self._carregar()
        else:
            self._f_codigo.set(dao.proximo_codigo_imovel())

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG2,
                                        scrollbar_button_color=BORDER)
        scroll.pack(fill="both", expand=True)
        self._sc = scroll

        ctk.CTkLabel(scroll, text="Dados do imóvel",
                     font=("Segoe UI", 16, "bold"), text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(16, 10))

        # Grid principal
        g = ctk.CTkFrame(scroll, fg_color="transparent")
        g.pack(fill="x", padx=20)
        g.columnconfigure((0, 1, 2), weight=1)

        self._f_codigo   = Campo(g, "Código", width=160)
        self._f_codigo.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)

        self._f_area     = Campo(g, "Área (m²)", width=140)
        self._f_area.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=4)

        self._f_cat = Campo(g, "Categoria", widget_class=ctk.CTkOptionMenu,
                            values=["Urbano", "Rural"], width=140)
        self._f_cat.grid(row=0, column=2, sticky="ew", pady=4)
        self._f_cat.w.configure(command=self._on_cat_change)

        self._f_subtipo = Campo(g, "Subtipo", widget_class=ctk.CTkOptionMenu,
                                values=SUBTIPOS["Urbano"], width=160)
        self._f_subtipo.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        self._f_fin = Campo(g, "Finalidade", widget_class=ctk.CTkOptionMenu,
                            values=["venda", "aluguel", "ambos"], width=160)
        self._f_fin.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=4)
        self._f_fin.w.configure(command=self._on_fin_change)

        # Endereço
        ctk.CTkLabel(scroll, text="Endereço",
                     font=("Segoe UI", 13, "bold"), text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(14, 4))
        ge = ctk.CTkFrame(scroll, fg_color="transparent")
        ge.pack(fill="x", padx=20)
        ge.columnconfigure((0, 1), weight=1)

        self._f_rua = Campo(ge, "Rua / Logradouro (com nº)", width=300)
        self._f_rua.grid(row=0, column=0, columnspan=2, sticky="ew", pady=4)

        self._f_bairro = Campo(ge, "Bairro", width=190)
        self._f_bairro.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        self._f_cidade = Campo(ge, "Cidade", width=190)
        self._f_cidade.grid(row=1, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(scroll, text="Valores",
                     font=("Segoe UI", 13, "bold"), text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(14, 4))

        gv = ctk.CTkFrame(scroll, fg_color="transparent")
        gv.pack(fill="x", padx=20)
        gv.columnconfigure((0, 1), weight=1)

        self._wrap_venda = ctk.CTkFrame(gv, fg_color="transparent")
        self._wrap_venda.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
        self._f_venda = Campo(self._wrap_venda, "Valor de venda (R$)", width=190)
        self._f_venda.pack(fill="x")

        self._wrap_aluguel = ctk.CTkFrame(gv, fg_color="transparent")
        self._wrap_aluguel.grid(row=0, column=1, sticky="ew", pady=4)
        self._f_aluguel = Campo(self._wrap_aluguel, "Aluguel mensal (R$)", width=190)
        self._f_aluguel.pack(fill="x")

        # Proprietários
        ctk.CTkLabel(scroll, text="Proprietários",
                     font=("Segoe UI", 13, "bold"), text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(14, 4))

        self._lista_props = ListaTag(scroll, altura=120)
        self._lista_props.pack(fill="x", padx=20)

        ap = ctk.CTkFrame(scroll, fg_color="transparent")
        ap.pack(fill="x", padx=20, pady=(6, 0))

        clientes = dao.listar_clientes()
        self._cli_map = {f"{r['nome']} ({r['codigo']})": r["id"] for r in clientes}
        nomes = list(self._cli_map.keys()) or ["(nenhum)"]

        self._sel_prop = ctk.CTkOptionMenu(ap, values=nomes, width=280,
                                           fg_color=BG3, button_color=GREEN,
                                           dropdown_fg_color=BG3, text_color=TEXT)
        self._sel_prop.pack(side="left", padx=(0, 8))

        self._e_pct = ctk.CTkEntry(ap, placeholder_text="% posse (100)",
                                   fg_color=BG3, border_color=BORDER,
                                   text_color=TEXT, placeholder_text_color=MUTED,
                                   width=110)
        self._e_pct.pack(side="left", padx=(0, 8))

        btn_secondary(ap, "+ Adicionar", self._add_prop, width=110).pack(side="left")

        # Fotos
        ctk.CTkLabel(scroll, text="Fotos",
                     font=("Segoe UI", 12, "bold"), text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(14, 4))

        self._fotos_frame = ctk.CTkScrollableFrame(
            scroll, height=150, fg_color=BG3,
            scrollbar_button_color=BORDER)
        self._fotos_frame.pack(fill="x", padx=20)

        ftools = ctk.CTkFrame(scroll, fg_color="transparent")
        ftools.pack(fill="x", padx=20, pady=(6, 0))
        btn_secondary(ftools, "+ Adicionar fotos",
                     self._add_fotos, width=170).pack(side="left")
        self._foto_status = ctk.CTkLabel(
            ftools, text="", text_color=MUTED, font=("Segoe UI", 10))
        self._foto_status.pack(side="left", padx=10)

        # Rodapé
        sep = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        sep.pack(fill="x")
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=12)
        btn_secondary(footer, "Cancelar", self.destroy, width=110).pack(side="right", padx=(6, 0))
        btn_primary(footer, "Salvar imóvel", self._salvar, width=140).pack(side="right")

        self._on_fin_change(self._f_fin.get())

    def _on_cat_change(self, val):
        """Ajusta os campos disponíveis quando a categoria do imóvel muda."""
        self._f_subtipo.w.configure(values=SUBTIPOS.get(val, []))
        self._f_subtipo.w.set(SUBTIPOS.get(val, [""])[0])

    def _on_fin_change(self, val):
        """Ajusta os campos de preço quando a finalidade do imóvel muda."""
        if val == "venda":
            self._wrap_venda.grid()
            self._wrap_aluguel.grid_remove()
        elif val == "aluguel":
            self._wrap_venda.grid_remove()
            self._wrap_aluguel.grid()
        else:
            self._wrap_venda.grid()
            self._wrap_aluguel.grid()

    def _add_prop(self):
        """Adiciona um proprietário e seu percentual ao formulário do imóvel."""
        nome_key = self._sel_prop.get()
        cli_id = self._cli_map.get(nome_key)
        if not cli_id:
            self.toast.show("Selecione um cliente válido.", error=True); return
        pct = float(self._e_pct.get().strip() or "100")
        items = self._lista_props.get_items()
        if any(i.get("cliente_id") == cli_id for i in items):
            self.toast.show("Proprietário já adicionado.", error=True); return
        nome = nome_key.split(" (")[0]
        self._lista_props.adicionar({
            "label": nome,
            "sub":   f"  {pct}% de posse",
            "cliente_id": cli_id,
            "percentual": pct,
        })
        self._e_pct.delete(0, "end")

    # ── FOTOS ──────────────────────────────────────────────
    def _make_thumb(self, caminho, size=(110, 110)):
        """Cria a miniatura usada para representar uma foto no formulário."""
        from PIL import Image
        from customtkinter import CTkImage
        try:
            im = Image.open(caminho).convert("RGB")
            im.thumbnail(size, Image.LANCZOS)
            return CTkImage(light_image=im, dark_image=im, size=size)
        except Exception:
            return None

    def _render_fotos(self, fotos):
        """fotos: lista de dicts {id, caminho, legenda}."""
        for w in self._fotos_frame.winfo_children():
            w.destroy()
        if not fotos:
            ctk.CTkLabel(self._fotos_frame,
                         text="Nenhuma foto adicionada.",
                         text_color=MUTED, font=("Segoe UI", 10)
                         ).pack(anchor="w", padx=6, pady=8)
            return
        for f in fotos:
            card = ctk.CTkFrame(self._fotos_frame, fg_color=BG2,
                                 corner_radius=8)
            card.pack(side="left", padx=6, pady=6, anchor="nw")
            img = self._make_thumb(f["caminho"])
            if img:
                self._foto_imgs.append(img)
                lbl = ctk.CTkLabel(card, image=img, text="")
                lbl.image = img
                lbl.pack(padx=6, pady=6)
            else:
                ctk.CTkLabel(card, text="[imagem\nnão\nencontrada]",
                             text_color=RED, font=("Segoe UI", 9)
                             ).pack(padx=6, pady=6)
            ctk.CTkLabel(card, text=f.get("legenda") or f["caminho"].split("/")[-1],
                         text_color=TEXT, font=("Segoe UI", 9),
                         width=120, wraplength=120).pack(pady=(0, 4))
            btn_danger(card, "✕",
                       lambda fid=f["id"]: self._remover_foto(fid),
                       width=60).pack(pady=(0, 6))

    def _add_fotos(self):
        # se o imóvel ainda não foi salvo, salva primeiro (sem fechar o form)
        """Permite selecionar e acrescentar fotos ao imóvel."""
        if not self.id_:
            self.id_ = self._salvar_silencioso()
            if not self.id_:
                return  # validação falhou (toast já exibido)
            # atualiza o campo código caso tenha sido gerado
            self._f_codigo.set(dao.get_imovel(self.id_)[0]["codigo"])
        from tkinter import filedialog
        # O 'grab_set()' do form trava o filedialog no Windows — solta o grab,
        # abre o diálogo e restaura o grab em seguida.
        try:
            self.grab_release()
        except Exception:
            pass
        arquivos = filedialog.askopenfilenames(
            title="Selecione as fotos do imóvel",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif")])
        try:
            self.grab_set()
        except Exception:
            pass
        if not arquivos:
            return
        add = 0
        for path in arquivos:
            ok, err = dao.adicionar_foto(self.id_, path)
            if ok:
                add += 1
            else:
                self.toast.show(f"Erro ao adicionar foto: {err}",
                               error=True)
        if add:
            self.toast.show(f"{add} foto(s) adicionada(s).")
            self._foto_status.configure(text=f"{len(dao.get_fotos(self.id_))} foto(s)")
            self._render_fotos([
                {"id": r["id"], "caminho": r["caminho"], "legenda": r["legenda"]}
                for r in dao.get_fotos(self.id_)])

    def _remover_foto(self, fid):
        """Remove do formulário a foto selecionada."""
        ok, err = dao.remover_foto(fid)
        if ok:
            self.toast.show("Foto removida.")
            if self.id_:
                fotos = dao.get_fotos(self.id_)
                self._foto_status.configure(text=f"{len(fotos)} foto(s)")
                self._render_fotos([
                    {"id": r["id"], "caminho": r["caminho"], "legenda": r["legenda"]}
                    for r in fotos])
        else:
            self.toast.show(f"Erro: {err}", error=True)

    def _carregar(self):
        """Carrega no formulário os dados do registro que será editado."""
        row, props = dao.get_imovel(self.id_)
        if not row: return
        self._f_codigo.set(row["codigo"])
        self._f_area.set(row["area"])
        self._f_cat.set(row["categoria"])
        self._on_cat_change(row["categoria"])
        self._f_subtipo.set(row["subtipo"])
        self._f_fin.set(row["finalidade"])
        self._on_fin_change(row["finalidade"])
        self._f_rua.set(row["rua"])
        self._f_bairro.set(row["bairro"])
        self._f_cidade.set(row["cidade"])
        self._f_venda.set(row["preco_venda"] or "")
        self._f_aluguel.set(row["preco_aluguel"] or "")
        items = []
        for p in props:
            items.append({
                "label": p["nome"],
                "sub":   f"  {p['percentual']}% de posse",
                "cliente_id": p["cliente_id"],
                "percentual": p["percentual"],
            })
        self._lista_props.set_items(items)
        # fotos
        if self.id_:
            fotos = dao.get_fotos(self.id_)
            self._foto_status.configure(text=f"{len(fotos)} foto(s)")
            self._render_fotos([
                {"id": r["id"], "caminho": r["caminho"], "legenda": r["legenda"]}
                for r in fotos])

    def _salvar_silencioso(self):
        """Coleta os dados e salva (sem toast/destroy).
        Retorna o id do imóvel ou None se a validação falhar."""
        fin = self._f_fin.get()
        data = {
            "codigo":    self._f_codigo.get().strip(),
            "categoria": self._f_cat.get(),
            "subtipo":   self._f_subtipo.get(),
            "area":      float(self._f_area.get() or 0),
            "rua":       self._f_rua.get().strip(),
            "numero":    None,   # número agora integra o endereço (campo Rua)
            "bairro":    self._f_bairro.get().strip(),
            "cidade":    self._f_cidade.get().strip(),
            "finalidade":fin,
            "preco_venda":   float(self._f_venda.get() or 0) if fin != "aluguel" else None,
            "preco_aluguel": float(self._f_aluguel.get() or 0) if fin != "venda" else None,
        }
        props = self._lista_props.get_items()
        if not data["codigo"] or not data["rua"]:
            self.toast.show("Código e endereço são obrigatórios.", error=True); return None
        if not props:
            self.toast.show("Adicione ao menos um proprietário.", error=True); return None
        ok, err = dao.salvar_imovel(data, props, id_=self.id_)
        if not ok:
            msg = "Código já cadastrado." if "UNIQUE" in err else f"Erro: {err}"
            self.toast.show(msg, error=True); return None
        if self.id_ is None:
            self.id_ = dao.get_imovel_id_by_codigo(data["codigo"])
        dao.recalcular_status_imovel(self.id_)
        if self.on_save:
            self.on_save()
        return self.id_

    def _salvar(self):
        """Valida os campos, persiste o formulário e informa o resultado ao usuário."""
        if self._salvar_silencioso() is not None:
            self.toast.show("Imóvel salvo com sucesso.")
            self.destroy()
