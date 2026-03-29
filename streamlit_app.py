"""
Interface Streamlit — Système Intelligent de Compression Audio.

Tableau de bord interactif pour :
- Uploader un fichier audio
- Lancer l'analyse (extraction des caractéristiques)
- Voir la décision de compression (locale ou via n8n/LLM)
- Lancer la compression
- Évaluer la qualité
- Générer et télécharger un rapport

Lancer avec : streamlit run streamlit_app.py
"""

import io
import json
import base64
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# ── Configuration ─────────────────────────────────────────────────────────────

API_URL = "http://localhost:5001"
N8N_WEBHOOK_URL = "https://ibrah1111.app.n8n.cloud/webhook/analyse-audio"
N8N_WEBHOOK_TEST_URL = "https://ibrah1111.app.n8n.cloud/webhook-test/analyse-audio"

st.set_page_config(
    page_title="🎵 Compression Audio Intelligente",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles CSS (Light Mode) ──────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    /* ── Light mode base ── */
    .stApp {
        background-color: #f5f7fa;
        color: #1a1a2e;
    }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.25);
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .main-header-logo {
        width: 72px;
        height: 72px;
        object-fit: contain;
        border-radius: 10px;
        background: white;
        padding: 4px;
        flex-shrink: 0;
    }
    .main-header-text h1 { margin: 0; font-size: 1.7rem; font-weight: 700; }
    .main-header-text p  { margin: 0.3rem 0 0 0; opacity: 0.9; font-size: 0.95rem; }

    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(102,126,234,0.15); }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card .label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.3rem;
        font-weight: 600;
    }

    .step-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 0.8rem;
    }

    .quality-good  { color: #16a34a; font-weight: 700; font-size: 1.2rem; }
    .quality-medium { color: #d97706; font-weight: 700; font-size: 1.2rem; }
    .quality-bad   { color: #dc2626; font-weight: 700; font-size: 1.2rem; }

    .team-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.85rem;
        text-align: center;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .team-card .name { font-weight: 600; font-size: 0.9rem; color: #1a1a2e; }
    .team-card .role { font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; }

    div[data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #e2e8f0;
    }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s;
        width: 100%;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
        transform: translateY(-1px);
    }

    /* Streamlit widget overrides for light mode */
    .stTextInput > div > div > input {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        color: #1a1a2e;
    }
    .stSelectbox > div > div {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
    }
    hr { border-color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)


# ── Fonctions utilitaires ─────────────────────────────────────────────────────

def check_api():
    """Vérifie si l'API est accessible."""
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def make_metric_card(value, label):
    """Crée une carte métrique HTML."""
    return f"""
    <div class="metric-card">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """


def quality_badge(label):
    """Retourne un badge coloré selon la qualité."""
    css_class = {
        "bonne": "quality-good",
        "moyenne": "quality-medium",
        "faible": "quality-bad",
    }.get(label, "quality-medium")
    emoji = {"bonne": "✅", "moyenne": "⚠️", "faible": "❌"}.get(label, "❓")
    return f'<span class="{css_class}">{emoji} {label.upper()}</span>'


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # Logo at TOP of sidebar
    try:
        with open("logo.jpeg", "rb") as f:
            logo_b64_side = base64.b64encode(f.read()).decode()
        st.markdown(
            f"<div style='text-align:center;margin-bottom:0.5rem;'>"
            f"<img src='data:image/jpeg;base64,{logo_b64_side}' style='width:90px;border-radius:8px;'/></div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass
    st.markdown(
        "<div style='text-align:center;color:#64748b;font-size:0.75rem;margin-bottom:1rem;'>"
        "Université Hassan II — FSTM<br>Licence IRM 2025-2026</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### ⚙️ Configuration")

    pipeline_mode = st.radio(
        "Mode du pipeline",
        ["🔧 Local (API directe)", "☁️ n8n (Webhook)"],
        help="Local = chaque étape individuellement via l'API.\nn8n = tout le pipeline via le webhook n8n.",
    )
    use_n8n = pipeline_mode.startswith("☁️")

    if use_n8n:
        n8n_url_input = st.text_input("URL Webhook n8n", value=N8N_WEBHOOK_URL)
        if n8n_url_input:
            N8N_WEBHOOK_URL = n8n_url_input.rstrip("/")
        n8n_use_test = st.checkbox("Utiliser webhook-test (mode test n8n)", value=False,
            help="Cochez si vous cliquez 'Test workflow' dans l'éditeur n8n.")
    else:
        api_url_input = st.text_input("URL de l'API", value=API_URL)
        if api_url_input:
            API_URL = api_url_input.rstrip("/")

        api_ok = check_api()
        if api_ok:
            st.success("🟢 API connectée")
        else:
            st.error("🔴 API non disponible")

    st.markdown("---")
    st.markdown("### 👥 Équipe")
    team = [
        ("Brahim Benazzouz", "Architecture & LLM"),
        ("Omar El Haddad", "Extraction & Analyse"),
        ("Boukhar Hamza", "Compression"),
        ("Afkir Rida", "Évaluation & Rapport"),
    ]
    for name, role in team:
        st.markdown(f"""
        <div class="team-card">
            <div class="name">{name}</div>
            <div class="role">{role}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────

try:
    with open("logo.jpeg", "rb") as _f:
        _logo_b64 = base64.b64encode(_f.read()).decode()
    _logo_html = f"<img src='data:image/jpeg;base64,{_logo_b64}' class='main-header-logo'/>"
except Exception:
    _logo_html = ""

st.markdown(f"""
<div class="main-header">
    {_logo_html}
    <div class="main-header-text">
        <h1>Système Intelligent de Compression Audio</h1>
        <p>Architecture multi-agents — Analyse, Décision, Compression, Évaluation, Rapport</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

for key in ["analysis", "decision", "compression", "evaluation", "report_data", "n8n_result"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 : Upload du fichier
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="step-badge">ÉTAPE 1</div>', unsafe_allow_html=True)
st.markdown("### 📁 Charger un fichier audio")

uploaded_file = st.file_uploader(
    "Glissez ou sélectionnez un fichier audio",
    type=["wav", "mp3", "m4a", "flac", "aac", "ogg", "opus", "aiff", "wma", "amr", "webm"],
    help="Tous les formats audio courants sont acceptés. Le fichier sera automatiquement détecté et converti.",
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
    file_size_mb = len(file_bytes) / (1024 * 1024)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(make_metric_card(uploaded_file.name, "Fichier"), unsafe_allow_html=True)
    with col2:
        st.markdown(make_metric_card(f"{file_size_mb:.2f} MB", "Taille"), unsafe_allow_html=True)
    with col3:
        st.markdown(
            make_metric_card(uploaded_file.name.rsplit(".", 1)[-1].upper(), "Format"),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # MODE n8n — Pipeline complet via webhook
    # ══════════════════════════════════════════════════════════════════════════

    if use_n8n:
        st.markdown('<div class="step-badge">☁️ PIPELINE n8n</div>', unsafe_allow_html=True)
        st.markdown("### 🚀 Lancer le pipeline complet via n8n")
        st.info(
            "Le fichier sera envoyé au webhook n8n qui exécutera automatiquement : "
            "**Extraction → Décision (LLM) → Compression → Évaluation → Rapport**"
        )

        if st.button("🚀 Lancer le pipeline n8n", key="btn_n8n_pipeline"):
            webhook_url = N8N_WEBHOOK_TEST_URL if n8n_use_test else N8N_WEBHOOK_URL
            with st.spinner(f"Pipeline n8n en cours... (webhook: {webhook_url})"):
                try:
                    r = requests.post(
                        webhook_url,
                        json={
                            "file_base64": file_b64,
                            "nom_fichier": uploaded_file.name,
                        },
                        timeout=300,
                    )
                    r.raise_for_status()
                    result = r.json()
                    st.session_state.n8n_result = result
                    st.success("✅ Pipeline n8n terminé !")
                except Exception as e:
                    st.error(f"❌ Erreur n8n : {e}")

        if st.session_state.n8n_result:
            result = st.session_state.n8n_result
            st.markdown("---")
            st.markdown('<div class="step-badge">📋 RÉSULTATS</div>', unsafe_allow_html=True)

            # Try to extract report
            report_json = result.get("report_json", result.get("report", {}))
            if isinstance(report_json, str):
                try:
                    report_json = json.loads(report_json)
                except Exception:
                    pass

            # Display key metrics if available
            evaluation = report_json.get("evaluation", result.get("evaluation", {}))
            if isinstance(evaluation, dict):
                ev = evaluation.get("evaluation", evaluation)
                quality = ev.get("qualite_estimee", "—")
                st.markdown(quality_badge(quality), unsafe_allow_html=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(make_metric_card(f'{ev.get("snr_db", 0)} dB', "SNR"), unsafe_allow_html=True)
                with col2:
                    st.markdown(make_metric_card(f'{ev.get("psnr_db", 0)} dB', "PSNR"), unsafe_allow_html=True)
                with col3:
                    st.markdown(make_metric_card(ev.get("correlation", 0), "Corrélation"), unsafe_allow_html=True)
                with col4:
                    st.markdown(make_metric_card(f'{ev.get("taux_compression_pct", 0)}%', "Compression"), unsafe_allow_html=True)

                # Gauge
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=ev.get("snr_db", 0),
                    title={"text": "SNR (dB)", "font": {"color": "#333"}},
                    gauge={
                        "axis": {"range": [0, 60], "tickcolor": "#999"},
                        "bar": {"color": "#667eea"},
                        "bgcolor": "rgba(241,245,249,0.8)",
                        "steps": [
                            {"range": [0, 15], "color": "rgba(248,113,113,0.3)"},
                            {"range": [15, 25], "color": "rgba(251,191,36,0.3)"},
                            {"range": [25, 60], "color": "rgba(74,222,128,0.3)"},
                        ],
                        "threshold": {
                            "line": {"color": "#764ba2", "width": 3},
                            "thickness": 0.8,
                            "value": ev.get("snr_db", 0),
                        },
                    },
                    number={"font": {"color": "#333"}},
                ))
                fig_gauge.update_layout(
                    height=280,
                    margin=dict(l=30, r=30, t=60, b=30),
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#333"),
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

            # Report download
            report_id = result.get("report_id", report_json.get("report_id", ""))
            if report_id:
                st.markdown(f"**Report ID** : `{report_id}`")

            report_str = json.dumps(report_json, ensure_ascii=False, indent=2)
            st.download_button(
                "⬇️ Télécharger le rapport JSON",
                data=report_str,
                file_name=result.get("report_json_filename", f"report_n8n.json"),
                mime="application/json",
                key="btn_download_n8n",
            )

            with st.expander("📄 Réponse n8n complète"):
                st.json(result)

    # ══════════════════════════════════════════════════════════════════════════
    # MODE LOCAL — Pipeline automatique via l'API
    # ══════════════════════════════════════════════════════════════════════════

    else:
        st.markdown('<div class="step-badge">🔧 PIPELINE LOCAL</div>', unsafe_allow_html=True)
        st.markdown("### 🚀 Pipeline automatique via l'API locale")
        st.info(
            "Un clic lance automatiquement : "
            "**Extraction → Décision → Compression → Évaluation → Rapport**"
        )

        if st.button("🚀 Lancer le pipeline complet", key="btn_local_pipeline", type="primary"):
            if not api_ok:
                st.error("🔴 L'API n'est pas accessible. Lancez `python main.py` d'abord.")
            else:
                pipeline_steps = [
                    ("🔍 Extraction des caractéristiques (Omar)", 0.0, 0.2),
                    ("🧠 Décision de compression (Brahim)", 0.2, 0.4),
                    ("🗜️ Compression audio (Hamza)", 0.4, 0.6),
                    ("📊 Évaluation de la qualité (Rida)", 0.6, 0.8),
                    ("📝 Génération du rapport", 0.8, 1.0),
                ]
                progress_bar = st.progress(0, text="Démarrage du pipeline...")
                status_container = st.empty()
                pipeline_ok = True

                # ── Step 1: Extraction ─────────────────────────────────────────
                step_name, p_start, p_end = pipeline_steps[0]
                progress_bar.progress(p_start, text=step_name)
                status_container.info(f"⏳ {step_name}...")
                try:
                    r = requests.post(
                        f"{API_URL}/extract_base64",
                        json={"file_base64": file_b64, "nom_fichier": uploaded_file.name},
                        timeout=120,
                    )
                    r.raise_for_status()
                    st.session_state.analysis = r.json()
                    progress_bar.progress(p_end, text=f"✅ {step_name}")
                except Exception as e:
                    status_container.error(f"❌ {step_name} — {e}")
                    pipeline_ok = False

                # ── Step 2: Decision ───────────────────────────────────────────
                if pipeline_ok:
                    step_name, p_start, p_end = pipeline_steps[1]
                    progress_bar.progress(p_start, text=step_name)
                    status_container.info(f"⏳ {step_name}...")
                    try:
                        from decision import decider_parametres
                        decision_input = st.session_state.analysis.get("decision_input", {})
                        st.session_state.decision = decider_parametres(decision_input)
                        progress_bar.progress(p_end, text=f"✅ {step_name}")
                    except Exception as e:
                        status_container.error(f"❌ {step_name} — {e}")
                        pipeline_ok = False

                # ── Step 3: Compression ────────────────────────────────────────
                if pipeline_ok:
                    step_name, p_start, p_end = pipeline_steps[2]
                    progress_bar.progress(p_start, text=step_name)
                    status_container.info(f"⏳ {step_name}...")
                    dec = st.session_state.decision
                    data = st.session_state.analysis
                    try:
                        r = requests.post(
                            f"{API_URL}/compress",
                            json={
                                "file_base64": file_b64,
                                "nom_fichier": uploaded_file.name,
                                "codec": dec["codec"],
                                "bitrate": dec["bitrate"],
                                "sample_rate": dec["sample_rate"],
                                "channels": dec["channels"],
                                "decision": dec,
                                "analysis": data.get("decision_input", {}),
                            },
                            timeout=120,
                        )
                        r.raise_for_status()
                        st.session_state.compression = r.json()
                        progress_bar.progress(p_end, text=f"✅ {step_name}")
                    except Exception as e:
                        status_container.error(f"❌ {step_name} — {e}")
                        pipeline_ok = False

                # ── Step 4: Evaluation ─────────────────────────────────────────
                if pipeline_ok:
                    step_name, p_start, p_end = pipeline_steps[3]
                    progress_bar.progress(p_start, text=step_name)
                    status_container.info(f"⏳ {step_name}...")
                    comp = st.session_state.compression
                    compressed_b64 = comp.get("file_base64_compresse", "")
                    try:
                        r = requests.post(
                            f"{API_URL}/evaluate",
                            json={
                                "original_file_base64": file_b64,
                                "original_nom_fichier": uploaded_file.name,
                                "compressed_file_base64": compressed_b64,
                                "compressed_nom_fichier": comp.get("nom_fichier_compresse", "compressed.mp3"),
                                "compression_result": comp,
                                "decision": dec,
                                "analysis": data.get("decision_input", {}),
                            },
                            timeout=120,
                        )
                        r.raise_for_status()
                        st.session_state.evaluation = r.json()
                        progress_bar.progress(p_end, text=f"✅ {step_name}")
                    except Exception as e:
                        status_container.error(f"❌ {step_name} — {e}")
                        pipeline_ok = False

                # ── Step 5: Report ─────────────────────────────────────────────
                if pipeline_ok:
                    step_name, p_start, p_end = pipeline_steps[4]
                    progress_bar.progress(p_start, text=step_name)
                    status_container.info(f"⏳ {step_name}...")
                    try:
                        r = requests.post(
                            f"{API_URL}/report",
                            json={
                                "analysis": data,
                                "decision": dec,
                                "compression": comp,
                                "evaluation": st.session_state.evaluation,
                                "original_filename": uploaded_file.name,
                            },
                            timeout=30,
                        )
                        r.raise_for_status()
                        st.session_state.report_data = r.json()
                        progress_bar.progress(1.0, text="✅ Pipeline terminé !")
                        status_container.success("✅ Pipeline complet terminé avec succès !")
                    except Exception as e:
                        status_container.error(f"❌ {step_name} — {e}")

        # ══════════════════════════════════════════════════════════════════
        # DISPLAY RESULTS (after pipeline or from session state)
        # ══════════════════════════════════════════════════════════════════

        if st.session_state.analysis:
            data = st.session_state.analysis
            meta = data.get("metadonnees", {})
            carac = data.get("caracteristiques", {})
            type_audio = data.get("analyse", {}).get("type_audio", "—")

            st.markdown("---")
            st.markdown('<div class="step-badge">ÉTAPE 2 — OMAR</div>', unsafe_allow_html=True)
            st.markdown("### 🔍 Extraction des caractéristiques")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(make_metric_card(f'{meta.get("duree_secondes", 0)}s', "Durée"), unsafe_allow_html=True)
            with col2:
                st.markdown(make_metric_card(f'{meta.get("sample_rate", 0)} Hz', "Sample Rate"), unsafe_allow_html=True)
            with col3:
                st.markdown(make_metric_card(meta.get("channels", 0), "Canaux"), unsafe_allow_html=True)
            with col4:
                st.markdown(make_metric_card(type_audio.upper(), "Type Détecté"), unsafe_allow_html=True)

            # Radar chart
            st.markdown("#### 📊 Caractéristiques spectrales")
            categories = ["RMS", "ZCR", "Centroïde", "Bandwidth", "Entropie", "Dyn. Range"]
            values = [
                carac.get("rms_energy", 0) * 100,
                carac.get("zero_crossing_rate", 0) * 100,
                min(carac.get("spectral_centroid", 0) / 50, 100),
                min(carac.get("spectral_bandwidth", 0) / 50, 100),
                carac.get("spectral_entropy", 0) * 100,
                min(carac.get("dynamic_range_db", 0) / 0.5, 100),
            ]
            fig = go.Figure(data=go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(102, 126, 234, 0.15)",
                line=dict(color="#667eea", width=2),
                marker=dict(size=6, color="#764ba2"),
            ))
            fig.update_layout(
                polar=dict(
                    bgcolor="rgba(255,255,255,0.5)",
                    radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(0,0,0,0.08)"),
                    angularaxis=dict(gridcolor="rgba(0,0,0,0.08)"),
                ),
                showlegend=False, height=400,
                margin=dict(l=60, r=60, t=40, b=40),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#333"),
            )
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("📄 Données JSON complètes"):
                st.json(data)

        if st.session_state.decision:
            dec = st.session_state.decision
            st.markdown("---")
            st.markdown('<div class="step-badge">ÉTAPE 3 — BRAHIM</div>', unsafe_allow_html=True)
            st.markdown("### 🧠 Décision de compression")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(make_metric_card(dec["codec"].upper(), "Codec"), unsafe_allow_html=True)
            with col2:
                st.markdown(make_metric_card(dec["bitrate"], "Bitrate"), unsafe_allow_html=True)
            with col3:
                st.markdown(make_metric_card(f'{dec["sample_rate"]} Hz', "Sample Rate"), unsafe_allow_html=True)
            with col4:
                st.markdown(make_metric_card(dec["channels"], "Canaux"), unsafe_allow_html=True)
            st.info(f"💡 **Justification** : {dec.get('justification', '—')}")

        if st.session_state.compression:
            comp = st.session_state.compression
            taux = comp.get("taux_compression_pct", 0)
            compressed_b64 = comp.get("file_base64_compresse", "")

            st.markdown("---")
            st.markdown('<div class="step-badge">ÉTAPE 4 — HAMZA</div>', unsafe_allow_html=True)
            st.markdown("### 🗜️ Compression audio")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(make_metric_card(f"{comp.get('taille_originale_bytes', 0)/1024:.1f} KB", "Taille originale"), unsafe_allow_html=True)
            with col2:
                st.markdown(make_metric_card(f"{comp.get('taille_compressee_bytes', 0)/1024:.1f} KB", "Taille compressée"), unsafe_allow_html=True)
            with col3:
                st.markdown(make_metric_card(f"{taux}%", "Taux compression"), unsafe_allow_html=True)

            fig_bar = go.Figure(data=[
                go.Bar(name="Original", x=["Taille"], y=[comp.get("taille_originale_bytes", 0)], marker_color="#667eea"),
                go.Bar(name="Compressé", x=["Taille"], y=[comp.get("taille_compressee_bytes", 0)], marker_color="#764ba2"),
            ])
            fig_bar.update_layout(
                barmode="group", height=250,
                margin=dict(l=40, r=40, t=20, b=40),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#333"), yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            if compressed_b64:
                st.download_button(
                    "⬇️ Télécharger le fichier compressé",
                    data=base64.b64decode(compressed_b64),
                    file_name=comp.get("nom_fichier_compresse", "compressed.mp3"),
                    mime="audio/mpeg",
                )

        if st.session_state.evaluation:
            ev = st.session_state.evaluation.get("evaluation", {})
            quality = ev.get("qualite_estimee", "—")

            st.markdown("---")
            st.markdown('<div class="step-badge">ÉTAPE 5 — RIDA</div>', unsafe_allow_html=True)
            st.markdown("### 📊 Évaluation de la qualité")

            st.markdown(quality_badge(quality), unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(make_metric_card(f'{ev.get("snr_db", 0)} dB', "SNR"), unsafe_allow_html=True)
            with col2:
                st.markdown(make_metric_card(f'{ev.get("psnr_db", 0)} dB', "PSNR"), unsafe_allow_html=True)
            with col3:
                st.markdown(make_metric_card(ev.get("correlation", 0), "Corrélation"), unsafe_allow_html=True)
            with col4:
                st.markdown(make_metric_card(f'{ev.get("taux_compression_pct", 0)}%', "Compression"), unsafe_allow_html=True)

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=ev.get("snr_db", 0),
                title={"text": "SNR (dB)", "font": {"color": "#333"}},
                gauge={
                    "axis": {"range": [0, 60], "tickcolor": "#999"},
                    "bar": {"color": "#667eea"},
                    "bgcolor": "rgba(241,245,249,0.8)",
                    "steps": [
                        {"range": [0, 15], "color": "rgba(248,113,113,0.3)"},
                        {"range": [15, 25], "color": "rgba(251,191,36,0.3)"},
                        {"range": [25, 60], "color": "rgba(74,222,128,0.3)"},
                    ],
                    "threshold": {"line": {"color": "#764ba2", "width": 3}, "thickness": 0.8, "value": ev.get("snr_db", 0)},
                },
                number={"font": {"color": "#333"}},
            ))
            fig_gauge.update_layout(height=280, margin=dict(l=30, r=30, t=60, b=30), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#333"))
            st.plotly_chart(fig_gauge, use_container_width=True)

        if st.session_state.report_data:
            rpt = st.session_state.report_data
            report_json = rpt.get("report_json", {})

            st.markdown("---")
            st.markdown('<div class="step-badge">ÉTAPE 6</div>', unsafe_allow_html=True)
            st.markdown("### 📝 Rapport final")

            st.markdown(f"**Report ID** : `{rpt.get('report_id', '—')}`")
            report_str = json.dumps(report_json, ensure_ascii=False, indent=2)
            st.download_button(
                "⬇️ Télécharger le rapport JSON",
                data=report_str,
                file_name=rpt.get("report_json_filename", "report.json"),
                mime="application/json",
            )
            with st.expander("📄 Contenu du rapport"):
                st.json(report_json)

else:
    # Message d'accueil quand aucun fichier n'est uploadé
    st.markdown("""
    <div style="text-align: center; padding: 3rem 2rem; color: #64748b;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">🎵</div>
        <h3 style="color: #334155;">Bienvenue dans le système de compression audio</h3>
        <p style="max-width: 500px; margin: 0 auto; line-height: 1.6;">
            Uploadez un fichier audio pour commencer le pipeline :
            <strong>Analyse → Décision → Compression → Évaluation → Rapport</strong>
        </p>
        <p style="margin-top: 1rem; font-size: 0.85rem; color: #94a3b8;">
            Formats supportés : WAV, MP3, M4A, FLAC, AAC, OGG, OPUS, AIFF, WMA, AMR, WebM...
        </p>
    </div>
    """, unsafe_allow_html=True)
