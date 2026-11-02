# Gestion des habilitations

`main.py` assemble le service, le dépôt DSS et les callbacks sur l’instance Dash
fournie par Dataiku. `ui/` contient uniquement la présentation et les libellés.
`features/access/` définit les identifiants et les adaptateurs de callbacks.
`services/` porte l’autorisation, le classement et les aperçus signés ; ce code
ne dépend ni de Dash, ni de Flask, ni du SDK Dataiku. `repositories/dss.py`
est le seul point d’accès au SDK et conserve les paramètres utilisateur lors
d’un ajout de groupe. La politique administrative se trouve dans `config.py`.

Les callbacks sont enregistrés une fois au démarrage. Les données propres à
l’utilisateur sont transmises par requête ; aucune session utilisateur n’est
stockée dans des variables globales. Les verrous sont limités au processus ;
les écritures externes concurrentes doivent être coordonnées séparément.

Exécuter les tests sans connexion DSS depuis la racine de la bibliothèque :
`python -m unittest discover -s access_manager/tests -v`.
Les tests de câblage nécessitent Dash. Aucun test ne modifie une appartenance
réelle. Les limitations de Dataiku Cloud sur la sauvegarde des utilisateurs
restent applicables et aucune API de contournement n’est utilisée.
