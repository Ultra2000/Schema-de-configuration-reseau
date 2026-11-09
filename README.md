# PROJET : Générateur de schémas de configuration réseau

**GROUPE: SWEAT-POTATO**

**Membres :**
- _Ludolphe SAGBO_
- Fréjus BOURAIMA
- _Rayan Boudjemai_
- _Amsétou DIARRA_


Conception du projet

## Partie 1: noyau minimal et fonctionnalité

1. Permettre de créer un réseau et d'y ajouter des machines.
2. **Format du fichier de configuration** :
    * un fichier JSON unique décrit tout le réseau dont on veut le schéma (format détaillé plus bas) ;
    * types de machines autorisés : PC, serveur, routeur, switch ;
    * masque accepté sous les deux notations (/24 ou 255.255.255.0) ;
    * passerelle par défaut d'un hôte décrite comme une route vers 0.0.0.0/0 ;
    * liaisons physiques facultatives ;
    * fichier d'exemple fourni dans examples/ ;
    * dépend de #1
3. **Chargement du fichier de configuration** :
    * lecture du fichier JSON ;
    * création des machines avec leur nom et leur type ;
    * création des interfaces, avec conversion du masque en une forme unique ;
    * création des routes et des liaisons ;
    * message clair si le fichier est introuvable, mal formé ou s'il manque un champ obligatoire ;
    * dépend de #1, #2
4. **Validation des données** :
    * adresse IP et masque syntaxiquement valides ;
    * l'adresse n'est ni l'adresse réseau ni l'adresse de broadcast du sous-réseau ;
    * noms de machines et d'interfaces uniques ;
    * type de machine reconnu ;
    * l'interface de sortie d'une route existe sur la machine ;
    * la passerelle d'une route est joignable directement par l'interface indiquée ;
    * les deux extrémités d'une liaison existent ;
    * dépend de #3
5. **Analyse de topologie** :
    * calcul du sous-réseau de chaque interface à partir de son adresse et de son masque ;
    * regroupement des interfaces appartenant au même sous-réseau (liaisons déduites) ;
    * prise en compte des liaisons déclarées dans le fichier ;
    * repérage des routeurs comme points de passage entre sous-réseaux ;
    * dépend de #4
6. **Génération du schéma graphique** du réseau :
    * un nœud par machine, avec une forme différente selon le type ;
    * un nœud par sous-réseau (ex. 192.168.1.0/24) ;
    * une liaison entre chaque machine et son sous-réseau, étiquetée avec le nom de l'interface et l'adresse IP ;
    * disposition automatique des éléments ;
    * dépend de #5
7. **Export du schéma** :
    * formats PNG et SVG, PDF ;
    * choix du nom et de l'emplacement du fichier de sortie ;
    * dépend de #6
8. **Interface en ligne de commande** :
    * lancement avec un fichier de configuration et un fichier de sortie (python main.py examples/reseau_exemple.json -o schema.svg) ;
    * enchaînement chargement → validation → analyse → génération → export ;
    * affichage des erreurs de validation et arrêt si la configuration est invalide ;
    * dépend de #3, #4, #7


Comme fonctionnalités supplémentaires, on pourra considérer: 

9. **Détecter les conflits d'adresses IP** (même adresse sur deux interfaces).
    * modifier #4 pour ajouter un contrôle sur l'ensemble de la configuration
    * modifier #6 pour colorer en rouge les interfaces en conflit
    * dépend de #4
10. **Détecter les erreurs de routage** : passerelle injoignable, route vers un réseau inexistant, sous-réseau sans route de retour, boucle de routage. 
    * modifier #4 pour ajouter ces contrôles
    * modifier #8 pour afficher la liste des anomalies (avertissement / erreur)
    * dépend de #3, #5
11. **Personnaliser les couleurs et icônes** selon le type de machine, avec une légende. — **P2**
    * modifier #6 pour appliquer un style par type de machine
    * dépend de #6
12. **Améliorer l'organisation du schéma** : regrouper visuellement les machines par sous-réseau et choisir le type de disposition (hiérarchique ou libre).
    * modifier #6 pour créer des groupes par sous-réseau
    * modifier #8 pour ajouter une option de choix de disposition
    * dépend de #5, #6
