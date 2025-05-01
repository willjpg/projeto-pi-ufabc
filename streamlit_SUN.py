import streamlit as st
import pandas as pd
import logging
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

# === Configuração de logging ===
def setup_logging():
    # Define uma função chamada setup_logging para configurar o sistema de log da aplicação.
    logging.basicConfig(  # Chama a função basicConfig do módulo logging para definir as configurações básicas de log.
        filename='app.log',  # Define o nome do arquivo onde os logs serão salvos ('app.log').
        level=logging.INFO,  # Define o nível mínimo de severidade para capturar os logs (a partir de INFO).
        format='%(asctime)s - %(levelname)s - %(message)s'  # Define o formato das mensagens de log: data/hora, nível e mensagem.
    )
# === Modelos de dados ===
class Student:
    def __init__(self, ra, pct_presenca):
        self.ra = ra
        self.pct_presenca = pct_presenca
        self.grades = {}
        self.final_letter = None

    def calculate_final(self, pesos, nota_min_a, nota_min_b, nota_min_c, nota_min_d, presenca_minima):
        if self.pct_presenca < presenca_minima or not self.grades:
            self.final_letter = 'O'
            return
        soma_pesos = sum(pesos)
        media = sum(self.grades.get(i, 0) * w for i, w in enumerate(pesos, start=1)) / soma_pesos
        if media < nota_min_d:
            self.final_letter = 'F'
        elif media < nota_min_c:
            self.final_letter = 'D'
        elif media < nota_min_b:
            self.final_letter = 'C'
        elif media < nota_min_a:
            self.final_letter = 'B'
        else:
            self.final_letter = 'A'

    def as_list(self, num_provas):
        linha = [self.ra]
        for i in range(1, num_provas + 1):
            linha.append(self.grades.get(i, ''))
        linha.append(self.final_letter)
        return linha

class Report:
    def __init__(self):
        self.students = {}
        self.num_provas = 0
        self.pesos = []
        self.total_aulas = 0
        self.nota_min_a = 8.5
        self.nota_min_b = 6.5
        self.nota_min_c = 5.0
        self.nota_min_d = 4.0
        self.presenca_minima = 25

    def setup(self, total_aulas, num_provas, pesos, nota_min_a, nota_min_b, nota_min_c, nota_min_d, presenca_minima):
        # Inicializa parâmetros do relatório
        self.total_aulas = total_aulas
        self.num_provas = num_provas
        self.pesos = pesos
        self.nota_min_a = nota_min_a
        self.nota_min_b = nota_min_b
        self.nota_min_c = nota_min_c
        self.nota_min_d = nota_min_d
        self.presenca_minima = presenca_minima
        logging.info(f"Configuração: aulas={total_aulas}, provas={num_provas}, pesos={pesos}, notas_min={[nota_min_a, nota_min_b, nota_min_c, nota_min_d]}, presenca_min={presenca_minima}")

    def load_ra_list(self, buffer):
        # Lê RAs de arquivo .txt
        conteudo = StringIO(buffer.getvalue().decode('utf-8'))
        return [linha.strip() for linha in conteudo if linha.strip()]

    def add_student(self, ra, aulas_freq):
        pct = (aulas_freq / self.total_aulas) * 100
        self.students[ra] = Student(ra, pct)
        logging.info(f"Aluno {ra} adicionado, presença {pct:.1f}%")

    def add_grade(self, ra, prova, nota):
        if ra in self.students:
            self.students[ra].grades[prova] = nota
            logging.info(f"Nota {nota} adicionada: RA {ra}, prova {prova}")

    def edit_grade(self, ra, prova, nova_nota):
        if ra in self.students and prova in self.students[ra].grades:
            anterior = self.students[ra].grades[prova]
            self.students[ra].grades[prova] = nova_nota
            logging.info(f"Nota editada: RA {ra}, prova {prova}, {anterior}->{nova_nota}")

    def delete_student(self, ra):
        if ra in self.students:
            del self.students[ra]
            logging.info(f"Aluno {ra} excluído")

    def delete_grade(self, ra, prova):
        if ra in self.students and prova in self.students[ra].grades:
            del self.students[ra].grades[prova]
            logging.info(f"Nota excluída: RA {ra}, prova {prova}")

    def finalize(self):
        # Calcula letra final para todos
        for aluno in self.students.values():
            aluno.calculate_final(self.pesos, self.nota_min_a, self.nota_min_b, self.nota_min_c, self.nota_min_d, self.presenca_minima)
        
        logging.info("Médias finais calculadas")

    def summary(self):
        # Conta letras atribuídas
        contagens = {'A':0,'B':0,'C':0,'D':0,'F':0,'O':0}
        for aluno in self.students.values():
            if aluno.final_letter:
                contagens[aluno.final_letter] += 1
        return contagens

    def to_dataframe(self):
        # Constrói DataFrame para exibir/exportar
        dados = []
        cabecalho = ["RA"] + [f"P{i}" for i in range(1, self.num_provas+1)] + ["MÉDIA"]
        for aluno in self.students.values():
            dados.append(aluno.as_list(self.num_provas))
        return pd.DataFrame(dados, columns=cabecalho)


