import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional

# =============================
# CONFIG — seul endroit à toucher
# =============================
EXCEL_FILE       = "data/voc_allemand_s5l2.xlsx"
LABEL_A          = "Français"   # colonne 1
LABEL_B          = "Allemand"   # colonne 2
WINDOW_SIZE_DEFAULT = 10
PASS_SCORE_DEFAULT  = 1.5
SCORE_KNOW      = 1.0
SCORE_SOMEWHAT  = 0.5

# =============================
# CSS
# =============================
CSS = """
<style>
.big-prompt {
  font-size: 56px; font-weight: 900;
  line-height: 1.05; margin: 10px 0 18px 0;
}
.big-answer {
  font-size: 48px; font-weight: 800;
  line-height: 1.1; margin: 10px 0 14px 0; opacity: 0.97;
}
.small-muted { opacity: 0.78; }
</style>
"""

# =============================
# Données
# =============================
@dataclass
class Card:
    a: str
    b: str
    score: float = 0.0
    seen: int = 0

# =============================
# Lecture de l'Excel
# =============================
@st.cache_data
def get_sheet_names(filepath: str) -> List[str]:
    xl = pd.ExcelFile(filepath)
    return xl.sheet_names

def load_cards(filepath: str, sheet: str) -> List[Card]:
    df = pd.read_excel(filepath, sheet_name=sheet)
    c1, c2 = df.columns[0], df.columns[1]
    df = df[[c1, c2]].dropna()
    df[c1] = df[c1].astype(str).str.strip()
    df[c2] = df[c2].astype(str).str.strip()
    df = df[(df[c1] != "") & (df[c2] != "")]
    return [Card(a=row[c1], b=row[c2]) for _, row in df.iterrows()]

# =============================
# Session
# =============================
def init_session(sheet: str, window_size: int, pass_score: float):
    cards = load_cards(EXCEL_FILE, sheet)
    w = min(window_size, len(cards))
    st.session_state.deck_name       = sheet
    st.session_state.all_cards       = cards
    st.session_state.pass_score      = float(pass_score)
    st.session_state.window_size     = int(window_size)
    st.session_state.swap            = False
    st.session_state.next_index      = w
    st.session_state.active_indices  = list(range(w))
    st.session_state.active_pos      = 0
    st.session_state.revealed        = False
    st.session_state.validated_count = 0

# =============================
# Logique jeu
# =============================
def get_active_indices() -> List[int]:
    return st.session_state.get("active_indices", [])

def current_card_index() -> Optional[int]:
    idxs = get_active_indices()
    if not idxs:
        return None
    return idxs[st.session_state.active_pos % len(idxs)]

def current_card() -> Optional[Card]:
    i = current_card_index()
    return None if i is None else st.session_state.all_cards[i]

def maybe_refill_window():
    ci = current_card_index()
    if ci is None:
        return
    card = st.session_state.all_cards[ci]
    if card.score < st.session_state.pass_score:
        return
    idxs = get_active_indices()
    pos = st.session_state.active_pos % len(idxs)
    idxs.pop(pos)
    st.session_state.validated_count += 1
    ni = st.session_state.next_index
    if ni < len(st.session_state.all_cards):
        idxs.append(ni)
        st.session_state.next_index += 1
    st.session_state.active_indices = idxs
    st.session_state.active_pos = pos % len(idxs) if idxs else 0
    st.session_state.revealed = False

def advance_to_next():
    idxs = get_active_indices()
    if not idxs:
        return
    st.session_state.active_pos = (st.session_state.active_pos + 1) % len(idxs)
    st.session_state.revealed = False

def answer(action: str):
    card = current_card()
    if card is None:
        return
    first_time = (card.seen == 0)
    card.seen += 1
    if first_time and action == "know":
        card.score = max(card.score, st.session_state.pass_score)
    else:
        if action == "dont":
            card.score = 0.0
        elif action == "somewhat":
            card.score += SCORE_SOMEWHAT
        elif action == "know":
            card.score += SCORE_KNOW
    maybe_refill_window()
    advance_to_next()

