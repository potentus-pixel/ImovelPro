import customtkinter as ctk
import dao
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED,
                     Tabela, FiltroBar, ListaTag, Campo,
                     btn_primary, btn_secondary, btn_danger, confirmar, font)


class Corretores(ctk.CTkFrame):
    def __init__(self, master, toast, **kw):
        """Inicializa Corretores e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG, **kw)
        self.toast = toast
        self._build()

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(h, text="Corretores", font=("Segoe UI", 22, "bold"),
                     text_color=TEXT).pack(side="left")

        self._bar = FiltroBar(
            self, on_search=self._pesquisar,
            placeholder="Buscar por nome, CPF ou CRECI...",
            btn_label="+ Novo corretor", btn_cmd=self._novo,
        )
        self._bar.pack(fill="x")

        cols = ["Nome", "CPF", "CRECI", "Telefone(s)", "Contrato(s)"]
        largs = [200, 140, 100, 200, 110]
        self._tabela = Tabela(self, cols, largs)
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(8, 4))

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(0, 12))
        btn_secondary(brow, "✏  Editar", self._editar, width=110).pack(side="left", padx=(0, 6))
        btn_danger(brow, "🗑  Excluir", self._excluir, width=110).pack(side="left")

        self._pesquisar()

    def _pesquisar(self):
        """Aplica os filtros preenchidos e atualiza a listagem da tela."""
        from database import get_conn
        q = self._bar.get_query()
        rows = dao.listar_corretores(filtro=q)
        # UMA unica conexao para contar contratos de todos os corretores
        conn = get_conn()
        try:
            cnt_por_corr = {
                r[0]: r[1] for r in conn.execute(
                    "SELECT corretor_id, COUNT(*) FROM contrato_corretor GROUP BY corretor_id"
                ).fetchall()
            }
        finally:
            conn.close()
        dados = []
        for r in rows:
            cnt = cnt_por_corr.get(r["id"], 0)
            dados.append((
                r["id"], r["nome"], r["cpf"], r["creci"],
                r["telefones"] or "—",
                f"{cnt} contrato(s)",
            ))
        self._tabela.preencher(dados, id_col=0)

    def _novo(self):
        """Abre o formulário para cadastrar um novo registro."""
        FormCorretor(self, self.toast, on_save=self._pesquisar)

    def _editar(self):
        """Abre para edição o registro atualmente selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um corretor.", error=True); return
        FormCorretor(self, self.toast, id_=id_, on_save=self._pesquisar)

    def _excluir(self):
        """Executa a rotina interna “excluir” deste componente."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um corretor.", error=True); return
        row = self._tabela.selected_row()
        nome = row[1] if row else "?"
        if confirmar(self, "Excluir corretor", f"Excluir '{nome}'?"):
            ok, err = dao.excluir_corretor(id_)
            if ok:
                self.toast.show("Corretor excluído.")
                self._pesquisar()
            else:
                self.toast.show(f"Erro: {err}", error=True)

    def atualizar(self):
        """Recarrega os dados e redesenha as informações exibidas na tela."""
        self._pesquisar()


class FormCorretor(ctk.CTkToplevel):
    def __init__(self, master, toast, id_=None, on_save=None):
        """Inicializa FormCorretor e prepara seu estado e interface."""
        super().__init__(master)
        self.toast = toast
        self.id_ = id_
        self.on_save = on_save
        self.title("Editar corretor" if id_ else "Novo corretor")
        self.geometry("500x570")
        self.minsize(500, 540)
        self.resizable(False, True)
        self.grab_set()
        self.configure(fg_color=BG2)
        self._build()
        if id_:
            self._carregar()

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        ctk.CTkLabel(self, text="Dados do corretor",
                     font=("Segoe UI", 16, "bold"), text_color=TEXT
                     ).pack(padx=20, pady=(18, 12), anchor="w")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=20)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self._f_nome = Campo(grid, "Nome completo", width=440)
        self._f_nome.grid(row=0, column=0, columnspan=2, sticky="ew", pady=4)

        self._f_cpf = Campo(grid, "CPF", width=200)
        self._f_cpf.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=4)

        self._f_creci = Campo(grid, "CRECI", width=200)
        self._f_creci.grid(row=1, column=1, sticky="ew", pady=4)

        # Telefones
        ctk.CTkLabel(self, text="Telefones", font=("Segoe UI", 11),
                     text_color=MUTED).pack(anchor="w", padx=20, pady=(10, 2))
        tel_f = ctk.CTkFrame(self, fg_color="transparent")
        tel_f.pack(fill="x", padx=20)
        self._e_tel = ctk.CTkEntry(tel_f, placeholder_text="(00) 00000-0000",
                                   fg_color=BG3, border_color=BORDER,
                                   text_color=TEXT, placeholder_text_color=MUTED,
                                   width=260)
        self._e_tel.pack(side="left", padx=(0, 8))
        self._e_tel.bind("<Return>", lambda e: self._add_tel())
        btn_secondary(tel_f, "+ Adicionar", self._add_tel, width=110).pack(side="left")

        self._lista_tels = ListaTag(self, altura=110)
        self._lista_tels.pack(fill="x", padx=20, pady=(6, 0))

        sep = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=0, pady=(16, 0))
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=12)
        btn_secondary(footer, "Cancelar", self.destroy, width=110).pack(side="right", padx=(6, 0))
        btn_primary(footer, "Salvar", self._salvar, width=130).pack(side="right")

    def _add_tel(self):
        """Adiciona ao formulário um campo para informar telefone."""
        v = self._e_tel.get().strip()
        if not v: return
        if any(i["label"] == v for i in self._lista_tels.get_items()): return
        self._lista_tels.adicionar({"label": v})
        self._e_tel.delete(0, "end")

    def _carregar(self):
        """Carrega no formulário os dados do registro que será editado."""
        row, tels = dao.get_corretor(self.id_)
        if not row: return
        self._f_nome.set(row["nome"])
        self._f_cpf.set(row["cpf"])
        self._f_creci.set(row["creci"])
        self._lista_tels.set_items([{"label": t} for t in tels])

    def _salvar(self):
        """Valida os campos, persiste o formulário e informa o resultado ao usuário."""
        tels = [i["label"] for i in self._lista_tels.get_items()]
        if self._e_tel.get().strip():
            tels.append(self._e_tel.get().strip())
        data = {
            "nome":  self._f_nome.get().strip(),
            "cpf":   self._f_cpf.get().strip(),
            "creci": self._f_creci.get().strip(),
        }
        if not all(data.values()):
            self.toast.show("Todos os campos são obrigatórios.", error=True); return
        if not tels:
            self.toast.show("Informe ao menos um telefone.", error=True); return
        ok, err = dao.salvar_corretor(data, tels, id_=self.id_)
        if ok:
            self.toast.show("Corretor salvo.")
            if self.on_save: self.on_save()
            self.destroy()
        else:
            msg = "CPF ou CRECI já cadastrado." if "UNIQUE" in err else f"Erro: {err}"
            self.toast.show(msg, error=True)
