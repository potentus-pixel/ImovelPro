from database import get_conn
import datetime


# ── CLIENTES ────────────────────────────────────────────────
def listar_clientes(filtro="", perfil=""):
    """Consulta e devolve a lista de clientes, aplicando os filtros informados."""
    conn = get_conn()
    q = """
        SELECT c.*, GROUP_CONCAT(t.telefone, ' | ') AS telefones
        FROM cliente c
        LEFT JOIN cliente_telefone t ON t.cliente_id = c.id
        WHERE (c.nome LIKE ? OR c.cpf LIKE ? OR c.codigo LIKE ?)
    """
    params = [f"%{filtro}%", f"%{filtro}%", f"%{filtro}%"]
    if perfil:
        q += " AND (c.perfil = ? OR c.perfil = 'ambos')"
        params.append(perfil)
    q += " GROUP BY c.id ORDER BY c.nome"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_cliente(id_):
    """Consulta e devolve o cliente correspondente ao identificador informado."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM cliente WHERE id=?", (id_,)).fetchone()
    tels = [r["telefone"] for r in conn.execute(
        "SELECT telefone FROM cliente_telefone WHERE cliente_id=?", (id_,)).fetchall()]
    conn.close()
    return row, tels


def salvar_cliente(data, tels, id_=None):
    """Insere ou atualiza o cliente e devolve o resultado da operação."""
    conn = get_conn()
    try:
        if id_:
            conn.execute(
                "UPDATE cliente SET codigo=?,nome=?,cpf=?,perfil=? WHERE id=?",
                (data["codigo"], data["nome"], data["cpf"], data["perfil"], id_))
            conn.execute("DELETE FROM cliente_telefone WHERE cliente_id=?", (id_,))
        else:
            cur = conn.execute(
                "INSERT INTO cliente(codigo,nome,cpf,perfil) VALUES(?,?,?,?)",
                (data["codigo"], data["nome"], data["cpf"], data["perfil"]))
            id_ = cur.lastrowid
        conn.executemany(
            "INSERT INTO cliente_telefone(cliente_id,telefone) VALUES(?,?)",
            [(id_, t) for t in tels])
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def excluir_cliente(id_):
    """Exclui o cliente, tratando falhas de integridade ou persistência."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM cliente WHERE id=?", (id_,))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def proximo_codigo_cliente():
    """Gera o próximo código sequencial de o cliente."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM cliente").fetchone()[0]
    conn.close()
    return f"CLI-{n+1:04d}"


# ── CORRETORES ───────────────────────────────────────────────
def listar_corretores(filtro=""):
    """Consulta e devolve a lista de corretores, aplicando os filtros informados."""
    conn = get_conn()
    q = """
        SELECT c.*, GROUP_CONCAT(t.telefone, ' | ') AS telefones
        FROM corretor c
        LEFT JOIN corretor_telefone t ON t.corretor_id = c.id
        WHERE c.nome LIKE ? OR c.cpf LIKE ? OR c.creci LIKE ?
        GROUP BY c.id ORDER BY c.nome
    """
    rows = conn.execute(q, [f"%{filtro}%"]*3).fetchall()
    conn.close()
    return rows


def get_corretor(id_):
    """Consulta e devolve o corretor correspondente ao identificador informado."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM corretor WHERE id=?", (id_,)).fetchone()
    tels = [r["telefone"] for r in conn.execute(
        "SELECT telefone FROM corretor_telefone WHERE corretor_id=?", (id_,)).fetchall()]
    conn.close()
    return row, tels


