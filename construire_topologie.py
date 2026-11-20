
import json
import sys
import ipaddress


def lire_reseau(chemin):
    """
    Charge le fichier reseau.json et retourne son contenu.
    """
    try:
        with open(chemin, "r", encoding="utf-8") as fichier:
            reseau = json.load(fichier)

    except FileNotFoundError:
        raise ValueError(f"Fichier introuvable : {chemin}")

    except json.JSONDecodeError as erreur:
        raise ValueError(f"Fichier JSON invalide : {erreur}")

    if not isinstance(reseau, dict):
        raise ValueError("Le contenu du fichier doit être un objet JSON.")

    if not isinstance(reseau.get("machines"), dict):
        raise ValueError("Le champ 'machines' est absent ou invalide.")

    return reseau


def creer_noeuds_machines(machines):
    """
    Crée un nœud pour chaque machine du réseau.
    """
    noeuds = []

    for nom, machine in machines.items():
        noeuds.append({
            "id": f"machine:{nom}",
            "type": "machine",
            "nom": nom,
            "role": machine.get("type", "inconnu")
        })

    return noeuds


def calculer_sous_reseaux(machines):
    """
    Calcule le sous-réseau de chaque interface IPv4.

    Retourne :
    - les sous-réseaux uniques ;
    - les associations entre machines, interfaces et sous-réseaux.
    """
    sous_reseaux = {}
    associations = []

    for nom_machine, machine in machines.items():

        interfaces = machine.get("interfaces", [])

        for interface in interfaces:

            adresse = interface.get("ip")

            # Une interface sans adresse IPv4 ne permet pas
            # de déduire un sous-réseau.
            if not adresse:
                continue

            try:
                interface_ip = ipaddress.ip_interface(adresse)

            except ValueError:
                raise ValueError(
                    f"Adresse IPv4 invalide sur "
                    f"{nom_machine}/{interface.get('nom')} : {adresse}"
                )

            # Récupération du sous-réseau.
            cidr = str(interface_ip.network)

            # Un seul nœud est créé par sous-réseau.
            if cidr not in sous_reseaux:
                sous_reseaux[cidr] = {
                    "id": f"reseau:{cidr}",
                    "type": "sous-reseau",
                    "cidr": cidr
                }

            associations.append({
                "machine": nom_machine,
                "interface": interface.get("nom"),
                "ip": str(interface_ip),
                "sous_reseau": cidr
            })

    return sous_reseaux, associations


def creer_connexions_logiques(associations):
    """
    Relie chaque machine au sous-réseau de son interface.

    Une connexion logique est créée pour chaque interface IPv4.
    """
    connexions = []

    for association in associations:

        connexions.append({
            "source": f"machine:{association['machine']}",
            "cible": f"reseau:{association['sous_reseau']}",
            "type": "logique",
            "interface": association["interface"],
            "ip": association["ip"]
        })

    return connexions


def creer_connexions_physiques(machines):
    """
    Crée les connexions physiques déclarées par les voisins Netlab.

    Les liens sont dédupliqués : une liaison déclarée des deux côtés
    ne doit apparaître qu'une seule fois.
    """
    connexions = []
    liens_vus = set()

    for nom_machine, machine in machines.items():

        for interface in machine.get("interfaces", []):

            nom_interface = interface.get("nom")

            for voisin in interface.get("voisins", []):

                # Le format attendu est : machine:interface
                if not isinstance(voisin, str) or ":" not in voisin:
                    raise ValueError(
                        f"Voisin invalide sur "
                        f"{nom_machine}/{nom_interface} : {voisin}"
                    )

                nom_voisin, interface_distante = voisin.rsplit(":", 1)

                if not nom_voisin or not interface_distante:
                    raise ValueError(
                        f"Voisin incomplet sur "
                        f"{nom_machine}/{nom_interface} : {voisin}"
                    )

                # Vérification de l'existence de la machine distante.
                if nom_voisin not in machines:
                    raise ValueError(
                        f"Machine voisine inconnue : {nom_voisin}"
                    )

                # Vérification de l'existence de l'interface distante.
                interfaces_distantes = machines[nom_voisin].get(
                    "interfaces", []
                )

                interface_existe = any(
                    i.get("nom") == interface_distante
                    for i in interfaces_distantes
                )

                if not interface_existe:
                    raise ValueError(
                        f"Interface distante inconnue : "
                        f"{nom_voisin}/{interface_distante}"
                    )

                # Chaque extrémité est représentée par une paire.
                extremite_a = (nom_machine, nom_interface)
                extremite_b = (nom_voisin, interface_distante)

                # Le tri permet de reconnaître un même lien
                # même si Netlab le déclare dans les deux sens.
                cle_lien = tuple(sorted((extremite_a, extremite_b)))

                if cle_lien in liens_vus:
                    continue

                liens_vus.add(cle_lien)

                # On conserve le même ordre que celui de la clé.
                source, cible = cle_lien

                connexions.append({
                    "source": f"machine:{source[0]}",
                    "cible": f"machine:{cible[0]}",
                    "type": "physique",
                    "interface_locale": source[1],
                    "interface_distante": cible[1]
                })

    return connexions


def construire_topologie(reseau):
    """
    Assemble les nœuds et les connexions pour produire la topologie.
    """
    machines = reseau["machines"]

    # Création des nœuds représentant les machines.
    noeuds = creer_noeuds_machines(machines)

    # Calcul et création des nœuds représentant les sous-réseaux.
    sous_reseaux, associations = calculer_sous_reseaux(machines)

    noeuds.extend(sous_reseaux.values())

    # Création des deux catégories de connexions.
    connexions_logiques = creer_connexions_logiques(associations)
    connexions_physiques = creer_connexions_physiques(machines)

    connexions = connexions_logiques + connexions_physiques

    return {
        "nom": reseau.get("nom", "Réseau sans nom"),
        "noeuds": noeuds,
        "connexions": connexions
    }


def enregistrer_topologie(topologie, chemin):
    """
    Enregistre la topologie dans un fichier JSON.
    """
    with open(chemin, "w", encoding="utf-8") as fichier:
        json.dump(
            topologie,
            fichier,
            indent=4,
            ensure_ascii=False
        )


def main():
    """
    Point d'entrée du programme.
    """
    if len(sys.argv) != 2:
        print(
            "Utilisation : python construire_topologie.py reseau.json"
        )
        sys.exit(1)

    fichier_entree = sys.argv[1]
    fichier_sortie = "topologie.json"

    try:
        reseau = lire_reseau(fichier_entree)

        topologie = construire_topologie(reseau)

        enregistrer_topologie(topologie, fichier_sortie)

        print("Topologie construite avec succès.")
        print(f"Fichier généré : {fichier_sortie}")
        print(f"Nombre de nœuds : {len(topologie['noeuds'])}")
        print(f"Nombre de connexions : {len(topologie['connexions'])}")

    except (ValueError, OSError) as erreur:
        print(f"Erreur : {erreur}")
        sys.exit(1)


if __name__ == "__main__":
    main()
