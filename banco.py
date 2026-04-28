import sqlite3


def conectar():
    return sqlite3.connect("oficina.db")

def criar_tabela_usuarios():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        login TEXT UNIQUE,
        senha TEXT,
        tipo TEXT,
        primeiro_acesso INTEGER DEFAULT 1
    )
    """)

    # 🔥 garante a coluna mesmo se tabela já existir
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN primeiro_acesso INTEGER DEFAULT 1")
    except:
        pass

    conn.commit()
    conn.close()

def criar_admin_padrao():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
    usuario = cursor.fetchone()

    if not usuario:
        cursor.execute("""
        INSERT INTO usuarios (nome, login, senha, tipo)
        VALUES (?, ?, ?, ?)
        """, ("Administrador", "admin", "1234", "admin"))

        print("✅ Usuário admin criado: login=admin senha=1234")

    conn.commit()
    conn.close()


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # 🔷 TABELA PRINCIPAL (ORDENS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        telefone TEXT,
        veiculo TEXT,
        placa TEXT,
        problema TEXT,
        diagnostico TEXT,
        total REAL,
        tipo TEXT,
        status TEXT DEFAULT 'EM ANDAMENTO',
        mecanico TEXT,
        data_entrada TEXT,
        data_saida TEXT,
        quilometragem INTEGER
    )
    """)

    # 🔧 GARANTIR COLUNAS (produção segura)
    try:
        cursor.execute("ALTER TABLE ordens ADD COLUMN telefone TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE ordens ADD COLUMN quilometragem INTEGER")
    except:
        pass

    # 🔷 ITENS (PEÇAS E SERVIÇOS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ordem_id INTEGER,
        tipo TEXT,
        nome TEXT,
        valor REAL,
        quantidade INTEGER,
        comissao INTEGER DEFAULT 0,
        estoque INTEGER DEFAULT 0
    )
    """)

    # 🔷 RECEITAS 💰
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem TEXT,
        ordem_id INTEGER,
        descricao TEXT,
        valor_original REAL,
        valor_final REAL,
        forma_pagamento TEXT,
        status TEXT,
        data TEXT
    )
    """)

    # 🔷 VÍDEOS (SITE)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        link TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 🔷 FOTOS (SITE)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fotos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        arquivo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# 🔥 =========================
# 🔷 FUNÇÕES DE RECEITAS
# 🔥 =========================

def inserir_receita(origem, ordem_id, descricao, valor_original, valor_final, forma, status, data):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO receitas (
        origem, ordem_id, descricao,
        valor_original, valor_final,
        forma_pagamento, status, data
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (origem, ordem_id, descricao, valor_original, valor_final, forma, status, data))

    conn.commit()
    conn.close()


def listar_receitas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM receitas
    ORDER BY 
    CASE 
        WHEN status = 'PENDENTE' THEN 1
        ELSE 2
    END,
    id DESC
    """)

    dados = cursor.fetchall()
    conn.close()

    return dados


def buscar_receita_por_ordem(ordem_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM receitas WHERE ordem_id = ?
    """, (ordem_id,))

    dado = cursor.fetchone()
    conn.close()

    return dado


def atualizar_receita(id, valor_final, forma, status, data):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE receitas
    SET valor_final = ?, forma_pagamento = ?, status = ?, data = ?
    WHERE id = ?
    """, (valor_final, forma, status, data, id))

    conn.commit()
    conn.close()

def excluir_receita(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM receitas WHERE id = ?", (id,))

    conn.commit()
    conn.close()

def gerar_ou_atualizar_receita_os(ordem_id, descricao, valor_os, data):
    conn = conectar()
    cursor = conn.cursor()

    # Verifica se já existe receita para essa OS
    cursor.execute("SELECT id, valor_final FROM receitas WHERE ordem_id = ?", (ordem_id,))
    receita = cursor.fetchone()

    if receita:
        receita_id = receita[0]

        # Atualiza apenas o valor_original (NÃO mexe no valor_final)
        cursor.execute("""
        UPDATE receitas
        SET valor_original = ?, descricao = ?, data = ?
        WHERE id = ?
        """, (valor_os, descricao, data, receita_id))

    else:
        # Cria nova receita
        cursor.execute("""
        INSERT INTO receitas (
            origem, ordem_id, descricao,
            valor_original, valor_final,
            forma_pagamento, status, data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "OS",
            ordem_id,
            descricao,
            valor_os,
            valor_os,            # começa igual
            "",                  # forma ainda não definida
            "PENDENTE",          # padrão
            data
        ))

    conn.commit()
    conn.close()

