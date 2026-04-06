import sqlite3


def conectar():
    return sqlite3.connect("oficina.db")


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    # 🔷 TABELA PRINCIPAL (ORDENS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        veiculo TEXT,
        placa TEXT,
        problema TEXT,
        diagnostico TEXT,
        total REAL,
        tipo TEXT,
        status TEXT DEFAULT 'EM ANDAMENTO',
        mecanico TEXT,
        data_entrada TEXT,
        data_saida TEXT
    )
    """)

    # 🔷 ITENS (PEÇAS E SERVIÇOS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ordem_id INTEGER,
        tipo TEXT,
        nome TEXT,
        valor REAL,
        quantidade INTEGER,
        comissao INTEGER DEFAULT 0
    )
    """)

    # 🔷 NOVA TABELA: RECEITAS 💰
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        origem TEXT, -- OS ou VENDA
        ordem_id INTEGER, -- ligação com OS (se houver)

        descricao TEXT,

        valor_original REAL,
        valor_final REAL,

        forma_pagamento TEXT,
        status TEXT,

        data TEXT
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
    ORDER BY id DESC
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


def atualizar_receita(id, valor_final, forma, status):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE receitas
    SET valor_final = ?, forma_pagamento = ?, status = ?
    WHERE id = ?
    """, (valor_final, forma, status, id))

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
        status TEXT, -- PAGO / PENDENTE

        data TEXT
    )
    """)

    conn.commit()
    conn.close()


# 🔷 FUNÇÕES DESPESAS

def inserir_despesa(descricao, valor, forma, status, data):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO despesas (descricao, valor, forma_pagamento, status, data)
    VALUES (?, ?, ?, ?, ?)
    """, (descricao, valor, forma, status, data))

    conn.commit()
    conn.close()


def listar_despesas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM despesas
    ORDER BY id DESC
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
        data_nascimento TEXT
    )
    """)

    # 🔥 garante coluna em banco antigo
    try:
        cursor.execute("ALTER TABLE clientes ADD COLUMN data_nascimento TEXT")
    except:
        pass

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