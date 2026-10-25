import customtkinter as ctk
import os
import dao
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED, GREEN,
                     Tabela, FiltroBar, ListaTag, Campo,
                     btn_primary, btn_secondary, btn_danger,
                     confirmar, fmt_brl, fmt_date, font)


class Contratos(ctk.CTkFrame):
    def __init__(self, master, toast, **kw):
        """Inicializa Contratos e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG, **kw)
        self.toast = toast
        self._build()

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(h, text="Contratos", font=("Segoe UI", 22, "bold"),
                     text_color=TEXT).pack(side="left")

        self._bar = FiltroBar(
            self, on_search=self._pesquisar,
            placeholder="Buscar por código, imóvel, cliente...",
            filtros=[
                ("Tipo",     ["venda", "aluguel"]),
                ("Situação", ["em espera", "ativo", "encerrado"]),
            ],
            btn_label="+ Novo contrato", btn_cmd=self._novo,
        )
        self._bar.pack(fill="x")

        cols = ["Código", "Adquirente(s)", "Cedente(s)", "Imóvel",
                "Tipo", "Valor", "Assinatura", "Situação", "Corretor(es)"]
        largs = [90, 160, 230, 170, 80, 130, 100, 100, 230]
        self._tabela = Tabela(self, cols, largs)
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(8, 4))

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(0, 12))
        btn_secondary(brow, "✏  Editar", self._editar, width=110).pack(side="left", padx=(0, 6))
        btn_secondary(brow, "🧾  Gerar boletos", self._gerar_boletos, width=150).pack(side="left", padx=(0, 6))
        btn_danger(brow, "🗑  Excluir", self._excluir, width=110).pack(side="left")

        self._pesquisar()

    def _pesquisar(self):
        """Aplica os filtros preenchidos e atualiza a listagem da tela."""
        q   = self._bar.get_query()
        tp  = self._bar.get_filtro("Tipo")
        st  = self._bar.get_filtro("Situação")
        rows = dao.listar_contratos(filtro=q, tipo=tp, situacao=st)
        dados = []
        for r in rows:
            dados.append((
                r["id"],
                r["codigo"],
                (r["adquirentes"] or "—")[:30],
                (r["cedentes"]    or "—")[:30],
                f"{r['im_subtipo']} · {r['im_bairro']}",
                r["tipo"],
                fmt_brl(r["valor"]),
                fmt_date(r["data_assinatura"]),
                r["situacao"],
                (r["corretores"] or "—")[:30],
            ))
        self._tabela.preencher(dados, id_col=0)

    def _novo(self):
        """Abre o formulário para cadastrar um novo registro."""
        FormContrato(self, self.toast, on_save=self._pesquisar)

    def _editar(self):
        """Abre para edição o registro atualmente selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um contrato.", error=True); return
        FormContrato(self, self.toast, id_=id_, on_save=self._pesquisar)

    def _gerar_boletos(self):
        """Gera os boletos correspondentes às parcelas do contrato selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um contrato.", error=True); return
        criados, err = dao.gerar_boletos_contrato(id_)
        if err:
            self.toast.show(f"Erro: {err}", error=True); return
        row = self._tabela.selected_row()
        cod = row[1] if row else "?"
        if criados:
            self.toast.show(f"{criados} boleto(s) gerado(s) p/ '{cod}'.")
        else:
            self.toast.show("Nenhum boleto novo (já existem).")
        self._pesquisar()

    def _excluir(self):
        """Executa a rotina interna “excluir” deste componente."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um contrato.", error=True); return
        row = self._tabela.selected_row()
        cod = row[1] if row else "?"
        if confirmar(self, "Excluir contrato", f"Excluir contrato '{cod}'?"):
            ok, err = dao.excluir_contrato(id_)
            if ok:
                self.toast.show("Contrato excluído.")
                self._pesquisar()
            else:
                self.toast.show(f"Erro: {err}", error=True)

    def atualizar(self):
        """Recarrega os dados e redesenha as informações exibidas na tela."""
        self._pesquisar()


