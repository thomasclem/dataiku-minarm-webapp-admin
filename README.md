# Gestion des habilitations — Dataiku Dash

Application française de délégation d’appartenance aux groupes existants.
Le point d’entrée DSS importe et appelle uniquement l’initialiseur ; aucun
appel au SDK ou callback n’est défini dans le code de la webapp DSS.

## Ouvrir dans PyCharm

Ouvrir ce dossier comme projet, puis sélectionner un interpréteur Python 3.10
ou supérieur. DSS utilise actuellement Python 3.13 et Dash 4.4.1.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python run_tests.py
python run_local.py --debug
```

Le serveur local écoute sur `http://127.0.0.1:8050`. Il utilise exclusivement
des comptes, groupes et projets fictifs en mémoire. Une attribution locale
ne modifie jamais DSS. Aucune clé API n’est nécessaire pour cette démonstration.
Pour le débogage PyCharm, exécuter `run_local.py` avec la racine du projet
comme répertoire de travail et l’interpréteur de l’environnement virtuel.

## Architecture

```text
src/access_manager/
├── main.py                    # Assemblage et initialisation explicite
├── config.py                  # Politique administrative
├── features/access/
│   ├── layout.py              # Formulaire et récapitulatif de la fonctionnalité
│   ├── callbacks.py           # Adaptateurs Dash, contexte HTTP et rendu
│   └── ids.py                 # Identifiants stables partagés
├── ui/                        # En-tête, composants, styles, libellés
├── services/                  # Autorisation, classement, aperçu signé, audit
├── repositories/dss.py         # Seul module utilisant le SDK Dataiku
└── tests/                     # Services, dépôt, callbacks HTTP, câblage
dss/backend.py                 # Point d’entrée minimal pour DSS
devtools/                      # Dépôt de démonstration local, non déployé
```

Les services ne dépendent ni de Dash, ni de Flask, ni de Dataiku. Le dépôt est
injecté. Les données propres à un utilisateur restent dans la requête ou les
stores du navigateur. Les callbacks sont enregistrés une seule fois au
démarrage sur l’objet Dash fourni. Le CSS est intégré explicitement au modèle
Dash ; aucun répertoire d’assets non servi n’est supposé.

## DSS

Projet : `WEBAPP_ACCESS_MANAGER`, webapp : `ZmFdREB`.
Copier le contenu de `src/access_manager/` dans la bibliothèque Python du
projet sous `/python/access_manager/`, puis conserver ce seul point d’entrée :

```python
from access_manager.main import render_dash_webapp

render_dash_webapp(app)
```

DSS fournit `app` et le SDK. Ne pas créer une autre instance Dash dans ce fichier
et ne pas y appeler `app.run()`. Après synchronisation, redémarrer le backend
avec les outils Headless/Cobuild ou depuis DSS. Le développement local avec
Headless correspond à l’option 2 du workflow GS Tools ; aucun dépôt distant
ou déploiement sur un nœud Automation n’est requis pour ce projet.

## Politique et vérification

La configuration `DELEGABLE_GROUPS_BY_PROJECT` est administrée dans `config.py`.
Elle reste vide tant qu’un administrateur n’a pas approuvé les couples
projet/groupe. Les groupes administrateurs sont exclus ; la vérification des
droits couvre tous les projets concernés. Un aperçu signé, non expiré et
cohérent avec les sélections est nécessaire avant attribution.

Les tests ne se connectent pas à une instance et n’effectuent aucune écriture
réelle. Ils couvrent l’autorisation, le classement, la préservation des groupes,
les aperçus périmés, les callbacks HTTP et le rendu initial sous Dash 4.4.1.
Les restrictions de Dataiku Cloud sur la sauvegarde des paramètres utilisateur
restent applicables. Le verrou d’écriture est limité au processus ; les
modifications externes concurrentes doivent être coordonnées séparément.