def salvar_corretor(data, tels, id_=None):
    """Insere ou atualiza o corretor e devolve o resultado da operação."""
    conn = get_conn()
    try:
        if id_:
            conn.execute(
                "UPDATE corretor SET nome=?,cpf=?,creci=? WHERE id=?",
                (data["nome"], data["cpf"], data["creci"], id_))
            conn.execute("DELETE FROM corretor_telefone WHERE corretor_id=?", (id_,))
        else:
            cur = conn.execute(
                "INSERT INTO corretor(nome,cpf,creci) VALUES(?,?,?)",
                (data["nome"], data["cpf"], data["creci"]))
            id_ = cur.lastrowid
        conn.executemany(
            "INSERT INTO corretor_telefone(corretor_id,telefone) VALUES(?,?)",
            [(id_, t) for t in tels])
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def excluir_corretor(id_):
    """Exclui o corretor, tratando falhas de integridade ou persistência."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM corretor WHERE id=?", (id_,))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def todos_corretores():
    """Consulta todos os corretores disponíveis para seleção."""
    conn = get_conn()
    rows = conn.execute("SELECT id, nome, creci FROM corretor ORDER BY nome").fetchall()
    conn.close()
    return rows


# ── IMÓVEIS ──────────────────────────────────────────────────
def listar_imoveis(filtro="", categoria="", finalidade="", status="",
                   cidade="", preco_min=None, preco_max=None,
                   ordenar="codigo"):
    """Consulta e devolve a lista de imóveis, aplicando os filtros informados."""
    conn = get_conn()
    q = """
        SELECT i.*,
               GROUP_CONCAT(c.nome, ' | ') AS proprietarios,
               GROUP_CONCAT(ip.percentual, ' | ') AS percentuais
        FROM imovel i
        LEFT JOIN imovel_proprietario ip ON ip.imovel_id = i.id
        LEFT JOIN cliente c ON c.id = ip.cliente_id
        WHERE (i.codigo LIKE ? OR i.rua LIKE ? OR i.bairro LIKE ? OR i.cidade LIKE ?)
    """
    params = [f"%{filtro}%"]*4
    if categoria:
        q += " AND i.categoria=?"; params.append(categoria)
    if finalidade:
        q += " AND (i.finalidade=? OR i.finalidade='ambos')"; params.append(finalidade)
    if status:
        q += " AND i.status=?"; params.append(status)
    if cidade:
        q += " AND i.cidade LIKE ?"; params.append(f"%{cidade}%")
    if preco_min is not None:
        q += " AND COALESCE(i.preco_venda,i.preco_aluguel,0)>=?"; params.append(preco_min)
    if preco_max is not None:
        q += " AND COALESCE(i.preco_venda,i.preco_aluguel,0)<=?"; params.append(preco_max)
    order_by = {
        "codigo": "i.codigo COLLATE NOCASE",
        "recentes": "i.id DESC",
        "menor_preco": "COALESCE(i.preco_venda,i.preco_aluguel,0), i.codigo",
        "maior_preco": "COALESCE(i.preco_venda,i.preco_aluguel,0) DESC, i.codigo",
        "maior_area": "i.area DESC, i.codigo",
    }.get(ordenar, "i.codigo COLLATE NOCASE")
    q += f" GROUP BY i.id ORDER BY {order_by}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_imovel(id_):
    """Consulta e devolve o imóvel correspondente ao identificador informado."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM imovel WHERE id=?", (id_,)).fetchone()
    props = conn.execute("""
        SELECT ip.cliente_id, ip.percentual, c.nome
        FROM imovel_proprietario ip JOIN cliente c ON c.id=ip.cliente_id
        WHERE ip.imovel_id=?""", (id_,)).fetchall()
    conn.close()
    return row, props


