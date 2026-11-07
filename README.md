# PROJET : Générateur de schémas de configuration réseau

** GROUPE: SWEAT-POTATO **

# Conception du projet

## Partie 1: noyau minimal et fonctionnalité

1. Ajouter une machine au réseau.
2. Saisie d'une machine avec son nom et son type (PC, serveur, routeur, switch).
    * dépend de #1
3. Saisie des interfaces d'une machine avec adresse IP et masque (/24 ou 255.255.255.0). 
    * dépend de #1,#2
4. Saisie de la table de routage d'un routeur (et de la passerelle par défaut d'un hôte).
    * dépend de #1,#2,#3
5. Sauvegarde et chargement d'une configuration au format Json
    * dépend de #1
6. Validation des données saisies:
    * adresse IP et masque syntaxiquement valide;
    * l'adresse n'est ni l'adresse réseau ni l'adresse de broadcast du sous réseau;
    * noms de machines et d'interfaces uniques;
    * l'interface de sortie d'une route existe sur la machine;
    * la passerelle d'une route est joignable directement par l'interface indiquée. 
    * dépend de #1,#3,#4
7. Analyse de topologie
    * regroupement des interfaces par sous-réseaux et prise en compte des liaisons déclarées par l'utilisateur.
    * * dépend de #3,#6
8. Générer le schéma graphique  du réseau
    * dépend de #7
9. Exporter le schéma au format image
    * dépend de #9

Comme fonctionnalités supplémentaires, on pourra considérer: 

10. Détecter les erreurs de configuration
    * dépend de #6
11. Détecter les conflits d'adresses IP
    * dépend de #6
12. Afficher les détails d'une machine au survol ou à la sélection 
    * dépend de #8
13. Personnaliser les couleurs et icônes selon le type de machine
    * dépend de #2,#8
14. Organiser automatiquement les machines sur le schéma
    * dépend de #8
15. 