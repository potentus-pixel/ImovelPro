import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "imovel_pro.db")


def get_conn():
    """Abre e configura uma conexão com o banco SQLite da aplicação."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas do banco de dados e executa a carga inicial necessária."""
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS cliente (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo  TEXT NOT NULL UNIQUE,
        nome    TEXT NOT NULL,
        cpf     TEXT NOT NULL UNIQUE,
        perfil  TEXT NOT NULL CHECK(perfil IN ('dono','interessado','ambos'))
    );
    CREATE TABLE IF NOT EXISTS cliente_telefone (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL REFERENCES cliente(id) ON DELETE CASCADE,
        telefone   TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS corretor (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        nome  TEXT NOT NULL,
        cpf   TEXT NOT NULL UNIQUE,
        creci TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS corretor_telefone (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        corretor_id INTEGER NOT NULL REFERENCES corretor(id) ON DELETE CASCADE,
        telefone    TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS imovel (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo        TEXT NOT NULL UNIQUE,
        categoria     TEXT NOT NULL CHECK(categoria IN ('Urbano','Rural')),
        subtipo       TEXT NOT NULL,
        area          REAL NOT NULL,
        rua           TEXT NOT NULL,
        numero        TEXT,
        bairro        TEXT NOT NULL,
        cidade        TEXT NOT NULL,
        finalidade    TEXT NOT NULL CHECK(finalidade IN ('venda','aluguel','ambos')),
        preco_venda   REAL,
        preco_aluguel REAL,
        status        TEXT NOT NULL DEFAULT 'disponivel'
                      CHECK(status IN ('disponivel','em negociacao','alugado','vendido'))
    );
    CREATE TABLE IF NOT EXISTS imovel_proprietario (
        imovel_id  INTEGER NOT NULL REFERENCES imovel(id) ON DELETE CASCADE,
        cliente_id INTEGER NOT NULL REFERENCES cliente(id) ON DELETE RESTRICT,
        percentual REAL NOT NULL DEFAULT 100,
        PRIMARY KEY (imovel_id, cliente_id)
    );
    CREATE TABLE IF NOT EXISTS imovel_foto (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        imovel_id INTEGER NOT NULL REFERENCES imovel(id) ON DELETE CASCADE,
        caminho   TEXT NOT NULL,
        legenda   TEXT,
        ordem     INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS contrato (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo          TEXT NOT NULL UNIQUE,
        tipo            TEXT NOT NULL CHECK(tipo IN ('venda','aluguel')),
        valor           REAL NOT NULL,
        comissao        REAL NOT NULL,
        data_assinatura TEXT NOT NULL,
        situacao        TEXT NOT NULL CHECK(situacao IN ('em espera','ativo','encerrado')),
        imovel_id       INTEGER NOT NULL REFERENCES imovel(id) ON DELETE RESTRICT,
        valor_entrada   REAL,
        num_parcelas    INTEGER,
        duracao_meses   INTEGER,
        dia_vencimento  INTEGER
    );
    CREATE TABLE IF NOT EXISTS contrato_adquirente (
        contrato_id INTEGER NOT NULL REFERENCES contrato(id) ON DELETE CASCADE,
        cliente_id  INTEGER NOT NULL REFERENCES cliente(id) ON DELETE RESTRICT,
        PRIMARY KEY (contrato_id, cliente_id)
    );
    CREATE TABLE IF NOT EXISTS contrato_cedente (
        contrato_id INTEGER NOT NULL REFERENCES contrato(id) ON DELETE CASCADE,
        cliente_id  INTEGER NOT NULL REFERENCES cliente(id) ON DELETE RESTRICT,
        PRIMARY KEY (contrato_id, cliente_id)
    );
    CREATE TABLE IF NOT EXISTS contrato_corretor (
        contrato_id INTEGER NOT NULL REFERENCES contrato(id) ON DELETE CASCADE,
        corretor_id INTEGER NOT NULL REFERENCES corretor(id) ON DELETE RESTRICT,
        percentual  REAL NOT NULL DEFAULT 100,
        PRIMARY KEY (contrato_id, corretor_id)
    );
    CREATE TABLE IF NOT EXISTS boleto (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        sequencial      TEXT NOT NULL UNIQUE,
        contrato_id     INTEGER NOT NULL REFERENCES contrato(id) ON DELETE CASCADE,
        tipo            TEXT NOT NULL CHECK(tipo IN ('comissao','parcela','aluguel')),
        situacao        TEXT NOT NULL CHECK(situacao IN ('pendente','pago','vencido')),
        valor           REAL NOT NULL,
        data_vencimento TEXT NOT NULL,
        data_pagamento  TEXT
    );
    """)

    if c.execute("SELECT COUNT(*) FROM cliente").fetchone()[0] == 0:
        _seed(c)

    _migrar(c)

    conn.commit()
    conn.close()


def _migrar(c):
    """Aplica migrações em bancos já existentes (colunas/tabelas novas)."""
    # status no imovel
    cols = [r[1] for r in c.execute("PRAGMA table_info(imovel)")]
    if "status" not in cols:
        c.execute("ALTER TABLE imovel ADD COLUMN status TEXT NOT NULL DEFAULT 'disponivel'")
    # numero do imóvel (parte do endereço)
    if "numero" not in cols:
        c.execute("ALTER TABLE imovel ADD COLUMN numero TEXT")
    # tabela de fotos
    c.execute("""CREATE TABLE IF NOT EXISTS imovel_foto (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        imovel_id INTEGER NOT NULL REFERENCES imovel(id) ON DELETE CASCADE,
        caminho   TEXT NOT NULL,
        legenda   TEXT,
        ordem     INTEGER NOT NULL DEFAULT 0
    )""")
    # recalcula status de todos os imóveis
    for row in c.execute("SELECT id FROM imovel").fetchall():
        recalcular_status(c, row[0])


def recalcular_status(c, imovel_id):
    """Recalcula o status do imóvel com base nos contratos vigentes.

    Regras:
      - contrato de venda ativo         -> 'vendido'
      - aluguel ativo                   -> 'alugado'
      - qualquer contrato 'em espera'   -> 'em negociacao'
      - nenhum contrato vigente         -> 'disponivel'
    Precedência: vendido > alugado > em negociacao > disponivel.
    """
    vig = c.execute(
        """SELECT ct.tipo, ct.situacao
           FROM contrato ct
           WHERE ct.imovel_id = ? AND ct.situacao IN ('ativo','em espera')""",
        (imovel_id,)).fetchall()

    status = "disponivel"
    if any(v[1] == "ativo" and v[0] == "venda" for v in vig):
        status = "vendido"
    elif any(v[1] == "ativo" and v[0] == "aluguel" for v in vig):
        status = "alugado"
    elif any(v[1] == "em espera" for v in vig):
        status = "em negociacao"

    c.execute("UPDATE imovel SET status = ? WHERE id = ?", (status, imovel_id))
    return status


def _seed(c):
    """Insere os dados iniciais somente quando o banco ainda está vazio."""
    clientes = [
        ("CLI-0001","Maria Clara Souza","111.222.333-44","ambos"),
        ("CLI-0002","Pedro Teixeira Lima","222.333.444-55","interessado"),
        ("CLI-0003","Ana Lima Ferreira","333.444.555-66","interessado"),
        ("CLI-0004","Roberto Freitas Costa","444.555.666-77","dono"),
        ("CLI-0005","Fernanda Souza Melo","555.666.777-88","ambos"),
        ("CLI-0006","Carlos Andrade","666.777.888-99","dono"),
    ]
    c.executemany("INSERT INTO cliente(codigo,nome,cpf,perfil) VALUES(?,?,?,?)", clientes)

    tels_cli = [(1,"(21) 98001-1111"),(2,"(21) 97002-2222"),(3,"(21) 96003-3333"),
                (3,"(21) 3001-9999"),(4,"(21) 95004-4444"),(5,"(21) 94005-5555"),(6,"(21) 93006-6666")]
    c.executemany("INSERT INTO cliente_telefone(cliente_id,telefone) VALUES(?,?)", tels_cli)

    corretores = [("João Corretor Silva","100.200.300-40","12345/RJ"),
                  ("Maria Santos Dias","200.300.400-50","23456/RJ"),
                  ("Carlos Mendes","300.400.500-60","34567/RJ")]
    c.executemany("INSERT INTO corretor(nome,cpf,creci) VALUES(?,?,?)", corretores)

    tels_cor = [(1,"(21) 99100-2000"),(2,"(21) 99200-3000"),(3,"(21) 99300-4000")]
    c.executemany("INSERT INTO corretor_telefone(corretor_id,telefone) VALUES(?,?)", tels_cor)

    imoveis = [
        ("IM-0001","Urbano","Apartamento",85,"Av. Atlântica, 302","Copacabana","Rio de Janeiro","aluguel",None,2800),
        ("IM-0002","Urbano","Casa",180,"Rua das Palmeiras, 5B","Botafogo","Rio de Janeiro","venda",485000,None),
        ("IM-0003","Urbano","Apartamento",45,"Rua do Catete, 12","Centro","Rio de Janeiro","aluguel",None,1500),
        ("IM-0004","Urbano","Terreno",400,"Av. das Américas, Lot.7","Barra da Tijuca","Rio de Janeiro","venda",120000,None),
        ("IM-0005","Rural","Fazenda",12000,"Estrada Velha, km 12","Zona Rural","Itaperuna","venda",1200000,None),
    ]
    c.executemany("INSERT INTO imovel(codigo,categoria,subtipo,area,rua,bairro,cidade,finalidade,preco_venda,preco_aluguel) VALUES(?,?,?,?,?,?,?,?,?,?)", imoveis)

    props = [(1,1,100),(2,4,70),(2,6,30),(3,6,100),(4,5,50),(4,1,50),(5,4,100)]
    c.executemany("INSERT INTO imovel_proprietario(imovel_id,cliente_id,percentual) VALUES(?,?,?)", props)

    contratos = [
        ("CT-0038","aluguel",2800,280,"2024-03-01","ativo",1,None,None,12,1),
        ("CT-0039","venda",485000,19400,"2024-04-15","ativo",2,50000,120,None,None),
        ("CT-0041","aluguel",1500,150,"2024-05-01","em espera",3,None,None,12,5),
        ("CT-0043","venda",120000,6000,"2024-01-10","encerrado",4,20000,60,None,None),
    ]
    c.executemany("INSERT INTO contrato(codigo,tipo,valor,comissao,data_assinatura,situacao,imovel_id,valor_entrada,num_parcelas,duracao_meses,dia_vencimento) VALUES(?,?,?,?,?,?,?,?,?,?,?)", contratos)

    c.executemany("INSERT INTO contrato_adquirente VALUES(?,?)", [(1,1),(2,2),(3,3),(4,2)])
    c.executemany("INSERT INTO contrato_cedente VALUES(?,?)",    [(1,1),(2,4),(2,6),(3,6),(4,5),(4,1)])
    c.executemany("INSERT INTO contrato_corretor VALUES(?,?,?)", [(1,1,100),(2,2,60),(2,1,40),(3,1,100),(4,3,100)])

    boletos = [
        ("BOL-0001",1,"aluguel","pago",2800,"2024-03-01","2024-02-28"),
        ("BOL-0002",1,"aluguel","pago",2800,"2024-04-01","2024-04-01"),
        ("BOL-0003",1,"aluguel","pendente",2800,"2024-05-01",None),
        ("BOL-0004",1,"comissao","pago",280,"2024-03-05","2024-03-05"),
        ("BOL-0005",2,"comissao","pendente",19400,"2024-05-01",None),
        ("BOL-0006",3,"comissao","vencido",150,"2024-05-10",None),
        ("BOL-0007",2,"parcela","pago",3625,"2024-05-15","2024-05-14"),
    ]
    c.executemany("INSERT INTO boleto(sequencial,contrato_id,tipo,situacao,valor,data_vencimento,data_pagamento) VALUES(?,?,?,?,?,?,?)", boletos)
