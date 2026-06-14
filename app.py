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
import os
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)

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

@app.context_processor
def inject_user():
    return dict(tipo=session.get("tipo"))

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

@app.route("/trocar_senha", methods=["GET", "POST"])
def trocar_senha():
    if not session.get("logado"):
        return redirect("/login")

    if request.method == "POST":
        nova_senha = request.form.get("senha")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE usuarios
            SET senha = ?, primeiro_acesso = 0
            WHERE id = ?
        """, (nova_senha, session["usuario_id"]))

        conn.commit()
        conn.close()

        return redirect("/painel")

    return """
    <h2>🔐 Primeiro acesso - Defina sua senha</h2>
    <form method="POST">
        <input type="password" name="senha" placeholder="Nova senha" required>
        <button type="submit">Salvar</button>
    </form>
    """

# 🔐 LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/resetar_senha/<int:id>")
def resetar_senha(id):
    if proteger(): return proteger()

    if session.get("tipo") != "admin":
        return "Acesso restrito"

    conn = conectar()
    cursor = conn.cursor()

    # senha padrão temporária
    nova_senha = "1234"

    cursor.execute("""
    UPDATE usuarios
    SET senha = ?, primeiro_acesso = 1
    WHERE id = ?
    """, (nova_senha, id))

    conn.commit()
    conn.close()

    return redirect("/usuarios")

@app.route("/esqueci_senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        login = request.form.get("login")

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id FROM usuarios WHERE login = ?
        """, (login,))

        user = cursor.fetchone()

        if user:
            cursor.execute("""
            UPDATE usuarios
            SET senha = ?, primeiro_acesso = 1
            WHERE id = ?
            """, ("1234", user[0]))

            conn.commit()
            conn.close()

            return """
            <h2>🔑 Senha resetada!</h2>
            <p>Use a senha: <b>1234</b></p>
            <a href="/login">Voltar</a>
            """

        conn.close()
        return "Usuário não encontrado"

    return """
    <h2>🔐 Recuperar senha</h2>
    <form method="POST">
        <input type="text" name="login" placeholder="Digite seu login" required>
        <button type="submit">Resetar senha</button>
    </form>
    """

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    if proteger(): return proteger()

    # 🔐 só admin acessa
    if session.get("tipo") != "admin":
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

@app.route("/excluir_usuario/<int:id>")
def excluir_usuario(id):
    if proteger(): return proteger()

    # 🔐 só admin pode excluir
    if session.get("tipo") != "admin":
        return "Acesso restrito"

    conn = conectar()
    cursor = conn.cursor()

    # 🔒 NÃO DEIXA EXCLUIR O PRÓPRIO USUÁRIO LOGADO
    if id == session.get("usuario_id"):
        conn.close()
        return "Você não pode excluir seu próprio usuário"

    # 🔒 NÃO DEIXA EXCLUIR O ADMIN PRINCIPAL
    cursor.execute("SELECT login FROM usuarios WHERE id = ?", (id,))
    user = cursor.fetchone()

    if user and user[0] == "admin":
        conn.close()
        return "Não é permitido excluir o administrador principal"

    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect("/usuarios")

@app.route("/editar_usuario/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    if proteger(): return proteger()

    # 🔐 só admin
    if session.get("tipo") != "admin":
        return "Acesso restrito"

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form.get("nome")
        login = request.form.get("login")
        tipo = request.form.get("tipo")

        cursor.execute("""
        UPDATE usuarios
        SET nome = ?, login = ?, tipo = ?
        WHERE id = ?
        """, (nome, login, tipo, id))

        conn.commit()
        conn.close()

        return redirect("/usuarios")

    # GET → carregar dados
    cursor.execute("""
    SELECT id, nome, login, tipo
    FROM usuarios
    WHERE id = ?
    """, (id,))

    usuario = cursor.fetchone()
    conn.close()

    return render_template("editar_usuario.html", u=usuario)

from banco import total_receitas_recebidas, total_despesas_pagas
from banco import aniversariantes_hoje

# SITE
@app.route("/")
def site():
    from banco import conectar

    conn = conectar()
    cursor = conn.cursor()

    # 🎬 vídeos
    cursor.execute("""
        SELECT * FROM videos
        ORDER BY id DESC
        LIMIT 6
    """)
    videos = cursor.fetchall()

    # 📸 fotos
    cursor.execute("""
        SELECT * FROM fotos
        ORDER BY id DESC
        LIMIT 8
    """)
    fotos = cursor.fetchall()

    conn.close()

    return render_template("site.html", videos=videos, fotos=fotos)

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

def normalizar_link_instagram(link):
    link = link.strip()

    match = re.search(r"instagram\.com/(reel|p)/([^/?]+)", link)

    if match:
        tipo = match.group(1)
        codigo = match.group(2)
        return f"https://www.instagram.com/{tipo}/{codigo}/embed"

    return link


@app.route('/admin/videos', methods=['GET', 'POST'])
def admin_videos():
    if proteger():
        return proteger()

    if session.get('tipo') not in ['admin', 'marketing']:
        return redirect('/')

    if request.method == 'POST':
        titulo = request.form['titulo']
        link = normalizar_link_instagram(request.form['link'])

        from banco import conectar
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO videos (titulo, link)
            VALUES (?, ?)
        """, (titulo, link))

        conn.commit()
        conn.close()

        return redirect('/admin/videos')

    from banco import conectar
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM videos ORDER BY id DESC")
    videos = cursor.fetchall()

    conn.close()

    return render_template('admin_videos.html', videos=videos)

@app.route('/admin/videos/excluir/<int:id>')
def excluir_video(id):

    if proteger():
        return proteger()

    if session.get('tipo') not in ['admin', 'marketing']:
        return redirect('/')

    from banco import conectar
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM videos WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin/videos')


@app.route('/admin/fotos', methods=['GET', 'POST'])
def admin_fotos():

    if proteger(): return proteger()

    if session.get('tipo') not in ['admin', 'marketing']:
        return redirect('/')

    if request.method == 'POST':
        arquivo = request.files['foto']

        if arquivo:
            nome_seguro = secure_filename(arquivo.filename)

            caminho = os.path.join('static/fotos', nome_seguro)
            arquivo.save(caminho)

            from banco import conectar
            conn = conectar()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO fotos (arquivo)
                VALUES (?)
            """, (nome_seguro,))

            conn.commit()
            conn.close()

        return redirect('/admin/fotos')

    from banco import conectar
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM fotos ORDER BY id DESC")
    fotos = cursor.fetchall()

    conn.close()

    return render_template('admin_fotos.html', fotos=fotos)

