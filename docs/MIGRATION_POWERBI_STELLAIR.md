# Migration Power BI — Page Support Stellair (3 premiers graphiques)

> **Objectif** : reproduire fidèlement les **3 premiers graphiques** de la page *Support Stellair*
> du dashboard Streamlit, **100 % dans Power BI**, à partir des **fichiers Excel bruts**
> (aucun Python, aucun cache `.db`). Le fichier se rafraîchit en rechargeant les Excel.
>
> Source de vérité de la logique métier : `data_processing/aircall_processing.py` et
> `data_processing/hubspot_processing.py`. Les règles ci-dessous en sont la transposition exacte.

---

## 1. Les 3 graphiques ciblés

| # | Titre | Source brute | Filtre « Stellair » | Mesure clé |
|---|-------|--------------|---------------------|------------|
| 1 | **Activité Support Stellair** | Appels Aircall (`data_v3/*.xls`) | `line = armatistechnique` **OU** `Logiciel = Stellair`, entrants | Taux de service = répondus / entrants + volumes/semaine |
| 2 | **Activité % NXT vs Stellair** | Appels Aircall | entrants, `Logiciel ∈ {Affid, Stellair}` | part % Stellair vs Affid / semaine |
| 3 | **Temps de réponse aux tickets** | Tickets HubSpot (`.xlsx`) | `Pipeline ∈ {SSI, SSIA, SPSA}` **et** `Source ∈ {Chat, E-mail, Formulaire}` | moyenne `working_hours` + nb tickets/semaine |

Tous : agrégés **par semaine (ISO)**, hors `S2024-01`, filtrables par période.

---

## 2. Architecture du modèle (étoile)

```
        ┌───────────────┐
        │   Dim Date    │  (calendrier + Semaine ISO)
        └──────┬────┬───┘
       Date[Date]   Date[Date]
        │                │
┌───────▼──────┐  ┌──────▼─────────┐
│   Appels     │  │    Tickets     │
│ (Aircall v3) │  │   (HubSpot)    │
└──────────────┘  └────────────────┘
```

- **`Appels`** ← dossier `data/Affid/Aircall/data_v3/*.xls` (commencer par v3 ; voir §7).
- **`Tickets`** ← `data/Affid/Hubspot/ticket/hubspot-crm-exports-tous-les-tickets-AAAA-MM-JJ.xlsx`.
- **`Date`** ← table calculée DAX, reliée à `Appels[Date]` et `Tickets[Date de création]`.

---

## 3. ⚠️ Les 3 pièges à connaître

1. **Semaine ISO `S2026-23`** — Python utilise `strftime("S%Y-%V")` : **année civile** (`%Y`) +
   **numéro de semaine ISO 8601** (`%V`). La fonction native `Date.WeekOfYear` de Power Query
   **n'est pas ISO** → décalage d'une semaine. On utilise une formule ISO dédiée (ci-dessous).
   *C'est la cause n°1 d'écart lors de la validation.*
2. **`Logiciel` (Stellair/Affid)** — logique en cascade (IVR Branch → line → préfixe Tags).
3. **`working_hours`** — heures ouvrées 9h–18h, lundi-vendredi, entre création et 1ʳᵉ réponse :
   fonction M récursive (le point le plus technique).

---

## 4. Power Query — Requête `Appels` (Aircall)

### 4.1 Import
*Accueil → Obtenir les données → Dossier* → `data/Affid/Aircall/data_v3` → **Combiner et transformer**.
Power Query génère la table combinée. On applique ensuite les étapes ci-dessous.

### 4.2 Renommage des colonnes (= `aircall_processing.py:287-294`)
| Colonne brute | Renommer en |
|---|---|
| `answered` | `LastState` |
| `date (tz offset incl.)` (= `datetime (tz offset incl.)`) | `StartTime` |
| `duration (in call)` | `InCallDuration` |
| `from` | `FromNumber` |
| `to` | `ToNumber` |
| `user` | `UserName` |
| `tags` | `Tags` |
| `missed_call_reason` | `ScenarioName` |
| `ivr branch` | `IVR Branch` |

