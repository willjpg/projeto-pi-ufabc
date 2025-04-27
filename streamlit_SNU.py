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

    def calculate_final(self, pesos):
        if self.pct_presenca < 25 or not self.grades:
            self.final_letter = 'O'
            return
        soma_pesos = sum(pesos)
        media = sum(self.grades.get(i, 0) * w for i, w in enumerate(pesos, start=1)) / soma_pesos
        if media < 4:
            self.final_letter = 'F'
        elif media < 5:
            self.final_letter = 'D'
        elif media < 6.5:
            self.final_letter = 'C'
        elif media < 8.5:
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

    def setup(self, total_aulas, num_provas, pesos):
        # Inicializa parâmetros do relatório
        self.total_aulas = total_aulas
        self.num_provas = num_provas
        self.pesos = pesos
        logging.info(f"Configuração: aulas={total_aulas}, provas={num_provas}, pesos={pesos}")

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
            aluno.calculate_final(self.pesos)
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

# === Cabeçalho da página ===
st.title("SNU")
st.markdown("#### Sistema de Notas Universitário")

# === Barra lateral: configuração do relatório e importação de RAs ===
st.sidebar.header("Configuração do Relatório")
total_aulas = st.sidebar.number_input('Total de aulas', min_value=1, step=1)
num_provas = st.sidebar.number_input('Número de provas', min_value=1, step=1)
pesos_input = st.sidebar.text_input('Pesos (vírgula)', value=','.join(['1']*int(num_provas)))
if st.sidebar.button('Criar/Resetar Relatório'):
    pesos = list(map(float, pesos_input.split(',')))[:int(num_provas)]
    st.session_state.relatorio = Report()
    st.session_state.relatorio.setup(int(total_aulas), int(num_provas), pesos)
    st.success("Relatório configurado com sucesso.")

arquivo_ras = st.sidebar.file_uploader("Carregar arquivo de RAs (.txt)", type=['txt'])
if arquivo_ras:
    lista_ras = st.session_state.relatorio.load_ra_list(arquivo_ras)
    st.sidebar.write(f"RAs carregados: {len(lista_ras)} alunos")
    if st.sidebar.button('Adicionar RAs com presença'):
        for ra in lista_ras:
            aulas_freq = st.sidebar.number_input(
                f'Aulas frequentadas por {ra}', min_value=0,
                max_value=int(total_aulas), key=f'att_{ra}'
            )
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
    font-size: 16px;
}
</style>
""", unsafe_allow_html=True)

operacoes = {
    "Adicionar Aluno": "Adicionar Aluno 👥➕",
    "Lançar Nota": "Lançar Nota 📝✅",
    "Editar Nota": "Editar Nota ✏️🔄",
    "Excluir Aluno": "Excluir Aluno 👥➖",
    "Excluir Nota": "Excluir Nota 📝❌",
    "Finalizar": "Finalizar 🏁",
    "Resumo": "Resumo 📊",
    "Exportar TXT": "Exportar TXT 📄➡️",
    "Exportar PDF": "Exportar PDF 📄⬇️"
}
cols = st.columns(3)
for idx, (chave, rotulo) in enumerate(operacoes.items()):
    if cols[idx % 3].button(rotulo, key=chave):
        st.session_state.acao = chave

# === Lógica das ações ===
acao = st.session_state.acao
relatorio = st.session_state.relatorio

# 1) Adicionar aluno manualmente
if acao == "Adicionar Aluno":
    ra = st.text_input('RA do aluno', key='ra_add')
    aulas_freq = st.number_input('Aulas frequentadas', min_value=0,
                                max_value=int(relatorio.total_aulas) if relatorio.total_aulas else 0,
                                key='att_add')
    if st.button('Adicionar', key='btn_add') and ra:
        relatorio.add_student(ra, aulas_freq)
        st.success(f"Aluno {ra} adicionado.")

# 2) Lançar nota
elif acao == "Lançar Nota":
    ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_grade')
    prova = st.number_input('Prova', min_value=1, max_value=int(relatorio.num_provas), step=1, key='ex_grade')
    nota = st.number_input('Nota', min_value=0.0, max_value=10.0, step=0.1, key='val_grade')
    if st.button('Lançar', key='btn_grade'):
        relatorio.add_grade(ra, prova, nota)
        st.success(f"Nota {nota} lançada para {ra}.")

# ... (ações Editar, Excluir, Finalizar, Resumo, Exportar seguem padrão similar)
elif acao == "Editar Nota":
    ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_edit')
    exam = st.number_input('Prova', min_value=1, max_value=int(relatorio.num_provas), step=1, key='ex_edit')
    new_grade = st.number_input('Nova Nota', min_value=0.0, max_value=10.0, step=0.1, key='val_edit')
    if st.button('Editar', key='btn_edit'):
        relatorio.edit_grade(ra, exam, new_grade)
        st.success(f"Nota atualizada para {ra}.")

elif acao == "Excluir Aluno":
    ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_del')
    if st.button('Excluir', key='btn_del'):
        relatorio.delete_student(ra)
        st.success(f"Aluno {ra} excluído.")

elif acao == "Excluir Nota":
    ra = st.selectbox('RA', list(relatorio.students.keys()), key='ra_delg')
    exam = st.number_input('Prova', min_value=1, max_value=int(relatorio.num_provas), step=1, key='ex_delg')
    if st.button('Excluir Nota', key='btn_delg'):
        relatorio.delete_grade(ra, exam)
        st.success(f"Nota de {ra} excluída.")

elif acao == "Finalizar":

    if st.button('Calcular Médias', key='btn_fin'):
        relatorio.finalize()
        st.success("Médias calculadas.")


elif acao == "Resumo":
    counts = relatorio.summary()
    total_alunos = sum(counts.values())

    st.subheader("Resumo de Letras 📚")
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


elif acao == "Exportar TXT":
    df = relatorio.to_dataframe()
    txt_buf = df.to_csv(index=False, sep=',')
    st.download_button('Baixar TXT', txt_buf, file_name='relatorio.txt', mime='text/csv', key='btn_txt')

elif acao == "Exportar PDF":
    df = relatorio.to_dataframe()
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

# === Exibição da tabela geral ===
st.header("Visão Geral")
if relatorio.students:
    df = relatorio.to_dataframe()
    st.dataframe(df)
else:
    st.write("Nenhum aluno adicionado ainda.")