@app.route('/admin/fotos/excluir/<int:id>')
def excluir_foto(id):

    if proteger():
        return proteger()

    if session.get('tipo') not in ['admin', 'marketing']:
        return redirect('/')

    import os
    from banco import conectar

    conn = conectar()
    cursor = conn.cursor()

    # pega nome do arquivo
    cursor.execute("SELECT arquivo FROM fotos WHERE id = ?", (id,))
    foto = cursor.fetchone()

    if foto:
        caminho = os.path.join('static/fotos', foto[0])

        # remove arquivo físico
        if os.path.exists(caminho):
            os.remove(caminho)

        # remove do banco
        cursor.execute("DELETE FROM fotos WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin/fotos')

@app.route("/financeiro")
def financeiro():
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(valor_final) FROM receitas WHERE status='RECEBIDO'")
    receitas = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(valor) FROM despesas WHERE status='PAGO'")
    despesas = cursor.fetchone()[0] or 0

    saldo = receitas - despesas

    conn.close()

    return render_template(
        "financeiro.html",
        receitas=receitas,
        despesas=despesas,
        saldo=saldo
    )

@app.route("/orcamento", methods=["GET", "POST"])
def orcamento():
    if proteger(): return proteger()

    import json
    from datetime import datetime

    conn = conectar()

    # =========================
    # POST (SALVAR / ATUALIZAR)
    # =========================
    if request.method == "POST":
        
        id = request.form.get("id")

        cliente = request.form.get("cliente")
        telefone = request.form.get("telefone")
        veiculo = request.form.get("veiculo")
        placa = request.form.get("placa")
        problema = request.form.get("problema")
        diagnostico = request.form.get("diagnostico")
        mecanico = request.form.get("mecanico")

        # 🧰 PEÇAS
        pecas = []
        pecas_json = request.form.get("pecas_json")

        if pecas_json:
            try:
                dados = json.loads(pecas_json)
                for p in dados:
                    nome = p.get("nome")
                    valor = float(p.get("valor") or 0)
                    qtd = int(p.get("qtd") or 1)

                    if nome:
                        pecas.append((nome, valor, qtd))
            except:
                pass

        # 🔧 SERVIÇOS
        servicos = []
        servicos_json = request.form.get("servicos_json")

        if servicos_json:
            try:
                dados = json.loads(servicos_json)
                for s in dados:
                    nome = s.get("nome")
                    valor = float(s.get("valor") or 0)
                    qtd = int(s.get("qtd") or 1)
                    comissao = bool(s.get("comissao"))

                    if nome:
                        servicos.append((nome, valor, qtd, comissao))
            except:
                pass

        # 💰 TOTAL
        total = 0
        for p in pecas:
            total += p[1] * p[2]

        for s in servicos:
            total += s[1] * s[2]

        cursor = conn.cursor()

        if id and id.isdigit():
            # 🔄 ATUALIZAR
            cursor.execute("""
                UPDATE ordens SET
                    cliente=?,
                    telefone=?,
                    veiculo=?,
                    placa=?,
                    problema=?,
                    diagnostico=?,
                    total=?,
                    mecanico=?
                WHERE id=?
            """, (
                cliente,
                telefone,
                veiculo,
                placa,
                problema,
                diagnostico,
                total,
                mecanico,
                id
            ))

            ordem_id = id

            cursor.execute("DELETE FROM itens WHERE ordem_id = ?", (ordem_id,))

        else:
            # ➕ NOVO
            cursor.execute("""
                INSERT INTO ordens (
                    cliente, telefone, veiculo, placa, problema, diagnostico,
                    total, tipo, status, mecanico, data_entrada
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cliente,
                telefone,
                veiculo,
                placa,
                problema,
                diagnostico,
                total,
                "orcamento",
                "PENDENTE",
                mecanico,
                datetime.now().strftime("%Y-%m-%d")
            ))

            ordem_id = cursor.lastrowid

        # 🧰 salvar peças
        for p in pecas:
            cursor.execute("""
                INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ordem_id, "peca", p[0], p[1], p[2], 0))

        # 🔧 salvar serviços
        for s in servicos:
            cursor.execute("""
                INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ordem_id, "servico", s[0], s[1], s[2], int(s[3])))

        conn.commit()
        conn.close()

        return redirect("/orcamentos")

    # =========================
    # GET (ABRIR TELA)
    # =========================

    id = request.args.get("id")

    mecanicos = conn.execute("SELECT nome FROM mecanicos").fetchall()

    if id:
        ordem = conn.execute("""
        SELECT 
            id, cliente, telefone, veiculo, placa,
            problema, diagnostico, total, tipo, status, mecanico,
            data_entrada, data_saida
        FROM ordens
        WHERE id = ?
        """, (id,)).fetchone()

        itens = conn.execute("SELECT * FROM itens WHERE ordem_id = ?", (id,)).fetchall()

        pecas = []
        servicos = []

        for i in itens:
            if i[2] == "peca":
                pecas.append((i[3], i[4], i[5]))
            elif i[2] == "servico":
                servicos.append((i[3], i[4], i[5], i[6]))

    else:
        ordem = None
        pecas = []
        servicos = []

    conn.close()

    return render_template(
        "orcamento.html",
        mecanicos=mecanicos,
        id=id,
        ordem=ordem,
        pecas=pecas,
        servicos=servicos
    )

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

@app.route("/excluir_orcamento/<int:id>")
def excluir_orcamento(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    # 🔥 apaga itens primeiro
    cursor.execute("DELETE FROM itens WHERE ordem_id = ?", (id,))

    # 🔥 apaga ordem
    cursor.execute("DELETE FROM ordens WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect("/orcamentos")

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
    AND status = 'PENDENTE'
    ORDER BY id DESC
    """)

    dados = cursor.fetchall()
    conn.close()

    return render_template("orcamentos.html", ordens=dados)

