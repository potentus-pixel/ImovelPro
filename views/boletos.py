import customtkinter as ctk
import dao
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED, GREEN,
                     Tabela, FiltroBar, Campo,
                     btn_primary, btn_secondary, btn_danger,
                     confirmar, fmt_brl, fmt_date, font)


class Boletos(ctk.CTkFrame):
    def __init__(self, master, toast, **kw):
        """Inicializa Boletos e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG, **kw)
        self.toast = toast
        self._build()

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(h, text="Boletos", font=("Segoe UI", 22, "bold"),
                     text_color=TEXT).pack(side="left")

        self._bar = FiltroBar(
            self, on_search=self._pesquisar,
            placeholder="Buscar por número ou contrato...",
            filtros=[
                ("Tipo",     ["comissao", "parcela", "aluguel"]),
                ("Situação", ["pendente", "pago", "vencido"]),
            ],
            btn_label="+ Novo boleto", btn_cmd=self._novo,
        )
        self._bar.pack(fill="x")

        cols = ["Sequencial", "Contrato", "Tipo", "Valor",
                "Vencimento", "Pagamento", "Situação"]
        largs = [110, 110, 100, 130, 110, 110, 100]
        self._tabela = Tabela(self, cols, largs)
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(8, 4))

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(0, 12))
        btn_secondary(brow, "✏  Editar", self._editar, width=120).pack(side="left", padx=(0, 6))
        btn_secondary(brow, "✓  Marcar pago", self._marcar_pago, width=140).pack(side="left", padx=(0, 6))
        btn_danger(brow, "🗑  Excluir", self._excluir, width=110).pack(side="left")

        self._pesquisar()

    def _pesquisar(self):
        """Aplica os filtros preenchidos e atualiza a listagem da tela."""
        q  = self._bar.get_query()
        tp = self._bar.get_filtro("Tipo")
        st = self._bar.get_filtro("Situação")
        rows = dao.listar_boletos(filtro=q, tipo=tp, situacao=st)
        dados = []
        for r in rows:
            dados.append((
                r["id"],
                r["sequencial"],
                r["ct_codigo"],
                r["tipo"],
                fmt_brl(r["valor"]),
                fmt_date(r["data_vencimento"]),
                fmt_date(r["data_pagamento"]),
                r["situacao"],
            ))
        self._tabela.preencher(dados, id_col=0)

    def _novo(self):
        """Abre o formulário para cadastrar um novo registro."""
        FormBoleto(self, self.toast, on_save=self._pesquisar)

    def _editar(self):
        """Abre para edição o registro atualmente selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um boleto.", error=True); return
        FormBoleto(self, self.toast, id_=id_, on_save=self._pesquisar)

    def _marcar_pago(self):
        """Marca o boleto selecionado como pago e atualiza a listagem."""
        from datetime import date
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um boleto.", error=True); return
        row = dao.get_boleto(id_)
        if not row:
            return
        data = {
            "sequencial":      row["sequencial"],
            "contrato_id":     row["contrato_id"],
            "tipo":            row["tipo"],
            "situacao":        "pago",
            "valor":           row["valor"],
            "data_vencimento": row["data_vencimento"],
            "data_pagamento":  str(date.today()),
        }
        ok, err = dao.salvar_boleto(data, id_=id_)
        if ok:
            self.toast.show("Boleto marcado como pago.")
            self._pesquisar()
        else:
            self.toast.show(f"Erro: {err}", error=True)

    def _excluir(self):
        """Executa a rotina interna “excluir” deste componente."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um boleto.", error=True); return
        row = self._tabela.selected_row()
        seq = row[1] if row else "?"
        if confirmar(self, "Excluir boleto", f"Excluir boleto '{seq}'?"):
            ok, err = dao.excluir_boleto(id_)
            if ok:
                self.toast.show("Boleto excluído.")
                self._pesquisar()
            else:
                self.toast.show(f"Erro: {err}", error=True)

    def atualizar(self):
        """Recarrega os dados e redesenha as informações exibidas na tela."""
        self._pesquisar()


class FormBoleto(ctk.CTkToplevel):
    def __init__(self, master, toast, id_=None, on_save=None):
        """Inicializa FormBoleto e prepara seu estado e interface."""
        super().__init__(master)
        self.toast   = toast
        self.id_     = id_
        self.on_save = on_save
        self.title("Editar boleto" if id_ else "Novo boleto")
        self.geometry("500x420")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG2)
        self._build()
        if id_:
            self._carregar()
        else:
            self._f_seq.set(dao.proximo_sequencial_boleto())

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        ctk.CTkLabel(self, text="Dados do boleto",
                     font=("Segoe UI", 16, "bold"), text_color=TEXT
                     ).pack(anchor="w", padx=20, pady=(18, 12))

        g = ctk.CTkFrame(self, fg_color="transparent")
        g.pack(fill="x", padx=20)
        g.columnconfigure((0, 1), weight=1)

        self._f_seq = Campo(g, "Sequencial", width=200)
        self._f_seq.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=4)

        contratos = dao.todos_contratos()
        self._ct_map = {f"{r['codigo']} ({r['tipo']})": r["id"] for r in contratos}
        nomes_ct = list(self._ct_map.keys()) or ["(nenhum)"]
        self._f_contrato = Campo(g, "Contrato", widget_class=ctk.CTkOptionMenu,
                                 values=nomes_ct, width=200)
        self._f_contrato.grid(row=0, column=1, sticky="ew", pady=4)

        self._f_tipo = Campo(g, "Tipo", widget_class=ctk.CTkOptionMenu,
                             values=["comissao", "parcela", "aluguel"], width=200)
        self._f_tipo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=4)

        self._f_situacao = Campo(g, "Situação", widget_class=ctk.CTkOptionMenu,
                                 values=["pendente", "pago", "vencido"], width=200)
        self._f_situacao.grid(row=1, column=1, sticky="ew", pady=4)
        # A situação é derivada das datas ao salvar; não deve ser escolhida
        # manualmente, pois isso permitiria combinações inconsistentes.
        self._f_situacao.w.configure(state="disabled")

        self._f_valor = Campo(g, "Valor (R$)", width=200)
        self._f_valor.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=4)

        self._f_venc = Campo(g, "Data de vencimento (AAAA-MM-DD)", width=200)
        self._f_venc.grid(row=2, column=1, sticky="ew", pady=4)

        self._f_pgto = Campo(g, "Data de pagamento (deixe vazio se pendente)", width=440)
        self._f_pgto.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)

        sep = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=0, pady=(16, 0))
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=12)
        btn_secondary(footer, "Cancelar", self.destroy, width=110).pack(side="right", padx=(6, 0))
        btn_primary(footer, "Salvar", self._salvar, width=130).pack(side="right")

    def _carregar(self):
        """Carrega no formulário os dados do registro que será editado."""
        row = dao.get_boleto(self.id_)
        if not row: return
        self._f_seq.set(row["sequencial"])
        for key, val in self._ct_map.items():
            if val == row["contrato_id"]:
                self._f_contrato.set(key); break
        self._f_tipo.set(row["tipo"])
        self._f_situacao.set(row["situacao"])
        self._f_valor.set(row["valor"])
        self._f_venc.set(row["data_vencimento"])
        self._f_pgto.set(row["data_pagamento"] or "")

    def _salvar(self):
        """Valida os campos, persiste o formulário e informa o resultado ao usuário."""
        ct_key = self._f_contrato.get()
        ct_id  = self._ct_map.get(ct_key)
        if not ct_id:
            self.toast.show("Selecione um contrato.", error=True); return
        data = {
            "sequencial":      self._f_seq.get().strip(),
            "contrato_id":     ct_id,
            "tipo":            self._f_tipo.get(),
            "situacao":        self._f_situacao.get(),
            "valor":           float(self._f_valor.get() or 0),
            "data_vencimento": self._f_venc.get().strip(),
            "data_pagamento":  self._f_pgto.get().strip() or None,
        }
        if not data["sequencial"] or not data["data_vencimento"] or not data["valor"]:
            self.toast.show("Sequencial, valor e vencimento são obrigatórios.", error=True)
            return
        ok, err = dao.salvar_boleto(data, id_=self.id_)
        if ok:
            self.toast.show("Boleto salvo.")
            if self.on_save: self.on_save()
            self.destroy()
        else:
            msg = "Sequencial já cadastrado." if "UNIQUE" in err else f"Erro: {err}"
            self.toast.show(msg, error=True)