# 🔷 TABELA DESPESAS 💸
def criar_tabela_despesas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT,
        valor REAL,
        forma_pagamento TEXT,
        status TEXT,
        data TEXT,
        vencimento TEXT
    )
    """)

    # 🔥 GARANTE QUE A COLUNA EXISTE (BANCO ANTIGO)
    try:
        cursor.execute("ALTER TABLE despesas ADD COLUMN vencimento TEXT")
    except:
        pass

    conn.commit()
    conn.close()


# 🔷 FUNÇÕES DESPESAS

def inserir_despesa(descricao, valor, forma, status, data, vencimento):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO despesas (descricao, valor, forma_pagamento, status, data, vencimento)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (descricao, valor, forma, status, data, vencimento))

    conn.commit()
    conn.close()


def listar_despesas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM despesas
    ORDER BY 
    CASE 
        WHEN status = 'PENDENTE' THEN 1
        ELSE 2
    END,
    id DESC
    """)

    dados = cursor.fetchall()
    conn.close()
    return dados


def atualizar_despesa(id, valor, forma, status):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE despesas
    SET valor = ?, forma_pagamento = ?, status = ?
    WHERE id = ?
    """, (valor, forma, status, id))

    conn.commit()
    conn.close()


def excluir_despesa(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM despesas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def total_receitas_recebidas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(valor_final) FROM receitas
    WHERE status = 'RECEBIDO'
    """)

    total = cursor.fetchone()[0] or 0
    conn.close()
    return total


def total_despesas_pagas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(valor) FROM despesas
    WHERE status = 'PAGO'
    """)

    total = cursor.fetchone()[0] or 0
    conn.close()
    return total

# 🔷 LISTAR ORDENS DE SERVIÇO (COM MECÂNICO)
def listar_ordens():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        id,
        cliente,
        veiculo,
        placa,
        total,
        tipo,
        status,
        mecanico,
        total  -- usado como base de comissão (temporário)
        FROM ordens
        WHERE tipo = 'os'
        ORDER BY id DESC
    """)

    dados = cursor.fetchall()
    conn.close()

    return dados

# 🔷 CLIENTES
def criar_tabela_clientes():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        telefone TEXT NOT NULL,
        documento TEXT,
        data_nascimento TEXT,
        cep TEXT,
        logradouro TEXT,
        numero TEXT,
        bairro TEXT,
        cidade TEXT,
        uf TEXT,
        email TEXT
    )
    """)

    conn.commit()
    conn.close()


# 🔷 VEÍCULOS
def criar_tabela_veiculos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS veiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        veiculo TEXT,
        placa TEXT
    )
    """)

    conn.commit()
    conn.close()


# 🔷 INSERIR CLIENTE
def inserir_cliente(nome, telefone, documento, data_nascimento):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO clientes (nome, telefone, documento, data_nascimento)
    VALUES (?, ?, ?, ?)
    """, (nome, telefone, documento, data_nascimento))

    conn.commit()
    cliente_id = cursor.lastrowid
    conn.close()

    return cliente_id


# 🔷 INSERIR VEÍCULO
def inserir_veiculo(cliente_id, veiculo, placa):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO veiculos (cliente_id, veiculo, placa)
    VALUES (?, ?, ?)
    """, (cliente_id, veiculo, placa))

    conn.commit()
    conn.close()


