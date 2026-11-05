# Gestion des habilitations - Dataiku Dash

Application française de création de comptes Reader et de partage multi-projets via les groupes existants.
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


## Parcours Reader et multi-projets

1. Actualiser les données, puis créer un utilisateur Reader ou sélectionner un Reader actif existant.
2. Sélectionner un à cinquante projets administrés par l’opérateur connecté.
3. Consulter la proposition automatique par projet, vérifier les droits, confirmer leur portée puis attribuer les accès.

La création est une action explicite distincte de l’attribution : elle crée un compte sans aucun groupe initial. Le profil `READER` est imposé côté serveur, jamais choisi par le navigateur. La capacité est relue avant création ; une licence absente, expirée ou sans place Reader bloque l’action. Aucun repli vers un profil plus privilégié n’est effectué. Les comptes existants doivent également avoir exactement le profil READER ; leur profil n’est jamais modifié.

La cible est une **instance DSS standard avec licence READER**. Le réglage administratif `READER_SOURCE_TYPE = 'LOCAL'` utilise un mot de passe initial saisi dans le formulaire et transmis uniquement lors de la création ; il est effacé du champ après la tentative et n’entre ni dans les stores ni dans les journaux applicatifs. Pour une authentification externe, un administrateur peut configurer `LDAP` ou `LOCAL_NO_AUTH`, après vérification de l’authentification sur l’instance cible. Aucun appel de création réel n’a été fait pendant le développement.

**Dataiku Cloud :** la création et la modification des utilisateurs DSS ne sont pas prises en charge par ces API. Utiliser Launchpad pour cette cible ; cette intégration n’est pas incluse dans le parcours DSS demandé. L’instance Cloud de prévisualisation actuelle ne dispose pas du profil READER ; le bouton de création y reste désactivé.

Les groupes proposés doivent déjà exister, être locaux, non administrateurs, ne porter aucune capacité globale et n’accorder que `readDashboards` ou `readProjectContent` dans les listes d’accès de tous les projets concernés. Tout droit inconnu ou d’écriture exclut le groupe. L’opérateur doit administrer chaque projet sélectionné ainsi que tous les projets également concernés. La politique `DELEGABLE_GROUPS_BY_PROJECT` existante reste obligatoire pour les opérateurs non administrateurs d’instance ; elle est vide par défaut et doit être renseignée par un administrateur après approbation des groupes.

Le classement est **par projet**, déterministe : consultation des tableaux de bord avant lecture du contenu du projet, puis moins de projets hors sélection, moins de droits, appartenance existante en cas d’égalité, puis nom. Il ne prétend pas calculer un optimum combinatoire de toutes les combinaisons de groupes. Les groupes retenus sont dédupliqués et ajoutés en une seule sauvegarde fraîche des paramètres utilisateur. Si un projet n’a aucun groupe admissible, toute l’attribution est bloquée. Aucune modification de groupe ou de liste d’accès de projet n’est effectuée.

L’aperçu signé expire et lie l’opérateur, le bénéficiaire, les projets, les groupes, leurs droits, la politique et les appartenances. Ces données sont recalculées avant sauvegarde. Une autre modification impose une nouvelle vérification. Les autorisations de ressources hors listes d’accès de projets (connexions, dossiers, etc.) ne font pas l’objet d’un inventaire exhaustif ; la portée doit être examinée avant délégation. Le verrou applicatif ne coordonne pas les autres processus DSS ni les modifications administratives externes.

`services/onboarding.py` porte ce parcours ; les opérations SDK restent uniquement dans `repositories/dss.py`. Le point d’entrée DSS reste inchangé. Le dépôt de démonstration local permet de créer des comptes et de partager deux projets uniquement en mémoire.


## Détection des groupes et admissibilité

Le formulaire affiche tous les groupes présents dans les listes d’accès des projets sélectionnés, y compris les groupes non attribuables. Le tableau indique les droits, les capacités globales et les motifs de refus : groupe administrateur ou externe, droits dépassant la consultation sur un projet, projet hors périmètre administré, absence de droit de consultation, définition manquante, ou délégation non approuvée. Les groupes admissibles sont classés en premier ; le groupe retenu par projet est identifié comme « Proposé ». Les contrôles d’attribution restent identiques.

Par exemple, un groupe DGA ayant `readProjectContent` et `writeProjectContent`, ou des capacités globales, apparaît avec ses droits et la mention « Non attribuable ». Il n’est plus masqué. Le profil READER du compte ne remplace pas ces contrôles d’autorisation.