> Vérifier que `StartTime` est typée **Date/Heure**.

### 4.3 Colonnes dérivées (Ajouter une colonne → Colonne personnalisée)

**`line` normalisée** (minuscules, sans espaces — `aircall_processing.py:451-462`) :
```m
Text.Lower(Text.Replace([line], " ", ""))
```
> Remplace la colonne `line` par cette version (ou crée `line_norm` et l'utiliser partout).

**`LastState`** (mapping `Yes/ANSWERED → yes`, tout le reste → `no` — `:342-347`) :
```m
if List.Contains({"yes", "answered"}, Text.Lower(Text.From([LastState]))) then "yes" else "no"
```

**`Date`** :
```m
Date.From([StartTime])
```

**`Jour`** (nom du jour en anglais, comme le Python `day_name()`) :
```m
Date.DayOfWeekName([StartTime], "en-US")
```

**`Heure`** :
```m
Time.Hour(DateTime.Time([StartTime]))
```

**`Semaine`** (ISO `S%Y-%V` — voir piège n°1) :
```m
let
    d        = Date.From([StartTime]),
    jeudi    = Date.AddDays(d, 3 - Date.DayOfWeek(d, Day.Monday)),   // jeudi de la semaine ISO
    semISO   = Number.IntegerDivide(Duration.Days(jeudi - Date.StartOfYear(jeudi)), 7) + 1,
    annee    = Date.Year(d)                                          // année CIVILE (= %Y)
in
    "S" & Text.From(annee) & "-" & Text.PadStart(Text.From(semISO), 2, "0")
```

**`Logiciel`** (cascade — `aircall_processing.py:506-534`) :
```m
let
    ivr   = if [IVR Branch] = null then "" else Text.Trim([IVR Branch]),
    tags3 = if [Tags] = null then "" else Text.Upper(Text.Start([Tags], 3))
in
    if ivr <> "" then [IVR Branch]
    else if [line] = "armatistechnique" then "Stellair"
    else if tags3 = "STE" then "Stellair"
    else if tags3 = "AFD" then "Affid"
    else "Inconnu"
```

**`est_stellair`** (flag du périmètre Stellair — `app.py:836`) :
```m
[line] = "armatistechnique" or [Logiciel] = "Stellair"
```

### 4.4 Filtres (exactement ceux du Python)
Appliquer ces filtres de lignes (Accueil → Conserver/Supprimer des lignes, ou filtres de colonne) :

| Filtre | Règle | Référence |
|---|---|---|
| Entrants uniquement | `direction = "inbound"` | charts 1 & 2 |
| Hors week-end | `Jour` ∉ {`Saturday`, `Sunday`} | `:336-339` |
| Hors hors-horaires/abandon | `ScenarioName` ∉ {`Fermé`, `out_of_opening_hours`, `abandoned_in_ivr`, `short_abandoned`} | `:336-339` |
| Hors agents techniques | `UserName` ∉ {`Vincent Gourvat`, `Thierry CAROFF`, `Armatis Agent 1`} | `:480-483` |
| Hors semaine corrompue | `Semaine ≠ "S2024-01"` | charts |

> Le filtre « 2 dernières années » (`:398-402`) est implicite si tu pars de `data_v3`.

### 4.5 Colonnes à conserver
`Date`, `Semaine`, `Jour`, `Heure`, `direction`, `LastState`, `Logiciel`, `est_stellair`,
`FromNumber`, `UserName`, `line`. (Les autres peuvent être supprimées pour alléger.)

---

## 5. Power Query — Requête `Tickets` (HubSpot)

### 5.1 Import
*Obtenir les données → Excel* → le `.xlsx` tickets → la feuille principale.

### 5.2 Dédoublonnage par `Ticket ID` (garder le plus récent — `hubspot_processing.py:216-230`)
1. Ajouter une colonne `_DateTri` :
   ```m
   if [#"Date de la première réponse par e-mail de l'agent"] = null
   then [Date de création]
   else [#"Date de la première réponse par e-mail de l'agent"]
   ```
2. Trier `Ticket ID` (croissant), puis `_DateTri` (**décroissant**).
3. *Accueil → Supprimer les lignes → Supprimer les doublons* en sélectionnant **uniquement** `Ticket ID`.
4. Supprimer `_DateTri`.

### 5.3 Normalisation du propriétaire (`:181-212`)
Créer une **requête de correspondance** `MapAgents` (table à 2 colonnes `Brut` / `Normalise`) :

| Brut | Normalise |
|---|---|
| Archimède KESSI | Archimede KESSI |
| Emilie Gest | Emilie GEST |
| HUMBLOT NASSUF | Mourad HUMBLOT |
| FREDERIC SAUVAN | Frederic SAUVAN |
| Morgane VANDENBUSSCHE | Morgane Vandenbussche |
| Pierre Goupillon | Pierre GOUPILLON |
| Cédeline Duval | Cédeline DUVAL |
| Cedeline Duval | Cédeline DUVAL |
| Cedeline DUVAL | Cédeline DUVAL |
| CÉDELINE DUVAL | Cédeline DUVAL |
| C√©deline DUVAL | Cédeline DUVAL |
| CÃ©deline DUVAL | Cédeline DUVAL |

Puis *Fusionner les requêtes* (`Propriétaire du ticket` ↔ `Brut`, jointure gauche) et remplacer la
valeur par `Normalise` quand elle existe :
```m
if [MapAgents] = null then [Propriétaire du ticket] else [MapAgents][Normalise]
```
> Pour les variantes Cédeline non listées, ajoute-les à `MapAgents` au fil de l'eau (le Python fait
> en plus un *fuzzy match* « contient cedeline + duval » — optionnel en v1).