@app.route("/os", methods=["POST"])
def os():    
    if proteger(): return proteger()
    
    import json
    from datetime import datetime

    id = request.form.get("id")

    cliente = request.form.get("cliente")
    telefone = request.form.get("telefone")
    veiculo = request.form.get("veiculo")
    placa = request.form.get("placa")
    mecanico = request.form.get("mecanico")
    problema = request.form.get("problema")
    diagnostico = request.form.get("diagnostico")
    status = request.form.get("status") or "EM ANDAMENTO"

    data_entrada = request.form.get("data_entrada")
    data_saida = request.form.get("data_saida")

    # 🔥 CORREÇÃO AQUI
    try:
        quilometragem = int(request.form.get("quilometragem"))
    except:
        quilometragem = 0

    # 🧰 PEÇAS
    pecas = []
    pecas_json = request.form.get("pecas_json")

    if pecas_json:
        try:
            dados = json.loads(pecas_json)
            for p in dados:
                nome = p.get("nome")
                valor = float(p.get("valor") or 0)
                qtd = int(p.get("qtd") or 1)

                if nome:
                    pecas.append((nome, valor, qtd))
        except:
            pass

    # 🔧 SERVIÇOS
    servicos = []
    servicos_json = request.form.get("servicos_json")

    if servicos_json:
        try:
            dados = json.loads(servicos_json)
            for s in dados:
                nome = s.get("nome")
                valor = float(s.get("valor") or 0)
                qtd = int(s.get("qtd") or 1)
                comissao = bool(s.get("comissao"))

                if nome:
                    servicos.append((nome, valor, qtd, comissao))
        except:
            pass

    # 💰 TOTAL
    total = sum(p[1] * p[2] for p in pecas) + sum(s[1] * s[2] for s in servicos)

    conn = conectar()
    cursor = conn.cursor()    

    if id and id.isdigit() and int(id) > 0:
        cursor.execute("""
            UPDATE ordens SET
                cliente=?,
                telefone=?,
                veiculo=?,
                placa=?,
                problema=?,
                diagnostico=?,
                total=?,
                mecanico=?,
                status=?,
                data_entrada=?,
                data_saida=?,
                quilometragem=?
            WHERE id=?
        """, (
            cliente, telefone, veiculo, placa,
            problema, diagnostico, total,
            mecanico, status,
            data_entrada, data_saida,
            quilometragem, id
        ))

        ordem_id = id
        cursor.execute("DELETE FROM itens WHERE ordem_id = ?", (ordem_id,))

    else:        
        cursor.execute("""
            INSERT INTO ordens (
                cliente, telefone, veiculo, placa, problema, diagnostico,
                total, tipo, status, mecanico, data_entrada, data_saida, quilometragem
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cliente, telefone, veiculo, placa,
            problema, diagnostico, total,
            "os", status, mecanico,
            datetime.now().strftime("%Y-%m-%d"),
            data_saida,
            quilometragem
        ))        

        ordem_id = cursor.lastrowid

    # 🧰 salvar peças
    for p in pecas:
        cursor.execute("""
            INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ordem_id, "peca", p[0], p[1], p[2], 0))

    # 🔧 salvar serviços
    for s in servicos:
        cursor.execute("""
            INSERT INTO itens (ordem_id, tipo, nome, valor, quantidade, comissao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ordem_id, "servico", s[0], s[1], s[2], int(s[3])))

    conn.commit()

    # 🔥 INTEGRAÇÃO COM RECEITAS
    if status and status.strip().upper() == "FINALIZADA":

        descricao = f"OS #{ordem_id} - {cliente} - {placa}"

        gerar_ou_atualizar_receita_os(
            ordem_id=ordem_id,
            descricao=descricao,
            valor_os=total,
            data=data_saida if data_saida else datetime.now().strftime("%Y-%m-%d")
        )

        conn.close()

    return redirect("/os_lista")

@app.route("/os_lista")
def os_lista():
    if proteger(): return proteger()

    busca = request.args.get("busca", "").strip().lower()

    conn = conectar()
    cursor = conn.cursor()

    query = """
    SELECT 
        o.id,
        o.cliente,
        o.veiculo,
        o.placa,
        o.total,
        o.quilometragem,   -- 🔥 NOVO (posição segura)
        o.tipo,
        o.status,
        o.mecanico,
        MAX(
            CASE

                WHEN COALESCE((
                    SELECT SUM(i2.valor * i2.quantidade)
                    FROM itens i2
                    WHERE i2.ordem_id = o.id
                    AND i2.tipo = 'servico'
                    AND i2.comissao = 1
                ), 0) <= (
                    SELECT limite_baixa
                    FROM mecanicos
                    WHERE nome = o.mecanico
                )

                THEN COALESCE((
                    SELECT SUM(i2.valor * i2.quantidade)
                    FROM itens i2
                    WHERE i2.ordem_id = o.id
                    AND i2.tipo = 'servico'
                    AND i2.comissao = 1
                ), 0) * (
                    SELECT comissao_baixa
                    FROM mecanicos
                    WHERE nome = o.mecanico
                )

                ELSE COALESCE((
                    SELECT SUM(i2.valor * i2.quantidade)
                    FROM itens i2
                    WHERE i2.ordem_id = o.id
                    AND i2.tipo = 'servico'
                    AND i2.comissao = 1
                ), 0) * (
                    SELECT comissao_padrao
                    FROM mecanicos
                    WHERE nome = o.mecanico
                )

            END
        ) as comissao_total
    FROM ordens o
    LEFT JOIN itens i ON o.id = i.ordem_id
    WHERE o.status != 'CANCELADA'
    AND o.tipo = 'os'
    """

    params = []

    # 🔷 PAGINAÇÃO
    pagina = int(request.args.get("pagina", 1))
    por_pagina = 12
    offset = (pagina - 1) * por_pagina

    if busca:
        query += " AND (LOWER(o.cliente) LIKE ? OR LOWER(o.placa) LIKE ?)"
        busca_like = f"%{busca}%"
        params.extend([busca_like, busca_like])

    # 🔷 QUERY TOTAL
    query_total = query
    params_total = params.copy()

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
    # 🔷 TOTAL DE REGISTROS
    cursor.execute(f"""
    SELECT COUNT(*) FROM (
        {query_total}
        GROUP BY o.id
    )
    """, params_total)

    total_registros = cursor.fetchone()[0]

    # 🔷 PAGINAÇÃO SQL
    query += f"""
    LIMIT {por_pagina} OFFSET {offset}
    """


    cursor.execute(query, params)

    ordens = cursor.fetchall()
    total_paginas = (
        total_registros // por_pagina
        + (1 if total_registros % por_pagina else 0)
    )
    conn.close()

    return render_template(
        "os_lista.html",
        ordens=ordens,
        busca=busca,
        pagina=pagina,
        total_paginas=total_paginas
    )

@app.route("/abrir_os/<int:id>")
def abrir_os(id):
    if proteger(): return proteger()

    mecanicos = listar_mecanicos()

    # 🆕 NOVA OS
    if id == 0:
        return render_template(
            "os.html",
            id=0,
            ordem=None,
            pecas=[],
            servicos=[],
            mecanicos=mecanicos
        )

    conn = conectar()
    cursor = conn.cursor()

    # 🔥 SELECT PADRONIZADO (AGORA COM QUILOMETRAGEM)
    cursor.execute("""
        SELECT 
            id,
            cliente,
            telefone,
            veiculo,
            placa,
            problema,
            diagnostico,
            total,
            tipo,
            status,
            mecanico,
            data_entrada,
            data_saida,
            quilometragem
        FROM ordens 
        WHERE id = ?
    """, (id,))
    
    ordem = cursor.fetchone()

    if not ordem:
        conn.close()
        return "OS não encontrada"

    # 🔧 ITENS
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
        ordem=ordem,
        pecas=pecas,
        servicos=servicos,
        mecanicos=mecanicos
    )


@app.route("/converter_os/<int:id>")
def converter_os(id):
    if proteger(): return proteger()

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
    
app.jinja_env.globals.update(formatar_data=formatar_data)

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

    # 🔥 AGORA TRAZ O TIPO
    cursor.execute("""
    SELECT tipo, nome, valor, quantidade FROM itens
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

    caminho = os.path.join(pasta, nome_arquivo)

    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    # 🔷 LOGO
    try:
        c.drawImage("static/logo_housecar.png", largura/2 - 110, altura - 110, width=220, height=80)
    except:
        pass

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura/2, altura - 130, "NOTA DE SERVIÇO")

    y = altura - 170

    # 🔷 CLIENTE
    c.rect(50, y - 80, 500, 80)
    c.line(50, y - 30, 550, y - 30)
    c.line(50, y - 55, 550, y - 55)

    c.setFont("Helvetica", 10)
    c.drawString(60, y - 20, f"Cliente: {cliente}")
    c.drawString(60, y - 45, f"Veículo: {veiculo}")
    c.drawString(60, y - 70, f"Placa: {placa}")

    y -= 100

    # 🔷 DATAS
    c.rect(50, y - 40, 500, 40)
    c.drawString(60, y - 20, f"Entrada: {data_entrada_fmt}")
    c.drawString(220, y - 20, f"Saída: {data_saida_fmt}")
    c.drawString(380, y - 20, f"Mecânico: {mecanico or ''}")

    y -= 60

    # 🔷 TEXTO
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

    caixa_texto("Problema Relatado:", problema, 50)
    caixa_texto("Diagnóstico Técnico / Solução:", diagnostico, 70)

    # 🔥 SEPARAR ITENS
    pecas = []
    servicos = []

    for tipo, nome, valor, qtd in itens:
        if tipo == "peca":
            pecas.append((nome, valor, qtd))
        else:
            servicos.append((nome, valor, qtd))

    # 🔷 FUNÇÃO TABELA
    def desenhar_tabela(titulo, lista):
        nonlocal y

        if not lista:
            return 0

        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(260, y, titulo)
        y -= 14

        altura_linha = 18
        x_inicio = 50
        x_qtd = 100
        x_desc = 420
        x_fim = 550
     

        # 🔷 CABEÇALHO
        c.setFillGray(0.85)
        c.rect(x_inicio, y - altura_linha, x_fim - x_inicio, altura_linha, fill=1, stroke=1)

        c.setFillColorRGB(0,0,0)
        c.setFont("Helvetica-Bold", 10)

        c.drawCentredString(75, y - 13, "QTD")
        c.drawCentredString(260, y - 13, "DESCRIÇÃO")
        c.drawCentredString(480, y - 13, "VALOR")

        y -= altura_linha
        topo = y + altura_linha

        c.setFont("Helvetica", 9)

        subtotal = 0

        # 🔷 LINHAS
        for nome, valor, qtd in lista:

            # 🔥 QUEBRA DE PÁGINA
            if y < 120:
                # 🔥 FECHA TABELA DA PÁGINA ANTERIOR
                base = y

                c.line(x_inicio, topo, x_inicio, base)
                c.line(x_qtd, topo, x_qtd, base)
                c.line(x_desc, topo, x_desc, base)
                c.line(x_fim, topo, x_fim, base)

                c.line(x_inicio, base, x_fim, base)

                c.showPage()
                # 🔷 CABEÇALHO DA NOVA PÁGINA
                try:
                    c.drawImage("static/logo_housecar.png", largura/2 - 110, altura - 110, width=220, height=80)
                except:
                    pass

                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(largura/2, altura - 130, "NOTA DE SERVIÇO")

                y = altura - 155
                
                # 🔷 REPETE CABEÇALHO
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(260, y, titulo)
                y -= 14

                c.setFillGray(0.85)
                c.rect(x_inicio, y - altura_linha, x_fim - x_inicio, altura_linha, fill=1, stroke=1)

                c.setFillColorRGB(0,0,0)
                c.setFont("Helvetica-Bold", 10)

                c.drawCentredString(75, y - 13, "QTD")
                c.drawCentredString(260, y - 13, "DESCRIÇÃO")
                c.drawCentredString(480, y - 13, "VALOR")

                y -= altura_linha
                topo = y + altura_linha

                c.setFont("Helvetica", 9)

            total_item = float(valor) * int(qtd)
            subtotal += total_item

            c.drawCentredString(75, y - 12, str(qtd))
            c.drawString(105, y - 12, nome[:45])
            c.drawRightString(540, y - 12, f"R$ {total_item:.2f}")

            # linha horizontal
            c.line(x_inicio, y - altura_linha, x_fim, y - altura_linha)

            y -= altura_linha
        
        # 🔥 BORDA COMPLETA
        base = y

        # laterais
        c.line(x_inicio, topo, x_inicio, base)
        c.line(x_qtd, topo, x_qtd, base)
        c.line(x_desc, topo, x_desc, base)
        c.line(x_fim, topo, x_fim, base)

        # topo e base
        c.line(x_inicio, topo, x_fim, topo)
        c.line(x_inicio, base, x_fim, base)

        # 🔷 SUBTOTAL ABAIXO DA TABELA
        y -= 18

        c.setFont("Helvetica-Bold", 10)

        c.drawRightString(
            540,
            y,
            f"SUBTOTAL {titulo}: R$ {subtotal:.2f}"
        )

        y -= 30

        return subtotal

    total_pecas = desenhar_tabela("PEÇAS", pecas) or 0
    total_servicos = desenhar_tabela("SERVIÇOS", servicos) or 0

    y -= 10

    
    # 🔷 TOTAL FINAL
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(540, y, f"TOTAL GERAL: R$ {total:.2f}")

    c.save()

    return send_file(caminho, as_attachment=False)