13. **Afficher les détails d'une machine au survol** (interfaces, adresses, routes) dans l'export SVG. — **P2**
    * modifier #6 pour ajouter une infobulle à chaque machine
    * modifier #7 pour que cette infobulle soit conservée dans le SVG
    * dépend de #6, #7
14. **Générer le schéma du réseau local** sur lequel l'application est lancée. 
    * découverte de la machine locale : interfaces, adresses IP, masques et table de routage ;
    * identification de la passerelle par défaut, représentée comme un routeur ;
    * découverte des autres machines du sous-réseau :
        * lecture de la table ARP (machines avec lesquelles la machine locale a déjà communiqué) ;
        * en option, envoi d'un ping à chaque adresse du sous-réseau pour trouver les machines actives ;
        * résolution des noms d'hôtes quand c'est possible ;
    * génération d'un fichier de configuration au format de #2, qui peut être conservé et modifié ;
    * réutilisation de #3 à #7 pour valider, analyser et dessiner le réseau découvert ;
    * modifier #8 pour ajouter une option --local (et --scan pour le ping) ;
    * limites :
        * les switchs sont invisibles au niveau IP et ne peuvent pas être découverts ;
        * le type des machines découvertes est deviné (passerelle = routeur, autres = hôte) ;
        * les tables de routage des autres machines ne sont pas accessibles ;
        * le scan ne doit être lancé que sur un réseau dont on a l'autorisation ;
    * dépend de #1, #2, #3, #4, #5, #6, #7, #8
15. **Interface graphique** : ouvrir un fichier de configuration ou lancer la découverte locale, afficher le schéma et la liste des anomalies. — **P3**
    * réutilise #3 à #7 sans modification
    * dépend de #3, #4, #5, #6, #7


## Partie 2: Identifier les briques logicielles utilisables 

### Modules Python dans la bibliothèque standard
Ces modules sont fournis avec Python : aucune installation, compatibles Windows / Linux / macOS, maintenus par l'équipe de Python et documentés sur docs.python.org.

Ces modules sont fournis avec Python : aucune installation, compatibles Windows / Linux / macOS, maintenus par l'équipe de Python et documentés sur docs.python.org.
 
1. **ipaddress** : vérifie les adresses IPv4/IPv6, les masques et les sous-réseaux, indique si une adresse appartient à un réseau et liste les adresses d'un sous-réseau. Limite : il ne gère pas le routage ; la règle du préfixe le plus long et la détection de boucles sont à programmer.
    * #3, #4, #5, #9, #10, #14
2. **dataclasses** : déclaration concise des classes Machine, Interface, Route, Liaison, Reseau. Limite : aucune vérification des types à l'exécution, la validation reste à écrire.
    * #1
3. **json** : lire le fichier de configuration et écrire celui produit par la découverte locale. Simple à utiliser, mais ne valide pas automatiquement la structure des données.
    * #2, #3, #14
4. **pathlib** : gérer les chemins des fichiers de configuration et des images. Compatible Windows, Linux et macOS.
    * #3, #7
5. **logging** : enregistrer les erreurs et événements du programme. Utile pour le débogage, mais nécessite une configuration adaptée (niveaux, format).
    * utilisé par toutes les fonctionnalités
6. **argparse** : créer l'interface en ligne de commande (arguments, options --local, --scan, choix de disposition, aide automatique). Limite : interface uniquement textuelle.
    * #8, #12, #14
7. **subprocess** : exécuter les commandes système (ip addr, ip route, ip neigh, ping) et récupérer leur sortie. Limite : les commandes et leur format dépendent du système d'exploitation.
    * #14
8. **re** : vérifier le format des noms de machines et d'interfaces, et extraire les adresses et routes des sorties de commandes. Limite : les expressions régulières sont fragiles si le format de sortie change.
    * #4, #14
9. **socket** : retrouver le nom d'hôte de la machine locale et des machines découvertes (résolution DNS inverse). Limite : beaucoup de machines d'un réseau local n'ont pas de nom résolvable.
    * #14
10. **concurrent.futures** : lancer les pings en parallèle pour que le scan d'un sous-réseau /24 prenne quelques secondes au lieu de plusieurs minutes. Limite : trop de requêtes simultanées peuvent saturer le réseau ou être bloquées.
    * #14
11. **tkinter** : créer l'interface graphique sans dépendance externe. Limites : apparence datée ; sur certaines distributions Linux, il faut installer le paquet système python3-tk.
    * #15
