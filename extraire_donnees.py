"""Extrait les données utiles de la sortie de netlab et produit reseau.json.

Étape 1 de la chaîne :
    netlab create -o yaml:nodes=build/nodes.yml examples/trois_machines.yml
    python extraire_donnees.py build/nodes.yml build/reseau.json "Deux PC et un routeur"

Pour chaque machine, on ne garde que :
    - role         -> type de la machine (host, router, bridge)
    - device       -> modèle d'équipement (linux, frr...)
    - interfaces   -> nom (ifname), adresse IPv4 et voisins
    - routing.static -> routes statiques IPv4

Tout le reste est ignoré, en particulier la section "mgmt" : c'est l'interface
d'administration créée par netlab (192.168.121.x), qui ne fait pas partie du réseau.

Règle pour les topologies : chaque PC (role: host) doit déclarer sa route par
défaut dans routing.static. Sinon netlab ajoute ses propres routes vers ses plages
d'adresses internes, et rien ne permet de les distinguer des routes réelles.

"""

import json
import sys

import yaml


def lire_nodes(chemin):
    """Charge le fichier produit par netlab (dictionnaire {nom machine: données})."""
    try:
        with open(chemin, encoding="utf-8") as fichier:
            nodes = yaml.safe_load(fichier)
    except FileNotFoundError:
        sys.exit(f"Erreur : fichier introuvable : {chemin}")
    except yaml.YAMLError as erreur:
        sys.exit(f"Erreur : {chemin} n'est pas un YAML valide ({erreur})")

    if not isinstance(nodes, dict) or not nodes:
        sys.exit(f"Erreur : {chemin} ne contient aucune machine")
    return nodes


def extraire_interfaces(noeud):
    """Interfaces de données de la machine (sans l'interface d'administration)."""
    interfaces = []
    for interface in noeud.get("interfaces", []):
        ip = interface.get("ipv4")
        interfaces.append({
            "nom": interface["ifname"],
            # netlab met parfois ipv4: True (interface sans adresse propre) : on garde None.
            "ip": ip if isinstance(ip, str) else None,
            "voisins": [
                f"{voisin['node']}:{voisin['ifname']}"
                for voisin in interface.get("neighbors", [])
            ],
        })
    return interfaces


def extraire_routes(noeud):
    """Routes statiques IPv4 déclarées pour la machine."""
    routes = []
    for route in noeud.get("routing", {}).get("static", []):
        if "ipv4" not in route:
            continue  # route IPv6 : hors du périmètre du MVP
        nexthop = route.get("nexthop", {})
        routes.append({
            "destination": route["ipv4"],
            "passerelle": nexthop.get("ipv4"),  # None si route sans passerelle
            "interface": nexthop.get("intf"),
        })
    return routes


def extraire_reseau(nodes, nom):
    """Construit le dictionnaire au format reseau.json."""
    machines = {}
    for nom_machine, noeud in nodes.items():
        machines[nom_machine] = {
            "type": noeud.get("role", "router"),   # netlab : router par défaut
            "device": noeud.get("device"),
            "interfaces": extraire_interfaces(noeud),
            "routes": extraire_routes(noeud),
        }
    return {"nom": nom, "machines": machines}


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit("Utilisation : python extraire_donnees.py build/nodes.yml build/reseau.json [nom du réseau]")

    entree, sortie = sys.argv[1], sys.argv[2]
    nom = sys.argv[3] if len(sys.argv) == 4 else "Réseau"

    reseau = extraire_reseau(lire_nodes(entree), nom)

    with open(sortie, "w", encoding="utf-8") as fichier:
        json.dump(reseau, fichier, indent=2, ensure_ascii=False)

    nb_interfaces = sum(len(m["interfaces"]) for m in reseau["machines"].values())
    print(f"{sortie} : {len(reseau['machines'])} machines, {nb_interfaces} interfaces")


if __name__ == "__main__":
    main()