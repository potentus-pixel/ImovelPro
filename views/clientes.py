import customtkinter as ctk
import dao
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED, GREEN, RED,
                     Tabela, FiltroBar, ListaTag, Campo,
                     btn_primary, btn_secondary, btn_danger,
                     confirmar, fmt_date, font)


class Clientes(ctk.CTkFrame):
    def __init__(self, master, toast, **kw):
        """Inicializa Clientes e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG, **kw)
        self.toast = toast
        self._build()

    def _build(self):
        # Cabeçalho
        """Cria e organiza os controles visuais que compõem esta tela."""
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(h, text="Clientes", font=("Segoe UI", 22, "bold"),
                     text_color=TEXT).pack(side="left")

        # Filtros
        self._bar = FiltroBar(
            self,
            on_search=self._pesquisar,
            placeholder="Buscar por nome, CPF ou código...",
            filtros=[
                ("Perfil", ["dono", "interessado"]),
            ],
            btn_label="+ Novo cliente",
            btn_cmd=self._novo,
        )
        self._bar.pack(fill="x")

        # Tabela
        cols = ["Código", "Nome", "CPF", "Telefone(s)", "Perfil", "Imóveis"]
        largs = [90, 200, 140, 240, 110, 100]
        self._tabela = Tabela(self, cols, largs)
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(8, 4))

        # Botões de ação
        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(0, 12))
        btn_secondary(brow, "✏  Editar", self._editar, width=110).pack(side="left", padx=(0, 6))
        btn_danger(brow, "🗑  Excluir", self._excluir, width=110).pack(side="left")

        self._pesquisar()

    def _pesquisar(self):
        """Aplica os filtros preenchidos e atualiza a listagem da tela."""
        from database import get_conn
        q = self._bar.get_query()
        perfil = self._bar.get_filtro("Perfil")
        rows = dao.listar_clientes(filtro=q, perfil=perfil)
        # usa UMA unica conexao para contar imoveis de todos os clientes
        conn = get_conn()
        try:
            cnt_por_cli = {
                r[0]: r[1] for r in conn.execute(
                    "SELECT cliente_id, COUNT(*) FROM imovel_proprietario GROUP BY cliente_id"
                ).fetchall()
            }
        finally:
            conn.close()
        dados = []
        for r in rows:
            cnt = cnt_por_cli.get(r["id"], 0)
            dados.append((
                r["id"],
                r["codigo"],
                r["nome"],
                r["cpf"],
                r["telefones"] or "—",
                r["perfil"],
                f"{cnt} imóvel(is)" if cnt else "—",
            ))
        self._tabela.preencher(dados, id_col=0)

    def _novo(self):
        """Abre o formulário para cadastrar um novo registro."""
        FormCliente(self, self.toast, on_save=self._pesquisar)

    def _editar(self):
        """Abre para edição o registro atualmente selecionado."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um cliente para editar.", error=True)
            return
        FormCliente(self, self.toast, id_=id_, on_save=self._pesquisar)

    def _excluir(self):
        """Executa a rotina interna “excluir” deste componente."""
        id_ = self._tabela.selected_id()
        if not id_:
            self.toast.show("Selecione um cliente para excluir.", error=True)
            return
        row = self._tabela.selected_row()
        nome = row[2] if row else "?"
        if confirmar(self, "Excluir cliente", f"Excluir o cliente '{nome}'?"):
            ok, err = dao.excluir_cliente(id_)
            if ok:
                self.toast.show("Cliente excluído.")
                self._pesquisar()
            else:
                self.toast.show(f"Erro: {err}", error=True)

    def atualizar(self):
        """Recarrega os dados e redesenha as informações exibidas na tela."""
        self._pesquisar()