# 🔷 LISTAR CLIENTES (COM VEÍCULOS)
def listar_clientes():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        c.id,
        c.nome,
        c.telefone,
        c.documento,
        c.data_nascimento,
        c.cep,
        c.logradouro,
        c.numero,
        c.bairro,
        c.cidade,
        c.uf,
        c.email,
        v.id,
        v.veiculo,
        v.placa
    FROM clientes c
    LEFT JOIN veiculos v ON v.cliente_id = c.id
    ORDER BY c.id DESC
    """)

    dados = cursor.fetchall()
    conn.close()
    return dados


# 🔷 BUSCA RÁPIDA
def buscar_cliente_rapido(termo):
    conn = conectar()
    cursor = conn.cursor()

    termo = f"%{termo}%"

    cursor.execute("""
    SELECT 
        c.nome,
        c.telefone,
        c.documento,
        c.data_nascimento,
        v.veiculo,
        v.placa
    FROM clientes c
    LEFT JOIN veiculos v ON v.cliente_id = c.id
    WHERE c.nome LIKE ? OR v.placa LIKE ?
    LIMIT 1
    """, (termo, termo))

    resultado = cursor.fetchone()
    conn.close()

    return resultado

def aniversariantes_hoje():
    from datetime import datetime

    hoje = datetime.now().strftime("%m-%d")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nome, telefone, data_nascimento
    FROM clientes
    """)

    clientes = cursor.fetchall()
    conn.close()

    lista = []

    for c in clientes:
        if c[2]:
            data = datetime.strptime(c[2], "%Y-%m-%d").strftime("%m-%d")

            if data == hoje:
                lista.append((c[0], c[1]))

    return lista

# 🔷 MECÂNICOS
def criar_tabela_mecanicos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mecanicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        comissao_padrao REAL,
        comissao_baixa REAL,
        limite_baixa REAL
    )
    """)

    conn.commit()
    conn.close()

# 🔷 INSERIR MECÂNICO
def inserir_mecanico(nome, comissao_padrao, comissao_baixa, limite_baixa):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO mecanicos (nome, comissao_padrao, comissao_baixa, limite_baixa)
    VALUES (?, ?, ?, ?)
    """, (nome, comissao_padrao, comissao_baixa, limite_baixa))

    conn.commit()
    conn.close()


# 🔷 LISTAR MECÂNICOS
def listar_mecanicos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM mecanicos ORDER BY nome")
    dados = cursor.fetchall()

    conn.close()
    return dados

# 🔷 BUSCAR MECÂNICO POR NOME
def buscar_mecanico(nome):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT comissao_padrao, comissao_baixa, limite_baixa
    FROM mecanicos
    WHERE nome = ?
    """, (nome,))

    dado = cursor.fetchone()
    conn.close()

    return dado

# 🔷 PAGAMENTOS DE MECÂNICOS
def criar_tabela_pagamentos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mecanico TEXT,
        data_inicio TEXT,
        data_fim TEXT,
        valor REAL,
        data_pagamento TEXT
    )
    """)

    conn.commit()
    conn.close()

def calcular_comissao_periodo(mecanico, data_inicio, data_fim):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        o.total,
        i.valor,
        i.quantidade,
        i.comissao
    FROM ordens o
    LEFT JOIN itens i ON o.id = i.ordem_id
    WHERE o.mecanico = ?
    AND DATE(o.data_entrada) BETWEEN DATE(?) AND DATE(?)
    """, (mecanico, data_inicio, data_fim))

    dados = cursor.fetchall()
    conn.close()

    total_comissao = 0

    from banco import buscar_mecanico
    config = buscar_mecanico(mecanico)

    if not config:
        return 0

    comissao_padrao, comissao_baixa, limite = config

    for d in dados:
        valor = float(d[1] or 0)
        qtd = float(d[2] or 1)
        usar = d[3]

        if usar:
            total_item = valor * qtd

            if total_item <= limite:
                total_comissao += total_item * comissao_baixa
            else:
                total_comissao += total_item * comissao_padrao

    return round(total_comissao, 2)