# === Inicialização do estado do Streamlit e logging ===
setup_logging()
if 'relatorio' not in st.session_state:
    st.session_state.relatorio = Report()

# ==e
st.sidebar.header("Configuração do Relatório")
total_aulas = st.sidebar.number_input('Total de aulas', min_value=1, step=1)
num_provas = st.sidebar.number_input('Número de provas', min_value=1, step=1)
pesos = []
colunas = st.sidebar.columns(int(num_provas))
for i in range(int(num_provas)):
    with colunas[i]:
        peso = st.number_input(f'P{i+1}', min_value=1, value=1, step=1)
        pesos.append(peso)

st.sidebar.markdown("---")
st.sidebar.subheader("Notas Mínimas por Conceito")
nota_min_a = st.sidebar.number_input('Nota mínima para A', min_value=0.0, max_value=10.0, value=8.5, step=0.1)
nota_min_b = st.sidebar.number_input('Nota mínima para B', min_value=0.0, max_value=10.0, value=6.5, step=0.1)
nota_min_c = st.sidebar.number_input('Nota mínima para C', min_value=0.0, max_value=10.0, value=5.0, step=0.1)
nota_min_d = st.sidebar.number_input('Nota mínima para D', min_value=0.0, max_value=10.0, value=4.0, step=0.1)
presenca_minima = st.sidebar.number_input('Porcentagem mínima de ausências', min_value=0, max_value=100, value=25, step=1)

if st.sidebar.button('Criar/Resetar Relatório'):
    st.session_state.relatorio = Report()
    st.session_state.relatorio.setup(int(total_aulas), int(num_provas), pesos, nota_min_a, nota_min_b, nota_min_c, nota_min_d, presenca_minima)
    st.success("Relatório configurado com sucesso.")

arquivo_ras = st.sidebar.file_uploader("Carregar arquivo de RAs (.txt)", type=['txt'])
# Armazena os campos de presença para todos os RAs
if 'presencas' not in st.session_state:
    st.session_state.presencas = {}

# Exibe campos de input para cada RA
if arquivo_ras:
    lista_ras = st.session_state.relatorio.load_ra_list(arquivo_ras)
    st.sidebar.write(f"RAs carregados: {len(lista_ras)} alunos")
    
    st.sidebar.subheader("Frequência dos alunos")
    for ra in lista_ras:
        st.session_state.presencas[ra] = st.sidebar.number_input(
            f'Aulas frequentadas por {ra}',
            min_value=0,
            max_value=int(total_aulas),
            key=f'att_{ra}'
        )

    if st.sidebar.button('Adicionar RAs com presença'):
        for ra in lista_ras:
            aulas_freq = st.session_state.presencas.get(ra, 0)
            if aulas_freq:
                st.session_state.relatorio.add_student(ra, aulas_freq)
        st.sidebar.success('Alunos adicionados via lista.')
st.sidebar.markdown("O aquivo deve seguir essa estrutura: <br> 11202225468 <br> 11202345648 <br> 11202278559 <br> ...", unsafe_allow_html=True)
# === Definição de ações principais ===
if 'acao' not in st.session_state:
    st.session_state.acao = None

# Estiliza todos os botões
st.markdown("""
<style>
div.stButton > button {
    width: 100%;
}
/* Estilo específico para o botão Resumo */
div[data-testid="stButton"] button[data-testid="baseButton-secondary"] {
    width: 100%;
    max-width: 100%;
}
/* === Estica TODO o container principal === */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 0px !important;
            padding-right: 0px !important;
        }
        /* (Opcional) diminui um pouco o padding vertical para aproveitar melhor o espaço */
        .main .block-container .element-container {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
        }
</style>
""", unsafe_allow_html=True)

