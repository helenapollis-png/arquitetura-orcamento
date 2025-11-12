# streamlit_app.py — versão visual com fundo oliva, logo centralizada menor
# Rodar com:
#   python3 -m streamlit run streamlit_app.py

import io
import datetime as dt
from typing import Dict, List
import streamlit as st

# ------------------------
# CONFIG E VISUAL
# ------------------------
st.set_page_config(page_title="Calculadora de Orçamentos — Sophia Pollis Arquitetura",
                   page_icon="📐", layout="wide")

# Paleta
OLIVA = "#7A7A52"
BRANCO = "#FFFFFF"
CINZA_CARD = "#F7F7F5"

# Estilos gerais (corrigido para não quebrar ícones da sidebar)
st.markdown(f"""
<style>
/* fundo geral oliva */
.stApp {{
  background: {OLIVA};
}}

/* container principal branco e centralizado */
.block-container {{
  background: {BRANCO};
  border-radius: 18px;
  padding: 28px 36px 36px 36px;
  box-shadow: 0 12px 28px rgba(0,0,0,0.10);
  max-width: 1100px;
  margin: 0 auto;
}}

/* sidebar com leve fundo e botões */
section[data-testid="stSidebar"] > div {{
  background: #F5F4F1;
}}
section[data-testid="stSidebar"] .stButton>button {{
  background: {OLIVA}; color: {BRANCO}; border:0; border-radius:10px;
}}

/* tipografia (não afeta os ícones) */
h1,h2,h3,h4,h5,h6,p,div,label {{
  color: #1A1A1A !important;
  font-family: 'Helvetica Neue', Arial, sans-serif !important;
}}

/* garantir família correta dos ícones/material-icons */
[class*="material-icons"], .material-icons {{
  font-family: 'Material Icons' !important;
}}

/* botões do conteúdo */
.stButton > button {{
  background: {OLIVA};
  color: {BRANCO};
  border: 0;
  padding: 8px 18px;
  border-radius: 10px;
  font-weight: 600;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* card utilitário opcional */
.card {{
  background: {BRANCO};
  border: 1px solid #E9E9E7;
  border-radius: 16px;
  padding: 16px;
  margin: 8px 0 14px 0;
}}
</style>
""", unsafe_allow_html=True)

# Cabeçalho com logo centralizada (menor)
try:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image("logo.png", width=420)  # ajuste se quiser maior/menor
except Exception:
    st.write("")  # segue sem logo se não encontrar o arquivo

st.markdown("### 📐 Calculadora de Orçamentos — Sophia Pollis Arquitetura")
st.caption("Regra: até 40 m² → mínimo R$ 5.000. Acima de 40 m² → R$ 150/m². Depois aplicam-se os multiplicadores.")