def salvar_imovel(data, props, id_=None):
    """Insere ou atualiza o imóvel e devolve o resultado da operação."""
    conn = get_conn()
    try:
        cols = "codigo,categoria,subtipo,area,rua,numero,bairro,cidade,finalidade,preco_venda,preco_aluguel"
        vals = (data["codigo"], data["categoria"], data["subtipo"], data["area"],
                data["rua"], data.get("numero"), data["bairro"], data["cidade"],
                data["finalidade"],
                data.get("preco_venda"), data.get("preco_aluguel"))
        if id_:
            conn.execute(f"UPDATE imovel SET {','.join(f'{k}=?' for k in cols.split(','))} WHERE id=?",
                         vals + (id_,))
            conn.execute("DELETE FROM imovel_proprietario WHERE imovel_id=?", (id_,))
        else:
            cur = conn.execute(f"INSERT INTO imovel({cols}) VALUES(?,?,?,?,?,?,?,?,?,?,?)", vals)
            id_ = cur.lastrowid
        conn.executemany(
            "INSERT INTO imovel_proprietario(imovel_id,cliente_id,percentual) VALUES(?,?,?)",
            [(id_, p["cliente_id"], p["percentual"]) for p in props])
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def excluir_imovel(id_):
    """Exclui o imóvel, tratando falhas de integridade ou persistência."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM imovel WHERE id=?", (id_,))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def todos_imoveis():
    """Consulta todos os imóveis disponíveis para seleção."""
    conn = get_conn()
    rows = conn.execute("SELECT id, codigo, subtipo, bairro FROM imovel ORDER BY codigo").fetchall()
    conn.close()
    return rows


def imoveis_por_cliente(cliente_id):
    """Imóveis dos quais o cliente é proprietário (tabela imovel_proprietario)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT i.id, i.codigo, i.subtipo, i.bairro
           FROM imovel i
           JOIN imovel_proprietario ip ON ip.imovel_id = i.id
           WHERE ip.cliente_id = ?
           ORDER BY i.codigo""",
        (cliente_id,)).fetchall()
    conn.close()
    return rows


def proximo_codigo_imovel():
    """Gera o próximo código sequencial de o imóvel."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM imovel").fetchone()[0]
    conn.close()
    return f"IM-{n+1:04d}"


def get_imovel_id_by_codigo(codigo):
    """Localiza e devolve o identificador do imóvel a partir de seu código."""
    conn = get_conn()
    row = conn.execute("SELECT id FROM imovel WHERE codigo=?",
                       (codigo,)).fetchone()
    conn.close()
    return row[0] if row else None


# ── FOTOS DO IMÓVEL ──────────────────────────────────────────
def get_fotos(imovel_id):
    """Consulta e devolve fotos correspondente ao identificador informado."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, caminho, legenda, ordem FROM imovel_foto "
        "WHERE imovel_id=? ORDER BY ordem, id",
        (imovel_id,)).fetchall()
    conn.close()
    return rows


def contratos_por_imovel(imovel_id):
    """Lista todos os contratos de um imóvel (para a página de detalhes)."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT ct.*,
                  GROUP_CONCAT(DISTINCT ca.nome) AS adquirentes
           FROM contrato ct
           LEFT JOIN contrato_adquirente caq ON caq.contrato_id = ct.id
           LEFT JOIN cliente ca ON ca.id = caq.cliente_id
           WHERE ct.imovel_id = ?
           GROUP BY ct.id
           ORDER BY ct.situacao != 'encerrado', ct.id DESC""",
        (imovel_id,)).fetchall()
    conn.close()
    return rows


def adicionar_foto(imovel_id, caminho, legenda=""):
    """Adiciona a foto e atualiza os dados relacionados."""
    conn = get_conn()
    try:
        ordem = conn.execute(
            "SELECT COALESCE(MAX(ordem),0)+1 FROM imovel_foto WHERE imovel_id=?",
            (imovel_id,)).fetchone()[0]
        conn.execute(
            "INSERT INTO imovel_foto(imovel_id,caminho,legenda,ordem) VALUES(?,?,?,?)",
            (imovel_id, caminho, legenda, ordem))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def remover_foto(foto_id):
    """Remove a foto e atualiza os dados relacionados."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM imovel_foto WHERE id=?", (foto_id,))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def recalcular_status_imovel(imovel_id):
    """Recalcula e persiste a situação do imóvel com base em seus contratos."""
    import database
    conn = get_conn()
    try:
        status = database.recalcular_status(conn, imovel_id)
        conn.commit()
        return status
    finally:
        conn.close()


