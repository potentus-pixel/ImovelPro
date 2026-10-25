import customtkinter as ctk
import os
import csv
from tkinter import filedialog
from datetime import date
import dao
import database
from widgets import (BG, BG2, BG3, BORDER, TEXT, MUTED, GREEN, GREEN_D,
                     AMBER, RED, TEAL_L, BLUE, PURPLE, fmt_brl, fmt_date,
                     font, DonutChart, BarChart)

STATUS_BG = {
    "ativo":      ("#1f3d2e", "#9FE1CB"),
    "em espera":  ("#4a3613", "#FAC775"),
    "encerrado":  ("#34373d", "#9aa0a8"),
    "pendente":   ("#4a3613", "#FAC775"),
    "pago":       ("#1f3d2e", "#9FE1CB"),
    "vencido":    ("#4d1f1f", "#F09595"),
}

# cores fixas para os gráficos (paleta viva, combinando com o tema)
STATUS_COLORS_G = {
    "disponivel":      GREEN,
    "em negociacao":   AMBER,
    "alugado":         BLUE,
    "vendido":         PURPLE,
}
TIPO_COLORS_G = {
    "venda":   BLUE,
    "aluguel": GREEN,
    "ambos":   PURPLE,
}
SIT_COLORS_G = {
    "pendente": AMBER,
    "pago":     GREEN,
    "vencido":  RED,
}
FINAL_COLORS_G = {
    "venda":   BLUE,
    "aluguel": GREEN,
    "ambos":   PURPLE,
}