## Historique des accès dans le Flow

Le dataset **managé** `WEBAPP_ACCESS_MANAGER.access_granted_history` reçoit l’historique des attributions du parcours Reader. Il est créé explicitement une seule fois avant la mise en service ; les callbacks ne créent pas de dataset et ne changent jamais son schéma. La connexion est choisie par l’administrateur parmi les connexions existantes autorisant des datasets managés.

Après import de la bibliothèque, exécuter dans un notebook Python du projet DSS :

```python
from access_manager.repositories.dss import DSSRepository
DSSRepository().provision_access_history("NOM_CONNEXION_MANAGEE_EXISTANTE")
```

Ou, depuis un terminal disposant du runtime Python et du contexte d’authentification du DSS cible :

```sh
python -m access_manager.setup_history --connection NOM_CONNEXION_MANAGEE_EXISTANTE
```

Le nom de connexion ci-dessus est un paramètre à remplacer, pas une connexion créée par l’application. Aucun mot de passe ou clé API ne doit être passé dans cette commande. La création utilise le constructeur DSS `new_managed_dataset`, avec `overwrite=False` et un schéma explicite. Si le dataset existe déjà, le provisionnement vérifie le caractère managé, la connexion et le schéma sans modifier les données. Un schéma différent doit être examiné par un administrateur ; il n’est jamais réécrit automatiquement. Une fois créé, ce dataset apparaît dans le Flow sans recette de reconstruction, puisqu’il est alimenté par la webapp.

Une ligne décrit un couple projet/groupe pour une opération : `record_id`, `event_id`, `ts_utc`, `actor_login`, `beneficiary_login`, `project_key`, `group_name`, `outcome`, `user_profile`, `project_permissions_json`, `affected_projects_json`, `source`. Les horodatages sont en UTC. Tous les projets d’une même attribution partagent un `event_id`, même lorsqu’un groupe commun n’est ajouté qu’une seule fois. Aucun mot de passe, en-tête HTTP, aperçu signé ou réglage utilisateur brut n’est conservé.

Les événements sont ajoutés avec `appendMode=True` et `write_row_dict`, sans lecture/réécriture du dataset ni inférence de schéma :

- `REQUESTED` : demande validée et enregistrée avant toute modification des appartenances.
- `GRANTED` : appartenance ajoutée et vérifiée. Filtrer sur ce statut pour les nouvelles attributions confirmées.
- `ALREADY_MEMBER` : appartenance déjà présente ; aucune nouvelle attribution pour ce groupe.
- `UNVERIFIED` : l’écriture des appartenances ou sa vérification n’a pas pu être confirmée ; contrôler le compte avant toute nouvelle tentative.

Une prévisualisation ou une demande rejetée avant soumission ne produit pas de ligne. Si l’enregistrement initial échoue, aucun accès n’est modifié. Si la finalisation de l’historique échoue après une attribution vérifiée, l’interface affiche un échec partiel avec la référence de l’opération et demande de contrôler l’historique, sans inviter à relancer l’attribution. Une ligne `REQUESTED` sans résultat final indique une opération à rapprocher des appartenances effectives. Les changements de groupes et l’historique ne constituent pas une transaction atomique DSS ; le journal structuré contient également l’identifiant de corrélation en cas de problème.

Le compte d’exécution de la webapp doit pouvoir écrire dans ce dataset. Réserver l’accès au dataset aux administrateurs chargés de la traçabilité. Ne pas lui appliquer de recette de reconstruction ou d’écriture en remplacement. Le verrou applicatif sérialise les soumissions au sein d’un processus ; utiliser un seul processus de backend pour les stockages fichiers. Pour plusieurs processus/instances, choisir un stockage SQL managé supportant les écritures concurrentes et vérifier cette configuration sur l’instance cible.

Le mode local conserve les événements uniquement en mémoire dans `DemoRepository.history`. Les tests couvrent l’ajout sans écrasement, le provisionnement sans remplacement, la corrélation multi-projets, l’absence de secrets, les demandes sans effet et les échecs partiels. Le code de création est fourni mais aucun dataset n’a été créé pendant cette préparation.

Références SDK : https://developer.dataiku.com/latest/concepts-and-examples/datasets/datasets-other.html et https://developer.dataiku.com/latest/concepts-and-examples/datasets/datasets-data.html.