# ── GERAÇÃO AUTOMÁTICA DE BOLETOS ─────────────────────────
def gerar_boletos_contrato(contrato_id):
    """Gera os boletos de um contrato conforme o tipo:

    - venda: 1 boleto de comissão (à vista sobre o valor da comissão)
             + parcelas mensais do saldo (valor - entrada) / num_parcelas
    - aluguel: boletos mensais de aluguel pelo prazo (duracao_meses),
               vencendo todo mês no dia_vencimento, a partir da assinatura

    Retorna (criados, erro). Boletos já existentes não são duplicados.
    """
    import database
    conn = get_conn()
    try:
        ct = conn.execute(
            "SELECT * FROM contrato WHERE id=?", (contrato_id,)).fetchone()
        if not ct:
            return 0, "Contrato não encontrado."

        # boletos já existentes deste contrato: chave (tipo, vencimento)
        existentes = {
            (r[0], r[1])
            for r in conn.execute(
                "SELECT tipo, data_vencimento FROM boleto WHERE contrato_id=?",
                (contrato_id,)).fetchall()}

        novos = []
        if ct["tipo"] == "venda":
            # comissão (à vista)
            novos.append(("comissao", ct["data_assinatura"],
                          ct["comissao"]))
            # parcelas do saldo
            if ct["num_parcelas"] and ct["num_parcelas"] > 0:
                saldo = (ct["valor"] or 0) - (ct["valor_entrada"] or 0)
                parcela = round(saldo / ct["num_parcelas"], 2)
                base = datetime.date.fromisoformat(ct["data_assinatura"])
                for i in range(ct["num_parcelas"]):
                    venc = (base + datetime.timedelta(days=30 * (i + 1))).isoformat()
                    novos.append(("parcela", venc, parcela))
        else:  # aluguel
            if ct["duracao_meses"] and ct["duracao_meses"] > 0:
                base = datetime.date.fromisoformat(ct["data_assinatura"])
                dia = max(1, min(28, ct["dia_vencimento"] or 1))
                for i in range(ct["duracao_meses"]):
                    # mantém o dia de vencimento; trata fim de mês
                    m = base.month + (i + 1)
                    y = base.year + (m - 1) // 12
                    m = (m - 1) % 12 + 1
                    try:
                        venc = datetime.date(y, m, dia).isoformat()
                    except ValueError:
                        venc = datetime.date(y, m, 28).isoformat()
                    novos.append(("aluguel", venc, ct["valor"]))

        # inseri só os que ainda não existem (mesmo tipo + vencimento)
        criados = 0
        seq = conn.execute(
            "SELECT COALESCE(MAX(id),0) FROM boleto").fetchone()[0]
        for tipo, venc, valor in novos:
            if (tipo, venc) in existentes:
                continue
            seq += 1
            conn.execute(
                "INSERT INTO boleto(sequencial,contrato_id,tipo,situacao,"
                "valor,data_vencimento,data_pagamento) VALUES(?,?,?,?,?,?,?)",
                (f"BOL-{seq:04d}", contrato_id, tipo, "pendente",
                 valor, venc, None))
            criados += 1

        # recalcula o status do imóvel (o contrato virou vigente)
        database.recalcular_status(conn, ct["imovel_id"])
        conn.commit()
        return criados, ""
    except Exception as e:
        conn.rollback()
        return 0, str(e)
    finally:
        conn.close()


