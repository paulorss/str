import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import bcrypt
import plotly.express as px
import plotly.graph_objects as go
import os

# Configuração inicial do Streamlit
st.set_page_config(page_title="CRM Imobiliário", layout="wide", initial_sidebar_state="expanded")

# Inicialização do session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# Funções de Banco de Dados
def init_db():
    conn = sqlite3.connect('crm_imoveis.db')
    c = conn.cursor()
    
    # Atualizar a tabela de usuários para incluir status
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, 
                  username TEXT UNIQUE, 
                  password TEXT, 
                  role TEXT, 
                  nome TEXT, 
                  email TEXT,
                  status TEXT DEFAULT 'ATIVO')''')
    
    # Tabelas de imóveis com todas as colunas necessárias
    c.execute('''CREATE TABLE IF NOT EXISTS imoveis
                 (id INTEGER PRIMARY KEY, 
                  matricula TEXT,
                  endereco TEXT,
                  valor REAL,
                  status TEXT,
                  tipo TEXT,
                  area REAL,
                  quartos INTEGER,
                  banheiros INTEGER,
                  vagas INTEGER,
                  proprietario_id INTEGER,
                  data_cadastro TEXT)''')
    
    # Adicionar tabela de documentos para leads
    c.execute('''CREATE TABLE IF NOT EXISTS documentos_lead
                 (id INTEGER PRIMARY KEY,
                  lead_id INTEGER,
                  tipo TEXT,
                  arquivo_path TEXT,
                  data_upload TEXT,
                  status_validacao TEXT,
                  observacoes TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS documentos_imovel
                 (id INTEGER PRIMARY KEY,
                  imovel_id INTEGER,
                  tipo TEXT,
                  arquivo_path TEXT,
                  data_upload TEXT,
                  status_validacao TEXT,
                  observacoes TEXT)''')
    
    # Adicionar tabela de documentos para leads
    c.execute('''CREATE TABLE IF NOT EXISTS documentos_lead
                 (id INTEGER PRIMARY KEY,
                  lead_id INTEGER,
                  tipo TEXT,
                  arquivo_path TEXT,
                  data_upload TEXT,
                  status_validacao TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS documentos_imovel
                 (id INTEGER PRIMARY KEY,
                  imovel_id INTEGER,
                  tipo TEXT,
                  arquivo_path TEXT,
                  data_upload TEXT,
                  status_validacao TEXT)''')
    
    # Tabelas de leads e relacionamentos
    c.execute('''CREATE TABLE IF NOT EXISTS leads
                 (id INTEGER PRIMARY KEY,
                  nome TEXT,
                  email TEXT,
                  telefone TEXT,
                  origem TEXT,
                  status TEXT,
                  interesse TEXT,
                  data_cadastro TEXT,
                  responsavel_id INTEGER,
                  ultima_interacao TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS interacoes
                 (id INTEGER PRIMARY KEY,
                  tipo TEXT,
                  descricao TEXT,
                  lead_id INTEGER,
                  responsavel_id INTEGER,
                  data_interacao TEXT,
                  resultado TEXT)''')
    
    # Tabelas de pipeline e negócios
    c.execute('''CREATE TABLE IF NOT EXISTS pipeline_vendas
                 (id INTEGER PRIMARY KEY,
                  lead_id INTEGER,
                  imovel_id INTEGER,
                  estagio TEXT,
                  valor_esperado REAL,
                  probabilidade INTEGER,
                  data_entrada TEXT,
                  data_previsao_fechamento TEXT,
                  responsavel_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS negociacoes
                 (id INTEGER PRIMARY KEY,
                  imovel_id INTEGER,
                  cliente_id INTEGER,
                  corretor_id INTEGER,
                  valor_proposto REAL,
                  status TEXT,
                  data_proposta TEXT,
                  data_conclusao TEXT,
                  observacoes TEXT)''')
    
    # Tabelas de agenda e tarefas
    c.execute('''CREATE TABLE IF NOT EXISTS agenda
                 (id INTEGER PRIMARY KEY,
                  tipo TEXT,
                  titulo TEXT,
                  descricao TEXT,
                  data_hora TEXT,
                  duracao INTEGER,
                  participantes TEXT,
                  status TEXT,
                  responsavel_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tarefas
                 (id INTEGER PRIMARY KEY,
                  tipo TEXT,
                  descricao TEXT,
                  relacionado_id INTEGER,
                  tipo_relacionado TEXT,
                  responsavel_id INTEGER,
                  status TEXT,
                  prioridade TEXT,
                  data_criacao TEXT,
                  data_vencimento TEXT)''')
    
    # Criar usuário admin se não existir
    c.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not c.fetchone():
        salt = bcrypt.gensalt()
        password_bytes = 'admin123'.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, salt)
        hashed_str = hashed.decode('utf-8')
        c.execute("INSERT INTO usuarios (username, password, role, nome, email) VALUES (?, ?, ?, ?, ?)",
                 ('admin', hashed_str, 'admin', 'Administrador', 'admin@sistema.com'))
    
    conn.commit()
    return conn

# Funções de Autenticação
def verify_password(stored_password, provided_password):
    stored_password_bytes = stored_password.encode('utf-8')
    provided_password_bytes = provided_password.encode('utf-8')
    try:
        return bcrypt.checkpw(provided_password_bytes, stored_password_bytes)
    except Exception as e:
        print(f"Erro na verificação da senha: {e}")
        return False

def login(username, password):
    conn = init_db()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
        user = c.fetchone()
        
        if user:
            stored_password = user[2]
            if verify_password(stored_password, password):
                st.session_state.user = {
                    'id': user[0],
                    'username': user[1],
                    'role': user[3],
                    'nome': user[4]
                }
                st.session_state.user_role = user[3]
                return True
        return False
    except Exception as e:
        print(f"Erro no login: {e}")
        return False
    finally:
        conn.close()

# Funções CRUD
def create_user(username, password, role, nome, email):
    conn = init_db()
    c = conn.cursor()
    try:
        salt = bcrypt.gensalt()
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, salt)
        hashed_str = hashed.decode('utf-8')
        
        c.execute("""INSERT INTO usuarios (username, password, role, nome, email) 
                     VALUES (?, ?, ?, ?, ?)""", 
                  (username, hashed_str, role, nome, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        return False
    finally:
        conn.close()

def adicionar_lead(nome, email, telefone, origem, interesse, responsavel_id):
    conn = init_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute("""INSERT INTO leads (nome, email, telefone, origem, status, 
                 interesse, data_cadastro, responsavel_id, ultima_interacao)
                 VALUES (?, ?, ?, ?, 'NOVO', ?, ?, ?, ?)""",
              (nome, email, telefone, origem, interesse, now, responsavel_id, now))
    
    lead_id = c.lastrowid
    conn.commit()
    conn.close()
    return lead_id

def adicionar_imovel(matricula, endereco, valor, tipo, area, quartos, banheiros, vagas, proprietario_id):
    conn = init_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute("""INSERT INTO imoveis (matricula, endereco, valor, status, tipo, 
                 area, quartos, banheiros, vagas, proprietario_id, data_cadastro)
                 VALUES (?, ?, ?, 'DISPONÍVEL', ?, ?, ?, ?, ?, ?, ?)""",
              (matricula, endereco, valor, tipo, area, quartos, banheiros, vagas, 
               proprietario_id, now))
    
    imovel_id = c.lastrowid
    conn.commit()
    conn.close()
    return imovel_id

def adicionar_tarefa(tipo, descricao, relacionado_id, tipo_relacionado, responsavel_id, prioridade, data_vencimento):
    conn = init_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute("""INSERT INTO tarefas (tipo, descricao, relacionado_id, tipo_relacionado,
                 responsavel_id, status, prioridade, data_criacao, data_vencimento)
                 VALUES (?, ?, ?, ?, ?, 'PENDENTE', ?, ?, ?)""",
              (tipo, descricao, relacionado_id, tipo_relacionado, responsavel_id,
               prioridade, now, data_vencimento))
    
    tarefa_id = c.lastrowid
    conn.commit()
    conn.close()
    return tarefa_id

# Interfaces
def login_page():
    st.title("Login CRM Imobiliário")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if login(username, password):
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def show_dashboard():
    st.title("Dashboard")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    conn = init_db()
    c = conn.cursor()
    
    with col1:
        c.execute("SELECT COUNT(*) FROM leads WHERE status = 'NOVO'")
        novos_leads = c.fetchone()[0]
        st.metric("Novos Leads", novos_leads)
    
    with col2:
        c.execute("SELECT COUNT(*) FROM imoveis WHERE status = 'DISPONÍVEL'")
        imoveis_disponiveis = c.fetchone()[0]
        st.metric("Imóveis Disponíveis", imoveis_disponiveis)
    
    with col3:
        c.execute("SELECT COUNT(*) FROM pipeline_vendas WHERE estagio = 'NEGOCIAÇÃO'")
        negocios_ativos = c.fetchone()[0]
        st.metric("Negócios Ativos", negocios_ativos)
    
    with col4:
        c.execute("SELECT COUNT(*) FROM tarefas WHERE status = 'PENDENTE'")
        tarefas_pendentes = c.fetchone()[0]
        st.metric("Tarefas Pendentes", tarefas_pendentes)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        pipeline_df = pd.read_sql_query("""
            SELECT estagio, COUNT(*) as quantidade, SUM(valor_esperado) as valor_total
            FROM pipeline_vendas
            GROUP BY estagio
        """, conn)
        
        fig = px.funnel(pipeline_df, 
                       x='quantidade', 
                       y='estagio',
                       title='Funil de Vendas')
        st.plotly_chart(fig)
    
    with col2:
        leads_df = pd.read_sql_query("""
            SELECT origem, COUNT(*) as quantidade
            FROM leads
            GROUP BY origem
        """, conn)
        
        fig = px.pie(leads_df,
                    values='quantidade',
                    names='origem',
                    title='Origem dos Leads')
        st.plotly_chart(fig)
    
    conn.close()

def show_pipeline():
    st.title("Pipeline de Vendas")
    
    # Novo negócio
    with st.expander("Novo Negócio"):
        with st.form("novo_negocio"):
            lead_id = st.number_input("ID do Lead", min_value=1)
            imovel_id = st.number_input("ID do Imóvel", min_value=1)
            valor = st.number_input("Valor Esperado", min_value=0.0)
            previsao = st.date_input("Previsão de Fechamento")
            
            if st.form_submit_button("Criar Negócio"):
                conn = init_db()
                c = conn.cursor()
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                c.execute("""INSERT INTO pipeline_vendas 
                         (lead_id, imovel_id, estagio, valor_esperado, probabilidade,
                          data_entrada, data_previsao_fechamento, responsavel_id)
                         VALUES (?, ?, 'PROSPECÇÃO', ?, 10, ?, ?, ?)""",
                         (lead_id, imovel_id, valor, now, previsao.strftime('%Y-%m-%d'),
                          st.session_state.user['id']))
                
                conn.commit()
                conn.close()
                st.success("Negócio criado com sucesso!")
                st.rerun()
    
    # Kanban do Pipeline
    estagios = ['PROSPECÇÃO', 'QUALIFICAÇÃO', 'PROPOSTA', 'NEGOCIAÇÃO', 'FECHAMENTO']
    cols = st.columns(len(estagios))
    
    conn = init_db()
    for i, estagio in enumerate(estagios):
        with cols[i]:
            st.markdown(f"### {estagio}")
            
            negocios_df = pd.read_sql_query("""
                SELECT p.*, l.nome as lead_nome, i.endereco as imovel
                FROM pipeline_vendas p
                JOIN leads l ON p.lead_id = l.id
                JOIN imoveis i ON p.imovel_id = i.id
                WHERE p.estagio = ?
                AND p.responsavel_id = ?
            """, conn, params=(estagio, st.session_state.user['id']))
            
            for _, negocio in negocios_df.iterrows():
                with st.expander(f"{negocio['lead_nome']} - {negocio['imovel']}"):
                    st.write(f"Valor: R$ {negocio['valor_esperado']:,.2f}")
                    st.write(f"Prob: {negocio['probabilidade']}%")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if i < len(estagios) - 1 and st.button("Avançar", key=f"av_{negocio['id']}"):
                            prox_estagio = estagios[i + 1]
                            nova_prob = min(negocio['probabilidade'] + 20, 100)
                            
                            c = conn.cursor()
                            c.execute("""UPDATE pipeline_vendas 
                                       SET estagio = ?, probabilidade = ?
                                       WHERE id = ?""",
                                    (prox_estagio, nova_prob, negocio['id']))
                            conn.commit()
                            st.rerun()
                    
                    with col2:
                        if st.button("Detalhes", key=f"det_{negocio['id']}"):
                            st.session_state.negocio_selecionado = negocio['id']
    conn.close()

def show_leads():
    st.title("Gestão de Leads/Clientes")
    
    # Novo Lead
    with st.expander("Novo Lead"):
        with st.form("novo_lead"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo")
                email = st.text_input("Email")
                telefone = st.text_input("Telefone")
                cpf = st.text_input("CPF")
            
            with col2:
                origem = st.selectbox(
                    "Origem",
                    ["SITE", "INDICAÇÃO", "REDES_SOCIAIS", "ANÚNCIO", "OUTROS"]
                )
                interesse = st.selectbox(
                    "Interesse",
                    ["COMPRA", "VENDA", "ALUGUEL", "INVESTIMENTO"]
                )
                status = st.selectbox(
                    "Status",
                    ["NOVO", "EM_ATENDIMENTO", "QUALIFICADO", "CONVERTIDO", "PERDIDO"]
                )
                observacoes = st.text_area("Observações")
            
            if st.form_submit_button("Cadastrar Lead"):
                try:
                    # Criar lead
                    lead_id = adicionar_lead(
                        nome, email, telefone, origem, interesse,
                        st.session_state.user['id']
                    )
                    
                    # Criar pasta para documentos
                    pasta_docs = f"documentos/leads/{lead_id}"
                    criar_pasta_se_nao_existe(pasta_docs)
                    
                    st.success(f"Lead cadastrado com sucesso! ID: {lead_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar lead: {e}")
    
    # Lista e Gestão de Leads
    tabs = st.tabs(["Listagem", "Documentos", "Interações", "Análise"])
    
    conn = init_db()
    try:
        # Carregar dados dos leads
        leads_df = pd.read_sql_query("""
            SELECT 
                l.id,
                l.nome,
                l.email,
                l.telefone,
                l.origem,
                l.status,
                l.interesse,
                l.data_cadastro,
                l.responsavel_id,
                l.ultima_interacao as ultima_interacao_lead,
                u.nome as responsavel,
                (SELECT COUNT(*) FROM interacoes i WHERE i.lead_id = l.id) as total_interacoes,
                (SELECT COUNT(*) FROM documentos_lead d WHERE d.lead_id = l.id) as total_documentos,
                (SELECT MAX(data_interacao) FROM interacoes i WHERE i.lead_id = l.id) as ultima_interacao
            FROM leads l
            JOIN usuarios u ON l.responsavel_id = u.id
            WHERE l.responsavel_id = ?
            ORDER BY l.data_cadastro DESC
        """, conn, params=(st.session_state.user['id'],))
        
        with tabs[0]:  # Listagem
            if not leads_df.empty:
                # Filtros
                col1, col2, col3 = st.columns(3)
                with col1:
                    filtro_origem = st.multiselect("Origem", leads_df['origem'].unique())
                with col2:
                    filtro_interesse = st.multiselect("Interesse", leads_df['interesse'].unique())
                with col3:
                    filtro_status = st.multiselect("Status", leads_df['status'].unique())
                
                # Aplicar filtros
                df_filtrado = leads_df.copy()
                if filtro_origem:
                    df_filtrado = df_filtrado[df_filtrado['origem'].isin(filtro_origem)]
                if filtro_interesse:
                    df_filtrado = df_filtrado[df_filtrado['interesse'].isin(filtro_interesse)]
                if filtro_status:
                    df_filtrado = df_filtrado[df_filtrado['status'].isin(filtro_status)]
                
                # Exibir leads
                st.dataframe(
                    df_filtrado.style.format({
                        'data_cadastro': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y %H:%M'),
                        'ultima_interacao': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else 'Sem interações'
                    }),
                    use_container_width=True
                )
            else:
                st.info("Nenhum lead cadastrado")
        
        with tabs[1]:  # Documentos
            if not leads_df.empty:
                lead_selecionado = st.selectbox(
                    "Selecione um lead",
                    leads_df['id'].tolist(),
                    format_func=lambda x: leads_df[leads_df['id'] == x]['nome'].iloc[0]
                )
                
                if lead_selecionado:
                    lead = leads_df[leads_df['id'] == lead_selecionado].iloc[0]
                    st.subheader(f"Documentos de {lead['nome']}")
                    
                    # Upload de documento
                    with st.form("upload_documento"):
                        col1, col2 = st.columns(2)
                        with col1:
                            tipo_doc = st.selectbox(
                                "Tipo de Documento",
                                ["RG", "CPF", "COMPROVANTE_RESIDENCIA", "COMPROVANTE_RENDA", 
                                 "CERTIDAO_CIVIL", "CONTRATO", "OUTROS"]
                            )
                        with col2:
                            arquivo = st.file_uploader(
                                "Selecione o arquivo",
                                type=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx']
                            )
                        
                        observacoes = st.text_area("Observações do documento")
                        
                        if st.form_submit_button("Enviar Documento"):
                            if arquivo:
                                try:
                                    file_path = gerenciar_documento(
                                        'leads', lead_selecionado, arquivo, tipo_doc, observacoes
                                    )
                                    st.success("Documento enviado com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao enviar documento: {e}")
                    
                    # Lista de documentos
                    docs_df = pd.read_sql_query("""
                        SELECT * FROM documentos_lead
                        WHERE lead_id = ?
                        ORDER BY data_upload DESC
                    """, conn, params=(lead_selecionado,))
                    
                    if not docs_df.empty:
                        for _, doc in docs_df.iterrows():
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                st.write(f"📄 {doc['tipo']}")
                                st.caption(f"Enviado em: {doc['data_upload']}")
                            with col2:
                                st.write(f"Status: {doc['status_validacao']}")
                                if doc['observacoes']:
                                    st.caption(doc['observacoes'])
                            with col3:
                                if os.path.exists(doc['arquivo_path']):
                                    with open(doc['arquivo_path'], 'rb') as file:
                                        st.download_button(
                                            label="📥 Download",
                                            data=file,
                                            file_name=os.path.basename(doc['arquivo_path']),
                                            mime="application/octet-stream",
                                            key=f"doc_{doc['id']}"
                                        )
                    else:
                        st.info("Nenhum documento cadastrado")
        
        with tabs[2]:  # Interações
            if not leads_df.empty:
                lead_selecionado = st.selectbox(
                    "Selecione um lead para registrar interação",
                    leads_df['id'].tolist(),
                    format_func=lambda x: leads_df[leads_df['id'] == x]['nome'].iloc[0],
                    key="interacao_select"
                )
                
                if lead_selecionado:
                    lead = leads_df[leads_df['id'] == lead_selecionado].iloc[0]
                    
                    # Nova interação
                    with st.form("nova_interacao"):
                        col1, col2 = st.columns(2)
                        with col1:
                            tipo = st.selectbox(
                                "Tipo de Interação",
                                ["LIGAÇÃO", "EMAIL", "REUNIÃO", "VISITA", "WHATSAPP"]
                            )
                            resultado = st.selectbox(
                                "Resultado",
                                ["POSITIVO", "NEUTRO", "NEGATIVO", "PENDENTE"]
                            )
                        
                        with col2:
                            data_agendamento = st.date_input("Data de Agendamento")
                            hora_agendamento = st.time_input("Hora de Agendamento")
                        
                        descricao = st.text_area("Descrição da Interação")
                        
                        if st.form_submit_button("Registrar Interação"):
                            try:
                                data_hora = datetime.combine(data_agendamento, hora_agendamento)
                                
                                # Registrar interação
                                registrar_interacao(
                                    lead_selecionado,
                                    tipo,
                                    descricao,
                                    resultado,
                                    data_hora,
                                    st.session_state.user['id']
                                )
                                
                                st.success("Interação registrada com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao registrar interação: {e}")
                    
                    # Histórico de interações
                    st.subheader("Histórico de Interações")
                    interacoes_df = pd.read_sql_query("""
                        SELECT i.*, u.nome as responsavel
                        FROM interacoes i
                        JOIN usuarios u ON i.responsavel_id = u.id
                        WHERE i.lead_id = ?
                        ORDER BY i.data_interacao DESC
                    """, conn, params=(lead_selecionado,))
                    
                    if not interacoes_df.empty:
                        for _, interacao in interacoes_df.iterrows():
                            with st.expander(
                                f"{interacao['tipo']} - {pd.to_datetime(interacao['data_interacao']).strftime('%d/%m/%Y %H:%M')}"
                            ):
                                st.write(f"**Responsável:** {interacao['responsavel']}")
                                st.write(f"**Resultado:** {interacao['resultado']}")
                                st.write(f"**Descrição:** {interacao['descricao']}")
                    else:
                        st.info("Nenhuma interação registrada")
        
        with tabs[3]:  # Análise
            if not leads_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Leads por origem
                    origem_counts = leads_df['origem'].value_counts()
                    fig = px.pie(
                        values=origem_counts.values,
                        names=origem_counts.index,
                        title='Leads por Origem'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Leads por interesse
                    interesse_counts = leads_df['interesse'].value_counts()
                    fig = px.bar(
                        x=interesse_counts.index,
                        y=interesse_counts.values,
                        title='Leads por Interesse'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Timeline de leads
                leads_por_dia = pd.read_sql_query("""
                    SELECT DATE(data_cadastro) as data, COUNT(*) as quantidade
                    FROM leads
                    WHERE responsavel_id = ?
                    GROUP BY DATE(data_cadastro)
                    ORDER BY data
                """, conn, params=(st.session_state.user['id'],))
                
                if not leads_por_dia.empty:
                    fig = px.line(
                        leads_por_dia,
                        x='data',
                        y='quantidade',
                        title='Evolução de Leads'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados suficientes para análise")
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
    finally:
        conn.close()

def show_agenda():
    st.title("Agenda")
    
    # Nova atividade
    with st.expander("Nova Atividade"):
        with st.form("nova_atividade"):
            tipo = st.selectbox("Tipo", ["VISITA", "REUNIÃO", "LIGAÇÃO", "VISTORIA"])
            titulo = st.text_input("Título")
            descricao = st.text_area("Descrição")
            
            # Separar data e hora em campos distintos
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Data")
            with col2:
                hora = st.time_input("Hora")
            
            duracao = st.number_input("Duração (minutos)", min_value=15, step=15)
            participantes = st.text_input("Participantes (separados por vírgula)")
            
            if st.form_submit_button("Agendar"):
                conn = init_db()
                c = conn.cursor()
                
                # Combinar data e hora
                data_hora = datetime.combine(data, hora)
                
                try:
                    c.execute("""INSERT INTO agenda 
                               (tipo, titulo, descricao, data_hora, duracao, 
                                participantes, status, responsavel_id)
                               VALUES (?, ?, ?, ?, ?, ?, 'AGENDADO', ?)""",
                             (tipo, titulo, descricao, data_hora.strftime('%Y-%m-%d %H:%M:%S'),
                              duracao, participantes, st.session_state.user['id']))
                    
                    conn.commit()
                    st.success("Atividade agendada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao agendar atividade: {e}")
                finally:
                    conn.close()
    
    # Calendário
    st.subheader("Calendário")
    hoje = datetime.now()
    semana_inicio = hoje - timedelta(days=hoje.weekday())
    
    # View semanal
    dias_semana = []
    for i in range(7):
        dia = semana_inicio + timedelta(days=i)
        dias_semana.append(dia)
    
    cols = st.columns(7)
    for i, dia in enumerate(dias_semana):
        with cols[i]:
            st.write(dia.strftime('%d/%m'))
            
            conn = init_db()
            try:
                atividades_df = pd.read_sql_query("""
                    SELECT * FROM agenda 
                    WHERE DATE(data_hora) = ? 
                    AND responsavel_id = ?
                    ORDER BY data_hora
                """, conn, params=(dia.strftime('%Y-%m-%d'), st.session_state.user['id']))
                
                for _, atividade in atividades_df.iterrows():
                    with st.expander(f"{datetime.strptime(atividade['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')} - {atividade['titulo']}"):
                        st.write(f"Tipo: {atividade['tipo']}")
                        st.write(f"Descrição: {atividade['descricao']}")
                        st.write(f"Participantes: {atividade['participantes']}")
                        
                        if atividade['status'] == 'AGENDADO':
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Concluir", key=f"conc_{atividade['id']}"):
                                    c = conn.cursor()
                                    c.execute("UPDATE agenda SET status = 'CONCLUÍDO' WHERE id = ?",
                                             (atividade['id'],))
                                    conn.commit()
                                    st.rerun()
                            
                            with col2:
                                if st.button("Cancelar", key=f"canc_{atividade['id']}"):
                                    c = conn.cursor()
                                    c.execute("UPDATE agenda SET status = 'CANCELADO' WHERE id = ?",
                                             (atividade['id'],))
                                    conn.commit()
                                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao carregar atividades: {e}")
            finally:
                conn.close()
    
    # Visão Mensal (opcional)
    if st.checkbox("Mostrar Visão Mensal"):
        st.subheader("Visão Mensal")
        mes_atual = hoje.replace(day=1)
        
        conn = init_db()
        try:
            atividades_mes_df = pd.read_sql_query("""
                SELECT data_hora, COUNT(*) as total_atividades
                FROM agenda
                WHERE strftime('%Y-%m', data_hora) = ?
                AND responsavel_id = ?
                GROUP BY DATE(data_hora)
                ORDER BY data_hora
            """, conn, params=(mes_atual.strftime('%Y-%m'), st.session_state.user['id']))
            
            if not atividades_mes_df.empty:
                fig = px.bar(atividades_mes_df, 
                           x='data_hora', 
                           y='total_atividades',
                           title='Atividades por Dia')
                st.plotly_chart(fig)
            else:
                st.info("Nenhuma atividade agendada para este mês.")
                
        except Exception as e:
            st.error(f"Erro ao carregar visão mensal: {e}")
        finally:
            conn.close()



def show_imoveis_interface():
    st.title("Gestão de Imóveis")
    
    # Novo Imóvel
    with st.expander("Novo Imóvel"):
        with st.form("novo_imovel"):
            col1, col2 = st.columns(2)
            
            with col1:
                matricula = st.text_input("Matrícula")
                endereco = st.text_input("Endereço")
                valor = st.number_input("Valor", min_value=0.0, step=1000.0)
                tipo = st.selectbox("Tipo", ["CASA", "APARTAMENTO", "TERRENO", "COMERCIAL"])
            
            with col2:
                area = st.number_input("Área (m²)", min_value=0.0)
                quartos = st.number_input("Quartos", min_value=0)
                banheiros = st.number_input("Banheiros", min_value=0)
                vagas = st.number_input("Vagas de Garagem", min_value=0)
            
            if st.form_submit_button("Cadastrar Imóvel"):
                try:
                    imovel_id = adicionar_imovel(
                        matricula, endereco, valor, tipo, area, quartos, 
                        banheiros, vagas, st.session_state.user['id']
                    )
                    # Criar pasta para documentos do imóvel
                    criar_pasta_se_nao_existe(f"documentos/imoveis/{imovel_id}")
                    st.success(f"Imóvel cadastrado com sucesso! ID: {imovel_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar imóvel: {e}")
    
    # Lista de Imóveis
    tab1, tab2 = st.tabs(["Imóveis", "Análise"])
    
    with tab1:
        conn = init_db()
        imoveis_df = pd.read_sql_query("""
            SELECT i.*, u.nome as proprietario,
                   (SELECT COUNT(*) FROM pipeline_vendas p WHERE p.imovel_id = i.id 
                    AND p.estagio IN ('PROPOSTA', 'NEGOCIAÇÃO')) as negociacoes_ativas,
                   (SELECT COUNT(*) FROM documentos_imovel d WHERE d.imovel_id = i.id) as total_documentos
            FROM imoveis i
            JOIN usuarios u ON i.proprietario_id = u.id
            ORDER BY i.data_cadastro DESC
        """, conn)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            tipos_disponiveis = sorted(imoveis_df['tipo'].unique())
            filtro_tipo = st.multiselect("Tipo", tipos_disponiveis)
        with col2:
            status_disponiveis = sorted(imoveis_df['status'].unique())
            filtro_status = st.multiselect("Status", status_disponiveis)
        with col3:
            valor_min = st.number_input("Valor Mínimo", min_value=0.0, step=10000.0)
            valor_max = st.number_input("Valor Máximo", min_value=0.0, step=10000.0)
        
        # Aplicar filtros
        df_filtrado = imoveis_df.copy()
        if filtro_tipo:
            df_filtrado = df_filtrado[df_filtrado['tipo'].isin(filtro_tipo)]
        if filtro_status:
            df_filtrado = df_filtrado[df_filtrado['status'].isin(filtro_status)]
        if valor_max > 0:
            df_filtrado = df_filtrado[
                (df_filtrado['valor'] >= valor_min) & 
                (df_filtrado['valor'] <= valor_max)
            ]
        
        # Exibir imóveis
        st.dataframe(
            df_filtrado.style.format({
                'valor': 'R$ {:,.2f}',
                'area': '{:.1f} m²'
            }),
            use_container_width=True
        )
        
        # Seleção de imóvel para detalhes
        imovel_selecionado = st.selectbox(
            "Selecione um imóvel para ver detalhes",
            df_filtrado['id'].tolist(),
            format_func=lambda x: df_filtrado[df_filtrado['id'] == x]['endereco'].iloc[0]
        )
        
        if imovel_selecionado:
            imovel = df_filtrado[df_filtrado['id'] == imovel_selecionado].iloc[0]
            
            st.markdown("---")
            st.subheader(f"Detalhes do Imóvel: {imovel['endereco']}")
            
            # Informações básicas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Valor", f"R$ {imovel['valor']:,.2f}")
                st.metric("Área", f"{imovel['area']} m²")
            with col2:
                st.metric("Quartos", imovel['quartos'])
                st.metric("Banheiros", imovel['banheiros'])
            with col3:
                st.metric("Vagas", imovel['vagas'])
                st.metric("Documentos", imovel['total_documentos'])
            
            # Documentos do imóvel
            st.subheader("Documentos")
            doc_tab1, doc_tab2 = st.tabs(["Lista de Documentos", "Upload"])
            
            with doc_tab1:
                documentos_df = pd.read_sql_query("""
                    SELECT * FROM documentos_imovel
                    WHERE imovel_id = ?
                    ORDER BY data_upload DESC
                """, conn, params=(imovel['id'],))
                
                if not documentos_df.empty:
                    for _, doc in documentos_df.iterrows():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.write(f"📄 {doc['tipo']}")
                            st.caption(f"Enviado em: {doc['data_upload']}")
                        with col2:
                            st.write(f"Status: {doc['status_validacao']}")
                        with col3:
                            if os.path.exists(doc['arquivo_path']):
                                with open(doc['arquivo_path'], 'rb') as file:
                                    st.download_button(
                                        label="📥 Download",
                                        data=file,
                                        file_name=os.path.basename(doc['arquivo_path']),
                                        mime="application/octet-stream",
                                        key=f"doc_{doc['id']}"
                                    )
                else:
                    st.info("Nenhum documento cadastrado para este imóvel")
            
            with doc_tab2:
                with st.form("upload_doc_imovel"):
                    tipo_doc = st.selectbox(
                        "Tipo de Documento",
                        ["MATRICULA", "IPTU", "ESCRITURA", "CERTIDAO", "PLANTA", 
                         "FOTO", "VISTORIA", "CONTRATO", "OUTROS"]
                    )
                    arquivo = st.file_uploader(
                        "Selecione o arquivo",
                        type=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx']
                    )
                    observacao = st.text_area("Observações", height=100)
                    
                    if st.form_submit_button("Enviar Documento"):
                        if arquivo:
                            try:
                                file_path = gerenciar_documento(
                                    'imoveis',
                                    imovel['id'],
                                    arquivo,
                                    tipo_doc,
                                    observacao
                                )
                                st.success("Documento enviado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao enviar documento: {e}")
                        else:
                            st.warning("Por favor, selecione um arquivo")
    
    with tab2:
        if not df_filtrado.empty:
            # Análises
            col1, col2 = st.columns(2)
            
            with col1:
                # Imóveis por tipo
                tipo_counts = df_filtrado['tipo'].value_counts()
                fig = px.pie(
                    values=tipo_counts.values,
                    names=tipo_counts.index,
                    title='Distribuição por Tipo de Imóvel'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Valor médio por tipo
                valor_medio = df_filtrado.groupby('tipo')['valor'].mean()
                fig = px.bar(
                    x=valor_medio.index,
                    y=valor_medio.values,
                    title='Valor Médio por Tipo (R$)',
                    labels={'x': 'Tipo', 'y': 'Valor Médio'}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para análise")
    
    conn.close()


def show_admin_users():
    st.title("Gestão de Usuários")
    
    # Novo Usuário
    with st.expander("Criar Novo Usuário"):
        with st.form("novo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Username")
                password = st.text_input("Senha", type="password")
                confirm_password = st.text_input("Confirmar Senha", type="password")
                role = st.selectbox("Função", [
                    "admin", "corretor", "analista", "assistente"
                ])
            
            with col2:
                nome = st.text_input("Nome Completo")
                email = st.text_input("Email")
            
            if st.form_submit_button("Criar Usuário"):
                if password != confirm_password:
                    st.error("As senhas não conferem!")
                else:
                    try:
                        if create_user(username, password, role, nome, email):
                            st.success("Usuário criado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Username já existe!")
                    except Exception as e:
                        st.error(f"Erro ao criar usuário: {e}")
    
    # Lista de Usuários
    st.subheader("Usuários Cadastrados")
    
    conn = init_db()
    try:
        # Query simplificada
        usuarios_df = pd.read_sql_query("""
            SELECT id, username, role, nome, email
            FROM usuarios
            WHERE username != 'admin'
            ORDER BY nome
        """, conn)
        
        # Exibir tabela de usuários
        st.dataframe(usuarios_df, use_container_width=True)
        
        # Editar Usuário
        st.subheader("Editar Usuário")
        col1, col2 = st.columns(2)
        
        with col1:
            if not usuarios_df.empty:
                usuario_id = st.selectbox("Selecione o Usuário", 
                                        options=usuarios_df['id'].tolist(),
                                        format_func=lambda x: usuarios_df[usuarios_df['id'] == x]['nome'].iloc[0])
                
                if usuario_id:
                    usuario = usuarios_df[usuarios_df['id'] == usuario_id].iloc[0]
                    
                    with st.form("editar_usuario"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            novo_role = st.selectbox("Nova Função", 
                                                   ["admin", "corretor", "analista", "assistente"],
                                                   index=["admin", "corretor", "analista", "assistente"].index(usuario['role']))
                            novo_nome = st.text_input("Novo Nome", value=usuario['nome'])
                            novo_email = st.text_input("Novo Email", value=usuario['email'])
                        
                        with col2:
                            nova_senha = st.text_input("Nova Senha (deixe em branco para manter)", type="password")
                            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
                        
                        if st.form_submit_button("Atualizar Usuário"):
                            try:
                                if nova_senha:
                                    if nova_senha != confirmar_senha:
                                        st.error("As senhas não conferem!")
                                        return
                                    
                                    # Atualizar com nova senha
                                    salt = bcrypt.gensalt()
                                    hashed = bcrypt.hashpw(nova_senha.encode('utf-8'), salt)
                                    hashed_str = hashed.decode('utf-8')
                                    
                                    c = conn.cursor()
                                    c.execute("""UPDATE usuarios 
                                               SET role = ?, nome = ?, email = ?, password = ?
                                               WHERE id = ?""",
                                             (novo_role, novo_nome, novo_email, hashed_str, usuario_id))
                                else:
                                    # Atualizar sem mudar a senha
                                    c = conn.cursor()
                                    c.execute("""UPDATE usuarios 
                                               SET role = ?, nome = ?, email = ?
                                               WHERE id = ?""",
                                             (novo_role, novo_nome, novo_email, usuario_id))
                                
                                conn.commit()
                                st.success("Usuário atualizado com sucesso!")
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"Erro ao atualizar usuário: {e}")
            else:
                st.info("Nenhum usuário cadastrado além do administrador.")
    
    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")
    finally:
        conn.close()
    
    # Desativar/Reativar Usuário
    st.subheader("Gerenciar Status do Usuário")
    col1, col2 = st.columns(2)
    
    with col1:
        usuario_status_id = st.selectbox(
            "Selecione o Usuário para Gerenciar Status", 
            options=usuarios_df['id'].tolist(),
            format_func=lambda x: usuarios_df[usuarios_df['id'] == x]['nome'].iloc[0],
            key="status_select"
        )
    
    if usuario_status_id:
        with col2:
            if st.button("Desativar/Reativar Usuário"):
                try:
                    conn = init_db()
                    c = conn.cursor()
                    
                    # Verificar status atual
                    c.execute("SELECT status FROM usuarios WHERE id = ?", (usuario_status_id,))
                    status_atual = c.fetchone()[0] if c.fetchone() else 'ATIVO'
                    
                    # Inverter status
                    novo_status = 'INATIVO' if status_atual == 'ATIVO' else 'ATIVO'
                    
                    c.execute("UPDATE usuarios SET status = ? WHERE id = ?",
                             (novo_status, usuario_status_id))
                    
                    conn.commit()
                    st.success(f"Usuário {novo_status.lower()} com sucesso!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao atualizar status: {e}")
                finally:
                    conn.close()



def criar_pasta_se_nao_existe(path):
    if not os.path.exists(path):
        os.makedirs(path)

def gerenciar_documento(entidade_tipo, entidade_id, arquivo, tipo_doc, observacao=''):
    # Criar estrutura de pastas
    base_path = f"documentos/{entidade_tipo}/{entidade_id}"
    criar_pasta_se_nao_existe(base_path)
    
    # Gerar nome único para o arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = arquivo.name.split('.')[-1]
    novo_nome = f"{tipo_doc}_{timestamp}.{ext}"
    file_path = os.path.join(base_path, novo_nome)
    
    # Salvar arquivo
    with open(file_path, "wb") as f:
        f.write(arquivo.getbuffer())
    
    # Registrar no banco
    conn = init_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if entidade_tipo == 'imoveis':
        c.execute("""INSERT INTO documentos_imovel 
                   (imovel_id, tipo, arquivo_path, data_upload, status_validacao, observacoes)
                   VALUES (?, ?, ?, ?, 'PENDENTE', ?)""",
                 (entidade_id, tipo_doc, file_path, now, observacao))
    elif entidade_tipo == 'leads':
        c.execute("""INSERT INTO documentos_lead 
                   (lead_id, tipo, arquivo_path, data_upload, status_validacao, observacoes)
                   VALUES (?, ?, ?, ?, 'PENDENTE', ?)""",
                 (entidade_id, tipo_doc, file_path, now, observacao))
    
    conn.commit()
    conn.close()
    return file_path






def show_admin_relatorios():
    st.title("Relatórios Administrativos")
    
    # Seleção de período
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início")
    with col2:
        data_fim = st.date_input("Data Fim")
    
    data_inicio_str = data_inicio.strftime('%Y-%m-%d')
    data_fim_str = data_fim.strftime('%Y-%m-%d')
    
    conn = init_db()
    try:
        # Métricas Gerais
        col1, col2, col3, col4 = st.columns(4)
        
        # Total de Imóveis
        with col1:
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*) FROM imoveis 
                WHERE DATE(data_cadastro) BETWEEN ? AND ?
            """, (data_inicio_str, data_fim_str))
            total_imoveis = c.fetchone()[0]
            st.metric("Total de Imóveis", total_imoveis)
        
        # Total de Leads
        with col2:
            c.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE DATE(data_cadastro) BETWEEN ? AND ?
            """, (data_inicio_str, data_fim_str))
            total_leads = c.fetchone()[0]
            st.metric("Novos Leads", total_leads)
        
        # Valor Total em Negociação
        with col3:
            c.execute("""
                SELECT SUM(valor_proposto) FROM negociacoes 
                WHERE DATE(data_proposta) BETWEEN ? AND ?
                AND status IN ('PROPOSTA', 'NEGOCIAÇÃO')
            """, (data_inicio_str, data_fim_str))
            valor_negociacao = c.fetchone()[0] or 0
            st.metric("Em Negociação", f"R$ {valor_negociacao:,.2f}")
        
        # Taxa de Conversão
        with col4:
            c.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM negociacoes 
                     WHERE status = 'CONCLUIDA' 
                     AND DATE(data_proposta) BETWEEN ? AND ?) * 100.0 / 
                    NULLIF((SELECT COUNT(*) FROM negociacoes 
                     WHERE DATE(data_proposta) BETWEEN ? AND ?), 0)
            """, (data_inicio_str, data_fim_str, data_inicio_str, data_fim_str))
            taxa_conversao = c.fetchone()[0] or 0
            st.metric("Taxa de Conversão", f"{taxa_conversao:.1f}%")
      
    finally:
        conn.close()

# Função auxiliar para registrar uma negociação:
def registrar_negociacao(imovel_id, cliente_id, corretor_id, valor_proposto, status='PROPOSTA'):
    conn = init_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        c.execute("""INSERT INTO negociacoes 
                     (imovel_id, cliente_id, corretor_id, valor_proposto, 
                      status, data_proposta)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (imovel_id, cliente_id, corretor_id, valor_proposto, 
                   status, now))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"Erro ao registrar negociação: {e}")
        return None
    finally:
        conn.close()


def main():
    if not st.session_state.user:
        login_page()
    else:
        st.sidebar.title(f"Bem-vindo, {st.session_state.user['nome']}")
        
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.session_state.user_role = None
            st.rerun()
        
        # Menu diferente para administradores
        if st.session_state.user_role == 'admin':
            menu = ["Dashboard", "Usuários", "Fluxograma", "Clientes", "Imóveis", "Agenda", "Relatórios"]
        else:
            menu = ["Dashboard", "Fluxograma", "Clientes", "Imóveis", "Agenda", "Relatórios"]
        
        choice = st.sidebar.selectbox("Menu", menu)
        
        if choice == "Dashboard":
            show_dashboard()
        elif choice == "Usuários" and st.session_state.user_role == 'admin':
            show_admin_users()
        elif choice == "Fluxograma":
            show_pipeline()
        elif choice == "Clientes":
            show_leads()
        elif choice == "Imóveis":
            show_imoveis_interface()
        elif choice == "Agenda":
            show_agenda()
        elif choice == "Relatórios":
            show_admin_relatorios()

if __name__ == '__main__':
    main()