"""
Interface Streamlit pour l'analyste MCP
"""

import streamlit as st
import pandas as pd
from data_processing.mcp_analyst import MCPAnalyst
import config


def render_mcp_analyst_page():
    """
    Affiche la page de l'analyste IA MCP.
    """
    st.title("🤖 Analyste IA - Requêtes en langage naturel")
    st.markdown("""
    Posez des questions en français sur vos données Hubspot et Aircall.
    L'IA générera automatiquement les requêtes SQL et vous affichera les résultats.
    """)
    
    # Configuration du provider
    col1, col2 = st.columns(2)
    
    with col1:
        provider = st.selectbox(
            "Provider LLM",
            ["openai", "anthropic"],
            index=0 if config.MCP_PROVIDER == "openai" else 1,
            help="Choisissez le fournisseur de LLM (OpenAI ou Anthropic)"
        )
    
    with col2:
        # Sélection du modèle selon le provider
        if provider == "openai":
            model = st.selectbox(
                "Modèle OpenAI",
                ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                index=0,
                help="Modèle OpenAI à utiliser"
            )
        else:
            model = st.selectbox(
                "Modèle Anthropic",
                ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
                index=0,
                help="Modèle Anthropic à utiliser"
            )
    
    # Vérification de la clé API
    api_key = None
    if provider == "openai":
        api_key = config.OPENAI_API_KEY
        if not api_key:
            st.error("⚠️ Clé API OpenAI non configurée. Définissez OPENAI_API_KEY dans config.py ou via variable d'environnement.")
            st.info("💡 Pour configurer :\n1. Ajoutez `OPENAI_API_KEY = 'votre-clé'` dans config.py\n2. Ou définissez la variable d'environnement : `export OPENAI_API_KEY='votre-clé'`")
            return
    else:
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            st.error("⚠️ Clé API Anthropic non configurée. Définissez ANTHROPIC_API_KEY dans config.py ou via variable d'environnement.")
            st.info("💡 Pour configurer :\n1. Ajoutez `ANTHROPIC_API_KEY = 'votre-clé'` dans config.py\n2. Ou définissez la variable d'environnement : `export ANTHROPIC_API_KEY='votre-clé'`")
            return
    
    # Initialiser l'analyste (avec cache Streamlit)
    @st.cache_resource
    def get_analyst(provider, api_key, model):
        try:
            return MCPAnalyst(provider=provider, api_key=api_key, model=model)
        except Exception as e:
            st.error(f"Erreur lors de l'initialisation de l'analyste : {e}")
            return None
    
    analyst = get_analyst(provider, api_key, model)
    
    if analyst is None:
        return
    
    # Afficher les tables disponibles
    with st.expander("📊 Tables disponibles dans les bases de données"):
        available_tables = analyst.get_available_tables()
        if available_tables:
            for db_name, tables in available_tables.items():
                st.subheader(f"Base : {db_name.upper()}")
                if tables:
                    for table in tables:
                        st.write(f"  - `{table}`")
                else:
                    st.write("  *Aucune table disponible*")
        else:
            st.warning("Aucune base de données trouvée. Assurez-vous que les données ont été chargées.")
    
    # Zone de saisie de la question
    st.divider()
    question = st.text_area(
        "Posez votre question :",
        placeholder="Exemples :\n- Combien de tickets ont été créés ce mois-ci ?\n- Quel est le temps de réponse moyen par agent ?\n- Quels sont les 10 tickets les plus récents ?",
        height=100
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        submit_button = st.button("🔍 Analyser", type="primary", use_container_width=True)
    
    # Traitement de la question
    if submit_button and question:
        with st.spinner("🤔 Génération de la requête SQL et exécution..."):
            result = analyst.query(question)
        
        if result["success"]:
            st.success("✅ Requête exécutée avec succès !")
            
            # Afficher la requête SQL générée
            with st.expander("📝 Requête SQL générée"):
                st.code(result["sql_query"], language="sql")
            
            # Afficher les résultats
            if result["data"] is not None and not result["data"].empty:
                st.subheader("📊 Résultats")
                st.write(f"**{result['row_count']}** ligne(s) trouvée(s)")
                
                # Afficher le DataFrame
                st.dataframe(result["data"], use_container_width=True)
                
                # Option de téléchargement
                csv = result["data"].to_csv(index=False)
                st.download_button(
                    label="📥 Télécharger en CSV",
                    data=csv,
                    file_name=f"resultat_analyse_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Aucun résultat trouvé pour cette requête.")
        else:
            st.error(f"❌ Erreur : {result.get('error', 'Erreur inconnue')}")
            if result.get("sql_query"):
                with st.expander("📝 Requête SQL générée (avec erreur)"):
                    st.code(result["sql_query"], language="sql")
    
    # Exemples de questions
    st.divider()
    st.subheader("💡 Exemples de questions")
    
    example_questions = [
        "Combien de tickets ont été créés ce mois-ci ?",
        "Quel est le nombre total de tickets par statut ?",
        "Quels sont les 10 tickets les plus récents ?",
        "Combien de tickets ont été créés par semaine sur les 4 dernières semaines ?",
        "Quel est le temps de réponse moyen par agent ?",
        "Combien de tickets ont été créés par source (E-mail, Chat, Téléphone) ?",
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(example_questions):
        with cols[i % 2]:
            if st.button(f"💬 {example}", key=f"example_{i}", use_container_width=True):
                st.session_state['mcp_question'] = example
                st.rerun()
    
    # Si une question d'exemple a été sélectionnée, la mettre dans le textarea
    if 'mcp_question' in st.session_state:
        question = st.session_state['mcp_question']
        del st.session_state['mcp_question']
        st.rerun()
