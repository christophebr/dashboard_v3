import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings('ignore')

def generate_kpis(df_support, df_tickets, agents, partenaire=None, partenaires=None):
    """
    Génère les KPIs pour un ou plusieurs agents.
    Retourne un dictionnaire avec les métriques, y compris les graphes, SLA, etc.
    """
    # Sauvegarde de l'entrée pour condition ultérieure
    agent_original = agents

    # --- DÉFINITIONS DES GROUPES D'AGENTS ---
    support_agents = ['Archimede KESSI', 'Mourad HUMBLOT']
    armatis_agents = ['Emilie GEST', 'Sandrine Sauvage', 'Melinda Marmin', 'Morgane Vandenbussche', 'Céline Crendal', 'Cédeline DUVAL']
    special_agents = ['agents_support', 'agents_armatis', 'agents_all']

    # Gestion des variantes de nom pour Céline Crendal
    correspondance_noms = {
        'Céline Crendal': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Celine Crendal': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Céline CRENDAL': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Celine CRENDAL': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        # Variantes pour Cédeline DUVAL
        'Cédeline DUVAL': ['Cédeline DUVAL', 'CÃ©deline DUVAL', 'C√©deline DUVAL', 'cedeline duval', 'Cedeline Duval', 'CÉDELINE DUVAL'],
    }

    # --- SÉLECTION DES AGENTS CIBLÉS ---
    if agents == 'agents_support':
        selected_agents = support_agents
    elif agents == 'agents_armatis':
        selected_agents = armatis_agents
    elif agents == 'agents_all':
        selected_agents = support_agents + armatis_agents
    else:
        # Si agents est une liste, on l'utilise directement
        if isinstance(agents, list):
            # Si Céline est dans la liste, on ajoute toutes ses variantes
            selected_agents = []
            for a in agents:
                if a in correspondance_noms:
                    selected_agents.extend(correspondance_noms[a])
                else:
                    selected_agents.append(a)
        else:
            if agents in correspondance_noms:
                selected_agents = correspondance_noms[agents]
            else:
                selected_agents = [agents]

    # --- KPIs SUPPORT ---
    taux_reponse, mean_difference, df_taux_reponse = calcul_taux_reponse(df_support)
    com_jour, temps_moy_com, nb_appels_jour, nb_appel, nb_appels_jour_entrants, nb_appels_jour_sortants, ratio_entrants, ratio_sortants = kpi_agent(selected_agents, df_support)
    Taux_de_service, Entrant, Numero_unique, temps_moy_appel, Nombre_appel_jour_agent = metrics_support(df_support, selected_agents)
    charge_affid_stellair_1, charge_affid_stellair_2, essai = graph_charge_affid_stellair(df_support)

    # --- KPIs TICKETS ---
    # Filtrer les tickets pour l'agent
    agent_tickets = df_tickets[
        (df_tickets['Propriétaire du ticket'].isin(selected_agents)) & 
        (df_tickets['Pipeline'].isin(['SSIA', 'SSI', 'SPSA'])) &
        (df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire']) | pd.isna(df_tickets['Source']))
    ]
    
    # Calculer la moyenne de tickets par jour
    nb_jours = len(df_support['Date'].unique())
    if nb_jours == 0:
        nb_jours = 1  # Pour éviter la division par zéro
    moy_ticket_agent = len(agent_tickets) / nb_jours

    activite_ticket = activite_ticket_source_pipeline(df_tickets)
    activite_ticket_semaine = activite_ticket_source_client(df_tickets)
    activite_categorie = metrics_nombre_ticket_categorie(df_tickets, partenaire)
    evo_appels_tickets, activite_appels_pourcentage, activite_tickets_pourcentage, ticket_s17 = evo_appels_ticket(df_tickets, df_support)
    # Version mensuelle
    evo_appels_tickets_mensuel = evo_appels_ticket_mensuel(df_tickets, df_support)
    # Top 30 catégories
    top30_categories = top30_categories_tickets(df_tickets)
    # Graphique Sunburst des catégories
    sunburst_categories = sunburst_categories_tickets(df_tickets)

    # --- SLA / RAPPORT PARTENAIRE ---
    canal = "partenaire" if partenaire else "b2c"
    sla_fig, sla_inferieur_2, delai_moyen, df_partenaire, df_b2c = sla(df_tickets, partenaire, canal)
    sla_partenaire, describe_partenaire = sla_2h_spsa(df_tickets)

    # --- GRAPHIQUES ---
    fig_activite_ticket = activite_ticket_source_client(df_tickets)
    fig_activite = graph_activite(df_support)
    fig_taux_jour = graph_taux_jour(df_support)
    fig_taux_heure = graph_taux_heure(df_support)

    # --- RÉPARTITION TICKETS / APPELS ---
    total_interactions = moy_ticket_agent + nb_appels_jour_entrants
    pourcentage_tickets = moy_ticket_agent / total_interactions if total_interactions > 0 else 0
    pourcentage_appels = nb_appels_jour_entrants / total_interactions if total_interactions > 0 else 0

    # --- STRUCTURE DU DICTIONNAIRE DE SORTIE ---
    kpis = {
        # SLA / partenaires
        'sla_partenaire': sla_partenaire,
        'describe_partenaire': describe_partenaire,
        'sla_fig': sla_fig,
        '%_sla_2': sla_inferieur_2,
        'delai_moyen_reponse': delai_moyen,

        # Activité générale
        'taux_reponse': taux_reponse,
        'mean_difference': mean_difference,
        'Taux_de_service': Taux_de_service,
        'Entrant': Entrant,
        'Numero_unique': Numero_unique,
        'temps_moy_appel': temps_moy_appel,
        'Nombre_appel_jour_agent': nb_appels_jour,
        'Nomnbre_appel_total': nb_appel,

        # Tickets / Appels pour objectif
        'moy_ticket_agent': moy_ticket_agent,
        'nb_appels_jour': nb_appels_jour,
        'nb_appels_jour_entrants': nb_appels_jour_entrants,
        'nb_appels_jour_sortants': nb_appels_jour_sortants,
        'ratio_entrants': ratio_entrants,
        'ratio_sortants': ratio_sortants,
        '% tickets': pourcentage_tickets * 100,
        '% Appels': pourcentage_appels * 100,
        'activite_appels_pourcentage': activite_appels_pourcentage,
        'activite_tickets_pourcentage': activite_tickets_pourcentage,

        # Évolution
        'evo_appels_tickets': evo_appels_tickets,
        'evo_appels_tickets_mensuel': evo_appels_tickets_mensuel,
        'top30_categories': top30_categories,
        'sunburst_categories': sunburst_categories,
        'essai': ticket_s17,

        # Charge Stellair
        'charge_affid_stellair_%': charge_affid_stellair_1,
        'charge_affid_stellair_v': charge_affid_stellair_2,
        'essai': essai,

        # Graphiques
        'fig_activite_ticket': fig_activite_ticket,
        'activite_categorie': activite_categorie,
        'activite_ticket_semaine': activite_ticket_semaine,
        'fig_activite': fig_activite,
        'fig_taux_jour': fig_taux_jour,
        'fig_taux_heure': fig_taux_heure,
    }

    # --- AJOUT DES KPIs AGENT UNIQUEMENT SI PAS UN GROUPE ---
    if agent_original not in special_agents:
        kpis.update({
            'com_jour': com_jour,
            'temps_moy_com': temps_moy_com,
        })

    return kpis

def filter_evaluation(df_evaluation, agents, periodes_eval):
    return df_evaluation[
        (df_evaluation["agent"].isin(agents)) &
        (df_evaluation["quarter"].isin(periodes_eval))]


def charge_entrant_sortant(df_support, agents, template="plotly_dark"):
    import pandas as pd

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    if isinstance(agents, str):
        agents = [agents]

    # Filtrage par les agents et par l'état 'yes'
    df_filtered = df_support[
        (df_support['UserName'].isin(agents)) &
        (df_support['direction'] == 'inbound')  # On se concentre sur les appels entrants
    ]

    # Vérifier si le dataframe filtré est vide
    if df_filtered.empty:
        return None, None

    # Groupement par Semaine, Agent, et Direction
    df_grouped = df_filtered.groupby(['Semaine', 'UserName']).agg({'Date': 'count'}).reset_index()

    # Vérifier si le groupement est vide
    if df_grouped.empty:
        return None, None

    # Étiquette série = Agent pour la courbe
    df_grouped['Série'] = df_grouped['UserName']

    # Calcul des semaines dans le bon ordre
    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))

    # 📈 Graphique en ligne
    fig_line = px.line(
        df_grouped,
        x='Semaine',
        y='Date',
        color='Série',
        markers=True,
        title="Volume d'appels entrants par agent",
        color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    )

    fig_line.update_layout(
        template=template,
        yaxis_title="Nombre d'appels",
        xaxis=dict(categoryorder="array", categoryarray=ordre_semaines),
        yaxis=dict(range=[0, df_grouped['Date'].max() + 10])
    )

    # 🥧 Graphique camembert (somme par agent)
    df_pie = df_grouped.groupby('UserName')['Date'].sum().reset_index()
    df_pie = df_pie.rename(columns={'Date': 'Total appels'})

    fig_pie = px.pie(
        df_pie,
        names='UserName',
        values='Total appels',
        color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        #title="Répartition des appels entrants par agent"
    )
    
    fig_pie.update_layout(template=template)

    return fig_line, fig_pie



def charge_ticket(df_ticket, agents, template="plotly_dark"):
    import pandas as pd

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_ticket = df_ticket[df_ticket['Semaine'] != 'S2024-01'].copy()

    if isinstance(agents, str):
        agents = [agents]

    # Étendre les alias pour certains agents (orthographes variables)
    alias_map = {
        'Céline Crendal': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Celine Crendal': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Céline CRENDAL': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Celine CRENDAL': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Cédeline DUVAL': ['Cédeline DUVAL', 'CÃ©deline DUVAL', 'C√©deline DUVAL', 'cedeline duval', 'Cedeline Duval', 'CÉDELINE DUVAL']
    }

    expanded_agents = []
    for a in agents:
        expanded_agents.extend(alias_map.get(a, [a]))
    agents = expanded_agents

    # Filtrage par les agents, le pipeline et la source
    df_filtered = df_ticket[
        (df_ticket['Propriétaire du ticket'].isin(agents)) &
        (df_ticket['Pipeline'].isin(['SSIA', 'SSI', 'SPSA'])) &
        (df_ticket['Source'].isin(['Chat', 'E-mail', 'Formulaire']))
    ]

    # Groupement par semaine et agent
    df_grouped = df_filtered.groupby(['Semaine', 'Propriétaire du ticket']).agg({'Date': 'count'}).reset_index()
    df_grouped['Série'] = df_grouped['Propriétaire du ticket']

    # Ordre des semaines
    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))

    # 📈 Graphique ligne
    fig_line = px.line(
        df_grouped,
        x='Semaine',
        y='Date',
        color='Série',
        markers=True,
        title="Volume de tickets par agent",
        color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
    )

    fig_line.update_layout(
        template=template,
        yaxis_title="Nombre de tickets",
        xaxis=dict(categoryorder="array", categoryarray=ordre_semaines),
        yaxis=dict(range=[0, df_grouped['Date'].max() + 10])
    )

    # 🥧 Graphique camembert
    df_pie = df_grouped.groupby('Propriétaire du ticket')['Date'].sum().reset_index()
    df_pie = df_pie.rename(columns={'Date': 'Total tickets'})

    fig_pie = px.pie(
        df_pie,
        names='Propriétaire du ticket',
        values='Total tickets',
        color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
        #title="Répartition des tickets par agent"
    )
    
    fig_pie.update_layout(template=template)

    return fig_line, fig_pie




def metrics_nombre_ticket_pipeline_agent(df_hubspot, agents):
    """
    Fonction pour analyser les tickets par pipeline et agent.
    Cette fonction est un placeholder - elle devrait être implémentée selon les besoins spécifiques.
    """
    # Pour l'instant, retourner un dictionnaire vide ou une structure de base
    # Cette fonction semble être une copie incomplète de generate_kpis
    return {}

def convert_to_sixtieth(seconds):
    if pd.isnull(seconds):  # Vérifie si seconds est NaN
        return "Invalid"  # Retourne une valeur par défaut ou un message d'erreur
    minutes, seconds = divmod(int(seconds), 60)  # Convertir en heures
    return f"{int(minutes)}m{int(seconds):02d}s"

def filtrer_par_periode(df_support, periode):
    """ Filtre les données en fonction de la période sélectionnée.
    periode peut être :
    - une chaîne fixe : "1 an", "6 derniers mois", etc.
    - un tuple (date_debut, date_fin) pour une période personnalisée (datetime ou date)
    """
    df_support = df_support.copy()
    df_support['Date'] = pd.to_datetime(df_support['Date'])  # Assure que 'Date' est bien en datetime
    derniere_date = df_support['Date'].max()

    # Période personnalisée : tuple (date_debut, date_fin)
    if isinstance(periode, (tuple, list)) and len(periode) == 2:
        date_limite = pd.to_datetime(periode[0])
        date_max = pd.to_datetime(periode[1])
        df_filtered = df_support[(df_support['Date'] >= date_limite) & (df_support['Date'] <= date_max)].copy()
    elif periode == "1 an":
        date_limite = derniere_date - pd.DateOffset(years=1)
        df_filtered = df_support[df_support['Date'] >= date_limite].copy()
    elif periode == "6 derniers mois":
        date_limite = derniere_date - pd.DateOffset(months=6)
        df_filtered = df_support[df_support['Date'] >= date_limite].copy()
    elif periode == "3 derniers mois":
        date_limite = derniere_date - pd.DateOffset(months=3)
        df_filtered = df_support[df_support['Date'] >= date_limite].copy()
    elif periode == "Dernier mois":
        date_limite = derniere_date - pd.DateOffset(months=1)
        df_filtered = df_support[df_support['Date'] >= date_limite].copy()
    else:
        date_limite = df_support['Date'].min()  # Toute la période
        df_filtered = df_support[df_support['Date'] >= date_limite].copy()
    
    # Exclure explicitement la semaine S2025-01 qui apparaît toujours
    # même après filtrage par date (probablement due à des dates mal formatées)
    if 'Semaine' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Semaine'] != 'S2025-01'].copy()
    
    return df_filtered

def graph_activite(df_support):
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    # Filtrage des données pour l'activité entrante
    data_graph1 = df_support[df_support['direction'] == 'inbound']

    # Agrégation des données par semaine et date
    data_graph2 = (
        data_graph1.groupby(['Semaine'])
        .agg(
            Entrant=('Entrant', 'sum'),
            Entrant_connect=('Entrant_connect', 'sum'),
            Numero_unique=('Number', 'nunique'),
            Effectif=('Effectif', 'mean')
        )
        .reset_index()
    )

    # Agrégation finale par semaine
    data_graph3 = (
        data_graph2.groupby('Semaine')[['Entrant', 'Entrant_connect', 'Numero_unique', 'Effectif']]
        .mean()
        .reset_index()
    )

    # Tri chronologique des semaines
    ordre_semaines = sorted(data_graph3['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    data_graph3['Semaine'] = pd.Categorical(data_graph3['Semaine'], categories=ordre_semaines, ordered=True)
    data_graph3 = data_graph3.sort_values('Semaine')

    # Calcul du taux de service support
    data_graph3['Taux_de_service_support'] = (
        data_graph3['Entrant_connect'] / data_graph3['Entrant']
    )

    # Ajout d'une colonne 100%
    data_graph3['100%'] = 1

    # Création de la figure avec des sous-graphiques
    fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])

    # Ajouter les barres pour le Taux de service support
    fig.add_trace(
        go.Bar(
            x=data_graph3['Semaine'],
            y=data_graph3['Taux_de_service_support'],
            name='Taux',
            opacity=0.7,
            text=data_graph3['Taux_de_service_support'],
            texttemplate='%{text:.0%}'
        ),
        secondary_y=True,
    )

    # Ajouter les lignes empilées pour Numero_unique, Entrant_connect et Entrant
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Numero_unique'],
            name='Numero_unique',
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Entrant_connect'],
            name='Entrant_connect',
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Entrant'],
            name='Entrant',
            fill='tozeroy'
        ),
        secondary_y=False,
    )

    # Mise à jour des axes Y pour les pourcentages
    fig.update_yaxes(range=[0, 1], secondary_y=True)
    fig.update_yaxes(tickformat=".0%", secondary_y=True)

    events = {
        "S2024-03": "Stellair HS",
        "S2024-51": "Mise à jour réglementaire",
        "S2025-01": "Effectif : 2",
        "S2025-05": "Stellair HS",
        "S2025-06": "Stellair HS",
        "S2025-07": "Stellair HS",
        "S2025-09": "Stellair HS",
        "S2025-10": "Stellair HS",
        "S2025-13": "Stellair HS",
        "S2025-19": "Stellair MAJ",
        "S2025-26": "MAJ Lecteurs",
        "S2025-32": "Stellair HS",
        "S2025-48": "Stellair HS",
        "S2026-04" : "Affid BUG",
    }

    # Préparation des listes pour les bulles
    x_events = []
    y_events = []
    text_events = []

    # Pour positionner la bulle, nous récupérons la valeur maximale parmi les séries 'Entrant', 'Entrant_connect' et 'Numero_unique'
    for week, event_text in events.items():
        if week in data_graph3['Semaine'].values:
            # Récupération de la ligne correspondante
            row = data_graph3[data_graph3['Semaine'] == week].iloc[0]
            # On définit la position verticale comme le maximum des trois séries
            y_val = row['Taux_de_service_support']
            marge = 0.05  
            y_val_event = min(y_val + marge, 1)
            x_events.append(week)
            y_events.append(y_val_event)
            text_events.append(event_text)

    # Ajout du trace pour les bulles d'événements
    fig.add_trace(
        go.Scatter(
            x=x_events,
            y=y_events,
            mode="markers+text",
            marker=dict(
                size=15,
                color="red"
            ),
            text=text_events,
            textposition="top center",
            name="Événements"
        ),
        secondary_y=True,
    )

    # Configuration de la mise en page et des légendes
    fig.update_layout(
        title="Graphique avec Taux en barres et Numero_unique/Entrant en aires empilées",
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Valeurs",
        title_text="Activité & Taux de service - 20 semaines",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

def evo_appels_ticket(df_ticket, df_support):
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_ticket = df_ticket[df_ticket['Semaine'] != 'S2024-01'].copy()
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    # Filtrage des données pour l'activité entrante (même logique que graph_activite)
    df_support_inbound = df_support[df_support['direction'] == 'inbound']
    
    # Agrégation des appels entrants par semaine (même logique que graph_activite)
    entrant = df_support_inbound.groupby('Semaine', as_index=False).agg({'Number': 'nunique'})
    entrant = entrant.rename(columns={'Number': 'Entrant'})
    entrant = entrant.set_index('Semaine')['Entrant']

    # Filtrage des tickets selon la source, puis agrégation
    ticket = df_ticket[
    (df_ticket['Source'].isin(['Chat', 'E-mail', 'Formulaire'])) &
    (df_ticket['Pipeline'].isin(['SSI', 'SSIA', 'SPSA']))
    ].groupby('Semaine', as_index=False)['Ticket ID'].nunique()

    ticket.rename(columns={'Ticket ID': 'Nb_Tickets'}, inplace=True)

    ticket_s17 = ticket[ticket['Semaine'] == 'S2025-15']

    # Fusionner les deux pour garantir la cohérence des semaines
    df_merged = pd.merge(entrant, ticket, on='Semaine', how='outer').fillna(0)

    activite_appels = df_merged['Entrant'].sum() / (df_merged['Nb_Tickets'].sum() + df_merged['Entrant'].sum() )
    activite_tickets = df_merged['Nb_Tickets'].sum() / (df_merged['Nb_Tickets'].sum() + df_merged['Entrant'].sum() )

    # Trier les semaines dans l'ordre chronologique
    ordre_semaines = sorted(df_merged['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_merged['Semaine'] = pd.Categorical(df_merged['Semaine'], categories=ordre_semaines, ordered=True)
    df_merged.sort_values('Semaine', inplace=True)

    # Création du graphique en aires empilées
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_merged['Semaine'],
        y=df_merged['Entrant'],
        mode='lines',
        name='Appels entrants',
        stackgroup='one',
        line=dict(color='lightblue')
    ))

    fig.add_trace(go.Scatter(
        x=df_merged['Semaine'],
        y=df_merged['Nb_Tickets'],
        mode='lines',
        name='Tickets',
        stackgroup='one',
        line=dict(color='indianred')
    ))

    fig.update_layout(
        title="Évolution hebdomadaire : Appels entrants + Tickets (aire empilée)",
        xaxis_title="Semaine",
        yaxis_title="Volume total",
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    return fig, activite_appels, activite_tickets, ticket_s17

def evo_appels_ticket_mensuel(df_ticket, df_support):
    # Construction d'un graphique mensuel similaire à evo_appels_ticket mais agrégé par mois
    df_ticket = df_ticket.copy()
    df_support = df_support.copy()

    # Assurer les colonnes Mois
    if 'Mois' not in df_support.columns:
        if 'StartTime' in df_support.columns:
            df_support['Mois'] = pd.to_datetime(df_support['StartTime']).dt.strftime('%Y-%m')
        elif 'Date' in df_support.columns:
            df_support['Mois'] = pd.to_datetime(df_support['Date']).dt.strftime('%Y-%m')
    if 'Mois' not in df_ticket.columns:
        if 'Date' in df_ticket.columns:
            df_ticket['Mois'] = pd.to_datetime(df_ticket['Date']).dt.strftime('%Y-%m')

    # Appels entrants par mois (unique Number par jour, puis somme mensuelle, comme l'hebdo)
    entrant_mensuel = df_support.groupby(['Mois','Date'], as_index=False).agg({'Number': 'nunique'})
    entrant_mensuel = entrant_mensuel.rename(columns={'Number': 'Entrant'})
    entrant_mensuel = entrant_mensuel.groupby('Mois', as_index=False)['Entrant'].sum()

    # Nombre de numéros uniques par mois (sans agrégation par jour)
    numeros_uniques_mensuel = df_support.groupby('Mois', as_index=False).agg({'Number': 'nunique'})
    numeros_uniques_mensuel = numeros_uniques_mensuel.rename(columns={'Number': 'Numeros_Uniques'})

    # Tickets par mois (sources et pipeline SSI uniquement)
    ticket_mensuel = df_ticket[
        (df_ticket['Source'].isin(['Chat', 'E-mail', 'Formulaire'])) &
        (df_ticket['Pipeline'] == 'SSI')
    ].groupby('Mois', as_index=False)['Ticket ID'].nunique()
    ticket_mensuel = ticket_mensuel.rename(columns={'Ticket ID': 'Nb_Tickets'})

    # Fusion (sans numéros uniques)
    df_merged = pd.merge(entrant_mensuel, ticket_mensuel, on='Mois', how='outer').fillna(0)
    df_merged['Mois_dt'] = pd.to_datetime(df_merged['Mois'] + '-01')

    # Générer la liste complète de tous les mois entre min et max
    if not df_merged.empty:
        min_month = df_merged['Mois_dt'].min().to_period('M').to_timestamp()
        max_month = df_merged['Mois_dt'].max().to_period('M').to_timestamp()
        full_months = pd.date_range(start=min_month, end=max_month, freq='MS')
        full_months_str = full_months.strftime('%Y-%m')

        # Reindexer pour inclure tous les mois manquants avec 0
        df_full = pd.DataFrame({'Mois': full_months_str})
        df_full['Mois_dt'] = full_months
        df_merged = df_full.merge(df_merged[['Mois','Entrant','Nb_Tickets','Mois_dt']], on=['Mois','Mois_dt'], how='left').fillna(0)

    # Tri chronologique
    df_merged = df_merged.sort_values('Mois_dt')

    # Graphique en barres empilées (Appels entrants + Tickets)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_merged['Mois'],
        y=df_merged['Entrant'],
        name='Appels entrants',
        marker=dict(color='lightblue')
    ))
    fig.add_trace(go.Bar(
        x=df_merged['Mois'],
        y=df_merged['Nb_Tickets'],
        name='Tickets',
        marker=dict(color='indianred')
    ))
    fig.update_layout(
        title="Évolution mensuelle : Appels entrants + Tickets (barres empilées)",
        xaxis_title="Mois",
        yaxis_title="Volume total",
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        barmode='stack',
        template='plotly_dark',
        margin=dict(l=40, r=20, t=60, b=100)
    )

    # Forcer l'ordre et l'affichage de chaque mois en ticks
    all_months = df_merged['Mois'].tolist()
    fig.update_xaxes(
        type='category',
        categoryorder='array',
        categoryarray=all_months,
        tickmode='array',
        tickvals=all_months,
        ticktext=all_months,
        ticks='outside',
        tickfont=dict(size=10),
        showticklabels=True,
        automargin=True
    )

    return fig