@app.route("/gerar_orcamento/<int:id>")
def gerar_orcamento(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT cliente, veiculo, placa, problema, diagnostico, total,
           data_entrada, mecanico
    FROM ordens
    WHERE id = ? AND tipo = 'orcamento'
    """, (id,))
    ordem = cursor.fetchone()

    if not ordem:
        conn.close()
        return "Orçamento não encontrado"

    cursor.execute("""
    SELECT tipo, nome, valor, quantidade
    FROM itens
    WHERE ordem_id = ?
    """, (id,))
    itens = cursor.fetchall()

    conn.close()

    (cliente, veiculo, placa, problema, diagnostico, total,
     data_entrada, mecanico) = ordem

    data_entrada_fmt = formatar_data(data_entrada)

    import re, textwrap, os
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def limpar_texto(txt):
        return re.sub(r'[^a-zA-Z0-9]', '_', txt or "")

    cliente_limpo = limpar_texto(cliente)
    placa_limpa = limpar_texto(placa)

    nome_arquivo = f"ORC_{id}_{cliente_limpo}_{placa_limpa}.pdf"

    pasta = "notas"
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome_arquivo)

    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    # LOGO
    try:
        c.drawImage("static/logo_housecar.png", largura/2 - 110, altura - 110, width=220, height=80)
    except:
        pass

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura/2, altura - 130, "ORÇAMENTO")

    y = altura - 170

    # CLIENTE
    c.rect(50, y - 80, 500, 80)
    c.line(50, y - 30, 550, y - 30)
    c.line(50, y - 55, 550, y - 55)

    c.setFont("Helvetica", 10)
    c.drawString(60, y - 20, f"Cliente: {cliente}")
    c.drawString(60, y - 45, f"Veículo: {veiculo}")
    c.drawString(60, y - 70, f"Placa: {placa}")

    y -= 100

    # DATA / MECÂNICO
    c.rect(50, y - 40, 500, 40)
    c.drawString(60, y - 20, f"Data: {data_entrada_fmt}")
    c.drawString(320, y - 20, f"Mecânico: {mecanico or ''}")

    y -= 60

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

    caixa_texto("Problema Relatado:", problema, 50)
    caixa_texto("Diagnóstico / Solução:", diagnostico, 70)

    pecas = []
    servicos = []

    for tipo, nome, valor, qtd in itens:
        if tipo == "peca":
            pecas.append((nome, valor, qtd))
        else:
            servicos.append((nome, valor, qtd))

    def desenhar_tabela(titulo, lista):
        nonlocal y

        if not lista:
            return 0

        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, titulo)
        y -= 20

        altura_linha = 18
        x_inicio = 50
        x_qtd = 100
        x_desc = 420
        x_fim = 550

        topo = y

        c.setFillGray(0.85)
        c.rect(x_inicio, y - altura_linha, x_fim - x_inicio, altura_linha, fill=1, stroke=1)

        c.setFillColorRGB(0,0,0)
        c.setFont("Helvetica-Bold", 10)

        c.drawCentredString(75, y - 13, "QTD")
        c.drawCentredString(260, y - 13, "DESCRIÇÃO")
        c.drawCentredString(480, y - 13, "VALOR")

        y -= altura_linha
        c.setFont("Helvetica", 9)

        subtotal = 0

        for nome, valor, qtd in lista:
            total_item = float(valor) * int(qtd)
            subtotal += total_item

            c.drawCentredString(75, y - 12, str(qtd))
            c.drawString(105, y - 12, nome[:45])
            c.drawRightString(540, y - 12, f"R$ {total_item:.2f}")
            c.line(x_inicio, y - altura_linha, x_fim, y - altura_linha)

            y -= altura_linha

        base = y

        c.line(x_inicio, topo, x_inicio, base)
        c.line(x_qtd, topo, x_qtd, base)
        c.line(x_desc, topo, x_desc, base)
        c.line(x_fim, topo, x_fim, base)

        c.line(x_inicio, topo, x_fim, topo)
        c.line(x_inicio, base, x_fim, base)

        y -= 15
        return subtotal

    desenhar_tabela("PEÇAS", pecas)
    desenhar_tabela("SERVIÇOS", servicos)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(540, y, f"TOTAL GERAL: R$ {total:.2f}")

    y -= 30
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Validade do orçamento: 3 dias.")

    c.save()

    return send_file(caminho, as_attachment=False)

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

    from datetime import datetime

    if request.method == "POST":
        descricao = request.form.get("descricao")
        valor = float(request.form.get("valor") or 0)
        forma = request.form.get("forma")
        status = request.form.get("status")

        data = request.form.get("data") or datetime.now().strftime("%Y-%m-%d")

        inserir_receita(
            origem="VENDA",
            ordem_id=None,
            descricao=descricao,
            valor_original=valor,
            valor_final=valor,
            forma=forma,
            status=status,
            data=data
        )

    # 🔥 PAGINAÇÃO
    pagina = int(request.args.get("pagina", 1))
    por_pagina = 10
    offset = (pagina - 1) * por_pagina

    conn = conectar()
    cursor = conn.cursor()

    # 🔢 TOTAL DE REGISTROS
    cursor.execute("SELECT COUNT(*) FROM receitas")
    total_registros = cursor.fetchone()[0]

    # 📋 DADOS ORDENADOS E PAGINADOS
    cursor.execute(f"""
        SELECT * FROM receitas
        ORDER BY 
            CASE 
                WHEN status = 'PENDENTE' THEN 1
                ELSE 2
            END,
            data DESC,
            id DESC
        LIMIT {por_pagina} OFFSET {offset}
    """)

    dados = cursor.fetchall()
    conn.close()

    # 🔢 TOTAL DE PÁGINAS
    total_paginas = (total_registros // por_pagina) + (1 if total_registros % por_pagina else 0)

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
        total_credito=total_credito,
        pagina=pagina,
        total_paginas=total_paginas,
        hoje=datetime.now().strftime("%Y-%m-%d")
    )

from banco import atualizar_receita

@app.route("/editar_receita/<int:id>", methods=["POST"])
def editar_receita(id):
    if proteger(): return proteger()

    valor = float(request.form.get("valor") or 0)
    forma = request.form.get("forma")
    status = request.form.get("status")
    data = request.form.get("data")

    atualizar_receita(id, valor, forma, status, data)

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
            vencimento if vencimento else datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        )

    # 🔥 PAGINAÇÃO
    pagina = int(request.args.get("pagina", 1))
    por_pagina = 10
    offset = (pagina - 1) * por_pagina

    conn = conectar()
    cursor = conn.cursor()

    # 🔢 TOTAL DE REGISTROS
    cursor.execute("SELECT COUNT(*) FROM despesas")
    total_registros = cursor.fetchone()[0]

    # 📋 DADOS PAGINADOS (PARA LISTA)
    cursor.execute(f"""
        SELECT * FROM despesas
        ORDER BY 
            CASE 
                WHEN status = 'PENDENTE' THEN 1
                ELSE 2
            END,
            vencimento DESC,
            id DESC
        LIMIT {por_pagina} OFFSET {offset}
    """)
    dados = cursor.fetchall()

    # 🔥 PEGA TODOS OS DADOS PARA CALCULAR TOTAIS (SEM PAGINAÇÃO)
    cursor.execute("SELECT * FROM despesas")
    todos = cursor.fetchall()

    conn.close()

    total_paginas = (total_registros // por_pagina) + (1 if total_registros % por_pagina else 0)

    # 💸 TOTAL (SÓ PAGAS)
    total = sum([d[2] for d in todos if d[4] == "PAGO"])

    # 💳 POR FORMA (SÓ PAGAS)
    total_pix = sum([d[2] for d in todos if d[3] == "PIX" and d[4] == "PAGO"])
    total_dinheiro = sum([d[2] for d in todos if d[3] == "DINHEIRO" and d[4] == "PAGO"])
    total_debito = sum([d[2] for d in todos if d[3] == "DÉBITO" and d[4] == "PAGO"])
    total_credito = sum([d[2] for d in todos if d[3] == "CRÉDITO" and d[4] == "PAGO"])

    return render_template(
        "despesas.html",
        despesas=dados,
        total=total,
        total_pix=total_pix,
        total_dinheiro=total_dinheiro,
        total_debito=total_debito,
        total_credito=total_credito,
        pagina=pagina,
        total_paginas=total_paginas,
        hoje=datetime.now().strftime("%Y-%m-%d")
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
        logradouro = request.form.get("logradouro")
        numero = request.form.get("numero")
        bairro = request.form.get("bairro")
        cidade = request.form.get("cidade")
        uf = request.form.get("uf")
        cep = request.form.get("cep")
        email = request.form.get("email")

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
        INSERT INTO clientes (
            nome, telefone, documento, data_nascimento,
            cep, logradouro, numero, bairro, cidade, uf, email
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome, telefone, documento, data_nascimento,
            cep, logradouro, numero, bairro, cidade, uf, email
        ))

        cliente_id = cursor.lastrowid

        if veiculo or placa:
            cursor.execute("""
            INSERT INTO veiculos (cliente_id, veiculo, placa)
            VALUES (?, ?, ?)
            """, (cliente_id, veiculo, placa))

        conn.commit()
        conn.close()

        return redirect("/clientes")

    busca = request.args.get("busca", "").strip().lower()

    # 🔷 PAGINAÇÃO
    pagina = int(request.args.get("pagina", 1))
    por_pagina = 10

    dados = listar_clientes()
    dados = sorted(dados, key=lambda c: (c[1] or "").lower())

    if busca:
        dados = [
            c for c in dados
            if busca in (c[1] or "").lower()  # nome
            or busca in (c[13] or "").lower()  # placa
        ]

    # 🔷 TOTAL DE REGISTROS
    total_registros = len(dados)

    # 🔷 TOTAL DE PÁGINAS
    total_paginas = (
        total_registros // por_pagina
        + (1 if total_registros % por_pagina else 0)
    )

    # 🔷 FATIA DA PÁGINA ATUAL
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina

    dados = dados[inicio:fim]
    
    return render_template(
        "clientes.html",
        clientes=dados,
        busca=busca,
        pagina=pagina,
        total_paginas=total_paginas
    )

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

    cep = request.form.get("cep")
    logradouro = request.form.get("logradouro")
    numero = request.form.get("numero")
    bairro = request.form.get("bairro")
    cidade = request.form.get("cidade")
    uf = request.form.get("uf")
    email = request.form.get("email")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE clientes
    SET nome=?, telefone=?, documento=?, data_nascimento=?,
        cep=?, logradouro=?, numero=?, bairro=?, cidade=?, uf=?, email=?
    WHERE id=?
    """, (
        nome, telefone, documento, data_nascimento,
        cep, logradouro, numero, bairro, cidade, uf, email,
        id
    ))

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
    if session.get("tipo") != "admin":
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
    valor = float(request.form.get("valor") or 0)

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