# ── CONTRATOS ────────────────────────────────────────────────
def listar_contratos(filtro="", tipo="", situacao=""):
    """Consulta e devolve a lista de contratos, aplicando os filtros informados."""
    conn = get_conn()
    q = """
        SELECT ct.*,
               im.codigo AS im_codigo, im.subtipo AS im_subtipo, im.bairro AS im_bairro,
               GROUP_CONCAT(DISTINCT ca.nome) AS adquirentes,
               GROUP_CONCAT(DISTINCT cc.nome) AS cedentes,
               GROUP_CONCAT(DISTINCT cr.nome) AS corretores
        FROM contrato ct
        JOIN imovel im ON im.id = ct.imovel_id
        LEFT JOIN contrato_adquirente caq ON caq.contrato_id = ct.id
        LEFT JOIN cliente ca ON ca.id = caq.cliente_id
        LEFT JOIN contrato_cedente cce ON cce.contrato_id = ct.id
        LEFT JOIN cliente cc ON cc.id = cce.cliente_id
        LEFT JOIN contrato_corretor ccr ON ccr.contrato_id = ct.id
        LEFT JOIN corretor cr ON cr.id = ccr.corretor_id
        WHERE (ct.codigo LIKE ? OR im.codigo LIKE ? OR im.bairro LIKE ?)
    """
    params = [f"%{filtro}%"]*3
    if tipo:
        q += " AND ct.tipo=?"; params.append(tipo)
    if situacao:
        q += " AND ct.situacao=?"; params.append(situacao)
    q += " GROUP BY ct.id ORDER BY ct.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_contrato(id_):
    """Consulta e devolve o contrato correspondente ao identificador informado."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM contrato WHERE id=?", (id_,)).fetchone()
    adqs = conn.execute("""
        SELECT ca.cliente_id, c.nome FROM contrato_adquirente ca
        JOIN cliente c ON c.id=ca.cliente_id WHERE ca.contrato_id=?""", (id_,)).fetchall()
    ceds = conn.execute("""
        SELECT cc.cliente_id, c.nome FROM contrato_cedente cc
        JOIN cliente c ON c.id=cc.cliente_id WHERE cc.contrato_id=?""", (id_,)).fetchall()
    corrs = conn.execute("""
        SELECT ccr.corretor_id, cr.nome, ccr.percentual FROM contrato_corretor ccr
        JOIN corretor cr ON cr.id=ccr.corretor_id WHERE ccr.contrato_id=?""", (id_,)).fetchall()
    conn.close()
    return row, adqs, ceds, corrs


def salvar_contrato(data, adqs, ceds, corrs, id_=None):
    """Insere ou atualiza o contrato e devolve o resultado da operação."""
    conn = get_conn()
    try:
        cols = ("codigo,tipo,valor,comissao,data_assinatura,situacao,imovel_id,"
                "valor_entrada,num_parcelas,duracao_meses,dia_vencimento")
        vals = (data["codigo"], data["tipo"], data["valor"], data["comissao"],
                data["data_assinatura"], data["situacao"], data["imovel_id"],
                data.get("valor_entrada"), data.get("num_parcelas"),
                data.get("duracao_meses"), data.get("dia_vencimento"))
        if id_:
            conn.execute(
                f"UPDATE contrato SET {','.join(f'{k}=?' for k in cols.split(','))} WHERE id=?",
                vals + (id_,))
            conn.execute("DELETE FROM contrato_adquirente WHERE contrato_id=?", (id_,))
            conn.execute("DELETE FROM contrato_cedente WHERE contrato_id=?", (id_,))
            conn.execute("DELETE FROM contrato_corretor WHERE contrato_id=?", (id_,))
        else:
            cur = conn.execute(
                f"INSERT INTO contrato({cols}) VALUES(?,?,?,?,?,?,?,?,?,?,?)", vals)
            id_ = cur.lastrowid
        conn.executemany("INSERT INTO contrato_adquirente VALUES(?,?)",
                         [(id_, a) for a in adqs])
        conn.executemany("INSERT INTO contrato_cedente VALUES(?,?)",
                         [(id_, a) for a in ceds])
        conn.executemany("INSERT INTO contrato_corretor VALUES(?,?,?)",
                         [(id_, r["corretor_id"], r["percentual"]) for r in corrs])
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def excluir_contrato(id_):
    """Exclui o contrato, tratando falhas de integridade ou persistência."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM contrato WHERE id=?", (id_,))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def todos_contratos():
    """Consulta todos os contratos disponíveis para seleção."""
    conn = get_conn()
    rows = conn.execute("SELECT id, codigo, tipo FROM contrato ORDER BY codigo").fetchall()
    conn.close()
    return rows


