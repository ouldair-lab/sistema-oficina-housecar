# 🔐 ADICIONADO session
from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from banco import criar_tabelas
from banco import conectar
from reportlab.pdfgen import canvas
from banco import gerar_ou_atualizar_receita_os
from datetime import datetime
from banco import criar_tabela_despesas
from banco import criar_tabela_clientes, criar_tabela_veiculos
from banco import criar_tabela_mecanicos
from banco import listar_mecanicos
from banco import criar_tabela_pagamentos
from banco import criar_tabela_usuarios
from banco import criar_admin_padrao

def iniciar_banco():
    criar_tabelas()
    criar_tabela_despesas()
    criar_tabela_clientes()
    criar_tabela_veiculos()
    criar_tabela_mecanicos()
    criar_tabela_pagamentos()
    criar_tabela_usuarios()
    criar_admin_padrao()

CONFIG = {
    "comissao_padrao": 0.4,
    "comissao_servico_baixo": 0.7,
    "limite_servico_baixo": 50
}

iniciar_banco()

EMPRESA = {
    "nome": "HOUSE CAR OFICINA MECÂNICA LTDA",
    "cnpj": "65.760.390/0001-43",
    "ie": "08.485.333/001-99",
    "telefone": "(61) 9 9580-5984",
    "endereco": "SOF CONJUNTO E LOTE 60 - SETOR NORTE - PLANALTINA-DF"
}

app = Flask(__name__)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# 🔐 CHAVE SECRETA
app.secret_key = "housecar_secreta_123"

# 🔐 PROTEÇÃO
def proteger():
    if not session.get("logado"):
        return redirect("/login")