# ── FORMULÁRIO ───────────────────────────────────────────────
class FormCliente(ctk.CTkToplevel):
    def __init__(self, master, toast, id_=None, on_save=None):
        """Inicializa FormCliente e prepara seu estado e interface."""
        super().__init__(master)
        self.toast = toast
        self.id_ = id_
        self.on_save = on_save
        self.title("Editar cliente" if id_ else "Novo cliente")
        self.geometry("520x650")
        self.minsize(520, 600)
        self.resizable(False, True)
        self.grab_set()
        self.configure(fg_color=BG2)
        self._tels = []
        self._build()
        if id_:
            self._carregar()

    def _build(self):
        """Cria e organiza os controles visuais que compõem esta tela."""
        ctk.CTkLabel(self, text="Dados do cliente",
                     font=("Segoe UI", 16, "bold"), text_color=TEXT
                     ).pack(padx=20, pady=(18, 12), anchor="w")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=20)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self._f_codigo = Campo(grid, "Código", width=200)
        self._f_codigo.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=4)

        self._f_cpf = Campo(grid, "CPF", width=200)
        self._f_cpf.grid(row=0, column=1, sticky="ew", pady=4)

        self._f_nome = Campo(grid, "Nome completo", width=440)
        self._f_nome.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)

        self._f_perfil = Campo(grid, "Perfil", widget_class=ctk.CTkOptionMenu,
                               values=["interessado", "dono", "ambos"], width=200)
        self._f_perfil.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=4)

        # Telefones
        ctk.CTkLabel(self, text="Telefones", font=("Segoe UI", 11),
                     text_color=MUTED).pack(anchor="w", padx=20, pady=(10, 2))

        tel_frame = ctk.CTkFrame(self, fg_color="transparent")
        tel_frame.pack(fill="x", padx=20)

        self._e_tel = ctk.CTkEntry(tel_frame, placeholder_text="(00) 00000-0000",
                                   fg_color=BG3, border_color=BORDER,
                                   text_color=TEXT, placeholder_text_color=MUTED,
                                   width=260)
        self._e_tel.pack(side="left", padx=(0, 8))
        self._e_tel.bind("<Return>", lambda e: self._add_tel())
        btn_secondary(tel_frame, "+ Adicionar", self._add_tel, width=110).pack(side="left")

        self._lista_tels = ListaTag(self, altura=110)
        self._lista_tels.pack(fill="x", padx=20, pady=(6, 0))

        # Rodapé
        sep = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=0, pady=(16, 0))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=12)
        btn_secondary(footer, "Cancelar", self.destroy, width=110).pack(side="right", padx=(6, 0))
        btn_primary(footer, "Salvar", self._salvar, width=130).pack(side="right")

        self._f_codigo.set(dao.proximo_codigo_cliente())

    def _add_tel(self):
        """Adiciona ao formulário um campo para informar telefone."""
        v = self._e_tel.get().strip()
        if not v:
            return
        items = self._lista_tels.get_items()
        if any(i["label"] == v for i in items):
            return
        self._lista_tels.adicionar({"label": v})
        self._e_tel.delete(0, "end")

    def _carregar(self):
        """Carrega no formulário os dados do registro que será editado."""
        row, tels = dao.get_cliente(self.id_)
        if not row:
            return
        self._f_codigo.set(row["codigo"])
        self._f_cpf.set(row["cpf"])
        self._f_nome.set(row["nome"])
        self._f_perfil.set(row["perfil"])
        self._lista_tels.set_items([{"label": t} for t in tels])

    def _salvar(self):
        """Valida os campos, persiste o formulário e informa o resultado ao usuário."""
        tels = [i["label"] for i in self._lista_tels.get_items()]
        tel_entry = self._e_tel.get().strip()
        if tel_entry:
            tels.append(tel_entry)

        data = {
            "codigo": self._f_codigo.get().strip(),
            "nome":   self._f_nome.get().strip(),
            "cpf":    self._f_cpf.get().strip(),
            "perfil": self._f_perfil.get(),
        }
        if not data["nome"] or not data["cpf"] or not data["codigo"]:
            self.toast.show("Código, nome e CPF são obrigatórios.", error=True)
            return
        if not tels:
            self.toast.show("Informe ao menos um telefone.", error=True)
            return

        ok, err = dao.salvar_cliente(data, tels, id_=self.id_)
        if ok:
            self.toast.show("Cliente salvo com sucesso.")
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            msg = "CPF já cadastrado." if "UNIQUE" in err else f"Erro: {err}"
            self.toast.show(msg, error=True)