def proximo_codigo_contrato():
    """Gera o próximo código sequencial de o contrato."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM contrato").fetchone()[0]
    conn.close()
    return f"CT-{n+1:04d}"


# ── BOLETOS ──────────────────────────────────────────────────
def _atualizar_situacoes_boletos(conn):
    """Sincroniza somente boletos cuja situação realmente mudou."""
    conn.execute("""
        UPDATE boleto
           SET situacao = CASE
               WHEN data_pagamento IS NOT NULL AND TRIM(data_pagamento) <> ''
                   THEN 'pago'
               WHEN date(data_vencimento) < date('now', 'localtime')
                   THEN 'vencido'
               ELSE 'pendente'
           END
         WHERE situacao <> CASE
               WHEN data_pagamento IS NOT NULL AND TRIM(data_pagamento) <> ''
                   THEN 'pago'
               WHEN date(data_vencimento) < date('now', 'localtime')
                   THEN 'vencido'
               ELSE 'pendente'
           END
    """)
    if conn.total_changes:
        conn.commit()


def listar_boletos(filtro="", tipo="", situacao=""):
    """Consulta e devolve a lista de boletos, aplicando os filtros informados."""
    conn = get_conn()
    _atualizar_situacoes_boletos(conn)
    q = """
        SELECT b.*, ct.codigo AS ct_codigo
        FROM boleto b
        JOIN contrato ct ON ct.id = b.contrato_id
        WHERE (b.sequencial LIKE ? OR ct.codigo LIKE ?)
    """
    params = [f"%{filtro}%", f"%{filtro}%"]
    if tipo:
        q += " AND b.tipo=?"; params.append(tipo)
    if situacao:
        q += " AND b.situacao=?"; params.append(situacao)
    q += " ORDER BY b.data_vencimento DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_boleto(id_):
    """Consulta e devolve o boleto correspondente ao identificador informado."""
    conn = get_conn()
    _atualizar_situacoes_boletos(conn)
    row = conn.execute("SELECT * FROM boleto WHERE id=?", (id_,)).fetchone()
    conn.close()
    return row


def salvar_boleto(data, id_=None):
    """Insere ou atualiza o boleto e devolve o resultado da operação."""
    conn = get_conn()
    try:
        from datetime import date
        vencimento = date.fromisoformat(data["data_vencimento"])
        pagamento_txt = data.get("data_pagamento")
        if pagamento_txt:
            date.fromisoformat(pagamento_txt)
            situacao = "pago"
        elif vencimento < date.today():
            situacao = "vencido"
        else:
            situacao = "pendente"
        cols = "sequencial,contrato_id,tipo,situacao,valor,data_vencimento,data_pagamento"
        vals = (data["sequencial"], data["contrato_id"], data["tipo"], situacao,
                data["valor"], data["data_vencimento"], data.get("data_pagamento"))
        if id_:
            conn.execute(
                f"UPDATE boleto SET {','.join(f'{k}=?' for k in cols.split(','))} WHERE id=?",
                vals + (id_,))
        else:
            conn.execute(f"INSERT INTO boleto({cols}) VALUES(?,?,?,?,?,?,?)", vals)
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def excluir_boleto(id_):
    """Exclui o boleto, tratando falhas de integridade ou persistência."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM boleto WHERE id=?", (id_,))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def proximo_sequencial_boleto():
    """Calcula o próximo número sequencial de o boleto."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM boleto").fetchone()[0]
    conn.close()
    return f"BOL-{n+1:04d}"


# ── DASHBOARD ────────────────────────────────────────────────
def kpis():
    """Calcula os indicadores numéricos apresentados no dashboard."""
    conn = get_conn()
    _atualizar_situacoes_boletos(conn)
    d = {
        "imoveis":   conn.execute("SELECT COUNT(*) FROM imovel").fetchone()[0],
        "clientes":  conn.execute("SELECT COUNT(*) FROM cliente").fetchone()[0],
        "corretores":conn.execute("SELECT COUNT(*) FROM corretor").fetchone()[0],
        "contratos_ativos": conn.execute(
            "SELECT COUNT(*) FROM contrato WHERE situacao != 'encerrado'").fetchone()[0],
        "boletos_pendentes": conn.execute(
            "SELECT COUNT(*) FROM boleto WHERE situacao='pendente'").fetchone()[0],
        "boletos_vencidos":  conn.execute(
            "SELECT COUNT(*) FROM boleto WHERE situacao='vencido'").fetchone()[0],
        "comissao_receber":  conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM boleto WHERE situacao='pendente' AND tipo='comissao'").fetchone()[0],
    }
    conn.close()
    return d


def ultimos_contratos(n=5):
    """Consulta os contratos mais recentes para exibição no dashboard."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT ct.codigo, ct.tipo, ct.situacao, ct.valor,
               GROUP_CONCAT(DISTINCT ca.nome) AS adquirentes,
               im.subtipo AS im_subtipo, im.bairro AS im_bairro
        FROM contrato ct
        JOIN imovel im ON im.id=ct.imovel_id
        LEFT JOIN contrato_adquirente caq ON caq.contrato_id=ct.id
        LEFT JOIN cliente ca ON ca.id=caq.cliente_id
        GROUP BY ct.id ORDER BY ct.id DESC LIMIT ?""", (n,)).fetchall()
    conn.close()
    return rows


def alertas():
    """Monta a lista de alertas operacionais que requerem atenção."""
    conn = get_conn()
    _atualizar_situacoes_boletos(conn)
    rows = conn.execute("""
        SELECT b.sequencial, b.situacao, b.valor, b.data_vencimento, ct.codigo AS ct_codigo
        FROM boleto b JOIN contrato ct ON ct.id=b.contrato_id
        WHERE b.situacao IN ('pendente','vencido')
        ORDER BY b.situacao DESC, b.data_vencimento LIMIT 8""").fetchall()
    conn.close()
    return rows


# ── GRÁFICOS DO DASHBOARD ──────────────────────────────────
def graf_imovel_status():
    """Contagem de imóveis por status."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM imovel GROUP BY status").fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def graf_contrato_tipo():
    """Agrupa contratos por tipo para alimentar o gráfico correspondente."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT tipo, COUNT(*) FROM contrato GROUP BY tipo").fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def graf_boleto_situacao():
    """Agrupa boletos por situação para alimentar o gráfico correspondente."""
    conn = get_conn()
    _atualizar_situacoes_boletos(conn)
    rows = conn.execute(
        "SELECT situacao, COUNT(*) FROM boleto GROUP BY situacao").fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def graf_finalidade():
    """Agrupa imóveis por finalidade para alimentar o gráfico correspondente."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT finalidade, COUNT(*) FROM imovel GROUP BY finalidade").fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def dashboard_snapshot():
    """Carrega todos os dados do dashboard usando uma única conexão."""
    conn = get_conn()
    try:
        _atualizar_situacoes_boletos(conn)
        kpi_row = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM imovel) AS imoveis,
                (SELECT COUNT(*) FROM cliente) AS clientes,
                (SELECT COUNT(*) FROM corretor) AS corretores,
                (SELECT COUNT(*) FROM contrato
                   WHERE situacao != 'encerrado') AS contratos_ativos,
                (SELECT COUNT(*) FROM boleto
                   WHERE situacao = 'pendente') AS boletos_pendentes,
                (SELECT COUNT(*) FROM boleto
                   WHERE situacao = 'vencido') AS boletos_vencidos,
                (SELECT COALESCE(SUM(valor), 0) FROM boleto
                   WHERE situacao = 'pendente'
                     AND tipo = 'comissao') AS comissao_receber
        """).fetchone()

        contratos = conn.execute("""
            SELECT ct.codigo, ct.tipo, ct.situacao, ct.valor,
                   GROUP_CONCAT(DISTINCT ca.nome) AS adquirentes,
                   im.subtipo AS im_subtipo, im.bairro AS im_bairro
            FROM contrato ct
            JOIN imovel im ON im.id = ct.imovel_id
            LEFT JOIN contrato_adquirente caq ON caq.contrato_id = ct.id
            LEFT JOIN cliente ca ON ca.id = caq.cliente_id
            GROUP BY ct.id ORDER BY ct.id DESC LIMIT 6
        """).fetchall()

        alertas_rows = conn.execute("""
            SELECT b.sequencial, b.situacao, b.valor, b.data_vencimento,
                   ct.codigo AS ct_codigo
            FROM boleto b JOIN contrato ct ON ct.id = b.contrato_id
            WHERE b.situacao IN ('pendente', 'vencido')
            ORDER BY b.situacao DESC, b.data_vencimento LIMIT 8
        """).fetchall()

        def agrupado(sql):
            """Agrupa os registros da consulta pela chave esperada pelo relatório."""
            return [(r[0], r[1]) for r in conn.execute(sql).fetchall()]

        return {
            "kpis": dict(kpi_row),
            "contratos": [dict(r) for r in contratos],
            "alertas": [dict(r) for r in alertas_rows],
            "graf_status": agrupado(
                "SELECT status, COUNT(*) FROM imovel GROUP BY status"),
            "graf_finalidade": agrupado(
                "SELECT finalidade, COUNT(*) FROM imovel GROUP BY finalidade"),
            "graf_tipo": agrupado(
                "SELECT tipo, COUNT(*) FROM contrato GROUP BY tipo"),
            "graf_boleto": agrupado(
                "SELECT situacao, COUNT(*) FROM boleto GROUP BY situacao"),
        }
    finally:
        conn.close()


def relatorio_operacional(periodo=30):
    """Resume estoque disponível, contratos próximos do fim e inadimplência."""
    periodo = max(1, min(int(periodo), 365))
    hoje = datetime.date.today()
    limite = hoje + datetime.timedelta(days=periodo)
    conn = get_conn()
    try:
        estoque = conn.execute("""
            SELECT cidade, COUNT(*) AS quantidade,
                   COALESCE(SUM(COALESCE(preco_venda,preco_aluguel)),0) AS valor
            FROM imovel WHERE status='disponivel'
            GROUP BY cidade ORDER BY quantidade DESC, cidade
        """).fetchall()
        vencendo = conn.execute("""
            SELECT ct.codigo, ct.tipo, im.codigo AS imovel_codigo,
                   im.cidade, im.bairro,
                   date(ct.data_assinatura, '+' || ct.duracao_meses || ' months') AS fim
            FROM contrato ct JOIN imovel im ON im.id=ct.imovel_id
            WHERE ct.situacao='ativo' AND ct.duracao_meses IS NOT NULL
              AND date(ct.data_assinatura, '+' || ct.duracao_meses || ' months')
                  BETWEEN ? AND ?
            ORDER BY fim LIMIT 30
        """, (hoje.isoformat(), limite.isoformat())).fetchall()
        boletos = conn.execute("""
            SELECT COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS valor
            FROM boleto WHERE situacao='vencido'
        """).fetchone()
        disponiveis = conn.execute(
            "SELECT COUNT(*) FROM imovel WHERE status='disponivel'").fetchone()[0]
        return {
            "periodo": periodo, "disponiveis": disponiveis,
            "estoque_cidades": [dict(row) for row in estoque],
            "contratos_vencendo": [dict(row) for row in vencendo],
            "boletos_vencidos": dict(boletos),
        }
    finally:
        conn.close()