12. **unittest** : tester les fonctionnalités du programme. Intégré à Python, il reste adapté même s'il est moins concis que certains modules tiers comme pytest.
    * tests de toutes les fonctionnalités



### Modules Python dans les bibliothèques tierces
1. **graphviz** : génère les schémas réseau et organise automatiquement les machines.
    * **Service rendu** : description des nœuds et liaisons, styles, regroupements, infobulles en SVG, export en PNG, SVG et PDF.
    * **Limites** : ne fait aucune analyse du réseau ; contrôle limité sur la position exacte des machines.
    * **Installation** : pip install graphviz et installation du logiciel Graphviz sur le système.
    * **Utilisation** : simple (créer un graphe, ajouter nœuds et arêtes, appeler render()).
    * **Maintenance, communauté, documentation** : projet ancien et maintenu, largement utilisé, documentation claire avec exemples.
    * #6, #7, #11, #12, #13
2. **NetworkX** : modélise, analyse et manipule des structures en forme de graphe (nœuds et liens).
    * **Service rendu** : représentation de la topologie, recherche de chemins, détection de cycles (boucles de routage) et de machines isolées.
    * **Limites** : ne connaît pas les notions IP ; ne produit pas à lui seul des images aussi abouties qu'un moteur graphique dédié.
    * **Installation** : pip install networkx, sans dépendance obligatoire.
    * **Utilisation** : API simple, nombreux exemples.
    * **Maintenance, communauté, documentation** : projet très actif, large communauté, documentation complète.
    * #5, #6, #10
3. **psutil** : récupérer les interfaces de la machine locale avec leurs adresses et masques.
    * **Service rendu** : liste des interfaces, adresses IP, masques et état (active ou non), de la même façon sur Windows, Linux et macOS.
    * **Limites** : ne donne ni la table de routage, ni la passerelle par défaut, ni la table ARP ; ces informations restent à obtenir avec les commandes système.
    * **Installation** : pip install psutil, paquets précompilés pour les systèmes courants.
    * **Utilisation** : simple (psutil.net_if_addrs()).
    * **Maintenance, communauté, documentation** : projet ancien, très utilisé et activement maintenu, documentation complète.
    * #14
4. **Scapy** (alternative étudiée pour #14) : construire et envoyer des paquets, notamment un scan ARP plus fiable que le ping, car beaucoup de machines bloquent le ping mais répondent toujours à l'ARP.
    * **Limites** : nécessite les droits administrateur ; installation plus lourde sous Windows (pilote Npcap).
    * **Maintenance, communauté, documentation** : projet actif et reconnu dans le domaine de la sécurité réseau, documentation correcte.
    * Non retenu pour l'instant à cause des droits administrateur ; pourra remplacer le ping si le temps le permet.
5. **pytest** (alternative à unittest) : écriture de tests plus courte et rapports plus lisibles. Installation via pip install pytest, projet très utilisé et bien documenté. Non indispensable au fonctionnement du programme.

**Choix retenus :** NetworkX pour l'analyse de la topologie et graphviz pour le rendu, ce qui sépare l'analyse du réseau de sa représentation graphique. Pour la découverte locale, psutil pour les interfaces et les commandes système pour les routes et la table ARP.


### Outils indépendants qui seront appelés par le programme
1. **Graphviz (logiciel système, commandes dot, neato, fdp)** : moteur appelé par le module Python graphviz pour calculer la disposition et produire les images. dot donne une disposition hiérarchique (routeurs en haut), neato et fdp une disposition libre. Installation obligatoire et séparée (apt install graphviz, installeur Windows, brew install graphviz).
    * #6, #7, #12
2. **iproute2 (ip addr, ip route, ip neigh)** : obtenir sous Linux la table de routage, la passerelle par défaut et la table ARP de la machine locale. Installé par défaut sur les distributions Linux. Sous Windows, les équivalents sont route print et arp -a, avec un format de sortie différent à analyser séparément.
    * #14
3. **ping** : tester si une adresse du sous-réseau répond. Présent sur tous les systèmes, mais les options diffèrent entre Linux (-c) et Windows (-n), et certaines machines (pare-feu Windows notamment) ne répondent pas au ping.
    * #14
4. **Git** : suivi des versions et travail en groupe. Outil de développement, non livré avec le programme.
 