# ------------------------
# Helpers
# ------------------------
def moeda(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

# ------------------------
# Parâmetros fixos da regra nova (mantidos)
# ------------------------
MINIMO_VALOR = 5000.0
LIMITE_MINIMO_M2 = 40.0
VALOR_M2_PADRAO = 150.0

MULTIPLIERS = {
    "dificuldade": {"pequena": 1.00, "media": 1.10, "grande": 1.15},
    "natureza": {"nova": 1.00, "reforma": 1.0},
    "acabamento": {"conv": 1.00, "medio": 1.05, "premium": 1.10},
    "urgencia": {"normal": 1.00, "urgente": 1.25},
}

# Fases e pesos padrão (% do subtotal antes dos adicionais)
FASES_DEFAULT = {
    "EP": 20,           # Estudo Preliminar
    "AP": 25,           # Anteprojeto
    "EXEC": 35,         # Executivo
    "OBRA": 20,         # Acompanhamento de Obra
}

ADICIONAIS_DEFAULT = [
    {"id": "visita", "nome": "1ª visita (levantamento)", "preco": 700.0},
    {"id": "render", "nome": "Renderização realista (unid.)", "preco": 250.0},
    {"id": "visitaExtra", "nome": "Visita extra de obra", "preco": 300.0},
    {"id": "compat", "nome": "Compatibilização com terceiros (disciplina)", "preco": 800.0},
]

# ------------------------
# Sidebar
# ------------------------
st.sidebar.header("Parâmetros das Fases (%)")
cols = st.sidebar.columns(4)
pesos = {}
pesos["EP"]   = cols[0].number_input("EP", min_value=0, value=int(FASES_DEFAULT["EP"]), step=1)
pesos["AP"]   = cols[1].number_input("AP", min_value=0, value=int(FASES_DEFAULT["AP"]), step=1)
pesos["EXEC"] = cols[2].number_input("Executivo", min_value=0, value=int(FASES_DEFAULT["EXEC"]), step=1)
pesos["OBRA"] = cols[3].number_input("Obra", min_value=0, value=int(FASES_DEFAULT["OBRA"]), step=1)
soma_pesos = sum(pesos.values())
if soma_pesos == 0:
    st.sidebar.error("Defina ao menos 1% em alguma fase.")
else:
    st.sidebar.caption(f"Soma atual: **{soma_pesos}%** (o cálculo normaliza para 100% se necessário)")

st.sidebar.divider()
st.sidebar.subheader("Adicionais (opcionais)")
extras_escolhidos = []
for ex in ADICIONAIS_DEFAULT:
    with st.sidebar.expander(ex["nome"], expanded=False):
        ativo = st.checkbox("Incluir", value=False, key=f"ck_{ex['id']}")
        preco = st.number_input("Preço (R$)", min_value=0.0, value=float(ex["preco"]), step=50.0, key=f"pr_{ex['id']}")
        qtd   = st.number_input("Qtd", min_value=1, value=1, step=1, key=f"qt_{ex['id']}")
        extras_escolhidos.append((ativo, ex["nome"], preco, qtd))

extra_livre = st.sidebar.number_input("Extra livre (R$)", min_value=0.0, value=0.0, step=50.0)

# ------------------------
# Dados do Projeto
# ------------------------
st.header("Dados do Projeto")
c = st.columns([1,1,1,1,1])

area = c[0].number_input("Área (m²)", min_value=0.0, value=52.0, step=1.0)

DIFICULTADE_OPTS = {"pequena": "Pequena", "media": "Média", "grande": "Grande"}
NATUREZA_OPTS    = {"nova": "Obra nova", "reforma": "Reforma", "retrofit": "Retrofit"}
ACABAMENTO_OPTS  = {"conv": "Convencional", "medio": "Médio-alto", "premium": "Premium"}
URGENCIA_OPTS    = {"normal": "Normal", "urgente": "Urgente"}

sel_dif = c[1].selectbox("Dificuldade", options=list(DIFICULTADE_OPTS.keys()), format_func=lambda k: DIFICULTADE_OPTS[k], index=1)
sel_nat = c[2].selectbox("Natureza", options=list(NATUREZA_OPTS.keys()), format_func=lambda k: NATUREZA_OPTS[k], index=1)
sel_aca = c[3].selectbox("Acabamento", options=list(ACABAMENTO_OPTS.keys()), format_func=lambda k: ACABAMENTO_OPTS[k], index=1)
sel_urg = c[4].selectbox("Urgência", options=list(URGENCIA_OPTS.keys()), format_func=lambda k: URGENCIA_OPTS[k], index=0)

# Seleção de fases incluídas neste orçamento
st.subheader("Fases incluídas")
cc = st.columns(4)
inc_ep   = cc[0].checkbox("Estudo preliminar (EP)", value=True)
inc_ap   = cc[1].checkbox("Anteprojeto (AP)", value=True)
inc_exec = cc[2].checkbox("Executivo (EXEC)", value=True)
inc_obra = cc[3].checkbox("Acompanhamento de obra (OBRA)", value=True)

# ------------------------
# Cálculo (mantido)
# ------------------------
# Base: mínimo 5k até 40 m²; acima disso, 150/m²
if area <= LIMITE_MINIMO_M2:
    base = MINIMO_VALOR
    valor_m2_aplicado = None  # não se aplica
else:
    valor_m2_aplicado = VALOR_M2_PADRAO
    base = area * valor_m2_aplicado
    if base < MINIMO_VALOR:
        base = MINIMO_VALOR  # proteção adicional

# Multiplicadores
mult = (
    MULTIPLIERS["dificuldade"][sel_dif]
    * MULTIPLIERS["natureza"][sel_nat]
    * MULTIPLIERS["acabamento"][sel_aca]
    * MULTIPLIERS["urgencia"][sel_urg]
)

subtotal = base * mult

# Normaliza os pesos se não somarem 100
if soma_pesos == 0:
    norm = {"EP":0,"AP":0,"EXEC":0,"OBRA":0}
else:
    norm = {k: (v / soma_pesos) for k, v in pesos.items()}

# Valores por fase (do subtotal)
fases_valores = {
    "EP":   subtotal * norm["EP"],
    "AP":   subtotal * norm["AP"],
    "EXEC": subtotal * norm["EXEC"],
    "OBRA": subtotal * norm["OBRA"],
}

# Considera apenas as fases marcadas
subtotal_fases_incluidas = 0.0
incluidas = []
if inc_ep:
    subtotal_fases_incluidas += fases_valores["EP"];  incluidas.append(("EP", fases_valores["EP"]))
if inc_ap:
    subtotal_fases_incluidas += fases_valores["AP"];  incluidas.append(("AP", fases_valores["AP"]))
if inc_exec:
    subtotal_fases_incluidas += fases_valores["EXEC"];incluidas.append(("EXEC", fases_valores["EXEC"]))
if inc_obra:
    subtotal_fases_incluidas += fases_valores["OBRA"];incluidas.append(("OBRA", fases_valores["OBRA"]))

# Adicionais
adicionais_total = 0.0
detalhe_adicionais: List[str] = []
for ativo, nome, preco, qtd in extras_escolhidos:
    if ativo:
        valor = preco * max(1, int(qtd))
        adicionais_total += valor
        detalhe_adicionais.append(f"- {nome} ({qtd}×): {moeda(valor)}")

adicionais_total += max(0.0, extra_livre)

# Preço final
preco_final = subtotal_fases_incluidas + adicionais_total

# ------------------------
# Exibição
# ------------------------
st.header("Resultado")
left, right = st.columns([1,2])

with left:
    st.metric("Preço final", moeda(preco_final))
    st.write(f"Base: **{moeda(base)}**")
    st.write(f"Multiplicadores: **× {mult:.3f}**")
    st.write(f"Subtotal (todas as fases): **{moeda(subtotal)}**")
    st.write(f"Subtotal (fases incluídas): **{moeda(subtotal_fases_incluidas)}**")
    st.write(f"Adicionais: **{moeda(adicionais_total)}**")

    st.divider()
    st.write("**Fases (quebrado):**")
    st.write(f"- EP: {moeda(fases_valores['EP'])}")
    st.write(f"- AP: {moeda(fases_valores['AP'])}")
    st.write(f"- EXEC: {moeda(fases_valores['EXEC'])}")
    st.write(f"- OBRA: {moeda(fases_valores['OBRA'])}")

with right:
    hoje = dt.date.today().strftime("%d/%m/%Y")
    linhas = []
    linhas.append("Proposta de Serviços — Arquitetura")
    linhas.append("")
    linhas.append(f"Data: {hoje}")
    linhas.append(f"Área: {area:.0f} m²")
    if valor_m2_aplicado is None:
        linhas.append(f"Regra aplicada: mínimo {moeda(MINIMO_VALOR)} (≤ {LIMITE_MINIMO_M2:.0f} m²)")
    else:
        linhas.append(f"Regra aplicada: {moeda(VALOR_M2_PADRAO)}/m² (> {LIMITE_MINIMO_M2:.0f} m²)")
        linhas.append(f"Base variável (área × R$/m²): {moeda(area * VALOR_M2_PADRAO)}")
    linhas.append(f"Base considerada: {moeda(base)}")
    linhas.append("Multiplicadores:")
    linhas.append(f"  - Dificuldade: × {MULTIPLIERS['dificuldade'][sel_dif]:.2f} ({sel_dif})")
    linhas.append(f"  - Natureza: × {MULTIPLIERS['natureza'][sel_nat]:.2f} ({sel_nat})")
    linhas.append(f"  - Acabamento: × {MULTIPLIERS['acabamento'][sel_aca]:.2f} ({sel_aca})")
    linhas.append(f"  - Urgência: × {MULTIPLIERS['urgencia'][sel_urg]:.2f} ({sel_urg})")
    linhas.append("")
    linhas.append("Quebra por fase (antes dos adicionais):")
    for k, v in [("EP","Estudo Preliminar"),("AP","Anteprojeto"),("EXEC","Executivo"),("OBRA","Acompanhamento de obra")]:
        linhas.append(f"  - {v}: {moeda(fases_valores[k])} ({int(round(norm[k]*100))}% de {moeda(subtotal)})")
    linhas.append("")
    linhas.append("Fases incluídas nesta proposta: " + ", ".join([
        nome for nome, _ in incluidas
    ]) if incluidas else "Nenhuma fase selecionada.")
    linhas.append(f"Subtotal (fases incluídas): {moeda(subtotal_fases_incluidas)}")
    if detalhe_adicionais or extra_livre>0:
        linhas.append("Adicionais:")
        linhas.extend(detalhe_adicionais)
        if extra_livre>0: linhas.append(f"- Extra livre: {moeda(extra_livre)}")
        linhas.append(f"Adicionais total: {moeda(adicionais_total)}")
    linhas.append("")
    linhas.append(f"PREÇO FINAL: {moeda(preco_final)}")

    resumo_txt = "\n".join(linhas)
    st.text_area("Detalhamento / Proposta (copie e edite)", resumo_txt, height=320)
    st.download_button("Baixar resumo (.txt)", data=resumo_txt, file_name="proposta_orcamento.txt", mime="text/plain")

try:
    from docx import Document
    from docx.shared import Pt
    def gerar_docx(texto: str) -> bytes:
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)
        for linha in texto.split("\n"):
            doc.add_paragraph(linha)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.read()
    st.download_button("Baixar proposta (.docx)", data=gerar_docx(resumo_txt),
                       file_name="proposta_orcamento.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
except Exception:
    st.info("Para exportar .docx, instale: pip install python-docx")