def evo_tickets_par_sujets_mensuel(df_tickets):
    """
    Crée deux graphiques :
    1. Un graphique du nombre total de tickets par mois
    2. Un graphique d'évolution mensuelle du nombre de tickets par sujets (8 subplots)
    Utilise les mêmes 8 sujets principaux que le graphique sunburst
    """
    df_tickets = df_tickets.copy()
    
    # Assurer la colonne Mois
    if 'Mois' not in df_tickets.columns:
        if 'Date' in df_tickets.columns:
            df_tickets['Mois'] = pd.to_datetime(df_tickets['Date']).dt.strftime('%Y-%m')
    
    # Filtrer les tickets pertinents - uniquement pipeline SSI
    df_filtered = df_tickets[
        (df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire']) | pd.isna(df_tickets['Source'])) &
        (df_tickets['Pipeline'] == 'SSI')
    ].copy()
    
    # === GRAPHIQUE 1: TOTAL MENSUEL ===
    # Calculer le total de tickets par mois
    tickets_total_mensuel = df_filtered.groupby('Mois', as_index=False)['Ticket ID'].nunique()
    tickets_total_mensuel = tickets_total_mensuel.rename(columns={'Ticket ID': 'Nb_Tickets'})
    
    # Générer la liste complète de tous les mois
    if not tickets_total_mensuel.empty:
        min_month = pd.to_datetime(tickets_total_mensuel['Mois'].min() + '-01')
        max_month = pd.to_datetime(tickets_total_mensuel['Mois'].max() + '-01')
        full_months = pd.date_range(start=min_month, end=max_month, freq='MS')
        full_months_str = full_months.strftime('%Y-%m')
        
        # Reindexer pour inclure tous les mois manquants avec 0
        df_full = pd.DataFrame({'Mois': full_months_str})
        tickets_total_mensuel = df_full.merge(tickets_total_mensuel, on='Mois', how='left').fillna(0)
    
    # Créer le graphique du total mensuel
    fig_total = go.Figure()
    fig_total.add_trace(go.Bar(
        x=tickets_total_mensuel['Mois'],
        y=tickets_total_mensuel['Nb_Tickets'],
        marker_color='#2E86AB',
        hovertemplate='<b>Total tickets</b><br>' +
                     'Mois: %{x}<br>' +
                     'Nombre de tickets: %{y}<br>' +
                     '<extra></extra>'
    ))
    
    fig_total.update_layout(
        title="Évolution mensuelle du nombre total de tickets SSI",
        xaxis_title="Mois",
        yaxis_title="Nombre de tickets",
        xaxis_tickangle=-45,
        template='plotly_dark',
        margin=dict(l=40, r=20, t=60, b=100),
        height=400
    )
    
    # Forcer l'ordre et l'affichage de chaque mois en ticks
    all_months = tickets_total_mensuel['Mois'].tolist()
    fig_total.update_xaxes(
        type='category',
        categoryorder='array',
        categoryarray=all_months,
        tickmode='array',
        tickvals=all_months,
        ticktext=all_months,
        ticks='outside',
        tickfont=dict(size=10),
        showticklabels=True,
        automargin=True
    )
    
    # Mapping des catégories vers les 8 sujets principaux (même que sunburst)
    categories_to_subjects = {
        "Formation": "Formation",
        "Livraison": "Installation",
        "ADV (contrats, résiliation, commerce)": "ADV / Logistique",
        "Activation / Désactivation": "ADV / Logistique",
        "Recettes": "Recettes",
        "PbConnexion": "Lecteur",
        "Facturation": "Facturation",
        "Stellair": "Connexion à Stellair",
        "PC/SC": "Lecteur",
        "Information": "Utilisation",
        "MAN": "Installation",
        "Lecteur": "Lecteur",
        "Lecture CV": "Lecteur",
        "SCOR": "Utilisation",
        "Authentification / sécurisation CPS": "Lecteur",
        "Installation": "Installation",
        "Appairage": "Lecteur",
        "Stellair Erreur": "Connexion à Stellair",
        "Echange": "Lecteur",
        "CB": "Lecteur",
        "Amélioration": "Utilisation",
        "Lecteur/Parametrage": "Lecteur",
        "TPAMC": "Facturation",
        "Facturation C2S": "Facturation",
        "Authentification / sécurisation ProSanteConnect": "Lecteur",
        "Fonctionnalités": "Utilisation",
        "Télétransmission": "Utilisation",
        "MAJ": "Lecteur",
        "TP AMO": "Facturation",
        "Rejets": "Facturation",
        "Lecture CPS": "Lecteur",
        "ApCv": "Utilisation",
        "Stellair Connexion": "Connexion à Stellair",
        "Facturation TP AMC": "Facturation",
        "Lecteur Ethernet": "Lecteur",
        "Téléservices": "Utilisation",
        "Connexion Ethernet": "Lecteur",
        "Remplacant/Collaborateur": "Utilisation",
        "Impression": "Utilisation",
        "Lecteur CPS": "Lecteur",
        "AME": "Facturation",
        "Export API": "Utilisation",
        "Connexion Wifi": "Lecteur",
    }
    
    # Appliquer le mapping si la colonne Catégorie existe
    if 'Catégorie' in df_filtered.columns:
        df_filtered['Sujet'] = df_filtered['Catégorie'].map(categories_to_subjects).fillna('Autre')
    elif 'Sujet' not in df_filtered.columns:
        # Si pas de colonne Sujet ni Catégorie, créer un graphique simple
        tickets_par_mois = df_filtered.groupby('Mois', as_index=False)['Ticket ID'].nunique()
        tickets_par_mois = tickets_par_mois.rename(columns={'Ticket ID': 'Nb_Tickets'})
        
        # Générer la liste complète de tous les mois
        if not tickets_par_mois.empty:
            min_month = pd.to_datetime(tickets_par_mois['Mois'].min() + '-01')
            max_month = pd.to_datetime(tickets_par_mois['Mois'].max() + '-01')
            full_months = pd.date_range(start=min_month, end=max_month, freq='MS')
            full_months_str = full_months.strftime('%Y-%m')
            
            # Reindexer pour inclure tous les mois manquants avec 0
            df_full = pd.DataFrame({'Mois': full_months_str})
            tickets_par_mois = df_full.merge(tickets_par_mois, on='Mois', how='left').fillna(0)
        
        # Créer le graphique simple
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=tickets_par_mois['Mois'],
            y=tickets_par_mois['Nb_Tickets'],
            marker_color='lightblue',
            hovertemplate='<b>Total tickets</b><br>' +
                         'Mois: %{x}<br>' +
                         'Nombre de tickets: %{y}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title="Évolution mensuelle du nombre total de tickets",
            xaxis_title="Mois",
            yaxis_title="Nombre de tickets",
            xaxis_tickangle=-45,
            template='plotly_dark',
            margin=dict(l=40, r=20, t=60, b=100),
            height=400
        )
        
        return fig
    
    # Les 8 sujets principaux (même que sunburst)
    sujets_principaux = [
        "Formation", "Installation", "ADV / Logistique", "Recettes",
        "Lecteur", "Facturation", "Connexion à Stellair", "Utilisation"
    ]
    
    # Compter les tickets par mois et par sujet
    tickets_par_sujet_mois = df_filtered.groupby(['Mois', 'Sujet'], as_index=False)['Ticket ID'].nunique()
    tickets_par_sujet_mois = tickets_par_sujet_mois.rename(columns={'Ticket ID': 'Nb_Tickets'})
    
    # Filtrer pour ne garder que les 8 sujets principaux
    tickets_par_sujet_mois = tickets_par_sujet_mois[
        tickets_par_sujet_mois['Sujet'].isin(sujets_principaux)
    ]
    
    # Créer un pivot table pour avoir les sujets en colonnes
    pivot_df = tickets_par_sujet_mois.pivot(index='Mois', columns='Sujet', values='Nb_Tickets').fillna(0)
    
    # S'assurer que tous les sujets principaux sont présents (même avec 0 tickets)
    for sujet in sujets_principaux:
        if sujet not in pivot_df.columns:
            pivot_df[sujet] = 0
    
    # Réorganiser les colonnes dans l'ordre des sujets principaux
    pivot_df = pivot_df[sujets_principaux]
    
    # Générer la liste complète de tous les mois entre min et max
    if not pivot_df.empty:
        min_month = pd.to_datetime(pivot_df.index.min() + '-01')
        max_month = pd.to_datetime(pivot_df.index.max() + '-01')
        full_months = pd.date_range(start=min_month, end=max_month, freq='MS')
        full_months_str = full_months.strftime('%Y-%m')
        
        # Reindexer pour inclure tous les mois manquants avec 0
        pivot_df = pivot_df.reindex(full_months_str, fill_value=0)
    
    # Créer un graphique avec subplots - un pour chaque sujet
    from plotly.subplots import make_subplots
    
    # Créer 8 subplots (2 lignes x 4 colonnes)
    fig = make_subplots(
        rows=2, cols=4,
        subplot_titles=sujets_principaux,
        vertical_spacing=0.12,
        horizontal_spacing=0.08
    )
    
    # Couleurs pour les 8 sujets principaux
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
    ]
    
    # Ajouter une trace pour chaque sujet dans son propre subplot
    for i, sujet in enumerate(sujets_principaux):
        row = (i // 4) + 1  # Ligne (1 ou 2)
        col = (i % 4) + 1   # Colonne (1, 2, 3, ou 4)
        
        fig.add_trace(
            go.Bar(
                x=pivot_df.index,
                y=pivot_df[sujet],
                marker_color=colors[i % len(colors)],
                name=sujet,
                showlegend=False,  # Pas de légende car chaque sujet a son propre graphique
                hovertemplate=f'<b>{sujet}</b><br>' +
                             'Mois: %{x}<br>' +
                             'Nombre de tickets: %{y}<br>' +
                             '<extra></extra>'
            ),
            row=row, col=col
        )
    
    # Mise à jour du layout général
    fig.update_layout(
        title="Évolution mensuelle du nombre de tickets SSI par sujets principaux",
        template='plotly_dark',
        height=800,  # Plus de hauteur pour accommoder les 2 lignes
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    # Mise à jour des axes pour tous les subplots
    all_months = pivot_df.index.tolist()
    
    # Mise à jour des axes X pour tous les subplots
    for i in range(1, 9):  # 8 subplots
        fig.update_xaxes(
            type='category',
            categoryorder='array',
            categoryarray=all_months,
            tickmode='array',
            tickvals=all_months,
            ticktext=all_months,
            tickangle=-45,
            tickfont=dict(size=8),
            showticklabels=True,
            row=(i-1)//4 + 1,
            col=(i-1)%4 + 1
        )
        
        # Mise à jour des axes Y
        fig.update_yaxes(
            title_text="Tickets",
            title_font=dict(size=10),
            tickfont=dict(size=8),
            row=(i-1)//4 + 1,
            col=(i-1)%4 + 1
        )
    
    # Retourner les deux graphiques
    return fig_total, fig

def top30_categories_tickets(df_tickets):
    """
    Crée un graphique en barres de toutes les catégories de tickets
    """
    # Filtrer les tickets selon les mêmes critères que evo_appels_ticket
    df_filtered = df_tickets[
        (df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire'])) &
        (df_tickets['Pipeline'].isin(['SSI', 'SSIA', 'SPSA']))
    ].copy()
    
    # Compter les tickets par catégorie
    if 'Catégorie' in df_filtered.columns:
        category_col = 'Catégorie'
    elif 'Category' in df_filtered.columns:
        category_col = 'Category'
    else:
        # Si pas de colonne catégorie, utiliser Pipeline comme fallback
        category_col = 'Pipeline'
    
    df_categories = df_filtered.groupby(category_col)['Ticket ID'].nunique().reset_index()
    df_categories = df_categories.rename(columns={'Ticket ID': 'Nb_Tickets'})
    
    # Trier par nombre de tickets (toutes les catégories)
    df_categories = df_categories.sort_values('Nb_Tickets', ascending=False)
    
    # Calculer la hauteur dynamique en fonction du nombre de catégories
    nb_categories = len(df_categories)
    height = max(400, nb_categories * 25)  # Minimum 400px, 25px par catégorie
    
    # Créer le graphique en barres
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_categories['Nb_Tickets'],
        y=df_categories[category_col],
        orientation='h',
        marker=dict(color='lightcoral'),
        text=df_categories['Nb_Tickets'],
        textposition='auto'
    ))
    
    fig.update_layout(
        title=f"Toutes les catégories de tickets ({nb_categories} catégories)",
        xaxis_title="Nombre de tickets",
        yaxis_title="Catégorie",
        template='plotly_dark',
        height=height,
        margin=dict(l=200, r=40, t=60, b=40)  # Marge gauche plus grande pour les noms de catégories
    )
    
    # Inverser l'ordre des catégories pour avoir le top en haut
    fig.update_yaxes(autorange="reversed")
    
    return fig

def sunburst_categories_tickets(df_tickets):
    """
    Crée un graphique en barres empilées des catégories de tickets par sujets principaux
    """
    import pandas as pd
    
    # Mapping direct des catégories vers les sujets principaux
    categories_to_subjects = {
        "Formation": "Formation",
        "Livraison": "Installation",
        "ADV (contrats, résiliation, commerce)": "ADV / Logistique",
        "Activation / Désactivation": "ADV / Logistique",
        "Recettes": "Recettes",
        "PbConnexion": "Lecteur",
        "Facturation": "Facturation",
        "Stellair": "Connexion à Stellair",
        "PC/SC": "Lecteur",
        "Information": "Utilisation",
        "MAN": "Installation",
        "Lecteur": "Lecteur",
        "Lecture CV": "Lecteur",
        "SCOR": "Utilisation",
        "Authentification / sécurisation CPS": "Lecteur",
        "Installation": "Installation",
        "Appairage": "Lecteur",
        "Stellair Erreur": "Connexion à Stellair",
        "Echange": "Lecteur",
        "CB": "Lecteur",
        "Amélioration": "Utilisation",
        "Lecteur/Parametrage": "Lecteur",
        "TPAMC": "Facturation",
        "Facturation C2S": "Facturation",
        "Authentification / sécurisation ProSanteConnect": "Lecteur",
        "Fonctionnalités": "Utilisation",
        "Télétransmission": "Utilisation",
        "MAJ": "Lecteur",
        "TP AMO": "Facturation",
        "Rejets": "Facturation",
        "Lecture CPS": "Lecteur",
        "ApCv": "Utilisation",
        "Stellair Connexion": "Connexion à Stellair",
        "Facturation TP AMC": "Facturation",
        "Lecteur Ethernet": "Lecteur",
        "Téléservices": "Utilisation",
        "Connexion Ethernet": "Lecteur",
        "Remplacant/Collaborateur": "Utilisation",
        "Impression": "Utilisation",
        "Lecteur CPS": "Lecteur",
        "AME": "Facturation",
        "Export API": "Utilisation",
        "Connexion Wifi": "Lecteur",
        "Connexion 3G": "Lecteur",
        "Lecteur/Dechargement": "Lecteur",
        "Lecteur Alimentation": "Lecteur",
        "Remplacement": "Lecteur",
        "AmeliPro": "Utilisation",
        "Facturation ALD": "Facturation",
        "Lecteur CV": "Facturation",
        "Réclamation": "ADV / Logistique",
        "Ordoclic": "Utilisation",
        "Facturation Hôpital": "Facturation",
        "3G": "Lecteur",
        "SAV": "Lecteur"
    }
    
    # Filtrer les tickets du pipeline SSI uniquement
    df_filtered = df_tickets[
        (df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire'])) &
        (df_tickets['Pipeline'] == 'SSI')
    ].copy()
    
    # Déterminer la colonne catégorie dans les tickets
    if 'Catégorie' in df_filtered.columns:
        category_col = 'Catégorie'
    elif 'Category' in df_filtered.columns:
        category_col = 'Category'
    else:
        category_col = 'Pipeline'
    
    # Filtrer les tickets pour ne garder que les catégories présentes dans le mapping
    valid_categories = list(categories_to_subjects.keys())
    df_filtered = df_filtered[df_filtered[category_col].isin(valid_categories)]
    
    if df_filtered.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun ticket trouvé avec les catégories du mapping",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(title="Graphique des catégories par sujets (SSI)")
        return fig
    
    # Compter les tickets par catégorie
    df_tickets_count = df_filtered.groupby(category_col)['Ticket ID'].nunique().reset_index()
    df_tickets_count = df_tickets_count.rename(columns={'Ticket ID': 'count'})
    
    # Ajouter la colonne sujet basée sur le mapping
    df_tickets_count['sujet'] = df_tickets_count[category_col].map(categories_to_subjects)
    
    # Créer un Sunburst avec plotly.express - Structure hiérarchique correcte
    
    # Calculer le total de tous les tickets
    total_all_tickets = df_tickets_count['count'].sum()
    
    # Préparer les données pour le Sunburst
    sujets_data = df_tickets_count.groupby('sujet')['count'].sum().reset_index()
    sujets_data = sujets_data.sort_values('count', ascending=False)
    
    # Calculer les tickets non mappés (sujets manquants)
    total_mapped_tickets = sujets_data['count'].sum()
    tickets_non_mappes = total_all_tickets - total_mapped_tickets
    
    # Ajouter une catégorie "Autres" pour les tickets non mappés si nécessaire
    if tickets_non_mappes > 0:
        autres_row = pd.DataFrame({
            'sujet': ['Autres'],
            'count': [tickets_non_mappes]
        })
        sujets_data = pd.concat([sujets_data, autres_row], ignore_index=True)
    
    # Ajouter les catégories (niveau secondaire) - Top 30 seulement
    # Regrouper par sujet et prendre les top catégories de chaque sujet
    categories_by_subject = []
    for sujet in sujets_data['sujet']:
        sujet_categories = df_tickets_count[df_tickets_count['sujet'] == sujet].sort_values('count', ascending=False)
        # Prendre les top catégories de ce sujet (max 5 par sujet pour avoir ~30 au total)
        top_categories = sujet_categories.head(5)
        categories_by_subject.append(top_categories)
    
    # Concaténer et prendre les top 30
    categories_data = pd.concat(categories_by_subject).sort_values('count', ascending=False).head(30)
    
    # Calculer les tickets non inclus dans le top 30 pour compléter le cercle
    total_tickets_included = categories_data['count'].sum()
    total_tickets_all = df_tickets_count['count'].sum()
    tickets_autres = total_tickets_all - total_tickets_included
    
    if sujets_data.empty or categories_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée trouvée pour le graphique Sunburst",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(title="Graphique Sunburst des catégories")
        return fig
    
    # Créer la structure hiérarchique correcte avec valeurs brutes
    sunburst_rows = []
    
    # Ajout de la racine avec le total réel
    sunburst_rows.append({'names': 'Root', 'parents': '', 'values': total_all_tickets})
    
    # Ajout du niveau sujet/principal avec valeurs brutes - Éviter les doublons avec les catégories
    for _, row in sujets_data.iterrows():
        sujet_name = row['sujet']
        # Vérifier si le nom du sujet existe déjà comme catégorie
        if sujet_name in categories_data[category_col].values:
            sujet_name = f"{sujet_name}s"  # Ajouter un 's' pour éviter le doublon
        
        sunburst_rows.append({'names': sujet_name, 'parents': 'Root', 'values': row['count']})
    
    # Ajout des catégories/sous-niveaux avec valeurs brutes
    for _, row in categories_data.iterrows():
        sujet_name = row['sujet']
        # Utiliser le même nom modifié que pour le niveau sujet
        if sujet_name in categories_data[category_col].values:
            sujet_name = f"{sujet_name}s"
        
        sunburst_rows.append({
            'names': row[category_col], 
            'parents': sujet_name, 
            'values': row['count']
        })
    
    # Ajouter les catégories "Autres" pour chaque sujet si nécessaire
    for _, row in sujets_data.iterrows():
        sujet_name = row['sujet']
        # Utiliser le même nom modifié que pour le niveau sujet
        if sujet_name in categories_data[category_col].values:
            sujet_name = f"{sujet_name}s"
        
        # Calculer les tickets de ce sujet inclus dans le top 30
        sujet_categories_included = categories_data[categories_data['sujet'] == row['sujet']]['count'].sum()
        sujet_total = row['count']
        sujet_autres = sujet_total - sujet_categories_included
        
        # Ajouter "Autres" seulement s'il y a des tickets non inclus
        if sujet_autres > 0:
            sunburst_rows.append({
                'names': f"Autres {row['sujet']}", 
                'parents': sujet_name, 
                'values': sujet_autres
            })
    
    # Créer le DataFrame et supprimer les doublons
    sunburst_df = pd.DataFrame(sunburst_rows).drop_duplicates(subset=['names', 'parents'])
    
    # Créer le graphique Sunburst avec plotly.express
    fig = px.sunburst(
        sunburst_df,
        names='names',
        parents='parents',
        values='values',
        title="Répartition des tickets SSI par sujets et catégories",
        template='plotly_dark',
        height=600,
        branchvalues="total"  # Assure la répartition complète
    )
    
    # Modifier le hover template pour afficher les quantités et pourcentages
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Tickets: %{value}<br>Pourcentage: %{percentParent:.1f}%<extra></extra>'
    )
    
    # Ajouter les pourcentages sur les sujets principaux uniquement
    for i, trace in enumerate(fig.data):
        if trace.type == 'sunburst':
            # Créer une liste de textes personnalisés
            custom_text = []
            for j, label in enumerate(trace.labels):
                # Vérifier si c'est un sujet principal (parent de Root)
                if trace.parents[j] == 'Root':
                    # Calculer le pourcentage par rapport au total
                    value = trace.values[j]
                    percentage = (value / total_all_tickets) * 100
                    custom_text.append(f"{label}<br>{percentage:.1f}%")
                else:
                    # Pour les catégories, afficher seulement le nom
                    custom_text.append(label)
            
            # Appliquer les textes personnalisés
            fig.data[i].text = custom_text
            fig.data[i].textinfo = 'text'
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def calcul_taux_reponse(df_support):
    df = df_support
    df['LastState'] = df['LastState'] == 'yes'
    entrants = df[df['direction'] == 'inbound']
    sortants = df[df['direction'] == 'outbound']
    grouped_sortants = sortants.groupby(['Date', 'Number']).agg({'LastState': 'any', 'StartTime': 'mean'}).reset_index()
    grouped_entrants = entrants.groupby(['Date', 'Number']).agg({'LastState': 'any', 'StartTime': 'mean'}).reset_index()
    grouped_sortants = grouped_sortants.rename(columns={'LastState': 'Repondu_sortant', 'StartTime': 'Heure_sortant'})
    merged = pd.merge(grouped_entrants, grouped_sortants, on=['Date', 'Number'], how='left')
    merged['Repondu_sortant'].fillna(False, inplace=True)
    merged['Repondu_total'] = merged['LastState'] | merged['Repondu_sortant']
    taux_reponse = merged['Repondu_total'].mean()
    merged['StartTime'] = pd.to_datetime(merged['StartTime'])
    merged['Heure_sortant'] = pd.to_datetime(merged['Heure_sortant'])
    merged['minute_difference'] = np.where(merged['Repondu_sortant'] == True, (merged['Heure_sortant'] - merged['StartTime']) / pd.Timedelta(minutes=1), np.nan)
    mean_difference = merged['minute_difference'][merged['minute_difference'] >= 0].mean()
    return taux_reponse, mean_difference, merged

def metrics_support(df_support, agents):
    # Gestion des NaN pour 'Taux_de_service' avant conversion
    mean_taux_de_service = df_support['Taux_de_service'].mean()
    Taux_de_service = int(mean_taux_de_service * 100) if not pd.isna(mean_taux_de_service) else 0

    # Gestion des NaN et calcul des appels entrants
    mean_entrant = df_support.groupby('Date').agg({'Entrant': 'sum'}).mean().values[0]
    Entrant = int(mean_entrant) if not pd.isna(mean_entrant) else 0

    # Gestion des NaN et calcul des numéros uniques
    mean_numero_unique = df_support[df_support['direction'] == 'inbound'].groupby('Date').agg({'Number': 'nunique'}).mean().values[0]
    Numero_unique = int(mean_numero_unique) if not pd.isna(mean_numero_unique) else 0

    # Calcul de la moyenne de la durée des appels, en excluant les valeurs <= 0
    temps_moy_appel = df_support[df_support['InCallDuration'] > 0].InCallDuration.mean()
    temps_moy_appel = temps_moy_appel if not pd.isna(temps_moy_appel) else 0

    # Filtrage des agents
    if agents == "agents_support":
        df_support = df_support[df_support['UserName'].isin(["Mourad HUMBLOT", 'Archimede KESSI'])]
    elif agents == "agents_armatis":
        df_support = df_support[df_support['UserName'].isin(["Emilie GEST", 'Morgane Vandenbussche', 'Melinda Marmin', 'Sandrine Sauvage', 'Céline Crendal'])]
    elif agents == "agents_all":
        pass  # Pas besoin de filtrer
    else:
        df_support = df_support[df_support['UserName'].isin(agents)]

    # Calcul du nombre d'appels par agent
    Nombre_appel_jour_agent = df_support['UserName'].nunique()

    return [Taux_de_service, Entrant, Numero_unique, temps_moy_appel, Nombre_appel_jour_agent]

def sla_2h_spsa(df_tickets):
    df_sla_2h = df_tickets[(df_tickets['working_hours'] < 2) & (df_tickets['working_hours'] > 0.1)].groupby(['Semaine'])['working_hours'].count().reset_index().rename(columns={'working_hours': 'SLA < 2h'})
    df_tickets_std = df_tickets.groupby(['Semaine'])['working_hours'].count().reset_index().rename(columns={'working_hours': 'Nb tickets'})
    df_tickets_sla = pd.merge(df_tickets_std, df_sla_2h, how='left', on='Semaine')
    pourcentage_sla = (df_tickets_sla['SLA < 2h'].mean() / df_tickets_sla['Nb tickets'].mean()) * 100
    pourcentage_sla = f"{pourcentage_sla:.2f}%"
    return pourcentage_sla, df_tickets_std

def activite_ticket_source_client(df_tickets):
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()

    df = df_tickets[df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire'])].groupby(['Semaine', 'Pipeline'])['Ticket ID'].nunique().reset_index()
    
    # Tri chronologique
    ordre_semaines = sorted(df['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df['Semaine'] = pd.Categorical(df['Semaine'], categories=ordre_semaines, ordered=True)
    df = df.sort_values('Semaine')
    
    fig = px.bar(df, x="Semaine", y="Ticket ID", color="Pipeline", title="Activité des tickets par pipeline / semaine", labels={"working_hours": "Heures de travail", "Semaine": "Semaine"})
    return fig

def graph_charge_affid_stellair(df_support):
    df_support = df_support[df_support['Semaine'] != 'S2024-01']

    essai = df_support[df_support['Semaine'] == 'S2025-6']['IVR Branch'].value_counts()

    affid = df_support[(df_support['direction'] == 'inbound') & (df_support['Logiciel'] == 'Affid')] \
        .groupby(['Semaine']).agg({'Count': 'sum'}).rename(columns={'Count': 'Affid'}).reset_index()
    stellair = df_support[(df_support['direction'] == 'inbound') & (df_support['Logiciel'] == 'Stellair')] \
        .groupby(['Semaine']).agg({'Count': 'sum'}).rename(columns={'Count': 'Stellair'}).reset_index()

    df_resultats = pd.merge(stellair, affid, on='Semaine').reset_index()

    # Tri chronologique
    ordre_semaines = sorted(df_resultats['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_resultats['Semaine'] = pd.Categorical(df_resultats['Semaine'], categories=ordre_semaines, ordered=True)
    df_resultats = df_resultats.sort_values('Semaine')

    df_resultats['Charge_support_call_stellair'] = df_resultats['Stellair'] / (df_resultats['Stellair'] + df_resultats['Affid'])
    df_resultats['Charge_support_call_affid'] = df_resultats['Affid'] / (df_resultats['Stellair'] + df_resultats['Affid'])

    fig = px.bar(df_resultats, 
                 x='Semaine',
                 y=['Charge_support_call_stellair', 'Charge_support_call_affid'],
                 template='plotly_dark')
    
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(
        title_text="Activité en % - NXT & Stellair",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig2 = px.bar(df_resultats, 
                  x='Semaine',
                  y=['Stellair', 'Affid'],
                  template='plotly_dark')
    
    fig2.update_layout(
        title_text="Activité en Nb - NXT & Stellair",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig, fig2, essai

def graph_repartition_groupes_stellair(df_support):
    """
    Crée un graphique de type aire empilée montrant la répartition des appels entrants
    pris par 2 groupes d'agents sur la période sélectionnée.
    
    Groupe 1 : Mourad, Christophe, Archimède et Pierre
    Groupe 2 : Sandrine, Mélinda, Emilie, Celine et Morgane
    """
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    # AJOUT : filtrer sur line = 'armatistechnique' ou 'technique'
    if 'line' in df_support.columns:
        df_support = df_support[df_support['line'].isin(['armatistechnique', 'technique'])]

    # Définir les groupes d'agents avec leurs variantes de noms
    groupe_1_agents = [
        'Mourad HUMBLOT', 'HUMBLOT NASSUF',
        'Christophe Brichet',
        'Archimede KESSI', 'Archimède KESSI',
        'Pierre GOUPILLON', 'Pierre Goupillon'
    ]
    
    groupe_2_agents = [
        'Sandrine Sauvage',
        'Melinda Marmin',
        'Emilie GEST', 'Emilie Gest',
        'Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL',
        'Morgane Vandenbussche', 'Morgane VANDENBUSSCHE',
        'Cédeline DUVAL', 'CÃ©deline DUVAL', 'C√©deline DUVAL', 'Sandrine Siguret'
    ]
    
    # Filtrer les appels entrants uniquement
    df_inbound = df_support[df_support['direction'] == 'inbound'].copy()
    df_inbound = df_inbound[df_inbound['LastState'] == 'yes']
    
    if df_inbound.empty:
        # Retourner un graphique vide avec un message
        fig = px.area()
        fig.add_annotation(
            text="Pas de données d'appels entrants disponibles pour cette période",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            title="Répartition des appels entrants par groupe d'agents",
            template="plotly_dark"
        )
        return fig
    
    # Créer une colonne pour identifier le groupe de l'agent
    def assign_group(agent_name):
        if agent_name in groupe_1_agents:
            return "Groupe 1 (Mourad, Christophe, Archimède, Pierre)"
        elif agent_name in groupe_2_agents:
            return "Groupe 2 (Sandrine, Mélinda, Emilie, Celine, Morgane, Cédeline)"
        else:
            return "Autres"
    
    df_inbound['Groupe_Agent'] = df_inbound['UserName'].apply(assign_group)
    
    # Agréger par semaine et groupe d'agents
    df_grouped = df_inbound.groupby(['Semaine', 'Groupe_Agent']).agg({
        'Count': 'sum'
    }).reset_index()
    
    # Filtrer pour ne garder que les deux groupes principaux
    groupes_principaux = [
        "Groupe 1 (Mourad, Christophe, Archimède, Pierre)",
        "Groupe 2 (Sandrine, Mélinda, Emilie, Celine, Morgane, Cédeline)"
    ]
    df_grouped = df_grouped[df_grouped['Groupe_Agent'].isin(groupes_principaux)]
    
    if df_grouped.empty:
        # Retourner un graphique vide avec un message
        fig = px.area()
        fig.add_annotation(
            text="Pas de données pour les groupes d'agents spécifiés",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            title="Répartition des appels entrants par groupe d'agents",
            template="plotly_dark"
        )
        return fig
    
    # Calculer les pourcentages par semaine
    # IMPORTANT : Calculer le total par semaine UNIQUEMENT à partir des groupes 1 et 2
    # pour que les pourcentages fassent 100% (exclure les "Autres")
    df_total_par_semaine = df_grouped.groupby('Semaine')['Count'].sum().reset_index()
    df_total_par_semaine = df_total_par_semaine.rename(columns={'Count': 'Total_Semaine'})
    
    # Fusionner avec les données groupées pour avoir le total par semaine
    df_grouped = pd.merge(df_grouped, df_total_par_semaine, on='Semaine', how='left')
    
    # Calculer le pourcentage (maintenant basé uniquement sur les groupes 1 et 2)
    df_grouped['Pourcentage'] = (df_grouped['Count'] / df_grouped['Total_Semaine']) * 100
    
    # Tri chronologique des semaines
    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_grouped['Semaine'] = pd.Categorical(df_grouped['Semaine'], categories=ordre_semaines, ordered=True)
    df_grouped = df_grouped.sort_values(['Semaine', 'Groupe_Agent'])
    
    # Créer le graphique en barres empilées avec les pourcentages
    fig = px.bar(
        df_grouped,
        x='Semaine',
        y='Pourcentage',
        color='Groupe_Agent',
        template='plotly_dark',
        title="Répartition des appels entrants par groupe d'agents (pourcentage par semaine)",
        barmode='stack'
    )
    
    # Personnaliser le graphique
    fig.update_layout(
        xaxis_title="Semaine",
        yaxis_title="Pourcentage d'appels entrants",
        yaxis=dict(
            range=[0, 100],
            tickformat=".0f",
            ticksuffix="%"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    # Personnaliser les couleurs
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>" +
                     "Semaine: %{x}<br>" +
                     "Pourcentage: %{y:.1f}%<br>" +
                     "<extra></extra>"
    )
    
    return fig

def graph_taux_jour(df_support):
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    # Vérifier si le DataFrame est vide
    if df_support.empty:
        # Retourner un graphique vide avec un message
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_annotation(
            text="Pas de données disponibles pour cette période",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            title="Activité & Taux de service / jour",
            template="plotly_dark"
        )
        return fig

    df_support = df_support[df_support['direction'] == 'inbound']

    data_graph2 = df_support.groupby(['Semaine','Date', 'Jour']).agg({'Entrant':'sum',
                                                                'Entrant_connect':'sum',
                                                                'Number':'nunique',
                                                                'Effectif':'mean'})
    
    # Vérifier si data_graph2 est vide après l'agrégation
    if data_graph2.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_annotation(
            text="Pas de données après agrégation",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            title="Activité & Taux de service / jour",
            template="plotly_dark"
        )
        return fig
    
    data_graph2 = data_graph2.groupby(['Semaine','Date', 'Jour']).agg({'Entrant':'mean',
                                                    'Entrant_connect':'mean',
                                                    'Number':'mean',
                                                    'Effectif':'mean'}).rename(columns = {"Number":"Numero_unique",})
    
    data_graph2['Taux_de_service_support'] = (data_graph2['Entrant_connect'] 
                                            / data_graph2['Entrant'])

    data_graph2 = data_graph2.reset_index()

    data_moyenne = data_graph2.groupby("Jour")[["Taux_de_service_support", "Entrant"]].mean().reset_index()

    # Vérifier si data_graph2 a des données avant d'accéder au dernier élément
    if len(data_graph2) > 0:
        derniere_semaine = data_graph2['Semaine'].iloc[-1]
        data_derniere_semaine = data_graph2.loc[(data_graph2['Semaine'] == derniere_semaine)]
    else:
        derniere_semaine = None
        data_derniere_semaine = pd.DataFrame()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=data_moyenne['Jour'], y=data_moyenne['Taux_de_service_support'], name="Taux de service"),
        secondary_y=False,)

    fig.add_trace(
        go.Scatter(x=data_moyenne['Jour'], y=data_moyenne['Entrant'], mode='lines', name="Entrant"), 
        secondary_y=True,)

    fig.update_yaxes(range = [0,1], secondary_y=False)
    fig.update_yaxes(range=[20,120], secondary_y=True)
    fig.update_yaxes(tickformat=".0%", secondary_y=False)

    fig.update_layout(
        title="Graphique avec Taux en barres et Numero_unique/Entrant en aires empilées",
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Valeurs",
        title_text="Activité & Taux de service / jour",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

def graph_taux_heure (df_support): 

    data_by_heure = df_support.groupby(['Heure']).agg({'Entrant':'sum', 
                                                   'Entrant_connect':'sum'}).query("Heure > 8 & Heure < 18 != 12").reset_index()


    data_by_heure['Taux_de_service_support'] = data_by_heure['Entrant_connect'] / data_by_heure['Entrant']


    #def graph_taux_heure(): 
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(x=data_by_heure['Heure'], y=data_by_heure['Entrant'], name="Entrant"),
        secondary_y=True,
    )

    fig.add_trace(
        go.Bar(x=data_by_heure['Heure'], y=data_by_heure['Taux_de_service_support'], name="Taux de service"),
        secondary_y=False,
    )


    # Formater les étiquettes de l'axe y en pourcentages
    fig.update_yaxes(range = [0,1], secondary_y=False)
    fig.update_yaxes(tickformat=".0%", secondary_y=False)
    #fig.update_yaxes(range = [50,150], secondary_y=True)

    fig.update_layout(
        title="Graphique avec Taux en barres et Numero_unique/Entrant en aires empilées",
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Valeurs",
        title_text="Activité & Taux de service / Heure",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

def _is_cedeline_duval(name):
    """Détecte si un nom correspond à Cédeline Duval (matching souple pour toutes variantes)."""
    import unicodedata
    if pd.isna(name) or not isinstance(name, str):
        return False
    # Variante encodage : C√©deline (√© = é corrompu)
    if 'C√©deline' in name or 'c√©deline' in name.lower():
        return 'duval' in name.lower()
    n = str(name).strip().lower()
    # Normaliser les caractères accentués (é -> e, etc.)
    n = unicodedata.normalize('NFD', n)
    n = ''.join(c for c in n if unicodedata.category(c) != 'Mn')
    return 'cedeline' in n and 'duval' in n


def df_compute_ticket_appels_metrics(agents_n1, df_ticket, df_support):
    import pandas as pd
    rows = []

    # Gestion des variantes de nom pour Céline Crendal et Cédeline DUVAL (même que generate_kpis)
    correspondance_noms = {
        'Céline Crendal': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Celine Crendal': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Céline CRENDAL': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Celine CRENDAL': ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'],
        'Cédeline DUVAL': ['Cédeline DUVAL', 'C√©deline DUVAL'],  # C√© = encodage corrompu de é
    }

    for agent in agents_n1:
        # Gestion des variantes de nom (même logique que generate_kpis)
        if agent in correspondance_noms:
            selected_agents = correspondance_noms[agent]
        else:
            selected_agents = [agent]
        
        # Cas spécial Cédeline DUVAL : matching souple pour capturer toutes les variantes (accents, casse, encodage)
        use_cedeline_flexible = (agent == 'Cédeline DUVAL')
        
        # Calcul optimisé des métriques essentielles - même logique que generate_kpis mais plus rapide
        
        # 1. Calcul des appels (même logique que kpi_agent)
        if use_cedeline_flexible and not df_support.empty and 'UserName' in df_support.columns:
            mask_cedeline = df_support['UserName'].apply(_is_cedeline_duval)
            df_agent_support = df_support[mask_cedeline | df_support['UserName'].isin(selected_agents)]
        else:
            df_agent_support = df_support[df_support['UserName'].isin(selected_agents)]
        if not df_agent_support.empty:
            # Calcul de la productivité des appels (même que calcul_productivite_appels)
            df_agent_connect = df_agent_support[df_agent_support['LastState'] == 'yes']
            if not df_agent_connect.empty:
                df_grouped = df_agent_connect.groupby(['Date', 'UserName']).agg({'Count': 'sum'}).reset_index()
                nb_appels_jour = df_grouped.groupby('Date')['Count'].sum().mean()
            else:
                nb_appels_jour = 0
        else:
            nb_appels_jour = 0
        
        # 2. Calcul des tickets (même logique que generate_kpis)
        # Cédeline : inclure Chatbot Yelda (tickets N1 qu'elle traite) + matching souple Propriétaire
        pipeline_tickets = ['SSIA', 'SSI', 'SPSA', 'Chatbot Yelda'] if use_cedeline_flexible else ['SSIA', 'SSI', 'SPSA']
        if use_cedeline_flexible and not df_ticket.empty and 'Propriétaire du ticket' in df_ticket.columns:
            mask_cedeline = df_ticket['Propriétaire du ticket'].apply(_is_cedeline_duval)
            mask_proprio = mask_cedeline | df_ticket['Propriétaire du ticket'].isin(selected_agents)
        else:
            mask_proprio = df_ticket['Propriétaire du ticket'].isin(selected_agents)
        agent_tickets = df_ticket[
            mask_proprio & 
            (df_ticket['Pipeline'].isin(pipeline_tickets)) &
            (df_ticket['Source'].isin(['Chat', 'E-mail', 'Formulaire']) | pd.isna(df_ticket['Source']))
        ]
        
        # Calculer la moyenne de tickets par jour (même logique que generate_kpis)
        nb_jours = len(df_support['Date'].unique())
        if nb_jours == 0:
            nb_jours = 1
        moy_ticket_agent = len(agent_tickets) / nb_jours
        
        # 3. Calcul du ratio entrants (même logique que kpi_agent)
        if not df_agent_support.empty:
            nb_appels_entrants = df_agent_support[df_agent_support['direction'] == 'inbound']['Entrant_connect'].sum()
            nb_appels_sortants = df_agent_support[df_agent_support['direction'] == 'outbound']['Sortant_connect'].sum()
            total_appels = nb_appels_entrants + nb_appels_sortants
            ratio_entrants = nb_appels_entrants / total_appels if total_appels > 0 else 0
        else:
            ratio_entrants = 0

        rows.append({
            'Agent': agent,
            "Nombre d'appel traité": round(nb_appels_jour, 2),
            'Nombre de ticket traité': round(moy_ticket_agent, 2),
            "% tickets": round(moy_ticket_agent / (nb_appels_jour + moy_ticket_agent), 2) * 100 if (nb_appels_jour + moy_ticket_agent) > 0 else 0,
            "% appels": round(nb_appels_jour / (nb_appels_jour + moy_ticket_agent), 2) * 100 if (nb_appels_jour + moy_ticket_agent) > 0 else 0,
            '% appel entrant agent': round(ratio_entrants, 2) * 100,
        })

    df_kpi_agents = pd.DataFrame(rows)
    return df_kpi_agents

def repartition_lecteurs_par_type(df_tickets):
    """
    Crée un graphique camembert montrant la répartition des tickets 'Lecteur' par type de lecteur
    """
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Mapping des catégories vers les sujets (même que dans les autres fonctions)
    categories_to_subjects = {
        "Formation": "Formation",
        "Livraison": "Installation",
        "ADV (contrats, résiliation, commerce)": "ADV / Logistique",
        "Activation / Désactivation": "ADV / Logistique",
        "Recettes": "Recettes",
        "PbConnexion": "Lecteur",
        "Facturation": "Facturation",
        "Stellair": "Connexion à Stellair",
        "PC/SC": "Lecteur",
        "Information": "Utilisation",
        "MAN": "Installation",
        "Lecteur": "Lecteur",
        "Lecture CV": "Lecteur",
        "SCOR": "Utilisation",
        "Authentification / sécurisation CPS": "Lecteur",
        "Installation": "Installation",
        "Appairage": "Lecteur",
        "Stellair Erreur": "Connexion à Stellair",
        "Echange": "Lecteur",
        "CB": "Lecteur",
        "Amélioration": "Utilisation",
        "Lecteur/Parametrage": "Lecteur",
        "TPAMC": "Facturation",
        "Facturation C2S": "Facturation",
        "Authentification / sécurisation ProSanteConnect": "Lecteur",
        "Fonctionnalités": "Utilisation",
        "Télétransmission": "Utilisation",
        "MAJ": "Lecteur",
        "TP AMO": "Facturation",
        "Rejets": "Facturation",
        "Lecture CPS": "Lecteur",
        "ApCv": "Utilisation",
        "Stellair Connexion": "Connexion à Stellair",
        "Facturation TP AMC": "Facturation",
        "Lecteur Ethernet": "Lecteur",
        "Téléservices": "Utilisation",
        "Connexion Ethernet": "Lecteur",
        "Remplacant/Collaborateur": "Utilisation",
        "Impression": "Utilisation",
        "Lecteur CPS": "Lecteur",
        "AME": "Facturation",
        "Export API": "Utilisation",
        "Connexion Wifi": "Lecteur",
        "Connexion 3G": "Lecteur",
        "Lecteur/Dechargement": "Lecteur",
        "Lecteur Alimentation": "Lecteur",
        "Remplacement": "Lecteur",
        "AmeliPro": "Utilisation",
        "Facturation ALD": "Facturation",
        "Lecteur CV": "Facturation",
        "Réclamation": "ADV / Logistique",
        "Ordoclic": "Utilisation",
        "Facturation Hôpital": "Facturation",
        "3G": "Lecteur",
        "SAV": "Lecteur"
    }
    
    # Déterminer la colonne catégorie dans les tickets
    if 'Catégorie' in df_tickets.columns:
        category_col = 'Catégorie'
    elif 'Category' in df_tickets.columns:
        category_col = 'Category'
    else:
        # Créer un graphique d'erreur si aucune colonne catégorie n'existe
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune colonne catégorie trouvée dans les données",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="Répartition des tickets Lecteur par type de lecteur",
            showlegend=False
        )
        return fig
    
    # Filtrer les tickets du pipeline SSI uniquement
    df_filtered = df_tickets[
        (df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire'])) &
        (df_tickets['Pipeline'] == 'SSI')
    ].copy()
    
    # Filtrer les tickets pour ne garder que les catégories qui correspondent au sujet "Lecteur"
    categories_lecteur = [cat for cat, sujet in categories_to_subjects.items() if sujet == 'Lecteur']
    df_lecteur = df_filtered[df_filtered[category_col].isin(categories_lecteur)].copy()
    
    if df_lecteur.empty:
        # Créer un graphique vide si aucun ticket lecteur
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun ticket 'Lecteur' trouvé",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="Répartition des tickets Lecteur par type de lecteur",
            showlegend=False
        )
        return fig
    
    # Vérifier si la colonne 'Lecteur' existe
    if 'Lecteur' not in df_lecteur.columns:
        # Créer un graphique d'erreur si la colonne n'existe pas
        fig = go.Figure()
        fig.add_annotation(
            text="Colonne 'Lecteur' non trouvée dans les données",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="Répartition des tickets Lecteur par type de lecteur",
            showlegend=False
        )
        return fig
    
    # Nettoyer les données du champ Lecteur
    df_lecteur['Lecteur'] = df_lecteur['Lecteur'].fillna('')
    df_lecteur['Lecteur'] = df_lecteur['Lecteur'].astype(str).str.strip()
    
    # Filtrer les valeurs vides (chaînes vides, 'nan', 'None', etc.)
    df_lecteur = df_lecteur[
        (df_lecteur['Lecteur'] != '') & 
        (df_lecteur['Lecteur'] != 'nan') & 
        (df_lecteur['Lecteur'] != 'None') &
        (df_lecteur['Lecteur'].notna())
    ]
    
    if df_lecteur.empty:
        # Créer un graphique vide si aucun ticket avec type de lecteur spécifié
        fig = go.Figure()
        fig.add_annotation(
            text="Aucun type de lecteur spécifié trouvé",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="Répartition des tickets Lecteur par type de lecteur",
            showlegend=False
        )
        return fig
    
    # Compter les tickets par type de lecteur
    df_repartition = df_lecteur.groupby('Lecteur')['Ticket ID'].nunique().reset_index()
    df_repartition.columns = ['Type de lecteur', 'Nombre de tickets']
    
    # Trier par nombre de tickets décroissant
    df_repartition = df_repartition.sort_values('Nombre de tickets', ascending=False)
    
    # Créer le graphique camembert
    fig = px.pie(
        df_repartition, 
        values='Nombre de tickets', 
        names='Type de lecteur',
        title="Répartition des tickets Lecteur par type de lecteur",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Personnaliser le graphique
    fig.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Nombre de tickets: %{value}<br>Pourcentage: %{percent}<extra></extra>'
    )
    
    fig.update_layout(
        font=dict(size=12),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.01
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def activite_ticket_source_pipeline(df_tickets): 
    df = df_tickets[~df_tickets['Source'].isin(['Téléphone'])].groupby(['Pipeline'])['Ticket ID'].nunique().reset_index()

    fig = px.pie(
        df, 
        names="Pipeline", 
        values="Ticket ID", 
        title="Activité des tickets par pipeline"
    )

    return fig

def calculate_performance_score(row, objectif_total=25, ratio_appels=0.7, ratio_tickets=0.3, objectif_taux_service=0.70):
    """
    Calcule le score de performance d'un agent basé sur plusieurs critères
    
    Parameters:
    -----------
    row : pandas Series
        Ligne de données contenant les métriques de l'agent
    objectif_total : int
        Nombre total de demandes attendues par jour (défaut: 25)
    ratio_appels : float
        Pourcentage attendu d'appels (défaut: 0.7)
    ratio_tickets : float
        Pourcentage attendu de tickets (défaut: 0.3)
    objectif_taux_service : float
        Taux de service cible (défaut: 0.70)
    
    Returns:
    --------
    float
        Score de performance entre 0 et 100
    """
    # 1. Calcul du volume total traité
    nb_appels = row["Nombre d'appel traité"]
    nb_tickets = row["Nombre de ticket traité"]
    volume_total = nb_appels + nb_tickets
    
    # a. Score volume (45%)
    score_volume = min(100, (volume_total / objectif_total) * 100)
    
    # b. Score répartition (25%)
    if volume_total > 0:
        pct_appels = (nb_appels / volume_total) * 100
        pct_tickets = (nb_tickets / volume_total) * 100
        
        # Calcul des écarts absolus
        ecart_appels = abs(pct_appels - (ratio_appels * 100))
        ecart_tickets = abs(pct_tickets - (ratio_tickets * 100))
        ecart_total = ecart_appels + ecart_tickets
        
        # Score répartition = 100 - (écart total × 2)
        score_repartition = max(0, 100 - (ecart_total * 2))
    else:
        score_repartition = 0
    
    # c. Score comparaison à la moyenne (15%)
    # On utilise la moyenne du service passée via l'objectif pour l'instant
    score_comparaison = min(100, (volume_total / objectif_total) * 100)
    
    # d. Score taux d'appels entrants (15%)
    # Calcul du taux d'appels entrants
    if nb_appels > 0:
        taux_appels_entrants = row.get('% appels', 0)  # Pourcentage d'appels entrants
        # Application du seuil de 60%
        if taux_appels_entrants >= 60:
            score_taux_appels_entrants = 100
        else:
            score_taux_appels_entrants = (taux_appels_entrants / 60) * 100
    else:
        score_taux_appels_entrants = 0
    
    # Calcul du score final avec les nouvelles pondérations
    score_final = (
        score_volume * 0.55 +                    # 45% pour le volume
        score_repartition * 0.15 +               # 25% pour la répartition
        score_comparaison * 0.15 +               # 15% pour la comparaison
        score_taux_appels_entrants * 0.15        # 15% pour le taux d'appels entrants
    )
    
    return score_final  # Score entre 0 et 100

def graph_tickets_n2_cumulatif(df_tickets, pipeline_filter=None):
    """
    Crée un graphique cumulatif des tickets N2 (passés au support N2) avec le stock de tickets ouverts par semaine.
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()

    # Filtrer les lignes où le ticket est passé par le N2 (pour identifier les tickets N2)
    df_n2 = df_tickets[df_tickets['Passé par le support N2'] == 'Oui'].copy()

    # Obtenir la liste des pipelines disponibles avant de filtrer
    pipelines_disponibles = sorted(df_n2['Pipeline'].unique().tolist())
    
    # Appliquer le filtre par pipeline si spécifié
    if pipeline_filter:
        if isinstance(pipeline_filter, str): pipeline_filter = [pipeline_filter]
        df_n2 = df_n2[df_n2['Pipeline'].isin(pipeline_filter)]

    if df_n2.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket N2 trouvé pour cette sélection", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig, pipelines_disponibles, pd.DataFrame()

    # --- LOGIQUE DE CALCUL DU STOCK ---
    # 1) Résumé fermeture au niveau ticket (historique complet)
    df_tickets = df_tickets.copy()
    df_tickets['Date'] = pd.to_datetime(df_tickets['Date'])
    creation_dates_all = df_tickets.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création (globale)'})
    latest_entries = df_tickets.loc[df_tickets.groupby('Ticket ID')['Date'].idxmax()][['Ticket ID', 'Temps de fermeture (HH:mm:ss)']]
    df_ticket_summary = creation_dates_all.merge(latest_entries, on='Ticket ID', how='left')
    df_ticket_summary['Temps de fermeture'] = pd.to_timedelta(df_ticket_summary['Temps de fermeture (HH:mm:ss)'], errors='coerce').fillna(pd.Timedelta(seconds=0))
    df_ticket_summary['Date de fermeture'] = df_ticket_summary['Date de création (globale)'] + df_ticket_summary['Temps de fermeture']

    # 2) Date d'entrée N2 = première date où le ticket a été vu 'Passé par le support N2' == 'Oui'
    df_n2['Date'] = pd.to_datetime(df_n2['Date'])
    entree_n2 = df_n2.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date entrée N2'})

    # 3) Restreindre aux tickets N2 et rattacher les infos de fermeture
    df_n2_summary = entree_n2.merge(df_ticket_summary[['Ticket ID', 'Temps de fermeture', 'Date de fermeture']], on='Ticket ID', how='left')

    # Utiliser toutes les semaines présentes dans le dataset pour éviter les courbes tronquées
    all_weeks = sorted(df_tickets['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    weekly_data = []

    for week in all_weeks:
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)

        created_so_far = df_n2_summary[df_n2_summary['Date entrée N2'] <= week_end_date]
        closed_so_far = created_so_far[
            (created_so_far['Temps de fermeture'] > pd.Timedelta(seconds=0)) &
            (created_so_far['Date de fermeture'] <= week_end_date)
        ]
        
        open_stock = len(created_so_far) - len(closed_so_far)
        
        weekly_data.append({
            'Semaine': week,
            'Tickets créés (cumul)': len(created_so_far),
            'Tickets fermés (cumul)': len(closed_so_far),
            'Stock de tickets ouverts': open_stock
        })

    df_stock = pd.DataFrame(weekly_data)
    
    if df_stock.empty:
        fig = go.Figure()
        fig.add_annotation(text="Impossible de calculer le stock de tickets N2", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig, pipelines_disponibles, pd.DataFrame()
        
    # --- Création du graphique avec axe secondaire ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Ajouter les courbes cumulatives sur l'axe Y principal
    fig.add_trace(go.Scatter(x=df_stock['Semaine'], y=df_stock['Tickets créés (cumul)'], mode='lines', name='Tickets N2 créés (cumulatif)', line=dict(color='blue')), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_stock['Semaine'], y=df_stock['Tickets fermés (cumul)'], mode='lines', name='Tickets N2 fermés (cumulatif)', line=dict(color='green')), secondary_y=False)

    # Ajouter la courbe de stock sur l'axe Y secondaire
    fig.add_trace(go.Scatter(x=df_stock['Semaine'], y=df_stock['Stock de tickets ouverts'], mode='lines', name='Stock de tickets N2 ouverts', line=dict(color='red', dash='dash')), secondary_y=True)

    title = "Stock de tickets N2 ouverts par semaine"
    if pipeline_filter:
        title += f" - Pipeline(s): {', '.join(pipeline_filter)}"

    fig.update_layout(
        title=title,
        xaxis_title="Semaine",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Définir les titres des axes Y
    fig.update_yaxes(title_text="Total tickets (cumulatif)", secondary_y=False)
    fig.update_yaxes(title_text="Stock de tickets ouverts", secondary_y=True)
    
    last_week_end = pd.to_datetime(f'{all_weeks[-1][1:5]}-W{all_weeks[-1][6:]}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)
    tickets_ouverts_fin_periode = df_n2_summary[
        (df_n2_summary['Date entrée N2'] <= last_week_end) & 
        ((df_n2_summary['Temps de fermeture'] == pd.Timedelta(seconds=0)) | (df_n2_summary['Date de fermeture'] > last_week_end))
    ]

    # Debug rapide: afficher les 6 dernières semaines calculées
    try:
        print("DEBUG N2 cumulatif - Dernières semaines:")
        print(df_stock.tail(6))
    except Exception:
        pass

    return fig, pipelines_disponibles, tickets_ouverts_fin_periode

def graph_tickets_ouverts_pierre_goupillon(df_tickets):
    """
    Crée un graphique du nombre de tickets OUVERTS de Pierre Goupillon par semaine (basé sur Date de création + Temps de fermeture).
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    
    # Gestion des variantes de nom pour Pierre Goupillon
    correspondance_pierre = ['Pierre Goupillon', 'Pierre GOUPILLON']
    
    # Filtrer avec toutes les variantes possibles
    df_pierre = df_tickets[df_tickets['Propriétaire du ticket'].isin(correspondance_pierre)].copy()
    
    if df_pierre.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket pour Pierre Goupillon", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets ouverts de Pierre Goupillon par semaine", template="plotly_dark")
        return fig

    # --- NOUVELLE LOGIQUE DE CALCUL DU STOCK ---
    # 1. Préparation des dates
    df_pierre['Date'] = pd.to_datetime(df_pierre['Date'])
    
    # Obtenir la date de création (la plus ancienne date pour chaque ticket)
    creation_dates = df_pierre.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création'})
    
    # Obtenir le temps de fermeture depuis la dernière entrée de chaque ticket
    latest_entries = df_pierre.loc[df_pierre.groupby('Ticket ID')['Date'].idxmax()][['Ticket ID', 'Temps de fermeture (HH:mm:ss)']]
    
    # Combiner pour avoir une vue unique et propre par ticket
    df_pierre_summary = pd.merge(creation_dates, latest_entries, on='Ticket ID', how='left')

    # Calculer la date de fermeture réelle
    df_pierre_summary['Temps de fermeture'] = pd.to_timedelta(df_pierre_summary['Temps de fermeture (HH:mm:ss)'], errors='coerce')
    df_pierre_summary['Date de fermeture'] = df_pierre_summary['Date de création'] + df_pierre_summary['Temps de fermeture']

    # Obtenir toutes les semaines uniques et les trier
    all_weeks = sorted(df_pierre['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    weekly_open_counts = []

    for week in all_weeks:
        # Déterminer la date de fin de la semaine
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)
        
        # 1. Sélectionner les tickets créés avant la fin de cette semaine
        tickets_created_so_far = df_pierre_summary[df_pierre_summary['Date de création'] <= week_end_date]
        
        # 2. Compter ceux qui sont encore ouverts à cette date
        # Un ticket est ouvert si sa date de fermeture est future OU si elle n'existe pas (NaT)
        open_count = tickets_created_so_far[
            (tickets_created_so_far['Date de fermeture'] > week_end_date) | 
            (pd.isna(tickets_created_so_far['Date de fermeture']))
        ].shape[0]
        
        weekly_open_counts.append({'Semaine': week, 'Tickets ouverts': open_count})

    df_open_counts = pd.DataFrame(weekly_open_counts)
    
    if df_open_counts.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket ouvert pour Pierre Goupillon", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets ouverts de Pierre Goupillon par semaine", template="plotly_dark")
        return fig

    # Tri chronologique des semaines
    ordre_semaines = sorted(df_open_counts['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_open_counts['Semaine'] = pd.Categorical(df_open_counts['Semaine'], categories=ordre_semaines, ordered=True)
    df_open_counts = df_open_counts.sort_values('Semaine')
    
    fig = px.bar(
        df_open_counts,
        x='Semaine',
        y='Tickets ouverts',
        title="Stock de tickets ouverts de Pierre Goupillon par semaine",
        labels={'Tickets ouverts': 'Nombre de tickets ouverts'}
    )

    fig.update_xaxes(
        categoryorder='array',
        categoryarray=ordre_semaines,
        tickangle=-45
    )

    fig.update_layout(
        template="plotly_dark"
    )

    return fig

# Agents support pour le graphique cumulatif N1 (tickets attribués à ces agents uniquement)
# Variantes incluses pour matcher les noms HubSpot (normalisation préférable dans hubspot_processing)
AGENTS_SUPPORT_CUMUL_N1 = [
    'Christophe Brichet',
    'Vincent Le Quennec', 'Vincent LE QUENNEC',
    'Pierre Goupillon', 'Pierre GOUPILLON',
    'Archimède Kessi', 'Archimede KESSI', 'Archimède KESSI',
    'Mourad Humblot', 'Mourad HUMBLOT',
    'Emilie Gest', 'Emilie GEST',
    'Cédeline Duval', 'Cédeline DUVAL', 'Cedeline Duval', 'Cedeline DUVAL', 'CÉDELINE DUVAL', 'CÃ©deline DUVAL', 'cedeline duval', 'C√©deline DUVAL',
    'Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL',
    'Mélinda Marmin', 'Melinda Marmin', 'Mélinda MARMIN', 'Melinda MARMIN',
    'Sandrine Siguret', 'Sandrine Sauvage', 'Sandrine SIGURET', 'Sandrine SAUVAGE',
]

# Liste canonique pour l'affichage du filtre (tous les agents support, même sans tickets)
AGENTS_SUPPORT_CUMUL_N1_CANONIQUES = [
    'Archimede KESSI', 'Christophe Brichet', 'Cédeline DUVAL', 'Céline Crendal',
    'Emilie GEST', 'Melinda Marmin', 'Mourad HUMBLOT', 'Pierre GOUPILLON',
    'Sandrine Sauvage', 'Vincent Le Quennec',
]


def graph_tickets_n1_cumulatif(df_tickets, agent_filter=None, weeks_to_display=None):
    """
    Crée un graphique cumulatif des tickets N1 (pipelines SSI, SSIA, SPSA) avec le stock de tickets ouverts par semaine.
    Filtre par défaut sur les agents support (AGENTS_SUPPORT_CUMUL_N1).

    Important : le calcul du stock utilise TOUS les tickets passés (pas de filtre période sur les données).
    Le paramètre weeks_to_display permet de n'afficher que les semaines de la période sélectionnée,
    tout en comptant correctement les tickets ouverts avant cette période.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import pandas as pd

    # --- FILTRAGE INITIAL (sur TOUS les tickets, pas de filtre période) ---
    # 1. Filtrer les tickets des pipelines N1 (SSI, SSIA, SPSA, Chatbot Yelda) - TOUTES sources incluses
    pipelines_n1 = ['SSI', 'SSIA', 'SPSA', 'Chatbot Yelda']
    df_n1 = df_tickets[df_tickets['Pipeline'].isin(pipelines_n1)].copy()

    # 2. Filtrer sur les agents support uniquement (Propriétaire du ticket)
    df_n1 = df_n1[df_n1['Propriétaire du ticket'].isin(AGENTS_SUPPORT_CUMUL_N1)].copy()

    # Liste pour le filtre : agents canoniques (Cédeline DUVAL, etc.) pour afficher tous les agents support
    agents_disponibles = sorted(AGENTS_SUPPORT_CUMUL_N1_CANONIQUES)
    
    # Appliquer le filtre par agent si spécifié
    if agent_filter:
        if isinstance(agent_filter, str): agent_filter = [agent_filter]
        df_n1 = df_n1[df_n1['Propriétaire du ticket'].isin(agent_filter)]

    if df_n1.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket N1 trouvé pour cette sélection", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig, agents_disponibles, pd.DataFrame()

    # --- CALCUL DU STOCK (toujours sur TOUS les tickets N1, sans filtre période) ---
    # 1. Préparation des dates
    df_n1['Date de création'] = pd.to_datetime(df_n1['Date'])
    
    # Critère de fermeture : Statut = Résolu, Clos ou Fermé (plus fiable que Temps de fermeture)
    statuts_fermes = ['Résolu', 'Clos', 'Fermé']
    df_n1['_est_ferme'] = df_n1['Statut du ticket'].fillna('').str.strip().str.lower().isin([s.lower() for s in statuts_fermes])
    
    # Date de fermeture : colonne HubSpot si dispo, sinon Date de dernière modification en secours
    if 'Date de fermeture' in df_n1.columns:
        df_n1['Date de fermeture'] = pd.to_datetime(df_n1['Date de fermeture'], errors='coerce')
    else:
        df_n1['Date de fermeture'] = pd.NaT
    if 'Date de la dernière modification' in df_n1.columns:
        df_n1['_date_modif'] = pd.to_datetime(df_n1['Date de la dernière modification'], errors='coerce')
    else:
        df_n1['_date_modif'] = pd.NaT
    # Pour les tickets fermés sans Date de fermeture : utiliser la date de modification en secours
    df_n1['_date_fermeture_effective'] = df_n1['Date de fermeture'].fillna(df_n1['_date_modif'])

    # Exclure les NaN (float) et valeurs invalides avant tri
    semaines_valides = [w for w in df_n1['Semaine'].unique() if isinstance(w, str) and len(w) >= 8]
    all_weeks_full_n1 = sorted(semaines_valides, key=lambda x: (int(x[1:5]), int(x[6:])))
    weekly_data = []

    for week in all_weeks_full_n1:
        # Extraire l'année et le numéro de semaine pour calculer la date de fin de semaine
        year, week_num = int(week[1:5]), int(week[6:])
        # Le + '6' pour obtenir le dimanche (fin de semaine)
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)

        # Tickets créés jusqu'à la fin de cette semaine
        created_so_far = df_n1[df_n1['Date de création'] <= week_end_date]
        
        # Tickets fermés jusqu'à la fin de cette semaine
        # Critère : Statut = Résolu/Clos/Fermé ET date de fermeture <= fin de semaine
        closed_so_far = created_so_far[
            created_so_far['_est_ferme'] &
            (created_so_far['_date_fermeture_effective'].notna()) &
            (created_so_far['_date_fermeture_effective'] <= week_end_date)
        ]
        
        # Le stock est la différence
        open_stock = len(created_so_far) - len(closed_so_far)
        
        weekly_data.append({
            'Semaine': week,
            'Tickets créés (cumul)': len(created_so_far),
            'Tickets fermés (cumul)': len(closed_so_far),
            'Stock de tickets ouverts': open_stock
        })

    df_stock = pd.DataFrame(weekly_data)

    # Filtrer les semaines affichées si une période est sélectionnée (sans modifier le calcul du stock)
    if weeks_to_display is not None and len(weeks_to_display) > 0:
        weeks_sorted = sorted(weeks_to_display, key=lambda x: (int(x[1:5]), int(x[6:])))
        weeks_set = set(weeks_sorted)
        df_stock = df_stock[df_stock['Semaine'].isin(weeks_set)].copy()
        df_stock['Semaine'] = pd.Categorical(df_stock['Semaine'], categories=weeks_sorted, ordered=True)
        df_stock = df_stock.sort_values('Semaine')
        all_weeks_full_n1 = weeks_sorted
    
    if df_stock.empty:
        fig = go.Figure()
        fig.add_annotation(text="Impossible de calculer le stock de tickets", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig, agents_disponibles, pd.DataFrame()
        
    # --- Création du graphique avec axe secondaire ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Ajouter les courbes cumulatives sur l'axe Y principal
    fig.add_trace(go.Scatter(x=df_stock['Semaine'], y=df_stock['Tickets créés (cumul)'], mode='lines', name='Tickets créés (cumulatif)', line=dict(color='blue')), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_stock['Semaine'], y=df_stock['Tickets fermés (cumul)'], mode='lines', name='Tickets fermés (cumulatif)', line=dict(color='green')), secondary_y=False)
    
    # Ajouter la courbe de stock sur l'axe Y secondaire
    fig.add_trace(go.Scatter(x=df_stock['Semaine'], y=df_stock['Stock de tickets ouverts'], mode='lines', name='Stock de tickets ouverts', line=dict(color='red', dash='dash')), secondary_y=True)

    title = "Stock de tickets N1 ouverts par semaine"
    if agent_filter:
        title += f" - Agent(s): {', '.join(agent_filter)}"

    fig.update_layout(
        title=title,
        xaxis_title="Semaine",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Ordonner l'axe X selon l'ensemble complet des semaines
    fig.update_xaxes(
        categoryorder='array',
        categoryarray=all_weeks_full_n1,
    )

    # Définir les titres des axes Y
    fig.update_yaxes(title_text="Total tickets (cumulatif)", secondary_y=False)
    fig.update_yaxes(title_text="Stock de tickets ouverts", secondary_y=True)
    
    # La notion de "tickets en cours" à télécharger : créés avant fin de période et non fermés (Statut) ou fermés après
    last_week_end = pd.to_datetime(f'{all_weeks_full_n1[-1][1:5]}-W{all_weeks_full_n1[-1][6:]}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)
    tickets_ouverts_fin_periode = df_n1[
        (df_n1['Date de création'] <= last_week_end) & 
        (~df_n1['_est_ferme'] | df_n1['_date_fermeture_effective'].isna() | (df_n1['_date_fermeture_effective'] > last_week_end))
    ]

    return fig, agents_disponibles, tickets_ouverts_fin_periode

def compute_n1_stock_debug(df_tickets):
    """Retourne un DataFrame hebdo avec cumul créés/fermés et stock ouverts pour N1.

    Colonnes: Semaine, Tickets créés (cumul), Tickets fermés (cumul), Stock de tickets ouverts
    """
    import pandas as pd

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()

    # Filtrage N1
    sources_a_inclure = ['Chat', 'E-mail', 'Formulaire']
    df = df[df['Source'].isin(sources_a_inclure)]
    df = df[df['Pipeline'].isin(['SSI', 'SSIA', 'SPSA'])].copy()

    if df.empty:
        return pd.DataFrame(columns=['Semaine', 'Tickets créés (cumul)', 'Tickets fermés (cumul)', 'Stock de tickets ouverts'])

    # Préparation dates
    df['Date de création'] = pd.to_datetime(df['Date'])
    df['Temps de fermeture'] = pd.to_timedelta(df['Temps de fermeture (HH:mm:ss)'], errors='coerce').fillna(pd.Timedelta(seconds=0))
    df['Date de fermeture'] = df['Date de création'] + df['Temps de fermeture']

    # Liste complète des semaines présentes dans le dataset filtré
    all_weeks_full = sorted(df_tickets[df_tickets['Semaine'] != 'S2024-01']['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))

    weekly_data = []
    for week in all_weeks_full:
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)

        created_so_far = df[df['Date de création'] <= week_end_date]
        closed_so_far = created_so_far[(created_so_far['Temps de fermeture'] > pd.Timedelta(seconds=0)) & (created_so_far['Date de fermeture'] <= week_end_date)]

        weekly_data.append({
            'Semaine': week,
            'Tickets créés (cumul)': len(created_so_far),
            'Tickets fermés (cumul)': len(closed_so_far),
            'Stock de tickets ouverts': len(created_so_far) - len(closed_so_far)
        })

    return pd.DataFrame(weekly_data)

def compute_n2_stock_debug(df_tickets):
    """Retourne un DataFrame hebdo avec cumul créés/fermés et stock ouverts pour N2.

    Colonnes: Semaine, Tickets créés (cumul), Tickets fermés (cumul), Stock de tickets ouverts
    """
    import pandas as pd

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()

    # Filtre N2
    df = df[df['Passé par le support N2'] == 'Oui'].copy()
    if df.empty:
        return pd.DataFrame(columns=['Semaine', 'Tickets créés (cumul)', 'Tickets fermés (cumul)', 'Stock de tickets ouverts'])

    # Préparation dates
    df['Date de création'] = pd.to_datetime(df['Date'])
    df['Temps de fermeture'] = pd.to_timedelta(df['Temps de fermeture (HH:mm:ss)'], errors='coerce').fillna(pd.Timedelta(seconds=0))
    df['Date de fermeture'] = df['Date de création'] + df['Temps de fermeture']

    # Liste complète des semaines présentes dans le dataset global (pour avoir toutes les semaines)
    all_weeks_full = sorted(df_tickets[df_tickets['Semaine'] != 'S2024-01']['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))

    weekly_data = []
    for week in all_weeks_full:
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)

        created_so_far = df[df['Date de création'] <= week_end_date]
        closed_so_far = created_so_far[(created_so_far['Temps de fermeture'] > pd.Timedelta(seconds=0)) & (created_so_far['Date de fermeture'] <= week_end_date)]

        weekly_data.append({
            'Semaine': week,
            'Tickets créés (cumul)': len(created_so_far),
            'Tickets fermés (cumul)': len(closed_so_far),
            'Stock de tickets ouverts': len(created_so_far) - len(closed_so_far)
        })

    return pd.DataFrame(weekly_data)

def graph_tickets_n1_par_semaine(df_tickets, selected_agent=None):
    """
    Crée un graphique pour les agents N1 avec :
    - Barres : nouveaux tickets par semaine (cumulé par pipeline)
    - Courbe : tous les tickets ouverts (axe Y principal)
    - Courbe : tickets ouverts par agent (axe Y secondaire)
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    selected_agent : str, optional
        Nom de l'agent pour afficher ses tickets ouverts spécifiquement
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    from plotly.subplots import make_subplots

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()

    # Filtrer les pipelines spécifiques
    pipelines_filtres = ['SSIA', 'SSI', 'SPSA', 'A10', 'Affid NXT']
    df_tickets = df_tickets[df_tickets['Pipeline'].isin(pipelines_filtres)].copy()

    # Filtrer les tickets N1 (tous les tickets sauf ceux passés par le N2)
    df_n1 = df_tickets[df_tickets['Passé par le support N2'] != 'Oui'].copy()
    
    if df_n1.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket N1 trouvé", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets N1 par semaine", template="plotly_dark")
        return fig

    # --- Données pour les barres (nouveaux tickets par semaine/pipeline) ---
    df_grouped = df_n1.groupby(['Semaine', 'Pipeline'])['Ticket ID'].nunique().reset_index()

    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_grouped['Semaine'] = pd.Categorical(df_grouped['Semaine'], categories=ordre_semaines, ordered=True)
    df_grouped = df_grouped.sort_values('Semaine')

    # --- Création du graphique avec axe secondaire ---
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # --- Ajout des barres empilées (axe Y principal) ---
    for pipeline in pipelines_filtres:
        pipeline_data = df_grouped[df_grouped['Pipeline'] == pipeline]
        if not pipeline_data.empty:
            fig.add_trace(
                go.Bar(
                    x=pipeline_data['Semaine'],
                    y=pipeline_data['Ticket ID'],
                    name=f'Nouveaux tickets - {pipeline}',
                    yaxis='y'
                ),
                secondary_y=False
            )

    # --- Données pour la courbe des tickets ouverts (tous agents N1) ---
    weekly_open_counts = []
    
    # Préparer les données pour le calcul du stock
    df_n1['Date'] = pd.to_datetime(df_n1['Date'])
    
    # Obtenir la date de création (la plus ancienne date pour chaque ticket)
    creation_dates = df_n1.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création'})
    
    # Obtenir le temps de fermeture depuis la dernière entrée de chaque ticket
    latest_entries = df_n1.loc[df_n1.groupby('Ticket ID')['Date'].idxmax()][['Ticket ID', 'Temps de fermeture (HH:mm:ss)']]
    
    # Combiner pour avoir une vue unique et propre par ticket
    df_n1_summary = pd.merge(creation_dates, latest_entries, on='Ticket ID', how='left')

    # Calculer la date de fermeture réelle
    df_n1_summary['Temps de fermeture'] = pd.to_timedelta(df_n1_summary['Temps de fermeture (HH:mm:ss)'], errors='coerce')
    df_n1_summary['Date de fermeture'] = df_n1_summary['Date de création'] + df_n1_summary['Temps de fermeture']

    # --- Données pour la courbe des tickets ouverts par agent spécifique ---
    weekly_agent_open_counts = []
    
    # Liste complète des agents autorisés avec toutes leurs variantes
    agents_autorises = [
        'Pierre Goupillon', 'Pierre GOUPILLON',
        'Archimède KESSI', 'Archimede KESSI',
        'FREDERIC SAUVAN', 'Frederic SAUVAN',
        'HUMBLOT NASSUF', 'Mourad HUMBLOT',
        'Christophe Brichet',
        'Vincent LE QUENNEC', 'Vincent Le Quennec',
        'Nathalie Pottiez',
        'Emilie GEST', 'Emilie Gest',
        'Sandrine Sauvage',
        'Melinda Marmin',
        'Morgane Vandenbussche', 'Morgane VANDENBUSSCHE',
        'Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'
    ]
    agents_n1_filtres = [agent for agent in df_n1['Propriétaire du ticket'].unique().tolist() if agent in agents_autorises]
    
    if selected_agent and selected_agent in agents_autorises:
        # Filtrer les tickets de l'agent sélectionné
        df_agent = df_tickets[df_tickets['Propriétaire du ticket'] == selected_agent].copy()
        
        if not df_agent.empty:
            # Préparer les données pour l'agent spécifique
            df_agent['Date'] = pd.to_datetime(df_agent['Date'])
            
            # Obtenir la date de création pour l'agent
            creation_dates_agent = df_agent.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création'})
            
            # Obtenir le temps de fermeture pour l'agent
            latest_entries_agent = df_agent.loc[df_agent.groupby('Ticket ID')['Date'].idxmax()][['Ticket ID', 'Temps de fermeture (HH:mm:ss)']]
            
            # Combiner pour l'agent
            df_agent_summary = pd.merge(creation_dates_agent, latest_entries_agent, on='Ticket ID', how='left')
            df_agent_summary['Temps de fermeture'] = pd.to_timedelta(df_agent_summary['Temps de fermeture (HH:mm:ss)'], errors='coerce')
            df_agent_summary['Date de fermeture'] = df_agent_summary['Date de création'] + df_agent_summary['Temps de fermeture']

    # Calculer les tickets ouverts pour chaque semaine
    for week in ordre_semaines:
        # Déterminer la date de fin de la semaine
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)
        
        # 1. Sélectionner les tickets créés avant la fin de cette semaine (tous agents N1)
        tickets_created_so_far = df_n1_summary[df_n1_summary['Date de création'] <= week_end_date]
        
        # 2. Compter ceux qui sont encore ouverts à cette date
        open_count = tickets_created_so_far[
            (tickets_created_so_far['Date de fermeture'] > week_end_date) | 
            (pd.isna(tickets_created_so_far['Date de fermeture']))
        ].shape[0]
        
        weekly_open_counts.append({'Semaine': week, 'Tickets ouverts': open_count})
        
        # 3. Calculer les tickets ouverts de l'agent sélectionné pour cette semaine
        if selected_agent and selected_agent in agents_autorises and not df_agent.empty:
            tickets_agent_created_so_far = df_agent_summary[df_agent_summary['Date de création'] <= week_end_date]
            
            agent_open_count = tickets_agent_created_so_far[
                (tickets_agent_created_so_far['Date de fermeture'] > week_end_date) | 
                (pd.isna(tickets_agent_created_so_far['Date de fermeture']))
            ].shape[0]
        else:
            agent_open_count = 0
            
        weekly_agent_open_counts.append({'Semaine': week, f'Tickets ouverts {selected_agent}': agent_open_count})

    df_open_counts = pd.DataFrame(weekly_open_counts)
    df_agent_open_counts = pd.DataFrame(weekly_agent_open_counts)
    
    # --- Ajout de la courbe des tickets ouverts (tous agents N1) sur l'axe Y principal ---
    fig.add_trace(go.Scatter(
        x=df_open_counts['Semaine'],
        y=df_open_counts['Tickets ouverts'],
        mode='lines+markers',
        name='Stock de Tickets N1 Ouverts (tous agents)',
        line=dict(color='yellow', width=3)
    ), secondary_y=False)
    
    # --- Ajout de la courbe des tickets de l'agent sélectionné sur l'axe Y secondaire ---
    if selected_agent and selected_agent in agents_autorises and not df_agent.empty:
        fig.add_trace(go.Scatter(
            x=df_agent_open_counts['Semaine'],
            y=df_agent_open_counts[f'Tickets ouverts {selected_agent}'],
            mode='lines+markers',
            name=f'Stock de Tickets Ouverts - {selected_agent}',
            line=dict(color='red', width=3, dash='dash')
        ), secondary_y=True)

    # --- Mise en page finale ---
    fig.update_xaxes(
        categoryorder='array',
        categoryarray=ordre_semaines,
        tickangle=-45
    )
    
    # Configuration des axes
    fig.update_yaxes(title_text="Nombre de tickets (barres et stock global)", secondary_y=False)
    fig.update_yaxes(title_text=f"Stock de tickets - {selected_agent if selected_agent else 'Agent'}", secondary_y=True)
    
    fig.update_layout(
        title="Tickets N1 - Nouveaux tickets par semaine (barres) et tickets ouverts (courbes)",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode='stack'
    )

    return fig


def graph_tickets_n1_par_semaine_stellair(df_tickets, agent_filter=None, weeks_to_display=None):
    """
    Graphique N1 par semaine pour la page Support Stellair.
    Mêmes filtres et règles que graph_tickets_n1_cumulatif :
    - Pipelines : SSI, SSIA, SPSA, Chatbot Yelda
    - Agents : AGENTS_SUPPORT_CUMUL_N1
    - Fermeture : Statut Résolu/Clos/Fermé
    
    Visualisation : barres (nouveaux tickets par semaine/pipeline) + courbe stock ouverts.
    Returns:
        fig, agents_disponibles, tickets_n1_en_cours
    """
    import plotly.graph_objects as go
    import pandas as pd
    from plotly.subplots import make_subplots

    pipelines_filtres = ['SSI', 'SSIA', 'SPSA', 'Chatbot Yelda']
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    df_n1 = df_tickets[df_tickets['Pipeline'].isin(pipelines_filtres)].copy()
    df_n1 = df_n1[df_n1['Propriétaire du ticket'].isin(AGENTS_SUPPORT_CUMUL_N1)].copy()

    agents_disponibles = sorted(AGENTS_SUPPORT_CUMUL_N1_CANONIQUES)
    if agent_filter:
        if isinstance(agent_filter, str):
            agent_filter = [agent_filter]
        df_n1 = df_n1[df_n1['Propriétaire du ticket'].isin(agent_filter)]

    if df_n1.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket N1 trouvé pour cette sélection", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets N1 par semaine", template="plotly_dark")
        return fig, agents_disponibles, pd.DataFrame()

    # --- Barres : nouveaux tickets par semaine/pipeline ---
    df_grouped = df_n1.groupby(['Semaine', 'Pipeline'])['Ticket ID'].nunique().reset_index()
    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    if weeks_to_display and len(weeks_to_display) > 0:
        weeks_sorted = sorted(weeks_to_display, key=lambda x: (int(x[1:5]), int(x[6:])))
        df_grouped = df_grouped[df_grouped['Semaine'].isin(weeks_sorted)]
        ordre_semaines = weeks_sorted
    df_grouped['Semaine'] = pd.Categorical(df_grouped['Semaine'], categories=ordre_semaines, ordered=True)
    df_grouped = df_grouped.sort_values('Semaine')

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for pipeline in pipelines_filtres:
        pipeline_data = df_grouped[df_grouped['Pipeline'] == pipeline]
        if not pipeline_data.empty:
            fig.add_trace(
                go.Bar(
                    x=pipeline_data['Semaine'],
                    y=pipeline_data['Ticket ID'],
                    name=f'Nouveaux tickets - {pipeline}',
                    yaxis='y'
                ),
                secondary_y=False
            )

    # --- Stock de tickets ouverts : critère Statut (Résolu/Clos/Fermé) comme le cumulatif ---
    df_n1['Date de création'] = pd.to_datetime(df_n1['Date'])
    statuts_fermes = ['Résolu', 'Clos', 'Fermé']
    df_n1['_est_ferme'] = df_n1['Statut du ticket'].fillna('').str.strip().str.lower().isin([s.lower() for s in statuts_fermes])
    if 'Date de fermeture' in df_n1.columns:
        df_n1['Date de fermeture'] = pd.to_datetime(df_n1['Date de fermeture'], errors='coerce')
    else:
        df_n1['Date de fermeture'] = pd.NaT
    if 'Date de la dernière modification' in df_n1.columns:
        df_n1['_date_modif'] = pd.to_datetime(df_n1['Date de la dernière modification'], errors='coerce')
    else:
        df_n1['_date_modif'] = pd.NaT
    df_n1['_date_fermeture_effective'] = df_n1['Date de fermeture'].fillna(df_n1['_date_modif'])

    # Un ticket par ID : utiliser la dernière entrée pour le statut/fermeture
    latest_per_ticket = df_n1.loc[df_n1.groupby('Ticket ID')['Date'].idxmax()]
    creation_dates = df_n1.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création'})
    creation_dates['Date de création'] = pd.to_datetime(creation_dates['Date de création'])
    df_summary = creation_dates.merge(
        latest_per_ticket[['Ticket ID', '_est_ferme', '_date_fermeture_effective']],
        on='Ticket ID', how='left'
    )

    weekly_open_counts = []
    for week in ordre_semaines:
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.Timestamp(pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6))
        created_so_far = df_summary[df_summary['Date de création'] <= week_end_date]
        still_open = created_so_far[
            (~created_so_far['_est_ferme']) |
            (created_so_far['_date_fermeture_effective'].isna()) |
            (created_so_far['_date_fermeture_effective'] > week_end_date)
        ]
        weekly_open_counts.append({'Semaine': week, 'Tickets ouverts': len(still_open)})
    df_open_counts = pd.DataFrame(weekly_open_counts)

    fig.add_trace(go.Scatter(
        x=df_open_counts['Semaine'],
        y=df_open_counts['Tickets ouverts'],
        mode='lines+markers',
        name='Stock de Tickets N1 Ouverts',
        line=dict(color='yellow', width=3)
    ), secondary_y=False)

    fig.update_xaxes(categoryorder='array', categoryarray=list(ordre_semaines), tickangle=-45)
    fig.update_yaxes(title_text="Nombre de tickets (barres et stock)", secondary_y=False)
    fig.update_yaxes(title_text="Stock de tickets ouverts", secondary_y=True)
    title = "Tickets N1 par semaine (SSI/SSIA/SPSA/Chatbot Yelda - agents support)"
    if agent_filter:
        title += f" - {', '.join(agent_filter)}"
    fig.update_layout(
        title=title,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode='stack'
    )

    # Tickets N1 en cours (fin de période)
    if not ordre_semaines:
        return fig, agents_disponibles, pd.DataFrame()
    last_week = ordre_semaines[-1]
    year, week_num = int(last_week[1:5]), int(last_week[6:])
    last_week_end = pd.Timestamp(pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6))
    open_at_end = df_summary[
        (df_summary['Date de création'] <= last_week_end) &
        (
            (~df_summary['_est_ferme']) |
            (df_summary['_date_fermeture_effective'].isna()) |
            (df_summary['_date_fermeture_effective'] > last_week_end)
        )
    ]['Ticket ID'].tolist()
    tickets_n1_en_cours = df_n1[df_n1['Ticket ID'].isin(open_at_end)].drop_duplicates(subset=['Ticket ID'], keep='last')

    return fig, agents_disponibles, tickets_n1_en_cours


# --- Graphiques Yelda (chatbot Stellair) ---
def graph_yelda_evaluation_intentions(intentions_satisfaisant, intentions_non_satisfaisant, intentions_sans_avis=0):
    """Graphique camembert : répartition utilisateur satisfait / non satisfait / sans avis (Intentions)."""
    if intentions_satisfaisant == 0 and intentions_non_satisfaisant == 0 and intentions_sans_avis == 0:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée Intentions (reponse_agent_satisfaisante/non_satisfaisante)", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark", title="Évaluation utilisateurs (Intentions)")
        return fig
    labels = ['Satisfaisant', 'Non satisfaisant', 'Sans avis']
    values = [intentions_satisfaisant, intentions_non_satisfaisant, intentions_sans_avis]
    colors = ['#2ecc71', '#e74c3c', '#95a5a6']  # vert, rouge, gris
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=colors, hole=0)])
    fig.update_layout(
        title="Évaluation utilisateurs (Intentions : reponse_agent_satisfaisante / non_satisfaisante / sans avis)",
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig


def graph_yelda_evaluation(evaluation_counts):
    """Graphique camembert : répartition Satisfait / Insatisfait / À revoir (conversations évaluées uniquement)."""
    if not evaluation_counts or sum(evaluation_counts.values()) == 0:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée d'évaluation", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark", title="Évaluations Yelda")
        return fig
    labels = list(evaluation_counts.keys())
    values = list(evaluation_counts.values())
    colors = ['#2ecc71', '#e74c3c', '#f39c12']  # vert, rouge, orange
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=colors, hole=0)])
    fig.update_layout(
        title="Évaluation des conversations Yelda (fse.stellair.fr) — conversations évaluées uniquement",
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig


def graph_yelda_interactions_tickets_semaine(df_yelda):
    """
    Graphique : interactions et tickets créés par semaine.
    df_yelda doit avoir colonnes Date, Parcours (avec 'creation_ticket_hubspot' pour les tickets).
    """
    if df_yelda is None or df_yelda.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark")
        return fig
    df = df_yelda.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Semaine'] = df['Date'].dt.isocalendar().year.astype(str) + '-S' + df['Date'].dt.isocalendar().week.astype(str).str.zfill(2)
    parcours_col = 'Parcours' if 'Parcours' in df.columns else df.columns[0]
    df['Ticket créé'] = df[parcours_col].fillna('').astype(str).str.contains('creation_ticket_hubspot', regex=False)
    weekly = df.groupby('Semaine').agg(
        interactions=('Semaine', 'count'),
        tickets_crees=('Ticket créé', 'sum')
    ).reset_index()
    weekly = weekly.sort_values('Semaine')
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=weekly['Semaine'], y=weekly['interactions'], name="Interactions", marker_color='#3498db'),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=weekly['Semaine'], y=weekly['tickets_crees'], name="Tickets créés", mode='lines+markers', line=dict(color='#e74c3c', width=3)),
        secondary_y=True
    )
    fig.update_layout(
        title="Yelda : Conversations évaluées et tickets créés par semaine",
        template="plotly_dark",
        xaxis=dict(tickangle=-45),
        barmode='group'
    )
    fig.update_yaxes(title_text="Nombre d'interactions", secondary_y=False)
    fig.update_yaxes(title_text="Tickets créés", secondary_y=True)
    return fig