class Dashboard(ctk.CTkFrame):
    def __init__(self, master, on_open_imovel=None, **kw):
        """Inicializa Dashboard e prepara seu estado e interface."""
        super().__init__(master, fg_color=BG, **kw)
        self._on_open_imovel = on_open_imovel
        self._data_signature = None
        self._contratos_cache = None
        self._alertas_cache = None
        self._relatorio_cache = None
        self._periodo_relatorio = ctk.StringVar(value="30")
        self._kpi_widgets = []
        self._build()

    def _build(self):
        # Conteúdo rolável (scroll vertical) — evita corte quando há muitos
        # registros (ex.: muitos boletos em "Alertas e pendências").
        """Cria e organiza os controles visuais que compõem esta tela."""
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BG,
                                              scrollbar_button_color=BORDER)
        self._scroll.pack(fill="both", expand=True)

        # Título
        header = ctk.CTkFrame(self._scroll, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="Dashboard", font=font(24, "bold"),
                     text_color=TEXT).pack(side="left")
        self._lbl_hora = ctk.CTkLabel(header, text="", font=font(12),
                                      text_color=MUTED)
        self._lbl_hora.pack(side="right")
        self._tick()

        # KPIs
        self._kpi_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._kpi_frame.pack(fill="x", padx=20, pady=(0, 16))

        # Grade principal: 3 colunas
        bottom = ctk.CTkFrame(self._scroll, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 20))
        bottom.columnconfigure(0, weight=3, minsize=320)
        bottom.columnconfigure(1, weight=2, minsize=260)
        bottom.columnconfigure(2, weight=2, minsize=260)

        # Coluna esquerda: contratos + alertas
        left = ctk.CTkFrame(bottom, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._frame_contratos = ctk.CTkFrame(left, fg_color=BG2, corner_radius=10)
        self._frame_contratos.pack(fill="x", pady=(0, 8))
        self._sec_header(self._frame_contratos, "Últimos contratos")
        self._contratos_body = ctk.CTkFrame(self._frame_contratos,
                                            fg_color="transparent")
        self._contratos_body.pack(fill="x", padx=0, pady=(0, 10))

        self._frame_alertas = ctk.CTkFrame(left, fg_color=BG2, corner_radius=10)
        self._frame_alertas.pack(fill="x", pady=(8, 0))
        self._sec_header(self._frame_alertas, "Alertas e pendências")
        # corpo rolável dos alertas (limita o crescimento na tela)
        self._alertas_body = ctk.CTkScrollableFrame(
            self._frame_alertas, fg_color="transparent", height=300,
            scrollbar_button_color=BORDER)
        self._alertas_body.pack(fill="x", padx=12, pady=(0, 10))

        # Coluna do meio: gráficos (preenche o espaço que antes ficava vazio)
        mid = ctk.CTkFrame(bottom, fg_color="transparent")
        mid.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        mid.columnconfigure(0, weight=1)

        self._graf_status = DonutChart(mid, "Imóveis por status",
                                       largura=300, altura=200)
        self._graf_status.grid(row=0, column=0, sticky="new", pady=(0, 8))

        self._graf_finalidade = DonutChart(mid, "Imóveis por finalidade",
                                           largura=300, altura=200)
        self._graf_finalidade.grid(row=1, column=0, sticky="new", pady=(8, 0))

        # Coluna direita: gráficos
        right = ctk.CTkFrame(bottom, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self._graf_tipo = BarChart(right, "Contratos por tipo",
                                   largura=300, altura=200)
        self._graf_tipo.grid(row=0, column=0, sticky="new", pady=(0, 8))

        self._graf_boleto = BarChart(right, "Boletos por situação",
                                     largura=300, altura=200)
        self._graf_boleto.grid(row=1, column=0, sticky="new", pady=(8, 0))

        self._frame_relatorio = ctk.CTkFrame(
            self._scroll, fg_color=BG2, corner_radius=10)
        self._frame_relatorio.pack(fill="x", padx=20, pady=(0, 20))
        header_rel = ctk.CTkFrame(self._frame_relatorio, fg_color="transparent")
        header_rel.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(header_rel, text="Relatórios operacionais",
                     font=font(16, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkButton(header_rel, text="Exportar CSV", width=110, height=30,
                      fg_color=GREEN, hover_color=GREEN_D,
                      command=self._exportar_relatorio).pack(side="right")
        ctk.CTkOptionMenu(
            header_rel, values=["30", "60", "90"], variable=self._periodo_relatorio,
            width=90, height=30, fg_color=BG3, button_color=GREEN,
            button_hover_color=GREEN_D, dropdown_fg_color=BG2,
            text_color=TEXT, command=lambda _value: self._render_relatorio()
        ).pack(side="right", padx=8)
        ctk.CTkLabel(header_rel, text="Próximos dias:", font=font(11),
                     text_color=MUTED).pack(side="right")
        self._relatorio_body = ctk.CTkFrame(
            self._frame_relatorio, fg_color="transparent")
        self._relatorio_body.pack(fill="x", padx=14, pady=(4, 14))

    def _tick(self):
        """Agenda e executa a atualização periódica do dashboard."""
        from datetime import datetime
        self._lbl_hora.configure(
            text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.after(1000, self._tick)

    def atualizar(self, force=False):
        # Ao voltar de outra aba, os widgets já renderizados aparecem
        # imediatamente. Só refaz toda a árvore visual quando necessário.
        """Recarrega os dados e redesenha as informações exibidas na tela."""
        assinatura = self._assinatura_dados()
        if not force and assinatura == self._data_signature:
            return
        dados = dao.dashboard_snapshot()
        self._render_kpis(dados["kpis"])
        self._render_contratos(dados["contratos"])
        self._render_alertas(dados["alertas"])
        self._render_graficos(dados)
        self._render_relatorio()
        self._data_signature = self._assinatura_dados()

    @staticmethod
    def _assinatura_dados():
        """Gera uma assinatura dos dados para detectar alterações no dashboard."""
        try:
            st = os.stat(database.DB_PATH)
            arquivo = (st.st_mtime_ns, st.st_size)
        except OSError:
            arquivo = (None, None)
        return arquivo + (date.today().isoformat(),)

    def _kpi(self, parent, titulo, valor, sub="", cor=TEXT, cor_bar=GREEN):
        """Cria um cartão visual para apresentar um indicador do dashboard."""
        f = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=10)
        # barra de cor lateral (destaque)
        bar = ctk.CTkFrame(f, width=4, fg_color=cor_bar, corner_radius=0)
        bar.pack(side="left", fill="y")
        inner = ctk.CTkFrame(f, fg_color="transparent")
        inner.pack(side="left", fill="both", expand=True, padx=(12, 4))
        ctk.CTkLabel(inner, text=titulo, font=font(12),
                     text_color=MUTED).pack(anchor="w", padx=2, pady=(12, 0))
        valor_lbl = ctk.CTkLabel(inner, text=str(valor), font=font(30, "bold"),
                                 text_color=cor)
        valor_lbl.pack(anchor="w", padx=2)
        ctk.CTkLabel(inner, text=sub, font=font(11),
                     text_color=MUTED).pack(anchor="w", padx=2, pady=(0, 12))
        return f, valor_lbl

    def _render_kpis(self, d):
        """Renderiza os cartões com os indicadores atuais."""
        kpis = [
            ("Imóveis cadastrados",  d["imoveis"],            "no sistema",            TEXT,    BLUE),
            ("Contratos vigentes",   d["contratos_ativos"],   "ativos ou em espera",   GREEN,   GREEN),
            ("Boletos pendentes",    d["boletos_pendentes"],  "aguardando pagamento",  AMBER,   AMBER),
            ("Boletos vencidos",     d["boletos_vencidos"],   "em atraso",             RED,     RED),
            ("Clientes",             d["clientes"],           "cadastrados",           TEXT,    PURPLE),
            ("Comissão a receber",   fmt_brl(d["comissao_receber"]), "em aberto",       TEAL_L,  TEAL_L),
        ]
        if not self._kpi_widgets:
            for i, (t, v, s, c, cb) in enumerate(kpis):
                card, valor_lbl = self._kpi(self._kpi_frame, t, v, s, c, cb)
                card.grid(row=0, column=i, sticky="nsew", padx=4)
                self._kpi_frame.columnconfigure(i, weight=1)
                self._kpi_widgets.append(valor_lbl)
        else:
            for valor_lbl, (_, valor, _, _, _) in zip(self._kpi_widgets, kpis):
                valor_lbl.configure(text=str(valor))

    def _sec_header(self, parent, titulo):
        """Cria o cabeçalho visual de uma seção do dashboard."""
        h = ctk.CTkFrame(parent, fg_color="transparent")
        h.pack(fill="x", padx=12, pady=(12, 0))
        ctk.CTkLabel(h, text=titulo, font=font(15, "bold"),
                     text_color=TEXT).pack(side="left")
        sep = ctk.CTkFrame(parent, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=12, pady=(6, 0))

    def _render_contratos(self, rows):
        """Renderiza a seção de contratos recentes."""
        chave = tuple(
            tuple(r.get(k) for k in ("codigo", "tipo", "situacao", "valor",
                                     "adquirentes", "im_subtipo", "im_bairro"))
            for r in rows)
        if chave == self._contratos_cache:
            return
        self._contratos_cache = chave
        for w in self._contratos_body.winfo_children():
            w.destroy()
        if not rows:
            ctk.CTkLabel(self._contratos_body, text="Nenhum contrato cadastrado.",
                         text_color=MUTED, font=font(12)).pack(pady=24)
            return
        for r in rows:
            row_f = ctk.CTkFrame(self._contratos_body, fg_color="transparent")
            row_f.pack(fill="x", padx=12, pady=4)

            tipo_cor = ("#0C447C", "#E6F1FB") if r["tipo"] == "venda" else ("#085041", "#E1F5EE")
            tag = ctk.CTkLabel(row_f, text=r["tipo"].upper(),
                               fg_color=tipo_cor[0], text_color=tipo_cor[1],
                               font=font(9, "bold"),
                               corner_radius=4, width=50)
            tag.pack(side="left", padx=(0, 8))

            info = ctk.CTkFrame(row_f, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            adqs = (r["adquirentes"] or "").replace("|", ",")
            ctk.CTkLabel(info, text=adqs[:38] + ("…" if len(adqs) > 38 else ""),
                         font=font(12, "bold"), text_color=TEXT,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"{r['im_subtipo']} · {r['im_bairro']} · {r['codigo']}",
                         font=font(11), text_color=MUTED,
                         anchor="w").pack(anchor="w")

            st_bg, st_fg = STATUS_BG.get(r["situacao"], (BG3, MUTED))
            ctk.CTkLabel(row_f, text=r["situacao"],
                         fg_color=st_bg, text_color=st_fg,
                         font=font(9, "bold"),
                         corner_radius=4, padx=6).pack(side="right")

            ctk.CTkLabel(row_f, text=fmt_brl(r["valor"]),
                         font=font(12, "bold"), text_color=TEAL_L
                         ).pack(side="right", padx=10)

    def _render_alertas(self, rows):
        """Renderiza os alertas operacionais do dashboard."""
        chave = tuple(
            tuple(r.get(k) for k in ("sequencial", "situacao", "valor",
                                     "data_vencimento", "ct_codigo"))
            for r in rows)
        if chave == self._alertas_cache:
            return
        self._alertas_cache = chave
        for w in self._alertas_body.winfo_children():
            w.destroy()
        if not rows:
            ctk.CTkLabel(self._alertas_body, text="✓  Nenhuma pendência no momento.",
                         text_color=TEAL_L, font=font(12)).pack(pady=24)
            return
        for r in rows:
            row_f = ctk.CTkFrame(self._alertas_body, fg_color="transparent")
            row_f.pack(fill="x", padx=12, pady=5)

            icone = "⚠" if r["situacao"] == "vencido" else "🕐"
            cor = RED if r["situacao"] == "vencido" else AMBER
            ctk.CTkLabel(row_f, text=icone, font=font(14),
                         text_color=cor, width=24).pack(side="left")

            info = ctk.CTkFrame(row_f, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkLabel(info,
                         text=f"Boleto {r['sequencial']} — Contrato {r['ct_codigo']}",
                         font=font(12, "bold"), text_color=TEXT,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"Venc. {fmt_date(r['data_vencimento'])}  ·  {r['situacao'].upper()}",
                         font=font(11), text_color=cor,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(row_f, text=fmt_brl(r["valor"]),
                         font=font(12, "bold"),
                         text_color=TEXT).pack(side="right")

    def _render_graficos(self, dados):
        # Donut: imóveis por status
        """Renderiza os gráficos estatísticos do dashboard."""
        dados_status = list(dados["graf_status"])
        # garante ordem estável
        ordem = ["disponivel", "em negociacao", "alugado", "vendido"]
        dados_status.sort(key=lambda kv: ordem.index(kv[0]) if kv[0] in ordem else 99)
        data_donut = [(lbl, v, STATUS_COLORS_G.get(lbl, MUTED))
                      for lbl, v in dados_status]
        self._graf_status.set_data(data_donut)

        # Donut: imóveis por finalidade
        dados_final = list(dados["graf_finalidade"])
        ordem_f = ["venda", "aluguel", "ambos"]
        dados_final.sort(key=lambda kv: ordem_f.index(kv[0]) if kv[0] in ordem_f else 99)
        data_final = [(lbl, v, FINAL_COLORS_G.get(lbl, MUTED))
                      for lbl, v in dados_final]
        self._graf_finalidade.set_data(data_final)

        # Barras: contratos por tipo
        dados_tipo = dados["graf_tipo"]
        data_tipo = [(lbl, v, TIPO_COLORS_G.get(lbl, MUTED))
                     for lbl, v in dados_tipo]
        self._graf_tipo.set_data(data_tipo)

        # Barras: boletos por situação
        dados_bol = dados["graf_boleto"]
        data_bol = [(lbl, v, SIT_COLORS_G.get(lbl, MUTED))
                    for lbl, v in dados_bol]
        self._graf_boleto.set_data(data_bol)

    def _render_relatorio(self):
        """Exibe os indicadores de estoque, vencimentos e boletos atrasados."""
        dados = dao.relatorio_operacional(int(self._periodo_relatorio.get()))
        chave = (dados["periodo"], dados["disponiveis"],
                 tuple((r["cidade"], r["quantidade"], r["valor"])
                       for r in dados["estoque_cidades"]),
                 tuple((r["codigo"], r["fim"]) for r in dados["contratos_vencendo"]),
                 dados["boletos_vencidos"]["quantidade"],
                 dados["boletos_vencidos"]["valor"])
        if chave == self._relatorio_cache:
            return
        self._relatorio_cache = chave
        for child in self._relatorio_body.winfo_children():
            child.destroy()
        summary = ctk.CTkFrame(self._relatorio_body, fg_color="transparent")
        summary.pack(fill="x", pady=(0, 8))
        items = [
            ("Imóveis disponíveis", str(dados["disponiveis"]), GREEN),
            (f"Contratos a vencer em {dados['periodo']} dias",
             str(len(dados["contratos_vencendo"])), AMBER),
            ("Boletos vencidos",
             f"{dados['boletos_vencidos']['quantidade']} · {fmt_brl(dados['boletos_vencidos']['valor'])}", RED),
        ]
        for title, value, color in items:
            card = ctk.CTkFrame(summary, fg_color=BG3, corner_radius=8)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkLabel(card, text=title, font=font(11),
                         text_color=MUTED).pack(anchor="w", padx=10, pady=(8, 1))
            ctk.CTkLabel(card, text=value, font=font(16, "bold"),
                         text_color=color).pack(anchor="w", padx=10, pady=(0, 8))
        cols = ctk.CTkFrame(self._relatorio_body, fg_color="transparent")
        cols.pack(fill="x")
        estoque = ctk.CTkFrame(cols, fg_color="transparent")
        estoque.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(estoque, text="Estoque disponível por cidade",
                     font=font(12, "bold"), text_color=TEXT).pack(anchor="w", pady=4)
        for row in dados["estoque_cidades"][:6]:
            ctk.CTkLabel(estoque,
                         text=f"{row['cidade']}  ·  {row['quantidade']} imóvel(is)  ·  {fmt_brl(row['valor'])}",
                         font=font(11), text_color=MUTED, anchor="w"
                         ).pack(fill="x", pady=2)
        contratos = ctk.CTkFrame(cols, fg_color="transparent")
        contratos.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(contratos, text="Contratos com término previsto",
                     font=font(12, "bold"), text_color=TEXT).pack(anchor="w", pady=4)
        for row in dados["contratos_vencendo"][:6]:
            ctk.CTkLabel(contratos,
                         text=f"{row['codigo']} · {row['imovel_codigo']} · {fmt_date(row['fim'])}",
                         font=font(11), text_color=MUTED, anchor="w"
                         ).pack(fill="x", pady=2)
        if not dados["contratos_vencendo"]:
            ctk.CTkLabel(contratos, text="Nenhum término previsto no período.",
                         font=font(11), text_color=MUTED).pack(anchor="w", pady=2)

    def _exportar_relatorio(self):
        """Salva o relatório atual em CSV compatível com Excel."""
        dados = dao.relatorio_operacional(int(self._periodo_relatorio.get()))
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Exportar relatório operacional",
            defaultextension=".csv", initialfile="relatorio-operacional.csv",
            filetypes=[("Planilha CSV", "*.csv")])
        if not caminho:
            return
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.writer(arquivo, delimiter=";")
                writer.writerow(["Relatório operacional ImóvelPro"])
                writer.writerow(["Contratos a vencer nos próximos dias", dados["periodo"]])
                writer.writerow(["Imóveis disponíveis", dados["disponiveis"]])
                writer.writerow(["Boletos vencidos", dados["boletos_vencidos"]["quantidade"], dados["boletos_vencidos"]["valor"]])
                writer.writerow([])
                writer.writerow(["Estoque disponível por cidade", "Quantidade", "Valor aproximado"])
                for row in dados["estoque_cidades"]:
                    writer.writerow([row["cidade"], row["quantidade"], row["valor"]])
                writer.writerow([])
                writer.writerow(["Contratos a vencer", "Tipo", "Imóvel", "Bairro", "Cidade", "Fim previsto"])
                for row in dados["contratos_vencendo"]:
                    writer.writerow([row["codigo"], row["tipo"], row["imovel_codigo"], row["bairro"], row["cidade"], row["fim"]])
            toast = getattr(self.winfo_toplevel(), "_toast", None)
            if toast:
                toast.show("Relatório exportado com sucesso.")
        except OSError as exc:
            toast = getattr(self.winfo_toplevel(), "_toast", None)
            if toast:
                toast.show(f"Não foi possível exportar: {exc}", error=True)
