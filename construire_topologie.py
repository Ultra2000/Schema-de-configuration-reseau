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
            "role": machine.get("type", "inconnu"),

            "routes": machine.get("routes", [])
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

            if not adresse:
                continue

            try:
                interface_ip = ipaddress.ip_interface(adresse)

            except ValueError:
                raise ValueError(
                    f"Adresse IPv4 invalide sur "
                    f"{nom_machine}/{interface.get('nom')} : {adresse}"
                )

            cidr = str(interface_ip.network)

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


def creer_connexions_switchs(machines, associations):
    """
    Relie chaque switch au sous-réseau des machines branchées sur lui.

    Un switch n'a pas d'adresse IP : il n'apparaît donc dans aucune
    association. On retrouve son sous-réseau grâce à ses voisins.
    Une seule connexion est créée par switch et par sous-réseau.
    """

    sous_reseau_de = {
        (a["machine"], a["interface"]): a["sous_reseau"]
        for a in associations
    }

    connexions = []

    for nom_machine, machine in machines.items():

        if machine.get("type") != "bridge":
            continue

        deja_relies = set()

        for interface in machine.get("interfaces", []):

            if interface.get("nom", "").startswith("vlan"):
                continue

            for voisin in interface.get("voisins", []):

                nom_voisin, _, interface_voisine = voisin.rpartition(":")
                cidr = sous_reseau_de.get((nom_voisin, interface_voisine))

                if cidr is None or cidr in deja_relies:
                    continue

                deja_relies.add(cidr)

                connexions.append({
                    "source": f"machine:{nom_machine}",
                    "cible": f"reseau:{cidr}",
                    "type": "logique",
                    "interface": None,
                    "ip": None
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

    switchs = {
        nom for nom, machine in machines.items()
        if machine.get("type") == "bridge"
    }

    for nom_machine, machine in machines.items():

        for interface in machine.get("interfaces", []):

            nom_interface = interface.get("nom")
            voisins = interface.get("voisins", [])

            if str(nom_interface).startswith("vlan"):
                continue

            if machine.get("type") != "bridge" and any(
                isinstance(v, str) and v.rpartition(":")[0] in switchs
                for v in voisins
            ):
                continue

            for voisin in voisins:

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

                if nom_voisin not in machines:
                    raise ValueError(
                        f"Machine voisine inconnue : {nom_voisin}"
                    )

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

                extremite_a = (nom_machine, nom_interface)
                extremite_b = (nom_voisin, interface_distante)

                cle_lien = tuple(sorted((extremite_a, extremite_b)))

                if cle_lien in liens_vus:
                    continue

                liens_vus.add(cle_lien)

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

    noeuds = creer_noeuds_machines(machines)

    sous_reseaux, associations = calculer_sous_reseaux(machines)

    noeuds.extend(sous_reseaux.values())

    connexions_logiques = (
        creer_connexions_logiques(associations)
        + creer_connexions_switchs(machines, associations)
    )
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
    if len(sys.argv) not in (2, 3):
        print(
            "Utilisation : python construire_topologie.py "
            "reseau.json [topologie.json]"
        )
        sys.exit(1)

    fichier_entree = sys.argv[1]

    fichier_sortie = sys.argv[2] if len(sys.argv) == 3 else "topologie.json"

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