# 🔐 LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, senha, tipo, primeiro_acesso
            FROM usuarios
            WHERE login = ?
        """, (usuario,))
        
        user = cursor.fetchone()

        conn.close()

        if user and user[1] == senha:
            session["logado"] = True
            session["usuario_id"] = user[0]
            session["tipo"] = user[2]

            # 🔥 PRIMEIRO ACESSO
            if user[3] == 1:
                return redirect("/trocar_senha")

            return redirect("/painel")

        else:
            return "Login inválido"

    return render_template("login.html")

# 🔐 LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    if proteger(): return proteger()

    # 🔐 só admin acessa
    if session.get("usuario_tipo") != "admin":
        return "Acesso restrito"

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form.get("nome")
        login = request.form.get("login")
        senha = request.form.get("senha")
        tipo = request.form.get("tipo")

        try:
            cursor.execute("""
            INSERT INTO usuarios (nome, login, senha, tipo)
            VALUES (?, ?, ?, ?)
            """, (nome, login, senha, tipo))

            conn.commit()
        except:
            return "Erro: login já existe"

    cursor.execute("SELECT id, nome, login, tipo FROM usuarios")
    lista = cursor.fetchall()

    conn.close()

    return render_template("usuarios.html", usuarios=lista)

from banco import total_receitas_recebidas, total_despesas_pagas
from banco import aniversariantes_hoje

# 🌐 SITE (PÚBLICO)
@app.route("/")
def site():
    return render_template("site.html")

# 🔐 PAINEL (SISTEMA)
@app.route("/painel")
def index():
    if proteger(): return proteger()

    receitas = total_receitas_recebidas()
    despesas = total_despesas_pagas()
    saldo = receitas - despesas

    aniversariantes = aniversariantes_hoje()  # 👈 aqui

    return render_template(
        "index.html",
        saldo=saldo,
        receitas=receitas,
        despesas=despesas,
        aniversariantes=aniversariantes  # 👈 IMPORTANTE
    )

@app.route("/financeiro")
def financeiro():
    if proteger(): return proteger()

    return render_template("financeiro.html")

@app.route("/orcamento", methods=["GET", "POST"])
def orcamento():
    if proteger(): return proteger()

    mecanicos = listar_mecanicos()
    
    if request.method == "POST":
        cliente = request.form.get("cliente")
        veiculo = request.form.get("veiculo")
        placa = request.form.get("placa")

        # 🔧 Padroniza placa
        placa = placa.upper().replace(" ", "") if placa else placa

        # 🔒 Validação
        if not placa:
            return "Erro: a placa é obrigatória!", 400

        mecanico = request.form.get("mecanico")
        problema = request.form.get("problema")
        diagnostico = request.form.get("diagnostico")

        # 📄 Nome do arquivo (já pronto pro PDF)
        import re
        nome_arquivo = re.sub(r'[^a-zA-Z0-9]', '_', f"{cliente}_{placa}")

        # 🧰 PEÇAS
        pecas_nome = request.form.getlist("peca_nome")
        pecas_valor = request.form.getlist("peca_valor")
        pecas_qtd = request.form.getlist("peca_qtd")

        pecas = []
        for nome, valor, qtd in zip(pecas_nome, pecas_valor, pecas_qtd):
            if nome:
                valor = float(valor) if valor else 0
                qtd = int(qtd) if qtd else 1

                pecas.append({
                    "nome": nome,
                    "valor": valor,
                    "qtd": qtd,
                    "total": valor * qtd
                })

        # 🔧 SERVIÇOS
        servicos = []

        i = 0
        while True:
            nome = request.form.get(f"servico_nome_{i}")
            if not nome:
                break

            valor = float(request.form.get(f"servico_valor_{i}") or 0)
            qtd = int(request.form.get(f"servico_qtd_{i}") or 1)

            comissao = request.form.get(f"servico_comissao_{i}") is not None

            servicos.append({
                "nome": nome,
                "valor": valor,
                "qtd": qtd,
                "comissao": comissao,
                "total": valor * qtd
            })

            i += 1

        # 💰 TOTAL
        total = sum(p["total"] for p in pecas) + sum(s["total"] for s in servicos)

        # 💾 SALVAR NO BANCO
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ordens (cliente, veiculo, placa, problema, diagnostico, total, tipo, status, mecanico, data_entrada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cliente, veiculo, placa, problema, diagnostico, total, "orcamento", "PENDENTE", mecanico, datetime.now().strftime("%Y-%m-%d")))

        ordem_id = cursor.lastrowid

        # peças
        for p in pecas:
            cursor.execute("""
            INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (ordem_id, "peca", p["nome"], p["valor"], p["qtd"], 0))

        # serviços
        for s in servicos:
            cursor.execute("""
            INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ordem_id,
                "servico",
                s["nome"],
                s["valor"],
                s["qtd"],
                int(s["comissao"])
            ))

        conn.commit()
        conn.close()        

        return render_template(
            "ficha.html",
            empresa=EMPRESA,
            cliente=cliente,
            veiculo=veiculo,
            placa=placa,
            problema=problema,
            diagnostico=diagnostico,
            mecanicos=mecanicos,
            pecas=pecas,
            servicos=servicos,
            total=total
        )

    return render_template("orcamento.html", id=id, mecanicos=mecanicos)

@app.route("/aprovar_orcamento/<int:id>")
def aprovar_orcamento(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE ordens
    SET tipo = 'os',
        status = 'EM ANDAMENTO'
    WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return """
    <h2>✅ Orçamento aprovado com sucesso!</h2>
    <p>Em breve entraremos em contato.</p>
    """

@app.route("/os", methods=["POST"])
def os():
    if proteger(): return proteger()
    cliente = request.form.get("cliente")
    veiculo = request.form.get("veiculo")
    placa = request.form.get("placa")
    mecanico = request.form.get("mecanico")
    problema = request.form.get("problema")
    diagnostico = request.form.get("diagnostico")

    # 🧰 PEÇAS (mantém como está)
    pecas_nome = request.form.getlist("peca_nome")
    pecas_valor = request.form.getlist("peca_valor")
    pecas_qtd = request.form.getlist("peca_qtd")

    pecas = list(zip(pecas_nome, pecas_valor, pecas_qtd))

    # 🔧 SERVIÇOS (modo novo com índice)
    servicos = []

    i = 0
    while True:
        nome = request.form.get(f"servico_nome_{i}")
        if not nome:
            break

        valor = float(request.form.get(f"servico_valor_{i}") or 0)
        qtd = int(request.form.get(f"servico_qtd_{i}") or 1)

        comissao = request.form.get(f"servico_comissao_{i}") is not None

        servicos.append((
            nome,
            valor,
            qtd,
            comissao
        ))

        i += 1

    # 💰 CALCULAR TOTAL (garante que nunca seja None)
    total = 0

    # peças
    for p in pecas:
        valor = float(p[1]) if p[1] else 0
        qtd = int(p[2]) if p[2] else 0
        total += valor * qtd

    # serviços
    for s in servicos:
        total += s[1] * s[2]

    return render_template(
    "os.html",
    cliente=cliente,
    veiculo=veiculo,
    placa=placa,
    mecanico=mecanico,
    problema=problema,
    diagnostico=diagnostico,
    total=total,
    pecas=pecas,
    servicos=servicos,
    tipo="orcamento",  # 🔥 ESSENCIAL
    status="PENDENTE",
    data_entrada=datetime.now().strftime("%Y-%m-%d")
)

@app.route("/orcamentos")
def orcamentos():
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    from datetime import datetime, timedelta

    limite = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    cursor.execute("""
    DELETE FROM ordens
    WHERE tipo = 'orcamento'
    AND status = 'PENDENTE'
    AND DATE(data_entrada) < DATE(?)
    """, (limite,))

    cursor.execute("""
    SELECT id, cliente, veiculo, placa, total, status, mecanico
    FROM ordens
    WHERE tipo = 'orcamento'
    AND status != 'CANCELADA'
    ORDER BY id DESC
    """)

    dados = cursor.fetchall()
    conn.close()

    return render_template("orcamentos.html", ordens=dados)

@app.route("/os_lista")
def os_lista():
    if proteger(): return proteger()

    busca = request.args.get("busca", "").strip().lower()

    conn = conectar()
    cursor = conn.cursor()

    query = """
    SELECT o.id, o.cliente, o.veiculo, o.placa, o.total, o.tipo, o.status, o.mecanico,
        SUM(
            CASE 
                WHEN i.tipo = 'servico' AND i.comissao = 1 THEN 
                    CASE 
                        WHEN (CAST(i.valor AS REAL) * CAST(i.quantidade AS REAL)) <= (
                            SELECT limite_baixa FROM mecanicos WHERE nome = o.mecanico
                        )
                        THEN (CAST(i.valor AS REAL) * CAST(i.quantidade AS REAL)) * (
                            SELECT comissao_baixa FROM mecanicos WHERE nome = o.mecanico
                        )
                        ELSE (CAST(i.valor AS REAL) * CAST(i.quantidade AS REAL)) * (
                            SELECT comissao_padrao FROM mecanicos WHERE nome = o.mecanico
                        )
                    END
                ELSE 0
            END
        ) as comissao_total
    FROM ordens o
    LEFT JOIN itens i ON o.id = i.ordem_id
    WHERE o.status != 'CANCELADA'
    AND o.tipo = 'os'
    """

    params = []

    if busca:
        query += " AND (LOWER(o.cliente) LIKE ? OR LOWER(o.placa) LIKE ?)"
        busca_like = f"%{busca}%"
        params.extend([busca_like, busca_like])

    query += """
    GROUP BY o.id
    ORDER BY 
        CASE 
            WHEN o.status = 'EM ANDAMENTO' THEN 1
            WHEN o.status = 'PENDENTE' THEN 2
            WHEN o.status = 'AGUARDANDO PEÇAS' THEN 3
            ELSE 4
        END,
        o.id DESC
    """

    cursor.execute(query, params)

    ordens = cursor.fetchall()
    conn.close()

    return render_template("os_lista.html", ordens=ordens, busca=busca)

@app.route("/abrir_os/<int:id>")
def abrir_os(id):
    if proteger(): return proteger()
    mecanicos = listar_mecanicos()

    # 🆕 NOVA OS (quando clica em + Nova OS)
    if id == 0:
        return render_template(
            "os.html",
            id=0,
            cliente="",
            veiculo="",
            placa="",
            data_entrada="",
            data_saida="",
            mecanico="",
            problema="",
            diagnostico="",
            total=0,
            status="EM ANDAMENTO",
            tipo="os",
            pecas=[],
            servicos=[],
            mecanicos=mecanicos
        )

    conn = conectar()
    cursor = conn.cursor()

    # 🔥 AGORA TRAZ O TIPO JUNTO
    cursor.execute("""
        SELECT cliente, veiculo, placa, data_entrada, data_saida, mecanico, problema, diagnostico, total, status, tipo
        FROM ordens WHERE id = ?
    """, (id,))
    ordem = cursor.fetchone()
    
    # 🔒 Segurança extra
    if not ordem:
        conn.close()
        return "OS não encontrada"

    # Itens
    cursor.execute("""
        SELECT tipo, nome, valor, quantidade, comissao
        FROM itens WHERE ordem_id = ?
    """, (id,))
    itens = cursor.fetchall()

    conn.close()

    pecas = []
    servicos = []

    for item in itens:
        if item[0] == "peca":
            pecas.append((item[1], item[2], item[3]))
        else:
            servicos.append((item[1], item[2], item[3], bool(item[4])))

    return render_template(
        "os.html",
        id=id,
        cliente=ordem[0],
        veiculo=ordem[1],
        placa=ordem[2],
        data_entrada=ordem[3],
        data_saida=ordem[4],
        mecanico=ordem[5],
        problema=ordem[6],
        diagnostico=ordem[7],
        total=ordem[8],
        status=ordem[9],
        tipo=ordem[10],  # 🔥 ESSENCIAL
        pecas=pecas,
        servicos=servicos,
        mecanicos=mecanicos
    )

@app.route("/atualizar_os", methods=["POST"])
def atualizar_os():
    if proteger(): return proteger()
    ordem_id = request.form.get("ordem_id")

    cliente = request.form.get("cliente")
    veiculo = request.form.get("veiculo")
    placa = request.form.get("placa")
    data_entrada = request.form.get("data_entrada")
    data_saida = request.form.get("data_saida")
    mecanico = request.form.get("mecanico")
    problema = request.form.get("problema")
    diagnostico = request.form.get("diagnostico")
    status = request.form.get("status")

    # 🔧 padroniza placa
    placa = placa.upper().replace(" ", "") if placa else placa

    # 🧰 PEÇAS
    pecas_nome = request.form.getlist("peca_nome")
    pecas_valor = request.form.getlist("peca_valor")
    pecas_qtd = request.form.getlist("peca_qtd")

    pecas = list(zip(pecas_nome, pecas_valor, pecas_qtd))

    # 🔧 SERVIÇOS (modelo indexado)
    servicos = []

    i = 0
    while True:
        nome = request.form.get(f"servico_nome_{i}")
        if not nome:
            break

        valor = float(request.form.get(f"servico_valor_{i}") or 0)
        qtd = int(request.form.get(f"servico_qtd_{i}") or 1)
        comissao = request.form.get(f"servico_comissao_{i}") is not None

        servicos.append((nome, valor, qtd, comissao))
        i += 1

    # 💰 recalcular total
    total = 0

    for p in pecas:
        valor = float(p[1]) if p[1] else 0
        qtd = int(p[2]) if p[2] else 0
        total += valor * qtd

    for s in servicos:
        total += s[1] * s[2]

    conn = conectar()
    cursor = conn.cursor()

    # 🔥 atualizar dados principais
    cursor.execute("""
    UPDATE ordens
    SET cliente=?, veiculo=?, placa=?, data_entrada=?, data_saida=?, mecanico=?, problema=?, diagnostico=?, total=?, tipo=?, status=?
    WHERE id=?
    """, (cliente, veiculo, placa, data_entrada, data_saida, mecanico, problema, diagnostico, total, "os", status, ordem_id))

    # 🔥 apagar itens antigos
    cursor.execute("DELETE FROM itens WHERE ordem_id=?", (ordem_id,))

    # 🔧 inserir peças novamente
    for p in pecas:
        cursor.execute("""
        INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (ordem_id, "peca", p[0], p[1], p[2], 0))

    # 🔧 inserir serviços novamente
    for s in servicos:
        cursor.execute("""
        INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (ordem_id, "servico", s[0], s[1], s[2], int(s[3])))

    conn.commit()
    conn.close()

    # 🔥 INTEGRAÇÃO COM RECEITAS (AQUI É O PONTO CERTO)
    if status == "FINALIZADA":
        descricao = f"OS #{ordem_id} - {cliente} - {placa}"

        gerar_ou_atualizar_receita_os(
            ordem_id=ordem_id,
            descricao=descricao,
            valor_os=total,
            data=datetime.now().strftime("%d/%m/%Y %H:%M")
        )

    return redirect("/os_lista")

@app.route("/cancelar_os/<int:id>")
def cancelar_os(id):
    conn = conectar()
    cursor = conn.cursor()

    # Cancela OS
    cursor.execute("""
    UPDATE ordens
    SET status = 'CANCELADA'
    WHERE id = ?
    """, (id,))

    # Cancela receita vinculada
    cursor.execute("""
    UPDATE receitas
    SET status = 'CANCELADO'
    WHERE ordem_id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/os_lista")

from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
import textwrap
from datetime import datetime

def formatar_data(data):
    if not data:
        return ""
    try:
        return datetime.strptime(data, "%Y-%m-%d").strftime("%d-%m-%Y")
    except:
        return data

@app.route("/gerar_nota/<int:id>")
def gerar_nota(id):
    if proteger(): return proteger()
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT cliente, veiculo, placa, problema, diagnostico, total,
           data_entrada, data_saida, mecanico
    FROM ordens WHERE id = ?
    """, (id,))
    ordem = cursor.fetchone()

    cursor.execute("""
    SELECT nome, valor, quantidade FROM itens
    WHERE ordem_id = ?
    """, (id,))
    itens = cursor.fetchall()

    conn.close()

    (cliente, veiculo, placa, problema, diagnostico, total,
     data_entrada, data_saida, mecanico) = ordem
    
    data_entrada_fmt = formatar_data(data_entrada)
    data_saida_fmt = formatar_data(data_saida)

    import re

    def limpar_texto(txt):
        return re.sub(r'[^a-zA-Z0-9]', '_', txt or "")

    cliente_limpo = limpar_texto(cliente)
    placa_limpa = limpar_texto(placa)

    nome_arquivo = f"OS_{id}_{cliente_limpo}_{placa_limpa}.pdf"

    pasta = "notas"
    os.makedirs(pasta, exist_ok=True)

    caminho_base = os.path.join(pasta, nome_arquivo)

    # 🔥 EVITA SOBRESCREVER
    contador = 1
    caminho = caminho_base

    while os.path.exists(caminho):
        nome_sem_ext = nome_arquivo.replace(".pdf", "")
        caminho = os.path.join(pasta, f"{nome_sem_ext}_{contador}.pdf")
        contador += 1

    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    # 🔷 LOGO MAIOR
    try:
        c.drawImage("static/logo_housecar.png", largura/2 - 110, altura - 110, width=220, height=80)
    except:
        pass

    # 🔷 TÍTULO
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura/2, altura - 130, "NOTA DE SERVIÇO")

    y = altura - 170

    # 🔷 CAIXA CLIENTE COM DIVISÕES
    c.rect(50, y - 80, 500, 80)

    # linhas internas
    c.line(50, y - 30, 550, y - 30)
    c.line(50, y - 55, 550, y - 55)

    c.setFont("Helvetica", 10)
    c.drawString(60, y - 20, f"Cliente: {cliente}")
    c.drawString(60, y - 45, f"Veículo: {veiculo}")
    c.drawString(60, y - 70, f"Placa: {placa}")

    y -= 100

    # 🔷 DATAS E MECÂNICO
    c.rect(50, y - 40, 500, 40)

    c.drawString(60, y - 20, f"Entrada: {data_entrada_fmt}")
    c.drawString(220, y - 20, f"Saída: {data_saida_fmt}")
    c.drawString(380, y - 20, f"Mecânico: {mecanico or ''}")

    y -= 60

    # 🔷 FUNÇÃO CAIXA TEXTO
    def caixa_texto(titulo, texto, altura_box):
        nonlocal y

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, titulo)

        y -= 10
        c.rect(50, y - altura_box, 500, altura_box)

        c.setFont("Helvetica", 9)
        linhas = textwrap.wrap(texto or "", 90)

        yy = y - 15
        for linha in linhas[:5]:
            c.drawString(55, yy, linha)
            yy -= 12

        y -= (altura_box + 20)

    # 🔷 PROBLEMA
    caixa_texto("Problema Relatado:", problema, 50)

    # 🔷 DIAGNÓSTICO
    caixa_texto("Diagnóstico Técnico / Solução:", diagnostico, 70)

    # 🔷 CONFIGURAÇÃO DA TABELA
    c.setFont("Helvetica", 9)

    col_qtd = 50
    col_desc = 100
    col_valor = 420
    col_total = 550

    largura_total = 500
    altura_linha = 18

    y -= 20
    topo = y

    # 🔷 CABEÇALHO COM FUNDO CINZA
    c.setFillGray(0.85)
    c.rect(50, y - altura_linha, largura_total, altura_linha, fill=1, stroke=0)

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 10)

    # títulos centralizados
    c.drawCentredString(75, y - 13, "QTD")
    c.drawCentredString(260, y - 13, "DESCRIÇÃO")
    c.drawCentredString(480, y - 13, "VALOR")

    # linhas verticais do cabeçalho
    c.line(50, y, 50, y - altura_linha)
    c.line(100, y, 100, y - altura_linha)
    c.line(420, y, 420, y - altura_linha)
    c.line(550, y, 550, y - altura_linha)

    # linha inferior do cabeçalho
    c.line(50, y - altura_linha, 550, y - altura_linha)

    y -= altura_linha

    # 🔷 LINHAS DOS ITENS
    c.setFont("Helvetica", 9)

    for item in itens:
        nome, valor, qtd = item
        total_item = float(valor) * int(qtd)

        c.drawCentredString(75, y - 12, str(qtd))
        c.drawString(105, y - 12, nome[:45])
        c.drawRightString(540, y - 12, f"R$ {total_item:.2f}")

        # linhas horizontais
        c.line(50, y - altura_linha, 550, y - altura_linha)

        # linhas verticais
        c.line(50, y, 50, y - altura_linha)
        c.line(100, y, 100, y - altura_linha)
        c.line(420, y, 420, y - altura_linha)
        c.line(550, y, 550, y - altura_linha)

        y -= altura_linha

    # 🔷 LINHA DO TOTAL (DENTRO DA TABELA)
    c.setFont("Helvetica-Bold", 11)

    c.setFillGray(0.9)
    c.rect(50, y - altura_linha, largura_total, altura_linha, fill=1, stroke=0)

    c.setFillColorRGB(0, 0, 0)

    c.drawRightString(540, y - 12, f"TOTAL: R$ {total:.2f}")

    # linhas finais
    c.line(50, y - altura_linha, 550, y - altura_linha)

    # bordas finais completas
    c.line(50, topo, 550, topo)  # topo geral
    c.line(50, topo, 50, y - altura_linha)  # esquerda
    c.line(550, topo, 550, y - altura_linha)  # direita

   
    c.save()

    return send_file(
    caminho,
    as_attachment=False,
    download_name=os.path.basename(caminho)
    )

@app.route("/notas")
def notas():
    if proteger(): return proteger()

    import os

    pasta = "notas"
    arquivos = []

    if os.path.exists(pasta):
        arquivos = os.listdir(pasta)

        # ordenar mais recente primeiro
        arquivos.sort(reverse=True)

    return render_template("notas.html", arquivos=arquivos)

from flask import send_from_directory
import os

@app.route("/abrir_nota/<path:nome>")
def abrir_nota(nome):
    if proteger(): return proteger()

    pasta = os.path.abspath("notas")

    return send_from_directory(pasta, nome)


from banco import listar_receitas, inserir_receita
from datetime import datetime

@app.route("/receitas", methods=["GET", "POST"])
def receitas():
    if proteger(): return proteger()
    if request.method == "POST":
        descricao = request.form.get("descricao")
        valor = float(request.form.get("valor") or 0)
        forma = request.form.get("forma")
        status = request.form.get("status")

        inserir_receita(
            origem="VENDA",
            ordem_id=None,
            descricao=descricao,
            valor_original=valor,
            valor_final=valor,
            forma=forma,
            status=status,
            data=datetime.now().strftime("%d/%m/%Y %H:%M")
        )

    dados = listar_receitas()

    # 🔷 TOTAL GERAL (SÓ RECEBIDOS)
    total = sum([r[5] for r in dados if r[7] == "RECEBIDO"])

    # 🔷 TOTAL POR FORMA (SÓ RECEBIDOS)
    total_pix = sum([r[5] for r in dados if r[6] == "PIX" and r[7] == "RECEBIDO"])
    total_dinheiro = sum([r[5] for r in dados if r[6] == "DINHEIRO" and r[7] == "RECEBIDO"])
    total_debito = sum([r[5] for r in dados if r[6] == "DÉBITO" and r[7] == "RECEBIDO"])
    total_credito = sum([r[5] for r in dados if r[6] == "CRÉDITO" and r[7] == "RECEBIDO"])

    return render_template(
        "receitas.html",
        receitas=dados,
        total=total,
        total_pix=total_pix,
        total_dinheiro=total_dinheiro,
        total_debito=total_debito,
        total_credito=total_credito
    )

from banco import atualizar_receita

@app.route("/editar_receita/<int:id>", methods=["POST"])
def editar_receita(id):
    if proteger(): return proteger()
    valor = float(request.form.get("valor") or 0)
    forma = request.form.get("forma")
    status = request.form.get("status")

    atualizar_receita(id, valor, forma, status)

    return redirect("/receitas")

from banco import excluir_receita

@app.route("/excluir_receita/<int:id>")
def excluir_receita_route(id):
    if proteger(): return proteger()
    excluir_receita(id)
    return redirect("/receitas")

from banco import (
    inserir_despesa, listar_despesas,
    atualizar_despesa, excluir_despesa
)

@app.route("/despesas", methods=["GET", "POST"])
def despesas():
    if proteger(): return proteger()

    from datetime import datetime

    if request.method == "POST":
        descricao = request.form.get("descricao")
        valor = float(request.form.get("valor") or 0)
        forma = request.form.get("forma")
        status = request.form.get("status")
        vencimento = request.form.get("vencimento")

        inserir_despesa(
            descricao,
            valor,
            forma,
            status,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            vencimento
        )

    dados = listar_despesas()

    # 💸 TOTAL (SÓ PAGAS)
    total = sum([d[2] for d in dados if d[4] == "PAGO"])

    # 💳 POR FORMA (SÓ PAGAS)
    total_pix = sum([d[2] for d in dados if d[3] == "PIX" and d[4] == "PAGO"])
    total_dinheiro = sum([d[2] for d in dados if d[3] == "DINHEIRO" and d[4] == "PAGO"])
    total_debito = sum([d[2] for d in dados if d[3] == "DÉBITO" and d[4] == "PAGO"])
    total_credito = sum([d[2] for d in dados if d[3] == "CRÉDITO" and d[4] == "PAGO"])

    from datetime import datetime

    return render_template(
        "despesas.html",
        despesas=dados,
        total=total,
        total_pix=total_pix,
        total_dinheiro=total_dinheiro,
        total_debito=total_debito,
        total_credito=total_credito,
        hoje=datetime.now().strftime("%Y-%m-%d")  # 🔥 IMPORTANTE
    )


@app.route("/editar_despesa/<int:id>", methods=["POST"])
def editar_despesa(id):
    if proteger(): return proteger()
    valor = float(request.form.get("valor") or 0)
    forma = request.form.get("forma")
    status = request.form.get("status")

    atualizar_despesa(id, valor, forma, status)
    return redirect("/despesas")


@app.route("/excluir_despesa/<int:id>")
def excluir_despesa_route(id):
    if proteger(): return proteger()
    excluir_despesa(id)
    return redirect("/despesas")

from banco import inserir_cliente, inserir_veiculo, listar_clientes

@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if proteger(): return proteger()

    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        documento = request.form.get("documento")
        data_nascimento = request.form.get("data_nascimento")

        veiculo = request.form.get("veiculo")
        placa = request.form.get("placa")

        conn = conectar()
        cursor = conn.cursor()

        # 🔍 verifica se cliente já existe
        cursor.execute("""
        SELECT id FROM clientes
        WHERE nome = ? AND telefone = ?
        """, (nome, telefone))

        existente = cursor.fetchone()

        if existente:
            cliente_id = existente[0]

            # 🚗 adiciona veículo apenas
            if veiculo or placa:
                cursor.execute("""
                INSERT INTO veiculos (cliente_id, veiculo, placa)
                VALUES (?, ?, ?)
                """, (cliente_id, veiculo, placa))

            conn.commit()
            conn.close()

            return redirect("/clientes")

        # 🆕 cria novo cliente
        cursor.execute("""
        INSERT INTO clientes (nome, telefone, documento, data_nascimento)
        VALUES (?, ?, ?, ?)
        """, (nome, telefone, documento, data_nascimento))

        cliente_id = cursor.lastrowid

        if veiculo or placa:
            cursor.execute("""
            INSERT INTO veiculos (cliente_id, veiculo, placa)
            VALUES (?, ?, ?)
            """, (cliente_id, veiculo, placa))

        conn.commit()
        conn.close()

        return redirect("/clientes")

    dados = listar_clientes()
    return render_template("clientes.html", clientes=dados)

from flask import jsonify

@app.route("/buscar_cliente")
def buscar_cliente():
    if proteger(): return proteger()

    termo = request.args.get("q")

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
    LIMIT 5
    """, (termo, termo))

    resultados = cursor.fetchall()
    conn.close()

    lista = []
    for r in resultados:
        lista.append({
            "nome": r[0],
            "telefone": r[1],
            "documento": r[2],
            "data_nascimento": r[3],
            "veiculo": r[4],
            "placa": r[5]
        })

    return jsonify(lista)