col_menu, col_content = st.columns([3, 3])

with col_menu:
    # === Cabeçalho da página ===
    st.title("SUN")
    st.markdown("#### Sistema Universitário de Notas")
    # Mostra os botões de ação apenas se houver um relatório configurado
    if hasattr(st.session_state.relatorio, 'total_aulas') and st.session_state.relatorio.total_aulas > 0:
        # Verifica se as médias foram calculadas
        medias_calculadas = any(student.final_letter is not None for student in st.session_state.relatorio.students.values())
        #operacoes = {}

        operacoes = {
            "Adicionar Aluno": "Adicionar Aluno ➕",
            "Excluir Aluno": "Excluir Aluno ➖",
            "Lançar Nota": "Lançar Nota 📝✅",
            "Excluir Nota": "Excluir Nota 📝❌",
            "Editar Nota": "Editar Nota 🔢",
            "Exportar": "Exportar 📄"
        }

        # Botões principais em 3 colunas
        cols = st.columns(2)
        for idx, (chave, rotulo) in enumerate(operacoes.items()):
            if cols[idx % 2].button(rotulo, key=chave):
                st.session_state.acao = chave

        # Botão de resumo com largura total (se as médias foram calculadas)
        #if medias_calculadas:
        if st.button("Finalizar 🏁", key="Finalizar", use_container_width=True):
            relatorio = st.session_state.relatorio
            # só executa se tiver pelo menos um aluno
            if len(relatorio.students) == 0:
                st.warning("Não há alunos adicionados ao relatório")
            else:
                st.session_state.acao = "Finalizar"
        if st.button("Resumo 📊", key="Resumo", use_container_width=True):
            #relatorio = st.session_state.relatorio.students.values()
            # só executa se tiver pelo menos um aluno
            if medias_calculadas == False:
                st.warning("Não há médias caculadas ")
            else:
                st.session_state.acao = "Resumo"
    else:
        st.info("Configure o relatório no menu lateral para começar a usar o sistema.")

    st.divider()

    # === Lógica das ações ===
    acao = st.session_state.acao
    relatorio = st.session_state.relatorio

    if acao == "Adicionar Aluno":
        st.subheader("Adicionar Aluno")
        ra = st.text_input('RA do aluno', key='ra_add')
        aulas_freq = st.number_input('Aulas frequentadas', min_value=0,
                                    max_value=int(relatorio.total_aulas) if relatorio.total_aulas else 0,
                                    key='att_add')
        if st.button('Adicionar', key='btn_add') and ra:
            relatorio.add_student(ra, aulas_freq)
            st.success(f"Aluno {ra} adicionado.")

    elif acao == "Lançar Nota":
        st.subheader("Lançar Nota")
        ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_grade')
        notas = []
        for i in range(1, int(relatorio.num_provas) + 1):
            nota = st.number_input(f'Nota da Prova {i}', min_value=0.0, max_value=10.0, step=0.1, key=f'val_grade_{i}')
            notas.append(nota)
        if st.button('Lançar', key='btn_grade'):
            for i, nota in enumerate(notas, start=1):
                relatorio.add_grade(ra, i, nota)
            st.success(f"Notas lançadas para {ra}.")

    elif acao == "Editar Nota":
         ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_edit')
         exam = st.number_input('Prova', min_value=1, max_value=int(relatorio.num_provas), step=1, key='ex_edit')
         new_grade = st.number_input('Nova Nota', min_value=0.0, max_value=10.0, step=0.1, key='val_edit')
         if st.button('Editar', key='btn_edit'):
             relatorio.edit_grade(ra, exam, new_grade)
             st.success(f"Nota atualizada para {ra}.")

    elif acao == "Excluir Aluno":
        st.subheader("Excluir Aluno")
        ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_del')
        if st.button('Excluir', key='btn_del'):
            relatorio.delete_student(ra)
            st.success(f"Aluno {ra} excluído.")

    elif acao == "Excluir Nota":
        st.subheader("Excluir Nota")
        ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_delg')
        exam = st.number_input('Prova', min_value=1, max_value=int(relatorio.num_provas), step=1, key='ex_delg')
        if st.button('Excluir Nota', key='btn_delg'):
            relatorio.delete_grade(ra, exam)
            st.success(f"Nota de {ra} excluída.")

    elif acao == "Finalizar":
        st.subheader("Finalizar Relatório ✅")
        if st.button('Calcular Médias', key='btn_fin'):
            relatorio.finalize()
            st.success("Médias calculadas.")

    elif acao == "Resumo":
        counts = relatorio.summary()
        total_alunos = sum(counts.values())

        st.subheader("Resumo de Conceitos 📚")
        st.bar_chart(counts)

        st.subheader("Resumo em Percentuais 📈")
        percentuais = {k: (v / total_alunos) * 100 for k, v in counts.items()}
        st.write({k: f"{v:.1f}%" for k, v in percentuais.items()})

        st.subheader("Gráfico de Pizza 🥧")
        df_counts = pd.DataFrame.from_dict(counts, orient='index', columns=['Quantidade'])
        st.pyplot(df_counts.plot.pie(y='Quantidade', autopct='%1.1f%%', figsize=(6, 6), legend=False).figure)
        # Desempenho por prova
        provas = list(range(1, relatorio.num_provas+1))
        stats = {"Prova": [], "Média": [], "Mínima": [], "Máxima": [], "Desvio": []}
        for p in provas:
            notas = [s.grades[p] for s in relatorio.students.values() if p in s.grades]
            if notas:
                stats["Prova"].append(f"P{p}")
                stats["Média"].append(sum(notas)/len(notas))
                stats["Mínima"].append(min(notas))
                stats["Máxima"].append(max(notas))
                stats["Desvio"].append(pd.Series(notas).std())
        df_stats = pd.DataFrame(stats)
        st.subheader("Estatísticas por Prova")
        st.dataframe(df_stats)
        st.bar_chart(df_stats.set_index("Prova")["Média"])

        # Cálculo adicional
        if relatorio.students:
            medias = []
            presencas = []
            reprovados_falta = []
            for s in relatorio.students.values():
                if s.final_letter and s.final_letter != 'O':
                    nota = sum(s.grades.get(i, 0) * w for i, w in enumerate(relatorio.pesos, start=1)) / sum(relatorio.pesos)
                    medias.append(nota)
                if s.pct_presenca is not None:
                    presencas.append(s.pct_presenca)
                if s.final_letter == 'O':
                    reprovados_falta.append(s.ra)

            if medias:
                st.subheader("Notas da Turma 🧮")
                st.write(f"**Média geral:** {sum(medias)/len(medias):.2f}")
                st.write(f"**Nota máxima:** {max(medias):.2f}")
                st.write(f"**Nota mínima:** {min(medias):.2f}")

            if presencas:
                st.subheader("Frequência 📅")
                st.write(f"**Frequência média:** {sum(presencas)/len(presencas):.1f}%")

            if reprovados_falta:
                st.subheader("Reprovados por Falta 🚫")
                st.write(", ".join(reprovados_falta))

    elif acao == "Exportar":
        st.subheader("Exportar Relatório")
        if relatorio.students:
            df = relatorio.to_dataframe()
            # Exportação TXT e PDF lado a lado
            col1, col2 = st.columns(2)

            # Exportação TXT
            txt_buf = df.to_csv(index=False, sep=',')
            st.download_button('Baixar TXT', txt_buf, file_name='relatorio.txt', mime='text/csv', key='btn_txt')

            # Exportação PDF
            buffer = BytesIO()
            data = [df.columns.tolist()] + df.values.tolist()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            table = Table(data)
            style = TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)
            ])
            table.setStyle(style)
            doc.build([table])
            buffer.seek(0)
            st.download_button('Baixar PDF', buffer, file_name='relatorio.pdf', mime='application/pdf', key='btn_pdf')
        else:
            st.info("Adicione alunos ao relatório para poder exportá-lo.")
with col_content:
    # === Exibição da tabela geral ===
    st.title(" ")
    st.markdown("#### Visão Geral")
    
    #st.header("Visão Geral")
    if relatorio.students:
        df = relatorio.to_dataframe()
        st.dataframe(df,use_container_width=True,width=800,height=520,hide_index=True)
    else:
        st.write("Nenhum aluno adicionado ainda.")