### 5.4 Colonnes dérivées

**`Semaine`** (depuis `Date de création`, même formule ISO qu'au §4.3) :
```m
let
    d      = Date.From([Date de création]),
    jeudi  = Date.AddDays(d, 3 - Date.DayOfWeek(d, Day.Monday)),
    semISO = Number.IntegerDivide(Duration.Days(jeudi - Date.StartOfYear(jeudi)), 7) + 1,
    annee  = Date.Year(d)
in
    "S" & Text.From(annee) & "-" & Text.PadStart(Text.From(semISO), 2, "0")
```

**`working_hours`** — voir la fonction `fnWorkingHours` au §6 :
```m
fnWorkingHours([Date de création], [#"Date de la première réponse par e-mail de l'agent"])
```

**`scope_stellair`** (périmètre tickets Stellair — `kpi_generation.py:3784-3787`) :
```m
List.Contains({"SSI", "SSIA", "SPSA"}, [Pipeline])
and List.Contains({"Chat", "E-mail", "Formulaire"}, [Source])
```

### 5.5 Filtres
| Filtre | Règle |
|---|---|
| Hors semaine corrompue | `Semaine ≠ "S2024-01"` |

> **Affinage optionnel (fidélité exacte)** : le graphe 3 ne compte que les tickets dont le
> propriétaire est dans la liste des **agents support** (`agents_all`, codée dans `app.py`).
> En v1 on peut l'omettre ; pour coller au pixel, créer un flag `est_agent_support` à partir de
> cette liste et l'ajouter aux mesures.

---

## 6. Fonction M `fnWorkingHours` (heures ouvrées)

Crée une **requête vide** → *Éditeur avancé* → colle ceci → renomme la requête `fnWorkingHours`.
Transpose exactement `hubspot_processing.py:141-160` (9h–18h, lundi-vendredi).

```m
let
    fnWorkingHours = (debut as nullable datetime, fin as nullable datetime) as number =>
        if debut = null or fin = null or fin <= debut then 0
        else
            let
                j0      = Date.From(debut),
                j1      = Date.From(fin),
                nbJours = Duration.Days(j1 - j0) + 1,
                jours   = List.Dates(j0, nbJours, #duration(1, 0, 0, 0)),
                heures  = List.Transform(
                    jours,
                    (j) =>
                        let
                            estOuvre  = Date.DayOfWeek(j, Day.Monday) < 5,            // lun..ven
                            ouverture = DateTime.From(j) + #duration(0, 9, 0, 0),     // 09:00
                            fermeture = DateTime.From(j) + #duration(0, 18, 0, 0),    // 18:00
                            debJour   = List.Max({debut, ouverture}),
                            finJour   = List.Min({fin, fermeture}),
                            h         = if estOuvre and debJour < finJour
                                        then Duration.TotalHours(finJour - debJour)
                                        else 0
                        in
                            h
                ),
                total = List.Sum(heures)
            in
                total
in
    fnWorkingHours
```

---

## 7. Note sur les dossiers v1 / v2

`data_v1` et `data_v2` ont un **schéma Aircall différent** (d'où les fonctions de normalisation
Python `normalize_v3_data` et le renommage `aircall_processing.py:89-124`). **Commence par `data_v3`**
(qui couvre fin 2025 → aujourd'hui). Pour ajouter v1/v2 ensuite : créer une requête par version qui
harmonise les colonnes vers le schéma v3, puis *Ajouter les requêtes* (append).

---

## 8. Modèle de données & relations

1. Table **`Date`** (Modélisation → Nouvelle table) :
   ```dax
   Date =
   ADDCOLUMNS (
       CALENDAR (
           MINX ( 'Appels', 'Appels'[Date] ),
           MAXX ( 'Appels', 'Appels'[Date] )
       ),
       "Annee", YEAR ( [Date] ),
       "SemaineNum", WEEKNUM ( [Date], 21 ),                       -- 21 = semaine ISO 8601
       "Semaine", "S" & YEAR ( [Date] ) & "-" & FORMAT ( WEEKNUM ( [Date], 21 ), "00" ),
       "SemaineSort", YEAR ( [Date] ) * 100 + WEEKNUM ( [Date], 21 )
   )
   ```
   > Si la plage doit aussi couvrir les tickets, élargis le `CALENDAR` (ex. `DATE(2024,1,1)` →
   > `TODAY()`).
2. **Trier** la colonne `Date[Semaine]` **par** `Date[SemaineSort]` (Outils de colonne → Trier par colonne).
3. Marquer `Date` comme **table de dates** (sur `Date[Date]`).
4. Relations (1 → *) :
   - `Date[Date]` → `Appels[Date]`
   - `Date[Date]` → `Tickets[Date de création]`

> Les visuels utiliseront `Date[Semaine]` en axe X (trié chronologiquement), et un **segment**
> sur `Date[Date]` filtrera les deux faits simultanément.

---

## 9. Mesures DAX

> Comme `Appels` est déjà filtrée aux entrants en Power Query, les mesures ne refiltrent pas `direction`.

### Graphe 1 — Activité Support Stellair
```dax
Entrants Stellair :=
CALCULATE ( COUNTROWS ( 'Appels' ), 'Appels'[est_stellair] = TRUE () )

Entrants connectés Stellair :=
CALCULATE (
    COUNTROWS ( 'Appels' ),
    'Appels'[est_stellair] = TRUE (),
    'Appels'[LastState] = "yes"
)

Numéros uniques Stellair :=
CALCULATE (
    DISTINCTCOUNT ( 'Appels'[FromNumber] ),
    'Appels'[est_stellair] = TRUE ()
)

Taux de service Stellair :=
DIVIDE ( [Entrants connectés Stellair], [Entrants Stellair] )
```

### Graphe 2 — % NXT vs Stellair
Le plus simple : un **histogramme empilé 100 %** avec `Logiciel` en légende (filtre visuel
`Logiciel ∈ {Affid, Stellair}`) → la normalisation à 100 % est automatique, **aucune mesure requise**.
Valeur du visuel = `Nb appels` :
```dax
Nb appels := COUNTROWS ( 'Appels' )
```
Si tu veux la part explicite (ex. pour un KPI) :
```dax
% Stellair :=
VAR _stellair = CALCULATE ( COUNTROWS ( 'Appels' ), 'Appels'[Logiciel] = "Stellair" )
VAR _total    = CALCULATE ( COUNTROWS ( 'Appels' ), 'Appels'[Logiciel] IN { "Stellair", "Affid" } )
RETURN
    DIVIDE ( _stellair, _total )
```

### Graphe 3 — Temps de réponse aux tickets
```dax
Nb tickets Stellair :=
CALCULATE (
    COUNTROWS ( 'Tickets' ),
    'Tickets'[scope_stellair] = TRUE ()
)

Temps réponse moyen (h) :=
CALCULATE (
    AVERAGE ( 'Tickets'[working_hours] ),
    'Tickets'[scope_stellair] = TRUE (),
    'Tickets'[working_hours] > 0          -- le Python exclut working_hours <= 0 pour la moyenne
)
```

---

## 10. Construction des visuels

| # | Type de visuel Power BI | Axe X | Valeurs |
|---|--------------------------|-------|---------|
| 1 | **Histogramme empilé et courbe** | `Date[Semaine]` | Colonnes empilées : `Entrants`, `Entrants connectés Stellair`, `Numéros uniques Stellair` — Ligne (axe secondaire) : `Taux de service Stellair` (format %) |
| 2 | **Histogramme empilé 100 %** | `Date[Semaine]` | Valeur : `Nb appels` — Légende : `Logiciel` — Filtre visuel : `Logiciel ∈ {Affid, Stellair}` |
| 3 | **Histogramme groupé et courbe** | `Date[Semaine]` | Colonnes : `Nb tickets Stellair` — Ligne : `Temps réponse moyen (h)` |

- Graphe 3 : ajouter une **ligne de seuil à 2 h** via le volet **Analyses** (ligne constante = 2) —
  c'est le SLA de référence du dashboard d'origine.
- Ajouter un **segment** sur `Date[Date]` (remplace le sélecteur de période Streamlit).

> L'original (graphe 1) utilise des *aires* empilées ; Power BI rend cela naturellement en
> colonnes empilées — même information, geste natif. Possibilité d'utiliser un visuel « graphique
> en aires » si l'on tient au rendu exact.

---

## 11. Checklist de validation

Comparer **semaine par semaine** avec le Streamlit (sur 2-3 semaines récentes) :

- [ ] Les libellés `Semaine` correspondent (⚠️ piège ISO — vérifier en priorité).
- [ ] Graphe 1 : `Entrants`, `Entrants connectés`, `Numéros uniques`, `Taux de service` identiques.
- [ ] Graphe 2 : % Stellair / Affid identiques.
- [ ] Graphe 3 : `Temps réponse moyen` et `Nb tickets` identiques.
- [ ] Total appels Stellair sur la période = total Streamlit.
- [ ] (Si écart graphe 3) tester l'ajout du filtre **agents support** (§5.5).

---

## 12. Références code (logique d'origine)

| Règle | Fichier | Lignes |
|---|---|---|
| `Logiciel` (cascade) | `data_processing/aircall_processing.py` | 506-534 |
| `line` normalisée | `data_processing/aircall_processing.py` | 451-462 |
| `Semaine` ISO (appels) | `data_processing/aircall_processing.py` | 331 |
| `LastState` (yes/no) | `data_processing/aircall_processing.py` | 287, 342-347 |
| Filtres appels | `data_processing/aircall_processing.py` | 336-339, 480-483, 398-402 |
| Filtre Stellair (chart 1) | `app.py` | 836 |
| `Semaine` ISO (tickets) | `data_processing/hubspot_processing.py` | 169 |
| `working_hours` | `data_processing/hubspot_processing.py` | 141-160 |
| Dédoublonnage tickets | `data_processing/hubspot_processing.py` | 216-230 |
| Normalisation agents | `data_processing/hubspot_processing.py` | 181-212 |
| Filtre tickets (chart 3) | `data_processing/kpi_generation.py` | 3784-3787 |