# =============================
# App
# =============================
st.set_page_config(page_title="Flashcards — IÉSEG", page_icon="🃏", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

sheets = get_sheet_names(EXCEL_FILE)

# ── Sidebar ──
with st.sidebar:
    st.title("🃏 Flashcards")
    st.caption("IÉSEG — Vocabulaire")
    st.divider()

    st.subheader("📚 Choisir une liste")
    for sheet in sheets:
        if st.button(f"📖 {sheet}", use_container_width=True, key=f"load_{sheet}"):
            init_session(
                sheet,
                st.session_state.get("window_size", WINDOW_SIZE_DEFAULT),
                st.session_state.get("pass_score",  PASS_SCORE_DEFAULT),
            )
            st.rerun()

    st.divider()
    st.subheader("⚙️ Réglages")

    window_size = st.slider(
        "Cartes actives simultanément", 3, 30,
        st.session_state.get("window_size", WINDOW_SIZE_DEFAULT),
        help="Conseillé : 10"
    )
    st.caption("💡 Conseillé : 10")

    pass_score = st.slider(
        "Score pour valider une carte", 1.0, 5.0,
        st.session_state.get("pass_score", PASS_SCORE_DEFAULT),
        0.5, help="Conseillé : 1.5"
    )
    st.caption("💡 Conseillé : 1.5")

    if st.button("🔄 Recommencer depuis zéro", use_container_width=True):
        if "all_cards" in st.session_state:
            init_session(st.session_state.deck_name, int(window_size), float(pass_score))
            st.rerun()

# Appliquer sliders en live
if "all_cards" in st.session_state:
    st.session_state.window_size = int(window_size)
    st.session_state.pass_score  = float(pass_score)

# ── Écran d'accueil ──
if "all_cards" not in st.session_state:
    st.title("🃏 Flashcards")
    st.markdown("### IÉSEG — Vocabulaire")
    st.info("👈 Choisis une liste dans la barre latérale pour commencer !")
    cols = st.columns(min(len(sheets), 3))
    for i, sheet in enumerate(sheets):
        cards_preview = load_cards(EXCEL_FILE, sheet)
        with cols[i % len(cols)]:
            st.markdown(f"#### 📖 {sheet}\n{len(cards_preview)} mots")
    st.stop()

# ── UI principale ──
swap = st.session_state.get("swap", False)
label_a = LABEL_A
label_b = LABEL_B

st.title(f"📖 {st.session_state.deck_name}")

c1, c2 = st.columns([1, 1])
with c1:
    st.caption(f"Mode : {label_b + ' → ' + label_a if swap else label_a + ' → ' + label_b}")
with c2:
    if st.button("🔁 Inverser les langues", use_container_width=True):
        st.session_state.swap = not swap
        st.session_state.revealed = False
        st.rerun()

active_idxs = get_active_indices()
card = current_card()

if not active_idxs or card is None:
    st.success("🎉 Bravo ! Toutes les cartes ont été validées.")
    st.balloons()
    st.stop()

total     = len(st.session_state.all_cards)
validated = st.session_state.validated_count
pos       = (st.session_state.active_pos % len(active_idxs)) + 1

st.progress(validated / total, text=f"Progression : {validated}/{total} cartes validées")
st.caption(f"Carte {pos}/{len(active_idxs)} active · Score seuil : {st.session_state.pass_score:.1f}")

prompt_text  = card.b if swap else card.a
answer_text  = card.a if swap else card.b
prompt_label = label_b if swap else label_a
answer_label = label_a if swap else label_b

st.markdown(f"<div class='small-muted'>Question ({prompt_label})</div>", unsafe_allow_html=True)
st.markdown(f"<div class='big-prompt'>{prompt_text}</div>", unsafe_allow_html=True)

if not st.session_state.revealed:
    if st.button("👀 Afficher la réponse", use_container_width=True):
        st.session_state.revealed = True
        st.rerun()
else:
    st.markdown(f"<div class='small-muted'>Réponse ({answer_label})</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='big-answer'>{answer_text}</div>", unsafe_allow_html=True)
    st.caption(f"Score : {card.score:.1f} / {st.session_state.pass_score:.1f} · Vue {card.seen}x")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("✅ Je sais", use_container_width=True):
            answer("know")
            st.rerun()
    with b2:
        if st.button("🟡 À peu près", use_container_width=True):
            answer("somewhat")
            st.rerun()
    with b3:
        if st.button("❌ Je ne sais pas", use_container_width=True):
            answer("dont")
            st.rerun()

with st.expander("📋 Fenêtre active (scores)"):
    active_cards = [st.session_state.all_cards[i] for i in active_idxs]
    df_active = pd.DataFrame([{
        label_a: c.a, label_b: c.b,
        "Score": c.score, "Vues": c.seen
    } for c in active_cards])
    st.dataframe(df_active, use_container_width=True)