@app.route("/excluir_pagamento/<int:id>")
def excluir_pagamento(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    # 🔥 pega dados antes de apagar (pra achar a despesa)
    cursor.execute("SELECT mecanico, valor, data_pagamento FROM pagamentos WHERE id = ?", (id,))
    pagamento = cursor.fetchone()

    if pagamento:
        mecanico, valor, data = pagamento

        # 🔥 remove pagamento
        cursor.execute("DELETE FROM pagamentos WHERE id = ?", (id,))

        # 🔥 remove despesa vinculada
        cursor.execute("""
        DELETE FROM despesas
        WHERE descricao = ?
        AND valor = ?
        AND data = ?
        """, (f"Pagamento mecânico - {mecanico}", valor, data))

    conn.commit()
    conn.close()

    return redirect("/pagamentos")

@app.route("/editar_pagamento/<int:id>")
def editar_pagamento(id):
    if proteger(): return proteger()

    conn = conectar()
    cursor = conn.cursor()

    pagamento = cursor.execute("""
        SELECT id, mecanico, data_inicio, data_fim, valor
        FROM pagamentos
        WHERE id = ?
    """, (id,)).fetchone()

    mecanicos = cursor.execute("SELECT nome FROM mecanicos").fetchall()

    pagamentos = cursor.execute("""
        SELECT id, mecanico, data_inicio, data_fim, valor
        FROM pagamentos
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "pagamentos.html",
        pagamento_editar=pagamento,
        mecanicos=mecanicos,
        pagamentos=pagamentos
    )

@app.route("/atualizar_pagamento", methods=["POST"])
def atualizar_pagamento():
    if proteger(): return proteger()

    id = request.form.get("id")
    mecanico = request.form.get("mecanico")
    inicio = request.form.get("data_inicio")
    fim = request.form.get("data_fim")
    valor = float(request.form.get("valor") or 0)

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pagamentos
        SET mecanico=?, data_inicio=?, data_fim=?, valor=?
        WHERE id=?
    """, (mecanico, inicio, fim, valor, id))

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
    app.run(host="0.0.0.0", port=5000, debug=True)