class FormContrato(ctk.CTkToplevel):
    def __init__(self, master, toast, id_=None, on_save=None):
        """Inicializa FormContrato e prepara seu estado e interface."""
        super().__init__(master)
        self.toast   = toast
        self.id_     = id_
        self.on_save = on_save
        self.title("Editar contrato" if id_ else "Novo contrato")
        self.geometry("700x840")
        self.minsize(680, 560)
        self.resizable(True, True)
        self.grab_set()
        self.configure(fg_color=BG2)
        # Ícone da janela (mesmo do app)
        _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "app_icon.ico")
        try:
            self.iconbitmap(_ico)
        except Exception:
            pass
        self._build()
        if id_:
            self._carregar()
        else:
            self._f_codigo.set(dao.proximo_codigo_contrato())

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        scroll = ctk.CTkScrollableFrame(self, fg_color=BG2,
                                        scrollbar_button_color=BORDER,
                                        scrollbar_button_hover_color=MUTED,
                                        scrollbar_fg_color=BG3)
        scroll._scrollbar.configure(width=14)
        scroll.pack(fill="both", expand=True)

        def sec(txt):
            """Cria uma seção visual do formulário de contrato."""
            ctk.CTkLabel(scroll, text=txt, font=("Segoe UI", 13, "bold"),
                         text_color=TEXT).pack(anchor="w", padx=20, pady=(14, 4))

        # Dados gerais
        sec("Dados gerais")
        g = ctk.CTkFrame(scroll, fg_color="transparent")
        g.pack(fill="x", padx=20)
        g.columnconfigure((0, 1, 2), weight=1)

        self._f_codigo   = Campo(g, "Código", width=160)
        self._f_codigo.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)

        self._f_tipo = Campo(g, "Tipo", widget_class=ctk.CTkOptionMenu,
                             values=["venda", "aluguel"], width=140)
        self._f_tipo.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=4)
        self._f_tipo.w.configure(command=self._on_tipo_change)

        self._f_situacao = Campo(g, "Situação", widget_class=ctk.CTkOptionMenu,
                                 values=["em espera", "ativo", "encerrado"], width=140)
        self._f_situacao.grid(row=0, column=2, sticky="ew", pady=4)

        self._f_valor    = Campo(g, "Valor do contrato (R$)", width=190)
        self._f_valor.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        self._f_comissao = Campo(g, "Comissão total (R$)", width=190)
        self._f_comissao.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=4)

        self._f_data = Campo(g, "Data assinatura (AAAA-MM-DD)", width=190)
        self._f_data.grid(row=1, column=2, sticky="ew", pady=4)

        # Venda
        self._frame_venda = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_venda.pack(fill="x", padx=20)
        ctk.CTkLabel(self._frame_venda, text="Dados da venda",
                     font=("Segoe UI", 12, "bold"), text_color=TEXT
                     ).pack(anchor="w", pady=(10, 4))
        gv = ctk.CTkFrame(self._frame_venda, fg_color="transparent")
        gv.pack(fill="x")
        gv.columnconfigure((0, 1), weight=1)
        self._f_entrada   = Campo(gv, "Valor de entrada (R$)", width=190)
        self._f_entrada.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
        self._f_parcelas  = Campo(gv, "Número de parcelas", width=190)
        self._f_parcelas.grid(row=0, column=1, sticky="ew", pady=4)

        # Aluguel
        self._frame_aluguel = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_aluguel.pack(fill="x", padx=20)
        ctk.CTkLabel(self._frame_aluguel, text="Dados do aluguel",
                     font=("Segoe UI", 12, "bold"), text_color=TEXT
                     ).pack(anchor="w", pady=(10, 4))
        ga = ctk.CTkFrame(self._frame_aluguel, fg_color="transparent")
        ga.pack(fill="x")
        ga.columnconfigure((0, 1), weight=1)
        self._f_duracao  = Campo(ga, "Duração (meses)", width=190)
        self._f_duracao.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
        self._f_vencdia  = Campo(ga, "Dia de vencimento (1-31)", width=190)
        self._f_vencdia.grid(row=0, column=1, sticky="ew", pady=4)

        # Cedentes (vêm antes do imóvel para filtrar a lista)
        sec("Cedentes  (proprietários do imóvel)")
        self._lista_ceds = ListaTag(scroll, altura=100,
                                    on_change=self._atualizar_imoveis)
        self._lista_ceds.pack(fill="x", padx=20)
        self._add_parte_row(scroll, "cedente")

        # Imóvel (filtrado pelos cedentes selecionados)
        sec("Imóvel")
        self._sel_imovel = ctk.CTkOptionMenu(
            scroll, values=["(selecione um cedente)"], width=500,
            fg_color=BG3, button_color=GREEN,
            dropdown_fg_color=BG3, text_color=TEXT)
        self._sel_imovel.pack(anchor="w", padx=20, pady=(0, 4))
        self._im_map = {}

        # Adquirentes
        sec("Adquirentes  (compradores / locatários)")
        self._lista_adqs = ListaTag(scroll, altura=100)
        self._lista_adqs.pack(fill="x", padx=20)
        self._add_parte_row(scroll, "adquirente")

        # Corretores
        sec("Corretores")
        self._lista_corrs = ListaTag(scroll, altura=100)
        self._lista_corrs.pack(fill="x", padx=20)

        ap2 = ctk.CTkFrame(scroll, fg_color="transparent")
        ap2.pack(fill="x", padx=20, pady=(6, 0))
        corretores = dao.todos_corretores()
        self._corr_map = {f"{r['nome']} ({r['creci']})": r["id"] for r in corretores}
        nomes_cr = list(self._corr_map.keys()) or ["(nenhum)"]
        self._sel_corr = ctk.CTkOptionMenu(ap2, values=nomes_cr, width=280,
                                           fg_color=BG3, button_color=GREEN,
                                           dropdown_fg_color=BG3, text_color=TEXT)
        self._sel_corr.pack(side="left", padx=(0, 8))
        self._e_pct_corr = ctk.CTkEntry(ap2, placeholder_text="% comissão (100)",
                                        fg_color=BG3, border_color=BORDER,
                                        text_color=TEXT, placeholder_text_color=MUTED,
                                        width=130)
        self._e_pct_corr.pack(side="left", padx=(0, 8))
        btn_secondary(ap2, "+ Adicionar", self._add_corr, width=110).pack(side="left")

        # Footer
        sep = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        sep.pack(fill="x")
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=12)
        btn_secondary(footer, "Cancelar", self.destroy, width=110).pack(side="right", padx=(6, 0))
        btn_primary(footer, "Salvar contrato", self._salvar, width=150).pack(side="right")

        # Clientes map (adqs/ceds)
        clientes = dao.listar_clientes()
        self._cli_map = {f"{r['nome']} ({r['codigo']})": r["id"] for r in clientes}

        self._on_tipo_change("venda")

    def _add_parte_row(self, parent, tipo):
        """Cria uma linha de participante no formulário do contrato."""
        clientes = dao.listar_clientes()
        self._cli_map = {f"{r['nome']} ({r['codigo']})": r["id"] for r in clientes}
        nomes = list(self._cli_map.keys()) or ["(nenhum)"]
        ap = ctk.CTkFrame(parent, fg_color="transparent")
        ap.pack(fill="x", padx=20, pady=(6, 0))
        sel = ctk.CTkOptionMenu(ap, values=nomes, width=320,
                                fg_color=BG3, button_color=GREEN,
                                dropdown_fg_color=BG3, text_color=TEXT)
        sel.pack(side="left", padx=(0, 8))
        if tipo == "adquirente":
            self._sel_adq = sel
        else:
            self._sel_ced = sel
        btn_secondary(ap, "+ Adicionar",
                      lambda t=tipo: self._add_parte(t), width=110).pack(side="left")

    def _add_parte(self, tipo):
        """Adiciona um participante à seção correspondente do contrato."""
        sel = self._sel_adq if tipo == "adquirente" else self._sel_ced
        lista = self._lista_adqs if tipo == "adquirente" else self._lista_ceds
        nome_key = sel.get()
        cli_id = self._cli_map.get(nome_key)
        if not cli_id:
            self.toast.show("Selecione um cliente.", error=True); return
        if any(i.get("cliente_id") == cli_id for i in lista.get_items()):
            self.toast.show("Cliente já adicionado.", error=True); return
        nome = nome_key.split(" (")[0]
        lista.adicionar({"label": nome, "cliente_id": cli_id})

    def _atualizar_imoveis(self):
        """Refiltra o seletor de imóvel com base nos cedentes adicionados."""
        cli_ids = [i["cliente_id"] for i in self._lista_ceds.get_items()]
        if not cli_ids:
            nomes = ["(selecione um cedente)"]
            self._im_map = {}
        else:
            # imóveis de TODOS os cedentes selecionados (união)
            imoveis = []
            for cid in cli_ids:
                imoveis.extend(dao.imoveis_por_cliente(cid))
            # deduplica por id preservando ordem
            vistos, unicos = set(), []
            for r in imoveis:
                if r["id"] not in vistos:
                    vistos.add(r["id"]); unicos.append(r)
            self._im_map = {
                f"{r['codigo']} — {r['subtipo']} · {r['bairro']}": r["id"]
                for r in unicos}
            nomes = list(self._im_map.keys()) or ["(nenhum imóvel deste cedente)"]
        self._sel_imovel.configure(values=nomes)
        self._sel_imovel.set(nomes[0])

    def _add_corr(self):
        """Adiciona um corretor e sua participação ao formulário do contrato."""
        nome_key = self._sel_corr.get()
        corr_id  = self._corr_map.get(nome_key)
        if not corr_id:
            self.toast.show("Selecione um corretor.", error=True); return
        pct = float(self._e_pct_corr.get().strip() or "100")
        if any(i.get("corretor_id") == corr_id for i in self._lista_corrs.get_items()):
            self.toast.show("Corretor já adicionado.", error=True); return
        nome = nome_key.split(" (")[0]
        self._lista_corrs.adicionar({
            "label": nome, "sub": f"  {pct}% comissão",
            "corretor_id": corr_id, "percentual": pct,
        })
        self._e_pct_corr.delete(0, "end")

    def _on_tipo_change(self, val):
        """Ajusta os campos do formulário quando o tipo de contrato muda."""
        if val == "venda":
            self._frame_venda.pack(fill="x", padx=20)
            self._frame_aluguel.pack_forget()
        else:
            self._frame_aluguel.pack(fill="x", padx=20)
            self._frame_venda.pack_forget()

    def _carregar(self):
        """Carrega no formulário os dados do registro que será editado."""
        row, adqs, ceds, corrs = dao.get_contrato(self.id_)
        if not row: return
        self._f_codigo.set(row["codigo"])
        self._f_tipo.set(row["tipo"])
        self._on_tipo_change(row["tipo"])
        self._f_situacao.set(row["situacao"])
        self._f_valor.set(row["valor"])
        self._f_comissao.set(row["comissao"])
        self._f_data.set(row["data_assinatura"])

        if row["tipo"] == "venda":
            self._f_entrada.set(row["valor_entrada"] or "")
            self._f_parcelas.set(row["num_parcelas"] or "")
        else:
            self._f_duracao.set(row["duracao_meses"] or "")
            self._f_vencdia.set(row["dia_vencimento"] or "")

        self._lista_adqs.set_items([
            {"label": r["nome"], "cliente_id": r["cliente_id"]} for r in adqs])
        self._lista_ceds.set_items([
            {"label": r["nome"], "cliente_id": r["cliente_id"]} for r in ceds])
        # popula o seletor de imóvel a partir dos cedentes e seleciona o atual
        self._atualizar_imoveis()
        if row["imovel_id"]:
            for key, val in self._im_map.items():
                if val == row["imovel_id"]:
                    self._sel_imovel.set(key)
                    break
        self._lista_corrs.set_items([
            {"label": r["nome"], "sub": f"  {r['percentual']}% comissão",
             "corretor_id": r["corretor_id"], "percentual": r["percentual"]}
            for r in corrs])

    def _salvar(self):
        """Valida os campos, persiste o formulário e informa o resultado ao usuário."""
        tipo = self._f_tipo.get()
        im_key = self._sel_imovel.get()
        im_id  = self._im_map.get(im_key)
        if not im_id:
            self.toast.show("Selecione um imóvel.", error=True); return

        data = {
            "codigo":          self._f_codigo.get().strip(),
            "tipo":            tipo,
            "valor":           float(self._f_valor.get() or 0),
            "comissao":        float(self._f_comissao.get() or 0),
            "data_assinatura": self._f_data.get().strip(),
            "situacao":        self._f_situacao.get(),
            "imovel_id":       im_id,
        }
        if tipo == "venda":
            data["valor_entrada"] = float(self._f_entrada.get() or 0)
            data["num_parcelas"]  = int(self._f_parcelas.get() or 0)
        else:
            data["duracao_meses"]  = int(self._f_duracao.get() or 0)
            data["dia_vencimento"] = int(self._f_vencdia.get() or 1)

        adqs  = [i["cliente_id"]  for i in self._lista_adqs.get_items()]
        ceds  = [i["cliente_id"]  for i in self._lista_ceds.get_items()]
        corrs = self._lista_corrs.get_items()

        if not data["codigo"] or not data["data_assinatura"]:
            self.toast.show("Código e data são obrigatórios.", error=True); return
        if not adqs:
            self.toast.show("Adicione ao menos um adquirente.", error=True); return
        if not ceds:
            self.toast.show("Adicione ao menos um cedente.", error=True); return
        if not corrs:
            self.toast.show("Adicione ao menos um corretor.", error=True); return

        ok, err = dao.salvar_contrato(data, adqs, ceds, corrs, id_=self.id_)
        if ok:
            self.toast.show("Contrato salvo com sucesso.")
            # recalcula o status do imóvel vinculado (pode ter mudado)
            dao.recalcular_status_imovel(data["imovel_id"])
            if self.on_save: self.on_save()
            self.destroy()
        else:
            msg = "Código já cadastrado." if "UNIQUE" in err else f"Erro: {err}"
            self.toast.show(msg, error=True)