@app.route("/editar_cliente/<int:id>", methods=["POST"])
def editar_cliente(id):
    if proteger(): return proteger()

    nome = request.form.get("nome")
    telefone = request.form.get("telefone")
    documento = request.form.get("documento")
    data_nascimento = request.form.get("data_nascimento")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE clientes
    SET nome=?, telefone=?, documento=?, data_nascimento=?
    WHERE id=?
    """, (nome, telefone, documento, data_nascimento, id))

    conn.commit()
    conn.close()

    return redirect("/clientes")

@app.route("/excluir_cliente/<int:id>")
def excluir_cliente(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    # 🔥 remove veículos primeiro
    cursor.execute("DELETE FROM veiculos WHERE cliente_id=?", (id,))

    # 🔥 remove cliente
    cursor.execute("DELETE FROM clientes WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/clientes")

@app.route("/add_veiculo", methods=["POST"])
def add_veiculo():
    if proteger(): return proteger()

    cliente_id = request.form.get("cliente_id")
    veiculo = request.form.get("veiculo")
    placa = request.form.get("placa")

    inserir_veiculo(cliente_id, veiculo, placa)

    return redirect("/clientes")

@app.route("/editar_veiculo/<int:id>", methods=["POST"])
def editar_veiculo(id):
    if proteger(): return proteger()

    veiculo = request.form.get("veiculo")
    placa = request.form.get("placa")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE veiculos
    SET veiculo=?, placa=?
    WHERE id=?
    """, (veiculo, placa, id))

    conn.commit()
    conn.close()

    return redirect("/clientes")