def graph_yelda_score_llm(df_yelda):
    """Graphique : distribution du Score LLM."""
    if df_yelda is None or df_yelda.empty or 'Score LLM' not in df_yelda.columns:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée Score LLM", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark")
        return fig
    df = df_yelda[df_yelda['Score LLM'].notna()].copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun Score LLM disponible", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark")
        return fig
    fig = go.Figure(data=[go.Histogram(x=df['Score LLM'], nbinsx=6, marker_color='#9b59b6')])
    fig.update_layout(
        title="Distribution du Score LLM (Yelda)",
        xaxis_title="Score LLM",
        yaxis_title="Nombre de conversations",
        template="plotly_dark"
    )
    return fig


def graph_yelda_evolution_scores(df_yelda):
    """
    Graphique : évolution dans le temps (par semaine) de :
    - Score LLM moyen
    - Taux satisfaction (évaluation LLM - colonne Évaluation)
    - Taux satisfaction utilisateurs (colonne Intentions : reponse_agent_satisfaisante vs non_satisfaisante)
    """
    if df_yelda is None or df_yelda.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucune donnée", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_dark")
        return fig
    df = df_yelda.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Semaine'] = df['Date'].dt.isocalendar().year.astype(str) + '-S' + df['Date'].dt.isocalendar().week.astype(str).str.zfill(2)
    eval_col = 'Évaluation' if 'Évaluation' in df.columns else None
    intentions_col = 'Intentions' if 'Intentions' in df.columns else None
    score_col = 'Score LLM' if 'Score LLM' in df.columns else None
    weekly_list = []
    for sem, grp in df.groupby('Semaine'):
        row = {'Semaine': sem}
        if score_col:
            vals = grp['Score LLM'].dropna()
            row['score_llm_moyen'] = vals.mean() if len(vals) > 0 else np.nan
        if eval_col:
            s = grp[eval_col].fillna('').astype(str).str.lower()
            sat = ((s.str.contains('satisfait')) & (~s.str.contains('insatisfait'))).sum()
            tot = (s.str.contains('satisfait') | s.str.contains('insatisfait') | s.str.contains('revoir')).sum()
            row['taux_satisfaction_llm'] = 100 * sat / tot if tot > 0 else np.nan
        if intentions_col:
            intents = grp[intentions_col].fillna('').astype(str).str.lower()
            has_non = intents.str.contains('reponse_agent_non_satisfaisante', na=False)
            has_sat = intents.str.contains('reponse_agent_satisfaisante', na=False) & ~has_non
            satisfaisant = has_sat.sum()
            non_satisfaisant = has_non.sum()
            tot_intentions = satisfaisant + non_satisfaisant
            row['taux_satisfaction_utilisateurs'] = 100 * satisfaisant / tot_intentions if tot_intentions > 0 else np.nan
        weekly_list.append(row)
    weekly_data = pd.DataFrame(weekly_list).sort_values('Semaine')
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if score_col and 'score_llm_moyen' in weekly_data.columns and weekly_data['score_llm_moyen'].notna().any():
        fig.add_trace(
            go.Scatter(
                x=weekly_data['Semaine'],
                y=weekly_data['score_llm_moyen'],
                name="Score LLM moyen",
                mode='lines+markers',
                line=dict(color='#9b59b6', width=3)
            ),
            secondary_y=False
        )
    if eval_col and 'taux_satisfaction_llm' in weekly_data.columns and weekly_data['taux_satisfaction_llm'].notna().any():
        fig.add_trace(
            go.Scatter(
                x=weekly_data['Semaine'],
                y=weekly_data['taux_satisfaction_llm'],
                name="Taux satisfaction (éval. LLM)",
                mode='lines+markers',
                line=dict(color='#2ecc71', width=2, dash='dash')
            ),
            secondary_y=True
        )
    if intentions_col and 'taux_satisfaction_utilisateurs' in weekly_data.columns and weekly_data['taux_satisfaction_utilisateurs'].notna().any():
        fig.add_trace(
            go.Scatter(
                x=weekly_data['Semaine'],
                y=weekly_data['taux_satisfaction_utilisateurs'],
                name="Taux satisfaction utilisateurs (Intentions)",
                mode='lines+markers',
                line=dict(color='#3498db', width=2, dash='dot')
            ),
            secondary_y=True
        )
    if len(fig.data) == 0:
        fig.add_annotation(text="Aucune donnée pour l'évolution", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    fig.update_layout(
        title="Yelda : Évolution des scores et des évaluations dans le temps",
        template="plotly_dark",
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Score LLM moyen", range=[1, 5], secondary_y=False)
    fig.update_yaxes(title_text="Taux satisfaction (%)", secondary_y=True)
    return fig


def get_n1_agents_list(df_tickets):
    """
    Retourne la liste des agents N1 disponibles.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    
    Returns:
    --------
    list : Liste des noms d'agents N1
    """
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    
    # Filtrer les pipelines spécifiques
    pipelines_filtres = ['SSIA', 'SSI', 'SPSA', 'A10', 'Affid NXT']
    df_tickets = df_tickets[df_tickets['Pipeline'].isin(pipelines_filtres)].copy()
    
    # Filtrer les tickets N1 (tous les tickets sauf ceux passés par le N2)
    df_n1 = df_tickets[df_tickets['Passé par le support N2'] != 'Oui'].copy()
    
    if df_n1.empty:
        return []
    
    # Obtenir la liste unique des agents N1
    agents_n1 = sorted(df_n1['Propriétaire du ticket'].unique().tolist())
    
    # Filtrer pour ne garder que les agents autorisés (noms complets avec variantes)
    agents_autorises = [
        'Pierre Goupillon', 'Pierre GOUPILLON',
        'Archimède KESSI', 'Archimede KESSI',
        'FREDERIC SAUVAN', 'Frederic SAUVAN',
        'HUMBLOT NASSUF', 'Mourad HUMBLOT',
        'Christophe Brichet',
        'Vincent LE QUENNEC', 'Vincent Le Quennec',
        'Nathalie Pottiez',
        'Emilie GEST', 'Emilie Gest',
        'Sandrine Sauvage',
        'Melinda Marmin',
        'Morgane Vandenbussche', 'Morgane VANDENBUSSCHE',
        'Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL'
    ]
    agents_n1_filtres = [agent for agent in agents_n1 if agent in agents_autorises]
    
    return agents_n1_filtres

def metrics_nombre_ticket_categorie(df, partenaire=None):
    if partenaire:
        df = df[(df['Pipeline'] == 'SPSA')
                & (df['Formulaire SPSA'] == 'C2 - Assistance niveau 2')
                & (df['Associated Company'] == partenaire)
                & (~df['Source'].isin(['Migration JIRA']))
                & (~df['Semaine'].isin(['S2024-01']))]

    # Filtrer la catégorie "NC" et grouper par catégorie
    df = df[~df['Catégorie'].isin(['NC'])] \
        .groupby('Catégorie')['Nombre_ticket_client'].sum() \
        .reset_index() \
        .sort_values(by='Nombre_ticket_client', ascending=True) \
        .tail(10)

    # Création du graphique
    fig = px.bar(
        df,
        x="Nombre_ticket_client",
        y="Catégorie",
        labels={"Nombre_ticket_client": "Nombre de tickets", "Catégorie": "Catégorie"},
    )
    return fig

def sla(df, partenaire, canal="partenaire"):
    # Dataframe partenaire
    if partenaire:
        df_partenaire = df[(df['Pipeline'] == 'SPSA')
                          & (df['Formulaire SPSA'] == 'C2 - Assistance niveau 2')
                          & (df['Associated Company'] == partenaire)
                          & (~df['Source'].isin(['Migration JIRA']))
                          & (~df['Semaine'].isin(['S2024-01']))]
    else:
        df_partenaire = df[(df['Pipeline'] == 'SPSA')
                          & (df['Formulaire SPSA'] == 'C2 - Assistance niveau 2')
                          & (~df['Source'].isin(['Migration JIRA']))
                          & (~df['Semaine'].isin(['S2024-01']))]

    # Dataframe b2c
    df_b2c = df[(df['Pipeline'].isin(['SSIA', 'SSI']))
                & (~df['Source'].isin(['Migration JIRA']))
                & (~df['Semaine'].isin(['S2024-01']))]

    # Calcul du SLA pour les partenaires
    if not df_partenaire.empty:
        sla_inferieur_2 = (df_partenaire['working_hours'] <= 2).mean() * 100
        delai_moyen = df_partenaire['working_hours'].mean()
    else:
        sla_inferieur_2 = 0
        delai_moyen = 0

    # Création du graphique SLA
    fig = go.Figure()
    
    if not df_partenaire.empty:
        fig.add_trace(go.Histogram(
            x=df_partenaire['working_hours'],
            nbinsx=20,
            name='Partenaires',
            opacity=0.7
        ))
    
    if not df_b2c.empty:
        fig.add_trace(go.Histogram(
            x=df_b2c['working_hours'],
            nbinsx=20,
            name='B2C',
            opacity=0.7
        ))

    fig.update_layout(
        title="Distribution des temps de réponse",
        xaxis_title="Temps de réponse (heures)",
        yaxis_title="Nombre de tickets",
        barmode='overlay'
    )

    return fig, sla_inferieur_2, delai_moyen, df_partenaire, df_b2c

def calculate_ticket_response_time(df_tickets, agents=None):
    """
    Calcule les temps de réponse aux tickets avec filtrage des valeurs aberrantes.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    agents : list or None
        Liste des agents à filtrer. Si None, tous les agents sont inclus.
    
    Returns:
    --------
    tuple : (moyenne_temps_reponse, graphique_evolution)
    """
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    
    # Utiliser EXACTEMENT les mêmes filtres que evo_appels_ticket
    df_filtered = df_tickets[
        (df_tickets['Source'].isin(['Chat', 'E-mail', 'Formulaire'])) &
        (df_tickets['Pipeline'].isin(['SSI', 'SSIA', 'SPSA']))
    ]

    
    # Filtrer par agents si spécifié
    if agents is not None:
        df_filtered = df_filtered[df_filtered['Propriétaire du ticket'].isin(agents)]
    
    # Filtrer les valeurs aberrantes (±5 écarts-types) pour le calcul de la moyenne uniquement
    working_hours = df_filtered['working_hours'].dropna()
    
    if len(working_hours) > 0:
        mean_hours = working_hours.mean()
        std_hours = working_hours.std()
        
        # Filtrage des valeurs aberrantes pour le calcul de la moyenne uniquement
        lower_bound = mean_hours - 5 * std_hours
        upper_bound = mean_hours + 5 * std_hours
        
        df_clean_for_mean = df_filtered[
            (df_filtered['working_hours'] >= lower_bound) &
            (df_filtered['working_hours'] <= upper_bound) &
            (df_filtered['working_hours'] > 0)  # Exclure les valeurs négatives ou nulles
        ]
        
        # Calcul de la moyenne des temps de réponse nettoyés
        moyenne_temps_reponse = df_clean_for_mean['working_hours'].mean()
        
        # Pour le graphique d'évolution, utiliser TOUS les tickets filtrés (même logique que evo_appels_ticket)
        # Exclure les tickets sans réponse (working_hours NaN ou <= 0) pour le calcul de la moyenne
        # mais les inclure dans le comptage pour avoir le nombre total de tickets
        df_evolution_mean = df_filtered[df_filtered['working_hours'].notna() & (df_filtered['working_hours'] > 0)].groupby('Semaine')['working_hours'].agg(['mean']).reset_index()
        df_evolution_count = df_filtered.groupby('Semaine')['working_hours'].agg(['count']).reset_index()
        df_evolution = pd.merge(df_evolution_mean, df_evolution_count, on='Semaine', how='outer').fillna(0)
        # Renommer les colonnes pour compatibilité avec le code suivant
        df_evolution = df_evolution.rename(columns={'mean': 'mean', 'count': 'count'})
        
        # Trier les semaines chronologiquement (même logique que evo_appels_ticket)
        ordre_semaines = sorted(df_evolution['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
        df_evolution['Semaine'] = pd.Categorical(df_evolution['Semaine'], categories=ordre_semaines, ordered=True)
        df_evolution = df_evolution.sort_values('Semaine')
        
        # Créer le graphique
        fig = make_subplots(
            rows=2, cols=1,
            #subplot_titles=('Évolution du temps de réponse moyen par semaine', 'Nombre de tickets par semaine'),
            vertical_spacing=0.15,
            row_heights=[0.7, 0.3]
        )
        
        # Graphique du temps de réponse moyen
        fig.add_trace(
            go.Scatter(
                x=df_evolution['Semaine'],
                y=df_evolution['mean'],
                mode='lines+markers',
                name='Temps de réponse moyen (h)',
                line=dict(color='blue', width=2),
                marker=dict(size=8)
            ),
            row=1, col=1
        )
        
        # Ligne de référence à 2h
        fig.add_hline(
            y=2, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Seuil 2h",
            row=1, col=1
        )
        
        # Graphique du nombre de tickets (même comptage que evo_appels_ticket)
        fig.add_trace(
            go.Bar(
                x=df_evolution['Semaine'],
                y=df_evolution['count'],
                name='Nombre de tickets',
                marker_color='lightblue'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title="Évolution des temps de réponse aux tickets",
            template="plotly_dark",
            height=700,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis2_title="Semaine",
            yaxis_title="Temps de réponse (heures)",
            yaxis2_title="Nombre de tickets"
        )
        
        # Rotation des étiquettes de l'axe x et ajustement des marges
        fig.update_xaxes(tickangle=-45)
        
        # Ajuster les marges pour éviter les chevauchements
        fig.update_layout(
            margin=dict(l=50, r=50, t=100, b=100)
        )
        
    else:
        moyenne_temps_reponse = 0
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible pour les temps de réponse",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig.update_layout(
            title="Évolution des temps de réponse aux tickets",
            template="plotly_dark"
        )
    
    return moyenne_temps_reponse, fig, df_filtered

def historique_scores_total(agents_n1, df_tickets, df_support, date_debut=None, nb_semaines=None, objectif_total=25, ratio_appels=0.7, ratio_tickets=0.3, objectif_taux_service=0.70):
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    historique = []

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    if isinstance(agents_n1, str):
        agents_n1 = [agents_n1]

    # Identifier toutes les semaines uniques et les trier correctement
    all_weeks = df_tickets['Semaine'].unique()
    
    # Gérer les cas où il n'y a pas de semaines
    if len(all_weeks) == 0:
        fig = px.line()
        fig.update_layout(title="Aucune donnée de semaine disponible", yaxis=dict(range=[0, 100]))
        return fig
        
    sorted_weeks = sorted(all_weeks, key=lambda x: (int(x[1:5]), int(x[6:])))
    
    # Utiliser toutes les semaines disponibles si nb_semaines n'est pas spécifié
    # Sinon, prendre les nb_semaines dernières semaines
    if nb_semaines is None:
        weeks_to_process = sorted_weeks
    else:
        weeks_to_process = sorted_weeks[-nb_semaines:]
    
    for week_label in weeks_to_process:
        # Filtrer les dataframes pour la semaine en cours
        df_tickets_semaine = df_tickets[df_tickets['Semaine'] == week_label]
        df_support_semaine = df_support[df_support['Semaine'] == week_label]

        if df_tickets_semaine.empty and df_support_semaine.empty:
            continue

        df_week = df_compute_ticket_appels_metrics(agents_n1, df_tickets_semaine, df_support_semaine)
        
        if df_week.empty:
            continue

        df_week['Semaine'] = week_label
        historique.append(df_week)

    if not historique:
        fig = px.line()
        fig.update_layout(
            title="Aucune donnée disponible pour l'historique des scores",
            yaxis=dict(range=[0, 100])
        )
        return fig

    df_historique = pd.concat(historique, ignore_index=True)
    
    # Assurer le bon ordre pour le graphique
    df_historique['Semaine'] = pd.Categorical(df_historique['Semaine'], categories=weeks_to_process, ordered=True)
    df_historique = df_historique.sort_values(by="Semaine")

    # Calculer le score de performance pour chaque ligne
    df_historique['score_performance'] = df_historique.apply(
        lambda row: calculate_performance_score(
            row,
            objectif_total=objectif_total,  # Utiliser les paramètres passés
            ratio_appels=ratio_appels,
            ratio_tickets=ratio_tickets,
            objectif_taux_service=objectif_taux_service
        ),
        axis=1
    )

    # Créer un sous-graphique pour chaque agent
    nb_agents = len(agents_n1)
    
    # Titre dynamique selon le nombre de semaines
    if nb_semaines is None:
        title_text = f"Évolution du score total par agent ({len(weeks_to_process)} semaines)"
    else:
        title_text = f"Évolution du score total par agent (dernières {nb_semaines} semaines)"

    # Créer les sous-graphiques
    fig = make_subplots(
        rows=nb_agents, 
        cols=1,
        subplot_titles=agents_n1,
        vertical_spacing=0.08,
        shared_xaxes=True,
        shared_yaxes=True
    )

    # Couleurs pour les agents
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

    # Ajouter une ligne pour chaque agent
    for i, agent in enumerate(agents_n1):
        agent_data = df_historique[df_historique['Agent'] == agent]
        
        if not agent_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=agent_data['Semaine'],
                    y=agent_data['score_performance'],
                    mode='lines+markers',
                    name=agent,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6),
                    showlegend=False  # Pas de légende car chaque agent a son propre graphique
                ),
                row=i+1, col=1
            )
        else:
            # Si l'agent n'a pas de données, ajouter un point invisible pour éviter les erreurs
            # mais ne pas afficher de ligne
            fig.add_trace(
                go.Scatter(
                    x=[weeks_to_process[0]],  # Première semaine
                    y=[None],  # Pas de valeur
                    mode='markers',
                    name=agent,
                    marker=dict(size=0),  # Point invisible
                    showlegend=False
                ),
                row=i+1, col=1
            )

    # Ajouter les lignes de seuil sur chaque sous-graphique
    for i in range(nb_agents):
        # Seuil vert (70%)
        fig.add_hline(
            y=70, 
            line_dash="dash", 
            line_color="green",
            line_width=2,
            row=i+1, col=1
        )
        

    # Configuration du graphique
    fig.update_layout(
        title=title_text,
        template="plotly_dark",
        height=200 * nb_agents,  # Hauteur adaptée au nombre d'agents
        showlegend=False,
        yaxis=dict(
            range=[0, 100],
            tickformat=".0f",
            title="Score de performance"
        )
    )

    # Configuration des axes Y partagés
    for i in range(nb_agents):
        fig.update_yaxes(
            range=[0, 100],
            tickformat=".0f",
            row=i+1, col=1
        )
        
        # Ajouter le nom de l'agent sur l'axe Y
        if i == nb_agents - 1:  # Seulement pour le dernier graphique
            fig.update_yaxes(title_text="Score", row=i+1, col=1)

    # Configuration des axes X partagés
    for i in range(nb_agents):
        fig.update_xaxes(
            tickangle=-45,
            row=i+1, col=1
        )
        
        # Ajouter le titre de l'axe X seulement pour le dernier graphique
        if i == nb_agents - 1:
            fig.update_xaxes(title_text="Semaine", row=i+1, col=1)

    return fig

def calculer_scores_equipe(df_support, df_tickets, agents_n1):
    """
    Calcule les scores de l'équipe en utilisant la même méthode que le dashboard.
    """
    rows = []
    
    for agent in agents_n1:
        # Calcul des KPIs pour chaque agent
        kpis = generate_kpis(df_support, df_tickets, agent, None, 'b2c')
        
        nb_appels = kpis.get('nb_appels_jour', 0)
        nb_tickets = kpis.get('moy_ticket_agent', 0)
        volume_total = nb_appels + nb_tickets
        
        # Créer une ligne avec le format attendu par calculate_performance_score
        row_data = {
            'Agent': agent,
            "Nombre d'appel traité": nb_appels,
            'Nombre de ticket traité': nb_tickets,
            '% appel entrant agent': kpis.get('ratio_entrants', 0) * 100
        }
        
        # Utiliser calculate_performance_score pour le calcul du score
        score_total = calculate_performance_score(
            row_data,
            objectif_total=30,
            ratio_appels=0.7,
            ratio_tickets=0.3,
            objectif_taux_service=0.70
        )
        
        # Calculer les pourcentages
        if volume_total > 0:
            pct_appels = (nb_appels / volume_total) * 100
            pct_tickets = (nb_tickets / volume_total) * 100
        else:
            pct_appels = 0
            pct_tickets = 0
        
        # Ajouter les résultats
        rows.append({
            'Agent': agent,
            'Score Total': score_total,
            'Volume Total': volume_total,
            '% Appels': pct_appels,
            '% Tickets': pct_tickets
        })
    
    return pd.DataFrame(rows)

def graph_activite_xmed(df_support):
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    # Filtrage des données pour l'activité entrante et la ligne XMED
    data_graph1 = df_support[(df_support['direction'] == 'inbound') & (df_support['line'] == 'xmed')]

    # Agrégation des données par semaine et date
    data_graph2 = (
        data_graph1.groupby(['Semaine'])
        .agg(
            Entrant=('Entrant', 'sum'),
            Entrant_connect=('Entrant_connect', 'sum'),
            Numero_unique=('Number', 'nunique'),
            Effectif=('Effectif', 'mean')
        )
        .reset_index()
    )

    # Agrégation finale par semaine
    data_graph3 = (
        data_graph2.groupby('Semaine')[['Entrant', 'Entrant_connect', 'Numero_unique', 'Effectif']]
        .mean()
        .reset_index()
    )

    # Tri chronologique des semaines
    ordre_semaines = sorted(data_graph3['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    data_graph3['Semaine'] = pd.Categorical(data_graph3['Semaine'], categories=ordre_semaines, ordered=True)
    data_graph3 = data_graph3.sort_values('Semaine')

    # Calcul du taux de service support
    data_graph3['Taux_de_service_support'] = (
        data_graph3['Entrant_connect'] / data_graph3['Entrant']
    )

    # Ajout d'une colonne 100%
    data_graph3['100%'] = 1

    # Création de la figure avec des sous-graphiques
    fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])

    # Ajouter les barres pour le Taux de service support
    fig.add_trace(
        go.Bar(
            x=data_graph3['Semaine'],
            y=data_graph3['Taux_de_service_support'],
            name='Taux',
            opacity=0.7,
            text=data_graph3['Taux_de_service_support'],
            texttemplate='%{text:.0%}'
        ),
        secondary_y=True,
    )

    # Ajouter les lignes empilées pour Numero_unique, Entrant_connect et Entrant
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Numero_unique'],
            name='Numero_unique',
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Entrant_connect'],
            name='Entrant_connect',
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Entrant'],
            name='Entrant',
            fill='tozeroy'
        ),
        secondary_y=False,
    )

    # Mise à jour des axes Y pour les pourcentages
    fig.update_yaxes(range=[0, 1], secondary_y=True)
    fig.update_yaxes(tickformat=".0%", secondary_y=True)

    # Ajout d'éventuels événements (bulle)
    events = {}
    x_events = []
    y_events = []
    text_events = []
    for week, event_text in events.items():
        if week in data_graph3['Semaine'].values:
            row = data_graph3[data_graph3['Semaine'] == week].iloc[0]
            y_val = row['Taux_de_service_support']
            marge = 0.05  
            y_val_event = min(y_val + marge, 1)
            x_events.append(week)
            y_events.append(y_val_event)
            text_events.append(event_text)
    fig.add_trace(
        go.Scatter(
            x=x_events,
            y=y_events,
            mode="markers+text",
            marker=dict(size=15, color="red"),
            text=text_events,
            textposition="top center",
            name="Événements"
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Graphique avec Taux en barres et Numero_unique/Entrant en aires empilées",
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Valeurs",
        title_text="Activité & Taux de service XMED - 20 semaines",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

def graph_activite_tmaj(df_support):
    """
    Graphique d'activité et taux de service pour TMAJ (Support Hardware).
    Modèle sur graph_activite_xmed, filtre sur line = 'supporthardware'.
    """
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_support = df_support[df_support['Semaine'] != 'S2024-01'].copy()

    # Filtrage des données pour l'activité entrante et la ligne TMAJ (Support Hardware)
    data_graph1 = df_support[(df_support['direction'] == 'inbound') & (df_support['line'] == 'supporthardware')]

    # Agrégation des données par semaine et date
    data_graph2 = (
        data_graph1.groupby(['Semaine'])
        .agg(
            Entrant=('Entrant', 'sum'),
            Entrant_connect=('Entrant_connect', 'sum'),
            Numero_unique=('Number', 'nunique'),
            Effectif=('Effectif', 'mean')
        )
        .reset_index()
    )

    # Agrégation finale par semaine
    data_graph3 = (
        data_graph2.groupby('Semaine')[['Entrant', 'Entrant_connect', 'Numero_unique', 'Effectif']]
        .mean()
        .reset_index()
    )

    # Tri chronologique des semaines
    ordre_semaines = sorted(data_graph3['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    data_graph3['Semaine'] = pd.Categorical(data_graph3['Semaine'], categories=ordre_semaines, ordered=True)
    data_graph3 = data_graph3.sort_values('Semaine')

    # Calcul du taux de service support
    data_graph3['Taux_de_service_support'] = (
        data_graph3['Entrant_connect'] / data_graph3['Entrant']
    )

    # Ajout d'une colonne 100%
    data_graph3['100%'] = 1

    # Création de la figure avec des sous-graphiques
    fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])

    # Ajouter les barres pour le Taux de service support
    fig.add_trace(
        go.Bar(
            x=data_graph3['Semaine'],
            y=data_graph3['Taux_de_service_support'],
            name='Taux',
            opacity=0.7,
            text=data_graph3['Taux_de_service_support'],
            texttemplate='%{text:.0%}'
        ),
        secondary_y=True,
    )

    # Ajouter les lignes empilées pour Numero_unique, Entrant_connect et Entrant
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Numero_unique'],
            name='Numero_unique',
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Entrant_connect'],
            name='Entrant_connect',
            fill='tozeroy'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=data_graph3['Semaine'],
            y=data_graph3['Entrant'],
            name='Entrant',
            fill='tozeroy'
        ),
        secondary_y=False,
    )

    # Mise à jour des axes Y pour les pourcentages
    fig.update_yaxes(range=[0, 1], secondary_y=True)
    fig.update_yaxes(tickformat=".0%", secondary_y=True)

    # Ajout d'éventuels événements (bulle)
    events = {}
    x_events = []
    y_events = []
    text_events = []
    for week, event_text in events.items():
        if week in data_graph3['Semaine'].values:
            row = data_graph3[data_graph3['Semaine'] == week].iloc[0]
            y_val = row['Taux_de_service_support']
            marge = 0.05  
            y_val_event = min(y_val + marge, 1)
            x_events.append(week)
            y_events.append(y_val_event)
            text_events.append(event_text)
    fig.add_trace(
        go.Scatter(
            x=x_events,
            y=y_events,
            mode="markers+text",
            marker=dict(size=15, color="red"),
            text=text_events,
            textposition="top center",
            name="Événements"
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Graphique avec Taux en barres et Numero_unique/Entrant en aires empilées",
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Valeurs",
        title_text="Activité & Taux de service TMAJ (Support Hardware) - 20 semaines",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig

def calcul_productivite_appels(df_support, agent):
    # Filtre les données où la durée de l'appel est supérieure à 45
    df_support_all = df_support
    df_support = df_support[df_support['InCallDuration'] > 45]

    # Groupement des appels par date et agent (UserName)
    df_grouped = df_support.groupby(['Date', 'UserName']).size().reset_index(name='TotalAppels')
    df_grouped = df_grouped[df_grouped['UserName'].isin(agent)].groupby(['Date']).agg({'TotalAppels':'mean'})

    # Groupement des appels par agent(UserName)
    df_grouped_total = df_support.groupby(['UserName']).size().reset_index(name='TotalAppels')
    df_grouped_total = df_grouped_total[df_grouped_total['UserName'].isin(agent)].agg({'TotalAppels':'mean'})

    # Filtrage des appels par agent et par date
    df_support = df_support[df_support['UserName'].isin(agent)].groupby(['Date']).agg({'InCallDuration':'sum'})

    # Fusionner les deux dataframes sur la colonne 'Date'
    df_support = pd.merge(df_support, df_grouped, on='Date', how='left')
    
    def convert_minutes_to_hhmmss(minutes):
        # Convertir les minutes en heures, minutes et secondes
        hours = int(minutes // 3600)
        minutes = int(minutes % 60)
        seconds = int((minutes % 1) * 60)
        # Formater en hh:mm:ss
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    df_support['InCallDuration_format'] = df_support['InCallDuration'].apply(convert_minutes_to_hhmmss)
    df_support['InCallDuration_format'] = pd.to_timedelta(df_support['InCallDuration_format'], errors='coerce')

    # Calcul de la moyenne des durées d'appel par jour
    com_jour = df_support['InCallDuration_format'].mean()

    def timedelta_to_hms(td):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    # Vérifier si la valeur de com_jour est valide
    if pd.notnull(com_jour):  # Vérifie si com_jour n'est pas NaT
        com_jour = timedelta_to_hms(com_jour)
    else:
        com_jour = None  # Ou une autre valeur par défaut, comme '' ou '00:00:00'

    # Calcul du temps moyen de communication par appel
    temps_moy_com = (df_support['InCallDuration'] / df_support['TotalAppels']).mean()

    # Nombre moyen d'appels par jour
    nb_appels_jour = df_support['TotalAppels'].mean()
    nb_appels = df_grouped_total['TotalAppels'].mean()

    return com_jour, temps_moy_com, nb_appels_jour, nb_appels

def kpi_agent(agent, df_support):
    if isinstance(agent, str):
        agent = [agent]
    # Filtrer une seule fois pour l'agent donné
    df_agent = df_support[df_support['UserName'].isin(agent)]
    
    # Calcul des KPI de productivité (4 valeurs seulement)
    com_jour, temps_moy_com, nb_appels_jour, nb_appel = calcul_productivite_appels(df_agent, agent)

    # Calcul des appels entrants et sortants
    nb_appels_jour_entrants = df_agent[df_agent['direction'] == 'inbound']['Entrant_connect'].sum()
    nb_appels_jour_sortants = df_agent[df_agent['direction'] == 'outbound']['Sortant_connect'].sum()

    # Éviter une division par zéro pour le ratio
    total_appels = nb_appels_jour_entrants + nb_appels_jour_sortants
    if total_appels > 0:
        ratio_entrants = nb_appels_jour_entrants / total_appels
        ratio_sortants = nb_appels_jour_sortants / total_appels
    else:
        ratio_entrants = 0
        ratio_sortants = 0

    return com_jour, temps_moy_com, nb_appels_jour, nb_appel, nb_appels_jour_entrants, nb_appels_jour_sortants, ratio_entrants, ratio_sortants

def filtrer_par_agent(agent):
    # Dictionnaire associant les noms courts aux noms complets
    correspondance_agents = {
        "Mourad": ["Mourad HUMBLOT", "HUMBLOT NASSUF"],
        "Archimède": ["Archimede KESSI", "Archimède KESSI"],
        "Frederic": ["Frederic SAUVAN", "FREDERIC SAUVAN"],
        "Pierre": ["Pierre GOUPILLON", "Pierre Goupillon"],
        "Christophe": ["Christophe Brichet"],
        "Emilie" : ["Emilie Gest", 'Emilie GEST'], 
        "Morgane" : ["Morgane VANDENBUSSCHE", 'Morgane Vandenbussche'],
        "Melinda" : ["Melinda Marmin"], 
        "Sandrine" : ["Sandrine Sauvage"], 
        "Céline": ['Céline Crendal', 'Celine Crendal', 'Céline CRENDAL', 'Celine CRENDAL']
    }
    
    # Si l'agent est dans la liste, on filtre, sinon on renvoie tout le DataFrame
    if agent in correspondance_agents:
        noms_complets = correspondance_agents[agent]
    else:
        noms_complets = [agent]
        
    return noms_complets

def graph_tickets_n2_par_semaine(df_tickets):
    """
    Crée un graphique à barres cumulées du nombre de tickets passés par le N2 par semaine, 
    avec une courbe du nombre de tickets encore ouverts.
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd

    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()

    df_n2 = df_tickets[df_tickets['Passé par le support N2'] == 'Oui'].copy()
    
    if df_n2.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket passé par le support N2", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets passés par le N2 par semaine et par pipeline", template="plotly_dark")
        return fig

    # --- Données pour les barres (total des tickets passés au N2 par semaine/pipeline) ---
    df_grouped = df_n2.groupby(['Semaine', 'Pipeline'])['Ticket ID'].nunique().reset_index()

    # Déterminer l'ensemble des semaines d'affichage à partir de toutes les semaines présentes dans df_tickets
    # (et non seulement celles où il y a du N2), pour que les courbes évoluent semaine après semaine
    all_weeks_full = sorted(df_tickets['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))

    # Ordonner et trier les barres selon l'ordre complet des semaines
    df_grouped['Semaine'] = pd.Categorical(df_grouped['Semaine'], categories=all_weeks_full, ordered=True)
    df_grouped = df_grouped.sort_values('Semaine')

    # --- Création du graphique à barres ---
    fig = px.bar(
        df_grouped,
        x='Semaine',
        y='Ticket ID',
        color='Pipeline',
        title="Tickets N2 passés par semaine (barres) et ouverts (ligne)",
        labels={'Ticket ID': 'Nombre de tickets'},
        barmode='stack',
        color_discrete_map={
            'SSIA': '#1f77b4',  # bleu
            'SSI': '#ff7f0e',   # orange
            'SPSA': '#2ca02c',  # vert
            'A10': '#d62728',   # rouge
            'Affid NXT': '#9467bd'  # violet
        }
    )

    # --- Données pour la courbe (stock de tickets ouverts via Temps de fermeture) ---
    weekly_open_counts = []
    # Construire un résumé au niveau ticket basé sur l'historique complet
    df_tickets = df_tickets.copy()
    df_tickets['Date'] = pd.to_datetime(df_tickets['Date'])
    creation_dates = df_tickets.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création'})
    latest_entries = df_tickets.loc[df_tickets.groupby('Ticket ID')['Date'].idxmax()][['Ticket ID', 'Temps de fermeture (HH:mm:ss)']]
    df_ticket_summary = pd.merge(creation_dates, latest_entries, on='Ticket ID', how='left')
    df_ticket_summary['Temps de fermeture'] = pd.to_timedelta(df_ticket_summary['Temps de fermeture (HH:mm:ss)'], errors='coerce')
    df_ticket_summary['Date de fermeture'] = df_ticket_summary['Date de création'] + df_ticket_summary['Temps de fermeture']
    # Restreindre aux tickets qui sont passés par le N2
    ticket_ids_n2 = df_n2['Ticket ID'].unique()
    df_n2_summary = df_ticket_summary[df_ticket_summary['Ticket ID'].isin(ticket_ids_n2)].copy()

    # --- Données pour la courbe des tickets N2 ouverts de Pierre Goupillon ---
    weekly_pierre_open_counts = []
    
    # Gestion des variantes de nom pour Pierre Goupillon
    correspondance_pierre = ['Pierre Goupillon', 'Pierre GOUPILLON']
    
    # Obtenir TOUS les tickets de Pierre Goupillon (pas seulement ceux passés par le N2)
    df_pierre = df_tickets[df_tickets['Propriétaire du ticket'].isin(correspondance_pierre)].copy()
    
    if not df_pierre.empty:
        # Obtenir la date de création pour les tickets de Pierre
        creation_dates_pierre = df_pierre.groupby('Ticket ID')['Date'].min().reset_index().rename(columns={'Date': 'Date de création'})
        
        # Obtenir le temps de fermeture depuis la dernière entrée de chaque ticket de Pierre
        latest_entries_pierre = df_pierre.loc[df_pierre.groupby('Ticket ID')['Date'].idxmax()][['Ticket ID', 'Temps de fermeture (HH:mm:ss)']]
        
        # Combiner pour avoir une vue unique et propre par ticket de Pierre
        df_pierre_summary = pd.merge(creation_dates_pierre, latest_entries_pierre, on='Ticket ID', how='left')
        
        # Calculer la date de fermeture réelle pour les tickets de Pierre
        df_pierre_summary['Temps de fermeture'] = pd.to_timedelta(df_pierre_summary['Temps de fermeture (HH:mm:ss)'], errors='coerce')
        df_pierre_summary['Date de fermeture'] = df_pierre_summary['Date de création'] + df_pierre_summary['Temps de fermeture']

    for week in all_weeks_full:
        # Déterminer la date de fin de la semaine
        year, week_num = int(week[1:5]), int(week[6:])
        week_end_date = pd.to_datetime(f'{year}-W{week_num}-0', format='%Y-W%W-%w') + pd.Timedelta(days=6)
        
        # 1. Sélectionner les tickets créés avant la fin de cette semaine
        tickets_created_so_far = df_n2_summary[df_n2_summary['Date de création'] <= week_end_date]
        
        # 2. Compter ceux qui sont encore ouverts à cette date
        # Un ticket est ouvert si sa date de fermeture est future OU si elle n'existe pas (NaT)
        open_count = tickets_created_so_far[
            (tickets_created_so_far['Date de fermeture'] > week_end_date) | 
            (pd.isna(tickets_created_so_far['Date de fermeture']))
        ].shape[0]
        
        weekly_open_counts.append({'Semaine': week, 'Tickets ouverts': open_count})
        
        # 3. Calculer les tickets ouverts de Pierre Goupillon pour cette semaine
        if not df_pierre.empty:
            tickets_pierre_created_so_far = df_pierre_summary[df_pierre_summary['Date de création'] <= week_end_date]
            
            pierre_open_count = tickets_pierre_created_so_far[
                (tickets_pierre_created_so_far['Date de fermeture'] > week_end_date) | 
                (pd.isna(tickets_pierre_created_so_far['Date de fermeture']))
            ].shape[0]
        else:
            pierre_open_count = 0
            
        weekly_pierre_open_counts.append({'Semaine': week, 'Tickets ouverts Pierre': pierre_open_count})

    df_open_counts = pd.DataFrame(weekly_open_counts)
    df_pierre_open_counts = pd.DataFrame(weekly_pierre_open_counts)
    
    # --- Ajout de la courbe au graphique ---
    fig.add_trace(go.Scatter(
        x=df_open_counts['Semaine'],
        y=df_open_counts['Tickets ouverts'],
        mode='lines+markers',
        name='Stock de Tickets N2 Ouverts',
        line=dict(color='yellow', width=3)
    ))
    
    # --- Ajout de la courbe des tickets de Pierre Goupillon ---
    fig.add_trace(go.Scatter(
        x=df_pierre_open_counts['Semaine'],
        y=df_pierre_open_counts['Tickets ouverts Pierre'],
        mode='lines+markers',
        name='Stock de Tickets Ouverts - Pierre Goupillon',
        line=dict(color='red', width=3, dash='dash')
    ))

    # --- Mise en page finale ---
    fig.update_xaxes(
        categoryorder='array',
        categoryarray=all_weeks_full,
        tickangle=-45
    )
    fig.update_layout(
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Nombre de tickets"
    )

    return fig

def graph_tickets_n2_resolus_par_agent(df_tickets):
    """
    Crée un graphique du nombre de tickets résolus par le N2 par semaine et par agent.
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    
    df_n2_resolus = df_tickets[
        (df_tickets['Passé par le support N2'] == 'Oui') &
        (df_tickets['Statut du ticket'] == 'Résolu')
    ].copy()
    
    if df_n2_resolus.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket résolu par le support N2", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets N2 résolus par semaine et par agent", template="plotly_dark")
        return fig

    df_grouped = df_n2_resolus.groupby(['Semaine', 'Propriétaire du ticket'])['Ticket ID'].nunique().reset_index()
    
    # Tri chronologique des semaines
    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_grouped['Semaine'] = pd.Categorical(df_grouped['Semaine'], categories=ordre_semaines, ordered=True)
    df_grouped = df_grouped.sort_values('Semaine')
    
    fig = px.bar(
        df_grouped,
        x='Semaine',
        y='Ticket ID',
        color='Propriétaire du ticket',
        title="Tickets N2 résolus par semaine et par agent",
        labels={'Ticket ID': 'Nombre de tickets'}
    )
    
    # Forcer l'ordre chronologique sur l'axe X
    fig.update_xaxes(
        categoryorder='array',
        categoryarray=ordre_semaines,
        tickangle=-45
    )
    
    fig.update_layout(
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def graph_tickets_pierre_goupillon(df_tickets):
    """
    Crée un graphique du nombre de tickets de Pierre Goupillon par semaine.
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    
    # Exclure la semaine S2024-01 qui fausse les graphiques
    df_tickets = df_tickets[df_tickets['Semaine'] != 'S2024-01'].copy()
    
    # Gestion des variantes de nom pour Pierre Goupillon
    correspondance_pierre = ['Pierre Goupillon', 'Pierre GOUPILLON']
    
    # Filtrer avec toutes les variantes possibles
    df_pierre = df_tickets[df_tickets['Propriétaire du ticket'].isin(correspondance_pierre)].copy()
    
    if df_pierre.empty:
        fig = go.Figure()
        fig.add_annotation(text="Aucun ticket pour Pierre Goupillon", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Tickets de Pierre Goupillon par semaine", template="plotly_dark")
        return fig

    df_grouped = df_pierre.groupby('Semaine')['Ticket ID'].nunique().reset_index()

    # Tri chronologique des semaines
    ordre_semaines = sorted(df_grouped['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_grouped['Semaine'] = pd.Categorical(df_grouped['Semaine'], categories=ordre_semaines, ordered=True)
    df_grouped = df_grouped.sort_values('Semaine')
    
    fig = px.bar(
        df_grouped,
        x='Semaine',
        y='Ticket ID',
        title="Tickets de Pierre Goupillon par semaine",
        labels={'Ticket ID': 'Nombre de tickets'}
    )

    fig.update_xaxes(
        categoryorder='array',
        categoryarray=ordre_semaines,
        tickangle=-45
    )

    fig.update_layout(
        template="plotly_dark"
    )

    return fig

def analyser_categories_tickets_ssi_chat_ml(df_tickets, use_ml_model=True):
    """
    Analyse et catégorise automatiquement les tickets SSI/Chat en utilisant un modèle ML et une priorisation par mots-clés.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    use_ml_model : bool
        Si True, utilise le modèle ML. Sinon, utilise l'analyse par mots-clés
    
    Returns:
    --------
    tuple : (df_categorise, fig_categories, fig_evolution, df_tableau_complet)
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    import re
    
    # --- CHARGEMENT DES MOTS-CLÉS PRIORITAIRES POUR SSI/Chat ---
    mots_cles_dict = {}
    
    # Charger les mots-clés SSI/Chat
    mots_cles_ssi_path = 'data/Affid/modele/Mots_cles_ssi.xlsx'
    if os.path.exists(mots_cles_ssi_path):
        mots_cles_ssi_df = pd.read_excel(mots_cles_ssi_path)
        mots_cles_ssi_df['Mots'] = mots_cles_ssi_df['Mots'].astype(str).str.strip().str.lower()
        for cat in mots_cles_ssi_df['Categorie'].unique():
            mots_cles_dict[cat] = set(mots_cles_ssi_df[mots_cles_ssi_df['Categorie'] == cat]['Mots'].tolist())
    
    # Charger aussi les mots-clés de facturation pour inclure NGAP et CCAM
    mots_cles_fact_path = 'data/Affid/modele/Mots_cles.xlsx'
    if os.path.exists(mots_cles_fact_path):
        mots_cles_fact_df = pd.read_excel(mots_cles_fact_path)
        mots_cles_fact_df['Mots'] = mots_cles_fact_df['Mots'].astype(str).str.strip().str.lower()
        for cat in mots_cles_fact_df['Categorie'].unique():
            mots_cles_dict[cat] = set(mots_cles_fact_df[mots_cles_fact_df['Categorie'] == cat]['Mots'].tolist())
    
    # Filtrer les tickets SSI/Chat
    df_ssi_chat = df_tickets[
        (df_tickets['Pipeline'] == 'SSI') &
        (df_tickets['Source'] == 'Chat')
    ].copy()
    
    if df_ssi_chat.empty:
        fig_categories = go.Figure()
        fig_categories.add_annotation(
            text="Aucun ticket SSI/Chat trouvé",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig_categories.update_layout(title="Catégorisation des tickets SSI/Chat", template="plotly_dark")
        fig_evolution = go.Figure()
        fig_evolution.add_annotation(
            text="Aucun ticket SSI/Chat trouvé",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig_evolution.update_layout(title="Évolution des catégories par semaine", template="plotly_dark")
        return df_ssi_chat, fig_categories, fig_evolution, pd.DataFrame()
    
    colonnes_description_possibles = [
        'Description', 'Description du ticket', 'Contenu', 'Message', 
        'Sujet', 'Titre', 'Résumé', 'Détails', 'Commentaires', 'Subject'
    ]
    colonne_description = None
    for col in colonnes_description_possibles:
        if col in df_ssi_chat.columns:
            colonne_description = col
            break
    if colonne_description is None:
        # Essayer de combiner plusieurs colonnes pour créer une description
        description_parts = []
        if 'Subject' in df_ssi_chat.columns:
            description_parts.append(df_ssi_chat['Subject'].fillna(''))
        if 'Statut du ticket' in df_ssi_chat.columns:
            description_parts.append(df_ssi_chat['Statut du ticket'].fillna(''))
        if 'Propriétaire du ticket' in df_ssi_chat.columns:
            description_parts.append(df_ssi_chat['Propriétaire du ticket'].fillna(''))
        
        if description_parts:
            df_ssi_chat['Description'] = ' - '.join(description_parts)
        else:
            df_ssi_chat['Description'] = "Ticket SSI/Chat"
        colonne_description = 'Description'
    
    # --- CATEGORISATION PAR MOTS-CLÉS PRIORITAIRES ---
    def categorisation_par_mots_cles(description):
        import re
        desc = str(description).lower()
        found_ngap = False
        found_ccam = False
        # Recherche NGAP
        if 'Facturation - NGAP' in mots_cles_dict:
            for mot in mots_cles_dict['Facturation - NGAP']:
                if mot and re.search(r'\b' + re.escape(mot) + r'\b', desc):
                    found_ngap = True
                    break
        # Recherche CCAM
        if 'Facturation - CCAM' in mots_cles_dict:
            for mot in mots_cles_dict['Facturation - CCAM']:
                if mot and re.search(r'\b' + re.escape(mot) + r'\b', desc):
                    found_ccam = True
                    break
        # Cas mixte
        if found_ngap and found_ccam:
            return 'Facturation'
        elif found_ngap:
            return 'Facturation - NGAP'
        elif found_ccam:
            return 'Facturation - CCAM'
        # Sinon, logique classique avec correspondance exacte
        for cat, mots_set in mots_cles_dict.items():
            if cat in ['Facturation - NGAP', 'Facturation - CCAM']:
                continue
            for mot in mots_set:
                if mot and re.search(r'\b' + re.escape(mot) + r'\b', desc):
                    return cat
        return None
    if mots_cles_dict:
        df_ssi_chat['Categorie_MotsCles'] = df_ssi_chat[colonne_description].apply(categorisation_par_mots_cles)
    else:
        df_ssi_chat['Categorie_MotsCles'] = None
    
    # --- CATEGORISATION ML OU MOTS-CLÉS CLASSIQUE ---
    if use_ml_model:
        try:
            from data_processing.ticket_classifier import load_ticket_classifier
            classifier = load_ticket_classifier()
            descriptions = df_ssi_chat[colonne_description].tolist()
            predictions = classifier.predict(descriptions)
            if not isinstance(predictions, list):
                predictions = [predictions]
            df_ssi_chat['Categorie_Principale'] = [pred['categorie_predite'] for pred in predictions]
            df_ssi_chat['Confiance_ML'] = [pred['confiance'] for pred in predictions]
            df_ssi_chat['Sous_Categorie'] = 'Général'
        except Exception as e:
            use_ml_model = False
    if not use_ml_model:
        categories = {
            'Connexion/Accès': [r'\b(?:login|connexion|connect|authentification|password|mot de passe|accès|access)\b', r'\b(?:se connecter|se déconnecter|identifier|identification)\b', r'\b(?:session|token|clé|key)\b'],
            'Fonctionnalités': [r'\b(?:erreur|error|bug|problème|problem|ne fonctionne|doesn\'t work)\b', r'\b(?:impossible|can\'t|ne peut pas|ne marche pas)\b', r'\b(?:bloqué|blocked|planté|crashed)\b'],
            'Données': [r'\b(?:données|data|fichier|file|document|information)\b', r'\b(?:sauvegarder|save|enregistrer|record)\b', r'\b(?:perdu|lost|supprimé|deleted|corrompu|corrupted)\b', r'\b(?:synchronisation|sync|import|export)\b'],
            'Interface': [r'\b(?:interface|écran|screen|affichage|display)\b', r'\b(?:bouton|button|menu|page|fenêtre|window)\b', r'\b(?:cliquer|click|naviguer|navigate)\b', r'\b(?:visible|invisible|caché|hidden)\b'],
            'Performance': [r'\b(?:lent|slow|performance|rapidité|speed)\b', r'\b(?:chargement|loading|timeout|délai|delay)\b', r'\b(?:gelé|frozen|bloqué|stuck)\b'],
            'Configuration': [r'\b(?:configuration|config|paramètre|setting|option)\b', r'\b(?:installer|install|mise à jour|update)\b', r'\b(?:compte|account|profil|profile)\b']
        }
        def categoriser_ticket(description):
            if pd.isna(description) or description == '':
                return 'Non catégorisé'
            description_lower = str(description).lower()
            scores = {}
            for categorie, patterns in categories.items():
                score = 0
                for pattern in patterns:
                    matches = re.findall(pattern, description_lower, re.IGNORECASE)
                    score += len(matches)
                scores[categorie] = score
            if max(scores.values()) > 0:
                return max(scores, key=scores.get)
            else:
                return 'Non catégorisé'
        df_ssi_chat['Categorie_Principale'] = df_ssi_chat[colonne_description].apply(categoriser_ticket)
        df_ssi_chat['Confiance_ML'] = 0.0
        def determiner_sous_categorie(description, categorie_principale):
            if pd.isna(description) or description == '':
                return 'Général'
            description_lower = str(description).lower()
            sous_categories = {
                'Connexion/Accès': {'Login': r'\b(?:login|se connecter|identifier)\b', 'Mot de passe': r'\b(?:password|mot de passe|mdp)\b', 'Session': r'\b(?:session|déconnexion|logout)\b'},
                'Fonctionnalités': {'Erreur système': r'\b(?:erreur|error|exception)\b', 'Fonction bloquée': r'\b(?:bloqué|blocked|impossible)\b', 'Comportement anormal': r'\b(?:anormal|strange|inattendu)\b'},
                'Données': {'Perte de données': r'\b(?:perdu|lost|supprimé|deleted)\b', 'Synchronisation': r'\b(?:sync|synchronisation|import|export)\b', 'Corruption': r'\b(?:corrompu|corrupted|fichier endommagé)\b'},
                'Interface': {'Affichage': r'\b(?:affichage|display|visible|invisible)\b', 'Navigation': r'\b(?:navigation|menu|bouton|button)\b', 'Responsive': r'\b(?:mobile|responsive|écran|screen)\b'},
                'Performance': {'Lenteur': r'\b(?:lent|slow|chargement|loading)\b', 'Timeout': r'\b(?:timeout|délai|delay|gelé)\b', 'Ressources': r'\b(?:mémoire|memory|cpu|processeur)\b'},
                'Configuration': {'Paramètres': r'\b(?:paramètre|setting|option|config)\b', 'Installation': r'\b(?:install|installation|mise à jour)\b', 'Compte': r'\b(?:compte|account|profil|profile)\b'}
            }
            if categorie_principale in sous_categories:
                for sous_cat, pattern in sous_categories[categorie_principale].items():
                    if re.search(pattern, description_lower, re.IGNORECASE):
                        return sous_cat
            return 'Général'
        df_ssi_chat['Sous_Categorie'] = df_ssi_chat.apply(
            lambda row: determiner_sous_categorie(row[colonne_description], row['Categorie_Principale']), 
            axis=1
        )
    # --- FUSION LOGIQUE : priorité aux mots-clés ---
    df_ssi_chat['Categorie_Final'] = df_ssi_chat['Categorie_MotsCles']
    df_ssi_chat.loc[df_ssi_chat['Categorie_Final'].isna(), 'Categorie_Final'] = df_ssi_chat.loc[df_ssi_chat['Categorie_Final'].isna(), 'Categorie_Principale']
    # Calculs et graphiques sur Categorie_Final
    df_stats = df_ssi_chat['Categorie_Final'].value_counts().reset_index()
    df_stats.columns = ['Catégorie', 'Nombre de tickets']
    df_stats['Pourcentage'] = (df_stats['Nombre de tickets'] / df_stats['Nombre de tickets'].sum()) * 100
    df_stats['Pourcentage_cumulé'] = df_stats['Pourcentage'].cumsum()
    # Forcer l'affichage des catégories de facturation importantes
    categories_importantes = ['Facturation - NGAP', 'Facturation - CCAM', 'Facturation']
    
    # Prendre les catégories jusqu'à 80% + les catégories importantes
    df_stats_pareto = df_stats[df_stats['Pourcentage_cumulé'] <= 80].copy()
    
    # Ajouter les catégories importantes qui ne sont pas déjà dans Pareto
    for cat_importante in categories_importantes:
        if cat_importante in df_stats['Catégorie'].values and cat_importante not in df_stats_pareto['Catégorie'].values:
            cat_row = df_stats[df_stats['Catégorie'] == cat_importante].copy()
            df_stats_pareto = pd.concat([df_stats_pareto, cat_row], ignore_index=True)
    
    # Calculer les "Autres" avec les catégories restantes
    categories_affichees = df_stats_pareto['Catégorie'].tolist()
    autres_tickets = df_stats[~df_stats['Catégorie'].isin(categories_affichees)]['Nombre de tickets'].sum()
    autres_pourcentage = df_stats[~df_stats['Catégorie'].isin(categories_affichees)]['Pourcentage'].sum()
    
    if autres_tickets > 0:
        df_stats_pareto = pd.concat([
            df_stats_pareto,
            pd.DataFrame([{
                'Catégorie': 'Autres',
                'Nombre de tickets': autres_tickets,
                'Pourcentage': autres_pourcentage,
                'Pourcentage_cumulé': 100.0
            }])
        ], ignore_index=True)
    fig_categories = px.pie(
        df_stats_pareto,
        values='Nombre de tickets',
        names='Catégorie',
        title="Répartition des tickets SSI/Chat par catégorie (Principe de Pareto - 80% du volume)"
    )
    fig_categories.update_layout(template="plotly_dark")
    df_evolution = df_ssi_chat.groupby(['Semaine', 'Categorie_Final']).size().reset_index(name='Nombre')
    categories_principales = df_stats_pareto['Catégorie'].tolist()
    if 'Autres' in categories_principales:
        categories_principales.remove('Autres')
        autres_categories = df_stats[df_stats['Pourcentage_cumulé'] > 80]['Catégorie'].tolist()
        categories_principales.extend(autres_categories)
    df_evolution = df_evolution[df_evolution['Categorie_Final'].isin(categories_principales)]
    ordre_semaines = sorted(df_evolution['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_evolution['Semaine'] = pd.Categorical(df_evolution['Semaine'], categories=ordre_semaines, ordered=True)
    df_evolution = df_evolution.sort_values('Semaine')
    fig_evolution = px.line(
        df_evolution,
        x='Semaine',
        y='Nombre',
        color='Categorie_Final',
        title="Évolution des catégories de tickets SSI/Chat par semaine (Filtrable)",
        markers=True
    )
    fig_evolution.update_layout(
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Nombre de tickets",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_evolution.update_xaxes(tickangle=-45)
    df_tableau_complet = df_stats.copy()
    df_tableau_complet = df_tableau_complet.sort_values('Nombre de tickets', ascending=False)
    df_tableau_complet['Pourcentage'] = df_tableau_complet['Pourcentage'].round(1)
    df_tableau_complet['Pourcentage_cumulé'] = df_tableau_complet['Pourcentage_cumulé'].round(1)
    return df_ssi_chat, fig_categories, fig_evolution, df_tableau_complet

def analyser_facturation_specialisee(df_tickets, use_ml_model=True):
    """
    Analyse spécialisée des sous-catégories de facturation avec modèle ML dédié et priorisation par mots-clés.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    use_ml_model : bool
        Si True, utilise le modèle ML spécialisé. Sinon, utilise l'analyse par mots-clés
    
    Returns:
    --------
    tuple : (df_facturation, fig_sous_categories, fig_evolution_sous_categories, df_tableau_complet)
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    import re
    
    # --- CHARGEMENT DES MOTS-CLÉS PRIORITAIRES ---
    mots_cles_path = 'data/Affid/modele/Mots_cles.xlsx'
    mots_cles_df = pd.read_excel(mots_cles_path)
    # Nettoyage des espaces et mise en minuscules pour la recherche
    mots_cles_df['Mots'] = mots_cles_df['Mots'].astype(str).str.strip().str.lower()
    mots_cles_dict = {}
    for cat in mots_cles_df['Categorie'].unique():
        mots_cles_dict[cat] = set(mots_cles_df[mots_cles_df['Categorie'] == cat]['Mots'].tolist())
    
    # Filtrer les tickets de facturation
    df_facturation = df_tickets[df_tickets['Catégorie'] == 'Facturation'].copy()
    
    if df_facturation.empty:
        # Retourner des graphiques vides avec message
        fig_sous_categories = go.Figure()
        fig_sous_categories.add_annotation(
            text="Aucun ticket de facturation trouvé",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig_sous_categories.update_layout(title="Sous-catégories de facturation", template="plotly_dark")
        
        fig_evolution = go.Figure()
        fig_evolution.add_annotation(
            text="Aucun ticket de facturation trouvé",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        fig_evolution.update_layout(title="Évolution des sous-catégories par semaine", template="plotly_dark")
        
        return df_facturation, fig_sous_categories, fig_evolution, pd.DataFrame()
    
    # Vérifier les colonnes disponibles pour la description
    colonnes_description_possibles = [
        'Description', 'Description du ticket', 'Contenu', 'Message', 
        'Sujet', 'Titre', 'Résumé', 'Détails', 'Commentaires', 'Subject'
    ]
    colonne_description = None
    for col in colonnes_description_possibles:
        if col in df_facturation.columns:
            colonne_description = col
            break
    if colonne_description is None:
        # Essayer de combiner plusieurs colonnes pour créer une description
        description_parts = []
        if 'Subject' in df_facturation.columns:
            description_parts.append(df_facturation['Subject'].fillna(''))
        if 'Statut du ticket' in df_facturation.columns:
            description_parts.append(df_facturation['Statut du ticket'].fillna(''))
        if 'Propriétaire du ticket' in df_facturation.columns:
            description_parts.append(df_facturation['Propriétaire du ticket'].fillna(''))
        
        if description_parts:
            df_facturation['Description'] = ' - '.join(description_parts)
        else:
            df_facturation['Description'] = "Ticket de facturation"
        colonne_description = 'Description'
    
    # --- CATEGORISATION PAR MOTS-CLÉS PRIORITAIRES ---
    def categorisation_par_mots_cles(description):
        desc = str(description).lower()
        for cat, mots_set in mots_cles_dict.items():
            for mot in mots_set:
                if mot and mot in desc:
                    return cat
        return None
    
    # Appliquer la catégorisation prioritaire
    df_facturation['Categorie_MotsCles'] = df_facturation[colonne_description].apply(categorisation_par_mots_cles)
    
    # --- CATEGORISATION ML OU MOTS-CLÉS CLASSIQUE ---
    if use_ml_model:
        try:
            from data_processing.facturation_classifier import load_facturation_classifier
            classifier = load_facturation_classifier()
            descriptions = df_facturation[colonne_description].tolist()
            predictions = classifier.predict(descriptions)
            if not isinstance(predictions, list):
                predictions = [predictions]
            df_facturation['Sous_Categorie_ML'] = [pred['sous_categorie_predite'] for pred in predictions]
            df_facturation['Confiance_ML'] = [pred['confiance'] for pred in predictions]
        except Exception as e:
            use_ml_model = False
    if not use_ml_model:
        mots_cles_sous_categories = {
            'Facturation-Cotation CCAM': ['ccam', 'qzm', 'qama', 'base tarif', 'tarif sécu'],
            'Facturation-Exoneration (EXO, ALD, C2S)': ['exo', 'ald', 'c2s', 'exonération', 'code 7'],
            'Facturation-Cotation IVG': ['ivg', 'fmv', 'grossesse', '6 semaines'],
            'Facturation-Teleconsultation': ['téléconsultation', 'teleconsultation', 'tcs', '50 euros'],
            'Facturation-Majoration': ['majoration', 'md', 'vsp', 'mn', 'mm', 'hors garde'],
            'Facturation-PAV': ['pav', 'participation forfaitaire', 'patient hospitalisé', '24 euros'],
            'Facturation-ALD': ['ald', '100% amo', 'affection longue durée'],
            'Facturation-Association d\'actes': ['association', 'actes série', 'kiné', 'orthophoniste'],
            'Facturation-Dépassement': ['dépassement', 'honoraires', 'conventionné', 'optam'],
            'Facturation-Cotation SF': ['sf', '16.5', '7.5', 'codes sf'],
            'Facturation-Patient etranger': ['étranger', 'sécurité sociale', 'carte vitale', 'demandeur asile'],
            'Facturation-Taux de prise en charge': ['taux', 'prise en charge', 'remboursement', 'fse'],
            'Facturation-Cotation maternité': ['maternité', 'grossesse gémellaire', '70%'],
            'Facturation-MT/DMT': ['mt', 'dmt', 'discipline medico tarifaire', 'cpam'],
            'Facturation-SNCF': ['sncf', 'agréé'],
            'Facturation-Dégradé': ['dégradé', 'feuille soins', 'numéro sécu', 'sans cv'],
            'Facturation-Soins Anonyme': ['anonyme', 'anonymisé', 'feuille soin']
        }
        def categoriser_sous_categorie(description):
            if pd.isna(description) or description == '':
                return 'Facturation'
            description_lower = str(description).lower()
            scores = {}
            for sous_cat, mots_cles in mots_cles_sous_categories.items():
                score = 0
                for mot in mots_cles:
                    if mot in description_lower:
                        score += 1
                scores[sous_cat] = score
            if max(scores.values()) > 0:
                return max(scores, key=scores.get)
            else:
                return 'Facturation'
        df_facturation['Sous_Categorie_ML'] = df_facturation[colonne_description].apply(categoriser_sous_categorie)
        df_facturation['Confiance_ML'] = 0.0
    
    # --- FUSION LOGIQUE : priorité aux mots-clés ---
    df_facturation['Sous_Categorie_Final'] = df_facturation['Categorie_MotsCles']
    df_facturation.loc[df_facturation['Sous_Categorie_Final'].isna(), 'Sous_Categorie_Final'] = df_facturation.loc[df_facturation['Sous_Categorie_Final'].isna(), 'Sous_Categorie_ML']
    
    # Calculs et graphiques identiques, mais sur Sous_Categorie_Final
    df_stats = df_facturation['Sous_Categorie_Final'].value_counts().reset_index()
    df_stats.columns = ['Sous-catégorie', 'Nombre de tickets']
    df_stats['Pourcentage'] = (df_stats['Nombre de tickets'] / df_stats['Nombre de tickets'].sum()) * 100
    df_stats['Pourcentage_cumulé'] = df_stats['Pourcentage'].cumsum()
    df_stats_pareto = df_stats[df_stats['Pourcentage_cumulé'] <= 80].copy()
    if len(df_stats_pareto) < len(df_stats):
        autres_tickets = df_stats[df_stats['Pourcentage_cumulé'] > 80]['Nombre de tickets'].sum()
        autres_pourcentage = df_stats[df_stats['Pourcentage_cumulé'] > 80]['Pourcentage'].sum()
        df_stats_pareto = pd.concat([
            df_stats_pareto,
            pd.DataFrame([{
                'Sous-catégorie': 'Autres',
                'Nombre de tickets': autres_tickets,
                'Pourcentage': autres_pourcentage,
                'Pourcentage_cumulé': 100.0
            }])
        ], ignore_index=True)
    fig_sous_categories = px.pie(
        df_stats_pareto,
        values='Nombre de tickets',
        names='Sous-catégorie',
        title="Répartition des sous-catégories de facturation (Principe de Pareto - 80% du volume)"
    )
    fig_sous_categories.update_layout(template="plotly_dark")
    df_evolution = df_facturation.groupby(['Semaine', 'Sous_Categorie_Final']).size().reset_index(name='Nombre')
    sous_categories_principales = df_stats_pareto['Sous-catégorie'].tolist()
    if 'Autres' in sous_categories_principales:
        sous_categories_principales.remove('Autres')
        autres_categories = df_stats[df_stats['Pourcentage_cumulé'] > 80]['Sous-catégorie'].tolist()
        sous_categories_principales.extend(autres_categories)
    df_evolution = df_evolution[df_evolution['Sous_Categorie_Final'].isin(sous_categories_principales)]
    ordre_semaines = sorted(df_evolution['Semaine'].unique(), key=lambda x: (int(x[1:5]), int(x[6:])))
    df_evolution['Semaine'] = pd.Categorical(df_evolution['Semaine'], categories=ordre_semaines, ordered=True)
    df_evolution = df_evolution.sort_values('Semaine')
    fig_evolution = px.line(
        df_evolution,
        x='Semaine',
        y='Nombre',
        color='Sous_Categorie_Final',
        title="Évolution des sous-catégories de facturation par semaine (Filtrable)",
        markers=True
    )
    fig_evolution.update_layout(
        template="plotly_dark",
        xaxis_title="Semaine",
        yaxis_title="Nombre de tickets",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_evolution.update_xaxes(tickangle=-45)
    df_tableau_complet = df_stats.copy()
    df_tableau_complet = df_tableau_complet.sort_values('Nombre de tickets', ascending=False)
    df_tableau_complet['Pourcentage'] = df_tableau_complet['Pourcentage'].round(1)
    df_tableau_complet['Pourcentage_cumulé'] = df_tableau_complet['Pourcentage_cumulé'].round(1)
    return df_facturation, fig_sous_categories, fig_evolution, df_tableau_complet


def categoriser_avec_ia_personnalisee(df_tickets, use_sentence_transformers=True, seuil_confiance=0.3):
    """
    Catégorise les tickets en utilisant des embeddings et des mots-clés personnalisés.
    Ne traite que les tickets avec pipeline = 'ssi' et source = 'chat'.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    use_sentence_transformers : bool
        Si True, utilise Sentence Transformers. Sinon, utilise TF-IDF + cosinus
    seuil_confiance : float
        Score minimum pour accepter une catégorisation (0.0 à 1.0)
    
    Returns:
    --------
    DataFrame avec colonnes : ['Ticket ID', 'Categorie_IA', 'Confiance_IA', 'Scores_par_categorie']
    """
    import pandas as pd
    import numpy as np
    import re
    import os
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    # Filtrer les tickets avec pipeline = 'ssi' et source = 'chat'
    df_tickets_filtre = df_tickets.copy()
    
    # Vérifier si les colonnes existent
    if 'Pipeline' in df_tickets_filtre.columns and 'Source' in df_tickets_filtre.columns:
        # Filtrage plus flexible
        df_tickets_filtre = df_tickets_filtre[
            (df_tickets_filtre['Pipeline'].str.lower().str.contains('ssi', na=False)) & 
            (df_tickets_filtre['Source'].str.lower().str.contains('chat', na=False))
        ]
    
    # Si aucun ticket ne correspond aux critères, retourner un DataFrame vide avec les colonnes requises
    if df_tickets_filtre.empty:
        result_df = df_tickets.copy()
        result_df['Categorie_IA'] = 'Non catégorisé'
        result_df['Confiance_IA'] = 0.0
        result_df['Scores_par_categorie'] = [{} for _ in range(len(result_df))]
        return result_df
    
    # Charger les catégories personnalisées
    categories_path = 'data/Affid/modele/Categories_Mots_Cles_Personnalisees.xlsx'
    if not os.path.exists(categories_path):
        raise FileNotFoundError(f"Fichier de catégories non trouvé: {categories_path}")
    
    df_categories = pd.read_excel(categories_path)
    
    # Créer un dictionnaire catégorie -> mots-clés
    categories_dict = {}
    for _, row in df_categories.iterrows():
        categorie = row['Categorie']
        mot_cle = str(row['Mots_cles']).lower().strip()
        if mot_cle and mot_cle != 'nan':  # Ignorer les valeurs vides
            if categorie not in categories_dict:
                categories_dict[categorie] = []
            categories_dict[categorie].append(mot_cle)
    
    # Trouver la colonne de description
    colonnes_description_possibles = [
        'Description', 'Description du ticket', 'Contenu', 'Message', 
        'Sujet', 'Titre', 'Résumé', 'Détails', 'Commentaires', 'Subject'
    ]
    colonne_description = None
    for col in colonnes_description_possibles:
        if col in df_tickets_filtre.columns:
            colonne_description = col
            break
    
    if colonne_description is None:
        # Créer une description combinée
        description_parts = []
        for col in ['Subject', 'Statut du ticket', 'Propriétaire du ticket']:
            if col in df_tickets_filtre.columns:
                description_parts.append(df_tickets_filtre[col].fillna(''))
        
        if description_parts:
            df_tickets_filtre['Description'] = ' - '.join(description_parts)
        else:
            df_tickets_filtre['Description'] = "Ticket"
        colonne_description = 'Description'
    
    
    # Préparer les descriptions
    descriptions = df_tickets_filtre[colonne_description].fillna('').astype(str).str.lower()
    
    # Diagnostiquer la qualité des descriptions
    descriptions_non_vides = descriptions[descriptions.str.strip() != '']
    
    # Méthode 1: TF-IDF + Cosinus (plus rapide)
    if not use_sentence_transformers:
        # Créer les représentations des catégories
        categories_texts = []
        categories_names = []
        
        for categorie, mots_cles in categories_dict.items():
            # Créer un texte représentatif de la catégorie
            texte_categorie = ' '.join(mots_cles)
            categories_texts.append(texte_categorie)
            categories_names.append(categorie)
        
        # Ajouter les descriptions des tickets
        all_texts = categories_texts + descriptions.tolist()
        
        # Vectorisation TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=1
        )
        
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Séparer les vecteurs des catégories et des tickets
        categories_vectors = tfidf_matrix[:len(categories_texts)]
        tickets_vectors = tfidf_matrix[len(categories_texts):]
        
        # Calculer les similarités
        similarities = cosine_similarity(tickets_vectors, categories_vectors)
        
        # Trouver la meilleure catégorie pour chaque ticket
        best_categories = []
        confidences = []
        scores_details = []
        
        for i, sim_scores in enumerate(similarities):
            best_idx = np.argmax(sim_scores)
            best_score = sim_scores[best_idx]
            best_category = categories_names[best_idx]
            
            # Créer un dictionnaire des scores par catégorie
            scores_dict = {categories_names[j]: float(sim_scores[j]) for j in range(len(categories_names))}
            
            # Appliquer le seuil de confiance
            if best_score >= seuil_confiance:
                best_categories.append(best_category)
                confidences.append(best_score)
            else:
                best_categories.append('Non catégorisé')
                confidences.append(0.0)
            
            scores_details.append(scores_dict)
    
    # Méthode 2: Sentence Transformers (plus précis)
    else:
        try:
            from sentence_transformers import SentenceTransformer, util
            
            # Charger le modèle (léger et rapide)
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Créer des embeddings pour les catégories
            category_embeddings = model.encode(list(categories_dict.keys()), convert_to_tensor=True)
            
            # Fonction de prédiction de catégorie
            def predict_category(text):
                embedding = model.encode(text, convert_to_tensor=True)
                cosine_scores = util.cos_sim(embedding, category_embeddings)
                best_match_idx = cosine_scores.argmax()
                best_score = cosine_scores[0][best_match_idx].item()
                return list(categories_dict.keys())[best_match_idx], best_score, cosine_scores[0].tolist()
            
            # Catégoriser chaque ticket
            best_categories = []
            confidences = []
            scores_details = []
            
            for description in descriptions:
                best_category, best_score, all_scores = predict_category(description)
                
                # Créer un dictionnaire des scores par catégorie
                scores_dict = {list(categories_dict.keys())[i]: score for i, score in enumerate(all_scores)}
                
                # Appliquer le seuil de confiance
                if best_score >= seuil_confiance:
                    best_categories.append(best_category)
                    confidences.append(best_score)
                else:
                    best_categories.append('Non catégorisé')
                    confidences.append(0.0)
                
                scores_details.append(scores_dict)
                
        except ImportError:
            return categoriser_avec_ia_personnalisee(df_tickets, use_sentence_transformers=False, seuil_confiance=seuil_confiance)
    
    # Créer le DataFrame de résultats pour les tickets filtrés
    result_df_filtre = df_tickets_filtre.copy()
    result_df_filtre['Categorie_IA'] = best_categories
    result_df_filtre['Confiance_IA'] = confidences
    result_df_filtre['Scores_par_categorie'] = scores_details
    
    # Diagnostics des résultats
    tickets_categorises = len([c for c in best_categories if c != 'Non catégorisé'])
    taux_categorisation = (tickets_categorises / len(best_categories)) * 100 if best_categories else 0
    
    # Afficher les scores moyens par catégorie
    if scores_details:
        scores_par_categorie = {}
        for scores in scores_details:
            for cat, score in scores.items():
                if cat not in scores_par_categorie:
                    scores_par_categorie[cat] = []
                scores_par_categorie[cat].append(score)
        
    
    # Créer le DataFrame de résultats final (tous les tickets)
    result_df = df_tickets.copy()
    
    # Initialiser les colonnes de catégorisation avec des valeurs par défaut
    result_df['Categorie_IA'] = 'Non catégorisé'
    result_df['Confiance_IA'] = 0.0
    result_df['Scores_par_categorie'] = [{} for _ in range(len(result_df))]
    
    # Appliquer les résultats de catégorisation uniquement aux tickets SSI/Chat
    if not result_df_filtre.empty:
        # Créer un mapping des résultats par Ticket ID
        mapping_results = result_df_filtre[['Ticket ID', 'Categorie_IA', 'Confiance_IA', 'Scores_par_categorie']].set_index('Ticket ID')
        
        # Appliquer le mapping aux tickets correspondants
        for ticket_id in mapping_results.index:
            mask = result_df['Ticket ID'] == ticket_id
            if mask.any():
                result_df.loc[mask, 'Categorie_IA'] = mapping_results.loc[ticket_id, 'Categorie_IA']
                result_df.loc[mask, 'Confiance_IA'] = mapping_results.loc[ticket_id, 'Confiance_IA']
                result_df.loc[mask, 'Scores_par_categorie'] = mapping_results.loc[ticket_id, 'Scores_par_categorie']
    
    return result_df

def ajuster_seuil_automatiquement(df_tickets, use_sentence_transformers=True, seuil_cible=0.7):
    """
    Ajuste automatiquement le seuil de confiance pour atteindre un taux de catégorisation cible.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    use_sentence_transformers : bool
        Si True, utilise Sentence Transformers. Sinon, utilise TF-IDF + cosinus
    seuil_cible : float
        Taux de catégorisation cible (0.0 à 1.0)
    
    Returns:
    --------
    float : Seuil de confiance optimal
    """
    import pandas as pd
    import numpy as np
    
    # Test avec différents seuils
    seuils_test = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
    taux_categorisation = []
    
    for seuil in seuils_test:
        try:
            df_resultat = categoriser_avec_ia_personnalisee(df_tickets, use_sentence_transformers, seuil)
            tickets_ssi_chat = df_resultat[
                (df_resultat['Pipeline'].str.lower().str.contains('ssi', na=False)) & 
                (df_resultat['Source'].str.lower().str.contains('chat', na=False))
            ]
            if len(tickets_ssi_chat) > 0:
                taux = len(tickets_ssi_chat[tickets_ssi_chat['Categorie_IA'] != 'Non catégorisé']) / len(tickets_ssi_chat)
                taux_categorisation.append(taux)
            else:
                taux_categorisation.append(0.0)
        except Exception as e:
            taux_categorisation.append(0.0)
    
    # Trouver le seuil optimal
    if taux_categorisation:
        # Trouver le seuil le plus proche du taux cible
        differences = [abs(taux - seuil_cible) for taux in taux_categorisation]
        seuil_optimal_idx = np.argmin(differences)
        seuil_optimal = seuils_test[seuil_optimal_idx]
        return seuil_optimal
    else:
        return 0.1

def analyser_mots_cles_manquants(df_tickets, seuil_confiance=0.3, top_n=20):
    """
    Analyse les mots-clés des tickets non catégorisés pour identifier les sujets manquants.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    seuil_confiance : float
        Seuil de confiance utilisé pour la catégorisation
    top_n : int
        Nombre de mots-clés les plus fréquents à afficher
    
    Returns:
    --------
    dict : Dictionnaire avec les analyses
    """
    import pandas as pd
    import numpy as np
    import re
    from collections import Counter
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # Catégoriser les tickets avec le seuil donné
    df_categorise = categoriser_avec_ia_personnalisee(df_tickets, seuil_confiance=seuil_confiance)
    
    # Filtrer les tickets SSI/Chat
    tickets_ssi_chat = df_categorise[
        (df_categorise['Pipeline'].str.lower().str.contains('ssi', na=False)) & 
        (df_categorise['Source'].str.lower().str.contains('chat', na=False))
    ]
    
    # Séparer les tickets catégorisés et non catégorisés
    tickets_categorises = tickets_ssi_chat[tickets_ssi_chat['Categorie_IA'] != 'Non catégorisé']
    tickets_non_categorises = tickets_ssi_chat[tickets_ssi_chat['Categorie_IA'] == 'Non catégorisé']
    
    
    # Trouver la colonne de description
    colonnes_description_possibles = [
        'Description', 'Description du ticket', 'Contenu', 'Message', 
        'Sujet', 'Titre', 'Résumé', 'Détails', 'Commentaires', 'Subject'
    ]
    colonne_description = None
    for col in colonnes_description_possibles:
        if col in tickets_non_categorises.columns:
            colonne_description = col
            break
    
    if colonne_description is None:
        # Créer une description combinée
        description_parts = []
        for col in ['Subject', 'Statut du ticket', 'Propriétaire du ticket']:
            if col in tickets_non_categorises.columns:
                description_parts.append(tickets_non_categorises[col].fillna(''))
        
        if description_parts:
            tickets_non_categorises['Description'] = ' - '.join(description_parts)
        else:
            tickets_non_categorises['Description'] = "Ticket"
        colonne_description = 'Description'
    
    # Analyser les mots-clés des tickets non catégorisés
    descriptions_non_cat = tickets_non_categorises[colonne_description].fillna('').astype(str).str.lower()
    
    # Liste étendue des mots vides en français
    mots_vides_fr = {
        # Articles
        'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'au', 'aux',
        # Prépositions
        'à', 'avec', 'chez', 'contre', 'dans', 'de', 'depuis', 'derrière', 'devant', 'durant',
        'en', 'entre', 'hors', 'jusque', 'malgré', 'par', 'parmi', 'pendant', 'pour', 'sans',
        'selon', 'sous', 'sur', 'vers', 'via', 'voici', 'voilà',
        # Pronoms
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'me', 'te', 'se', 'nous', 'vous',
        'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses', 'notre', 'votre', 'leur',
        'ce', 'cette', 'ces', 'celui', 'celle', 'ceux', 'celles', 'qui', 'que', 'quoi', 'dont',
        'où', 'quand', 'comment', 'pourquoi', 'combien',
        # Conjonctions
        'et', 'ou', 'mais', 'donc', 'car', 'ni', 'or', 'puis', 'ensuite', 'alors', 'quand',
        'si', 'comme', 'quand', 'lorsque', 'tandis', 'pendant', 'avant', 'après',
        # Adverbes courants
        'très', 'trop', 'peu', 'beaucoup', 'assez', 'trop', 'plus', 'moins', 'bien', 'mal',
        'vite', 'lentement', 'ici', 'là', 'ailleurs', 'partout', 'nulle', 'maintenant',
        'aujourd', 'hier', 'demain', 'toujours', 'jamais', 'souvent', 'rarement',
        # Verbes auxiliaires et être/avoir
        'être', 'avoir', 'faire', 'aller', 'venir', 'pouvoir', 'vouloir', 'devoir', 'savoir',
        'voir', 'dire', 'donner', 'prendre', 'mettre', 'laisser', 'passer', 'rester',
        # Mots techniques courants mais peu informatifs
        'problème', 'erreur', 'bug', 'issue', 'ticket', 'demande', 'question', 'aide',
        'support', 'assistance', 'service', 'client', 'utilisateur', 'système', 'application',
        'logiciel', 'programme', 'fonction', 'fonctionnalité', 'option', 'paramètre',
        'configuration', 'installation', 'mise', 'jour', 'mise à jour', 'version',
        'fichier', 'document', 'donnée', 'information', 'message', 'notification',
        'écran', 'page', 'interface', 'bouton', 'menu', 'lien', 'url', 'adresse',
        'connexion', 'accès', 'authentification', 'identifiant', 'mot', 'passe',
        'session', 'compte', 'profil', 'utilisateur', 'administrateur',
        # Mots de liaison
        'aussi', 'encore', 'déjà', 'toujours', 'jamais', 'souvent', 'rarement',
        'peut', 'peut-être', 'probablement', 'certainement', 'sûrement',
        'peut-être', 'peut', 'peux', 'peuvent', 'pouvons', 'pouvez',
        'veut', 'veux', 'veulent', 'voulons', 'voulez',
        'doit', 'dois', 'doivent', 'devons', 'devez',
        'sait', 'sais', 'savent', 'savons', 'savez',
        'voit', 'vois', 'voient', 'voyons', 'voyez',
        'dit', 'dis', 'disent', 'disons', 'dites',
        'donne', 'donnes', 'donnent', 'donnons', 'donnez',
        'prend', 'prends', 'prennent', 'prenons', 'prenez',
        'met', 'mets', 'mettent', 'mettons', 'mettez',
        'laisse', 'laisses', 'laissent', 'laissons', 'laissez',
        'passe', 'passes', 'passent', 'passons', 'passez',
        'reste', 'restes', 'restent', 'restons', 'restez',
        # Formes contractées
        'qu', 's', 't', 'l', 'd', 'c', 'n', 'y', 'en',
        # Mots courts
        'ça', 'sa', 'ça', 'sa', 'ça', 'sa', 'ça', 'sa', 'ça', 'sa',
        # Autres mots peu informatifs
        'chose', 'rien', 'tout', 'tous', 'toute', 'toutes', 'aucun', 'aucune',
        'quelque', 'quelques', 'certain', 'certaine', 'certains', 'certaines',
        'autre', 'autres', 'même', 'mêmes', 'seul', 'seule', 'seuls', 'seules',
        'premier', 'première', 'premiers', 'premières', 'dernier', 'dernière',
        'derniers', 'dernières', 'nouveau', 'nouvelle', 'nouveaux', 'nouvelles',
        'ancien', 'ancienne', 'anciens', 'anciennes', 'bon', 'bonne', 'bons', 'bonnes',
        'mauvais', 'mauvaise', 'mauvais', 'mauvaises', 'grand', 'grande', 'grands', 'grandes',
        'petit', 'petite', 'petits', 'petites', 'gros', 'grosse', 'gros', 'grosses'
    }
    
    # Nettoyer et tokeniser
    def nettoyer_texte(texte):
        # Supprimer les caractères spéciaux et chiffres
        texte = re.sub(r'[^\w\s]', ' ', texte)
        texte = re.sub(r'\d+', ' ', texte)
        
        # Tokeniser et filtrer
        mots = texte.lower().split()
        
        # Filtrer les mots vides et les mots courts
        mots_filtres = []
        for mot in mots:
            # Garder seulement les mots de 4+ caractères qui ne sont pas des mots vides
            if len(mot) >= 4 and mot not in mots_vides_fr:
                # Vérifier que le mot n'est pas composé uniquement de lettres répétées
                if len(set(mot)) > 1:
                    mots_filtres.append(mot)
        
        return ' '.join(mots_filtres)
    
    descriptions_nettoyees = descriptions_non_cat.apply(nettoyer_texte)
    
    # Extraire les mots-clés avec TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=200,  # Augmenter le nombre de features
        ngram_range=(1, 3),  # Capturer les expressions de 1 à 3 mots
        stop_words='english',
        min_df=2,  # Mot doit apparaître dans au moins 2 documents
        max_df=0.8,  # Mot ne doit pas apparaître dans plus de 80% des documents
        analyzer='word'
    )
    
    if len(descriptions_nettoyees) > 0:
        tfidf_matrix = vectorizer.fit_transform(descriptions_nettoyees)
        feature_names = vectorizer.get_feature_names_out()
        
        # Calculer les scores TF-IDF moyens
        tfidf_scores = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # Créer un DataFrame avec les mots-clés et leurs scores
        mots_cles_df = pd.DataFrame({
            'Mot_cle': feature_names,
            'Score_TFIDF': tfidf_scores,
            'Frequence': np.sum(tfidf_matrix.toarray() > 0, axis=0)
        })
        
        # Filtrage supplémentaire des mots-clés
        def filtrer_mots_cles_avance(row):
            mot = row['Mot_cle'].lower()
            
            # Rejeter les mots trop courts
            if len(mot) < 4:
                return False
            
            # Rejeter les mots composés uniquement de lettres répétées
            if len(set(mot)) <= 1:
                return False
            
            # Rejeter les mots qui ressemblent à des URLs ou emails
            if re.search(r'[\.@\/\\]', mot):
                return False
            
            # Rejeter les mots qui contiennent trop de chiffres
            if sum(c.isdigit() for c in mot) > len(mot) * 0.3:
                return False
            
            # Rejeter les mots trop génériques
            mots_trop_generiques = {
                'fait', 'faites', 'faire', 'fait', 'faits', 'faite', 'faites',
                'avoir', 'a', 'as', 'ont', 'avons', 'avez', 'eu', 'eue', 'eus', 'eues',
                'être', 'est', 'sont', 'suis', 'es', 'êtes', 'sommes', 'été', 'étée', 'étés', 'étées',
                'aller', 'va', 'vont', 'vais', 'vas', 'allez', 'allons', 'allé', 'allée', 'allés', 'allées',
                'venir', 'vient', 'viennent', 'viens', 'venez', 'venons', 'venu', 'venue', 'venus', 'venues',
                'pouvoir', 'peut', 'peuvent', 'peux', 'pouvez', 'pouvons', 'pu', 'pue', 'pus', 'pues',
                'vouloir', 'veut', 'veulent', 'veux', 'voulez', 'voulons', 'voulu', 'voulue', 'voulus', 'voulues',
                'devoir', 'doit', 'doivent', 'dois', 'devez', 'devons', 'dû', 'due', 'dus', 'dues',
                'savoir', 'sait', 'savent', 'sais', 'savez', 'savons', 'su', 'sue', 'sus', 'sues',
                'voir', 'voit', 'voient', 'vois', 'voyez', 'voyons', 'vu', 'vue', 'vus', 'vues',
                'dire', 'dit', 'disent', 'dis', 'dites', 'disons', 'dit', 'dite', 'dits', 'dites',
                'donner', 'donne', 'donnent', 'donnes', 'donnez', 'donnons', 'donné', 'donnée', 'donnés', 'données',
                'prendre', 'prend', 'prennent', 'prends', 'prenez', 'prenons', 'pris', 'prise', 'pris', 'prises',
                'mettre', 'met', 'mettent', 'mets', 'mettez', 'mettons', 'mis', 'mise', 'mis', 'mises',
                'laisser', 'laisse', 'laissent', 'laisses', 'laissez', 'laissons', 'laissé', 'laissée', 'laissés', 'laissées',
                'passer', 'passe', 'passent', 'passes', 'passez', 'passons', 'passé', 'passée', 'passés', 'passées',
                'rester', 'reste', 'restent', 'restes', 'restez', 'restons', 'resté', 'restée', 'restés', 'restées'
            }
            
            if mot in mots_trop_generiques:
                return False
            
            return True
        
        # Appliquer le filtrage
        mots_cles_df['Valide'] = mots_cles_df.apply(filtrer_mots_cles_avance, axis=1)
        mots_cles_df = mots_cles_df[mots_cles_df['Valide'] == True].drop('Valide', axis=1)
        
        # Trier par score TF-IDF et prendre les meilleurs
        mots_cles_df = mots_cles_df.sort_values('Score_TFIDF', ascending=False).head(top_n)
        
        # Analyser aussi les mots simples (fréquence brute) avec le même filtrage
        tous_mots = []
        for desc in descriptions_nettoyees:
            mots_desc = desc.split()
            for mot in mots_desc:
                if len(mot) >= 4 and mot not in mots_vides_fr:
                    tous_mots.append(mot)
        
        compteur_mots = Counter(tous_mots)
        
        # Filtrer les mots fréquents avec les mêmes critères
        mots_frequents_filtres = []
        for mot, freq in compteur_mots.most_common(top_n * 2):  # Prendre plus pour compenser le filtrage
            if filtrer_mots_cles_avance({'Mot_cle': mot}):
                mots_frequents_filtres.append((mot, freq))
                if len(mots_frequents_filtres) >= top_n:
                    break
        
        mots_frequents = mots_frequents_filtres
    
    return {
        'seuil_confiance': seuil_confiance,
        'stats': {
            'total_ssi_chat': len(tickets_ssi_chat),
            'categorises': len(tickets_categorises),
            'non_categorises': len(tickets_non_categorises),
            'taux_categorisation': len(tickets_categorises) / len(tickets_ssi_chat) * 100
        },
        'mots_cles_tfidf': mots_cles_df,
        'mots_frequents': mots_frequents,
        'exemples_tickets': tickets_non_categorises[['Ticket ID', colonne_description, 'Confiance_IA']].head(10)
    }


def optimiser_seuil_confiance(df_tickets, seuils_test=None):
    """
    Teste différents seuils de confiance pour trouver le meilleur compromis.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    seuils_test : list
        Liste des seuils à tester
    
    Returns:
    --------
    dict : Résultats de l'optimisation
    """
    if seuils_test is None:
        seuils_test = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
    
    resultats = []
    
    for seuil in seuils_test:
        try:
            analyse = analyser_mots_cles_manquants(df_tickets, seuil)
            resultats.append({
                'seuil': seuil,
                'taux_categorisation': analyse['stats']['taux_categorisation'],
                'nb_categorises': analyse['stats']['categorises'],
                'nb_non_categorises': analyse['stats']['non_categorises']
            })
        except Exception as e:
            pass
    
    # Créer un DataFrame avec les résultats
    df_resultats = pd.DataFrame(resultats)
    
    # Calculer le score optimal (compromis entre taux et précision)
    # Score = taux_categorisation * (1 - ratio_non_categorises)
    df_resultats['score_optimal'] = df_resultats['taux_categorisation'] * (1 - df_resultats['nb_non_categorises'] / df_resultats['nb_categorises'])
    
    # Trouver le seuil optimal
    seuil_optimal = df_resultats.loc[df_resultats['score_optimal'].idxmax(), 'seuil']
    
    return {
        'resultats': df_resultats,
        'seuil_optimal': seuil_optimal,
        'analyse_optimale': analyser_mots_cles_manquants(df_tickets, seuil_optimal)
    }

def generer_fichier_mots_cles_manquants(df_tickets, seuil_confiance=0.3, output_path=None):
    """
    Génère un fichier Excel avec les mots-clés manquants organisés par catégories suggérées.
    
    Parameters:
    -----------
    df_tickets : pandas DataFrame
        DataFrame contenant les données de tickets
    seuil_confiance : float
        Seuil de confiance utilisé pour la catégorisation
    output_path : str
        Chemin du fichier de sortie (optionnel)
    
    Returns:
    --------
    str : Chemin du fichier généré
    """
    import pandas as pd
    import numpy as np
    import re
    from collections import Counter
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    
    # Analyser les mots-clés manquants
    analyse = analyser_mots_cles_manquants(df_tickets, seuil_confiance)
    
    if analyse['mots_cles_tfidf'].empty:
        return None
    
    # Charger les catégories existantes pour comprendre la structure
    categories_path = 'data/Affid/modele/Categories_Mots_Cles_Personnalisees.xlsx'
    if os.path.exists(categories_path):
        df_categories_existantes = pd.read_excel(categories_path)
        categories_existantes = df_categories_existantes['Categorie'].unique()
    else:
        categories_existantes = []
    
    # Analyser les mots-clés pour suggérer des catégories
    mots_cles_df = analyse['mots_cles_tfidf']
    
    # Créer des embeddings pour les mots-clés
    vectorizer = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
    mots_cles_text = ' '.join(mots_cles_df['Mot_cle'].tolist())
    tfidf_matrix = vectorizer.fit_transform([mots_cles_text])
    
    # Clustering des mots-clés (si assez de mots)
    if len(mots_cles_df) >= 3:
        try:
            # Utiliser les scores TF-IDF comme features
            features = mots_cles_df[['Score_TFIDF', 'Frequence']].values
            n_clusters = min(5, len(mots_cles_df) // 2)  # Maximum 5 clusters
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            mots_cles_df['Cluster'] = kmeans.fit_predict(features)
            
            # Nommer les clusters basé sur les mots les plus fréquents
            cluster_names = {}
            for cluster_id in range(n_clusters):
                cluster_mots = mots_cles_df[mots_cles_df['Cluster'] == cluster_id]['Mot_cle'].head(3).tolist()
                cluster_names[cluster_id] = f"Catégorie_{cluster_id+1}_{'_'.join(cluster_mots[:2])}"
        except:
            mots_cles_df['Cluster'] = 0
            cluster_names = {0: "Catégorie_1"}
    else:
        mots_cles_df['Cluster'] = 0
        cluster_names = {0: "Catégorie_1"}
    
    # Créer le fichier Excel
    if output_path is None:
        output_path = f"nouveaux_mots_cles_categories_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Onglet 1: Mots-clés organisés par clusters
        mots_cles_organises = []
        for cluster_id in range(mots_cles_df['Cluster'].max() + 1):
            cluster_data = mots_cles_df[mots_cles_df['Cluster'] == cluster_id]
            for _, row in cluster_data.iterrows():
                mots_cles_organises.append({
                    'Categorie_Suggeree': cluster_names[cluster_id],
                    'Mot_cle': row['Mot_cle'],
                    'Score_TFIDF': row['Score_TFIDF'],
                    'Frequence': row['Frequence'],
                    'Priorite': 'Haute' if row['Score_TFIDF'] > 0.1 else 'Moyenne' if row['Score_TFIDF'] > 0.05 else 'Basse'
                })
        
        df_organises = pd.DataFrame(mots_cles_organises)
        df_organises.to_excel(writer, sheet_name='Mots-clés par catégories', index=False)
        
        # Onglet 2: Mots-clés par priorité
        mots_cles_priorite = mots_cles_df.copy()
        mots_cles_priorite['Priorite'] = mots_cles_priorite['Score_TFIDF'].apply(
            lambda x: 'Haute' if x > 0.1 else 'Moyenne' if x > 0.05 else 'Basse'
        )
        mots_cles_priorite = mots_cles_priorite.sort_values(['Priorite', 'Score_TFIDF'], ascending=[False, False])
        mots_cles_priorite.to_excel(writer, sheet_name='Mots-clés par priorité', index=False)
        
        # Onglet 3: Format pour import dans le fichier existant
        format_import = mots_cles_df[['Mot_cle']].copy()
        format_import['Categorie'] = 'À définir'
        format_import['Mots_cles'] = format_import['Mot_cle']
        format_import = format_import[['Categorie', 'Mots_cles']]
        format_import.to_excel(writer, sheet_name='Format import', index=False)
        
        # Onglet 4: Statistiques
        stats_data = {
            'Métrique': [
                'Seuil de confiance utilisé',
                'Taux de catégorisation',
                'Tickets catégorisés',
                'Tickets non catégorisés',
                'Mots-clés identifiés',
                'Mots-clés haute priorité',
                'Mots-clés moyenne priorité',
                'Mots-clés basse priorité'
            ],
            'Valeur': [
                f"{seuil_confiance:.2f}",
                f"{analyse['stats']['taux_categorisation']:.1f}%",
                analyse['stats']['categorises'],
                analyse['stats']['non_categorises'],
                len(mots_cles_df),
                len(mots_cles_df[mots_cles_df['Score_TFIDF'] > 0.1]),
                len(mots_cles_df[(mots_cles_df['Score_TFIDF'] <= 0.1) & (mots_cles_df['Score_TFIDF'] > 0.05)]),
                len(mots_cles_df[mots_cles_df['Score_TFIDF'] <= 0.05])
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        # Onglet 5: Exemples de tickets non catégorisés
        if not analyse['exemples_tickets'].empty:
            analyse['exemples_tickets'].to_excel(writer, sheet_name='Exemples tickets', index=False)
    
    
    return output_path


# Fonctions Gantt supprimées
