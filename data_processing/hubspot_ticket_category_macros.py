"""
Regroupement des valeurs HubSpot « Catégorie » en deux familles pour analyses COMEX.

Aligné sur le mapping « Catégorie → sujet » utilisé dans kpi_generation (sunburst /
repartition_lecteurs_par_type). Les catégories dont le sujet agrégé est « Lecteur »
(matériel, CPS, connexion au lecteur, etc.) vont dans le bucket « incidents lecteurs » ;
tout le reste (Stellair, utilisation, facturation, formation, etc.) dans « infos & logiciels ».
"""
from __future__ import annotations

from typing import Dict, Optional

# Copie synchronisée avec kpi_generation.repartition_lecteurs_par_type (categories_to_subjects).
# Si le dashboard évolue, mettre à jour ce dictionnaire en cohérence.
HUBSPOT_CATEGORIE_VERS_SUJET: Dict[str, str] = {
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
    "SAV": "Lecteur",
}

SUJET_LECTEUR = "Lecteur"

# Libellés courts pour CSV / COMEX
MACRO_INFOS_LOGICIELS = (
    "Demandes d'information, Stellair, logiciel, facturation, autres (hors matériel lecteur)"
)
MACRO_LECTEURS = "Incidents et problèmes lecteurs (matériel, CPS, connexion lecteur)"


def sujet_agrege_depuis_categorie_hubspot(categorie: Optional[str]) -> Optional[str]:
    """Retourne le « sujet » agrégé ou None si la catégorie n'est pas dans le référentiel."""
    if categorie is None or (isinstance(categorie, float) and str(categorie) == "nan"):
        return None
    s = str(categorie).strip()
    if not s or s.lower() == "nan":
        return None
    return HUBSPOT_CATEGORIE_VERS_SUJET.get(s)


def macro_groupe_comex(categorie: Optional[str]) -> str:
    """
    Regroupe en 2 familles pour présentation COMEX :
    - incidents lecteurs : sujet agrégé = « Lecteur » dans le référentiel HubSpot ;
    - sinon : demandes d'info, logiciel, Stellair, facturation, etc.
    Catégorie inconnue / vide : rangée dans le groupe « hors lecteur » (comme « Autre »).
    """
    sujet = sujet_agrege_depuis_categorie_hubspot(categorie)
    if sujet == SUJET_LECTEUR:
        return MACRO_LECTEURS
    return MACRO_INFOS_LOGICIELS


def categories_hubspot_classees_lecteur() -> list[str]:
    """Liste des libellés exacts « Catégorie » HubSpot classés en sujet Lecteur."""
    return sorted(
        [cat for cat, suj in HUBSPOT_CATEGORIE_VERS_SUJET.items() if suj == SUJET_LECTEUR]
    )