@app.route("/excluir_veiculo/<int:id>")
def excluir_veiculo(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM veiculos WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/clientes")

from banco import inserir_mecanico, listar_mecanicos

@app.route("/mecanicos", methods=["GET", "POST"])
def mecanicos():
    if proteger(): return proteger()
    if session.get("usuario_tipo") != "admin":
        return "Acesso restrito ao administrador"

    if request.method == "POST":
        nome = request.form.get("nome")
        comissao_padrao = float(request.form.get("comissao_padrao"))
        comissao_baixa = float(request.form.get("comissao_baixa"))
        limite_baixa = float(request.form.get("limite_baixa"))

        inserir_mecanico(nome, comissao_padrao, comissao_baixa, limite_baixa)

        return redirect("/mecanicos")

    dados = listar_mecanicos()
    return render_template("mecanicos.html", mecanicos=dados)

@app.route("/editar_mecanico/<int:id>", methods=["POST"])
def editar_mecanico(id):
    if proteger(): return proteger()

    nome = request.form.get("nome")
    comissao_padrao = float(request.form.get("comissao_padrao"))
    comissao_baixa = float(request.form.get("comissao_baixa"))
    limite_baixa = float(request.form.get("limite_baixa"))

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE mecanicos
    SET nome=?, comissao_padrao=?, comissao_baixa=?, limite_baixa=?
    WHERE id=?
    """, (nome, comissao_padrao, comissao_baixa, limite_baixa, id))

    conn.commit()
    conn.close()

    return redirect("/mecanicos")

@app.route("/excluir_mecanico/<int:id>")
def excluir_mecanico(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM mecanicos WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/mecanicos")

from banco import calcular_comissao_periodo
@app.route("/pagamentos", methods=["GET", "POST"])
def pagamentos():
    if proteger(): return proteger()

    mecanicos = listar_mecanicos()
    resultado = None

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        mecanico = request.form.get("mecanico")
        data_inicio = request.form.get("data_inicio")
        data_fim = request.form.get("data_fim")

        valor = calcular_comissao_periodo(mecanico, data_inicio, data_fim)

        resultado = {
            "mecanico": mecanico,
            "valor": valor,
            "inicio": data_inicio,
            "fim": data_fim
        }

    cursor.execute("SELECT * FROM pagamentos ORDER BY id DESC")
    pagamentos_lista = cursor.fetchall()
    conn.close()

    return render_template("pagamentos.html",
        mecanicos=mecanicos,
        resultado=resultado,
        pagamentos=pagamentos_lista
    )

@app.route("/registrar_pagamento", methods=["POST"])
def registrar_pagamento():
    if proteger(): return proteger()

    mecanico = request.form.get("mecanico")
    inicio = request.form.get("data_inicio")
    fim = request.form.get("data_fim")
    valor = float(request.form.get("valor"))

    from datetime import datetime
    data_pagamento = datetime.now().strftime("%Y-%m-%d")

    conn = conectar()
    cursor = conn.cursor()

    # salva histórico
    cursor.execute("""
    INSERT INTO pagamentos (mecanico, data_inicio, data_fim, valor, data_pagamento)
    VALUES (?, ?, ?, ?, ?)
    """, (mecanico, inicio, fim, valor, data_pagamento))

    # 🔥 cria despesa pendente
    cursor.execute("""
    INSERT INTO despesas (descricao, valor, data, status)
    VALUES (?, ?, ?, ?)
    """, (f"Pagamento mecânico - {mecanico}", valor, data_pagamento, "PENDENTE"))

    conn.commit()
    conn.close()

    return redirect("/pagamentos")

@app.route("/estoque")
def estoque():
    if proteger(): return proteger()   
    return "<h1>Estoque</h1>"

@app.route("/relatorios")
def relatorios():
    if proteger(): return proteger()
    return "<h1>Relatórios</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

