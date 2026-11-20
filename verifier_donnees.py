"""Vérifie la cohérence d'un réseau décrit dans reseau.json."""

import json
import sys
import ipaddress


def lire_reseau(chemin):
    """Charge le fichier JSON."""
    try:
        with open(chemin, encoding="utf-8") as fichier:
            reseau = json.load(fichier)
    except FileNotFoundError:
        print(f"ERREUR : fichier introuvable : {chemin}")
        return None
    except json.JSONDecodeError as erreur:
        print(f"ERREUR : JSON invalide : {erreur}")
        return None

    if not isinstance(reseau, dict):
        print("ERREUR : le contenu JSON doit être un objet.")
        return None

    if not isinstance(reseau.get("machines"), dict):
        print("ERREUR : champ 'machines' absent ou invalide.")
        return None

    return reseau


def verifier_reseau(reseau):
    """Effectue les contrôles de cohérence du réseau."""

    erreurs = []
    machines = reseau["machines"]

    interfaces = {}
    adresses = {}
    sous_reseaux = set()

    # 1. Vérification des interfaces et des adresses IP
    for nom_machine, machine in machines.items():

        if not isinstance(machine, dict):
            erreurs.append(f"{nom_machine} : données machine invalides.")
            continue

        interfaces[nom_machine] = {}

        for interface in machine.get("interfaces", []):
            nom_interface = interface.get("nom")

            if not nom_interface:
                erreurs.append(
                    f"{nom_machine} : interface sans nom."
                )
                continue

            if nom_interface in interfaces[nom_machine]:
                erreurs.append(
                    f"{nom_machine} : interface {nom_interface} "
                    "déclarée plusieurs fois."
                )
                continue

            ip = interface.get("ip")

            if not ip:
                erreurs.append(
                    f"{nom_machine}:{nom_interface} : adresse IP absente."
                )
                interfaces[nom_machine][nom_interface] = {
                    "ip": None,
                    "reseau": None,
                    "donnees": interface
                }
                continue

            try:
                adresse = ipaddress.ip_interface(ip)

                if adresse.version != 4:
                    raise ValueError("IPv4 uniquement")

                reseau_ip = adresse.network

            except ValueError:
                erreurs.append(
                    f"{nom_machine}:{nom_interface} : "
                    f"adresse IP ou masque invalide ({ip})."
                )
                interfaces[nom_machine][nom_interface] = {
                    "ip": None,
                    "reseau": None,
                    "donnees": interface
                }
                continue

            # Vérification adresse réseau et broadcast
            if adresse.ip == reseau_ip.network_address:
                erreurs.append(
                    f"{nom_machine}:{nom_interface} : "
                    f"{ip} est une adresse réseau."
                )

            if adresse.ip == reseau_ip.broadcast_address:
                erreurs.append(
                    f"{nom_machine}:{nom_interface} : "
                    f"{ip} est une adresse de broadcast."
                )

            # Détection des IP dupliquées
            adresse_str = str(adresse.ip)

            if adresse_str in adresses:
                autre = adresses[adresse_str]
                erreurs.append(
                    f"IP dupliquée {adresse_str} : "
                    f"{autre} et {nom_machine}:{nom_interface}."
                )
            else:
                adresses[adresse_str] = (
                    f"{nom_machine}:{nom_interface}"
                )

            sous_reseaux.add(reseau_ip)

            interfaces[nom_machine][nom_interface] = {
                "ip": adresse,
                "reseau": reseau_ip,
                "donnees": interface
            }

    # 2. Vérification des liens entre interfaces
    liens_verifies = set()

    for nom_machine, machine in machines.items():

        for nom_interface, infos in interfaces.get(
            nom_machine, {}
        ).items():

            interface = infos["donnees"]

            for voisin in interface.get("voisins", []):

                try:
                    machine_voisine, interface_voisine = voisin.split(":", 1)
                except ValueError:
                    erreurs.append(
                        f"{nom_machine}:{nom_interface} : "
                        f"format de voisin invalide ({voisin})."
                    )
                    continue

                identifiant = tuple(sorted([
                    f"{nom_machine}:{nom_interface}",
                    f"{machine_voisine}:{interface_voisine}"
                ]))

                if identifiant in liens_verifies:
                    continue

                liens_verifies.add(identifiant)

                if machine_voisine not in machines:
                    erreurs.append(
                        f"{nom_machine}:{nom_interface} : "
                        f"machine voisine inconnue ({machine_voisine})."
                    )
                    continue

                infos_voisin = interfaces.get(
                    machine_voisine, {}
                ).get(interface_voisine)

                if infos_voisin is None:
                    erreurs.append(
                        f"{nom_machine}:{nom_interface} : "
                        f"interface voisine inexistante "
                        f"({voisin})."
                    )
                    continue

                reseau_local = infos["reseau"]
                reseau_distant = infos_voisin["reseau"]

                if reseau_local is None or reseau_distant is None:
                    continue

                if reseau_local != reseau_distant:
                    erreurs.append(
                        f"Lien {nom_machine}:{nom_interface} "
                        f"<-> {voisin} : les interfaces ne sont "
                        "pas dans le même sous-réseau "
                        f"({reseau_local} / {reseau_distant})."
                    )

    # 3. Vérification des routes
    routes_par_machine = {}

    for nom_machine, machine in machines.items():

        routes = machine.get("routes", [])
        routes_par_machine[nom_machine] = []

        for route in routes:

            destination = route.get("destination")
            passerelle = route.get("passerelle")
            nom_interface = route.get("interface")

            try:
                reseau_destination = ipaddress.ip_network(
                    destination, strict=False
                )

                if reseau_destination.version != 4:
                    raise ValueError("IPv4 uniquement")

            except (ValueError, TypeError):
                erreurs.append(
                    f"{nom_machine} : destination de route "
                    f"invalide ({destination})."
                )
                continue

            routes_par_machine[nom_machine].append(
                reseau_destination
            )

            # Vérifier l'existence de l'interface de sortie
            if not nom_interface:
                erreurs.append(
                    f"{nom_machine} : interface de sortie "
                    f"absente pour la route {destination}."
                )
                continue

            infos_interface = interfaces.get(
                nom_machine, {}
            ).get(nom_interface)

            if infos_interface is None:
                erreurs.append(
                    f"{nom_machine} : route vers {destination}, "
                    f"interface inexistante ({nom_interface})."
                )
                continue

            # Vérifier la passerelle
            if passerelle is not None:

                try:
                    ip_passerelle = ipaddress.ip_address(
                        passerelle
                    )

                    if ip_passerelle.version != 4:
                        raise ValueError("IPv4 uniquement")

                except ValueError:
                    erreurs.append(
                        f"{nom_machine}:{nom_interface} : "
                        f"passerelle invalide ({passerelle})."
                    )
                    continue

                reseau_interface = infos_interface["reseau"]

                if reseau_interface is not None:
                    if ip_passerelle not in reseau_interface:
                        erreurs.append(
                            f"{nom_machine}:{nom_interface} : "
                            f"passerelle {passerelle} non joignable "
                            f"directement (interface dans "
                            f"{reseau_interface})."
                        )

    # 4. Vérification des routes des routeurs
    for nom_machine, machine in machines.items():

        if machine.get("type") != "router":
            continue

        reseaux_directs = {
            infos["reseau"]
            for infos in interfaces.get(nom_machine, {}).values()
            if infos["reseau"] is not None
        }

        for reseau in sous_reseaux:

            # Un réseau directement connecté ne nécessite
            # pas de route statique.
            if reseau in reseaux_directs:
                continue

            # Chercher une route qui couvre ce réseau.
            route_trouvee = any(
                reseau.subnet_of(route)
                for route in routes_par_machine[nom_machine]
            )

            if not route_trouvee:
                erreurs.append(
                    f"{nom_machine} : aucune route vers "
                    f"le réseau {reseau} (réseau distant "
                    "potentiellement inaccessible)."
                )

    return erreurs


def main():

    if len(sys.argv) != 2:
        print(
            "Utilisation : python verifier_donnees.py reseau.json"
        )
        sys.exit(1)

    reseau = lire_reseau(sys.argv[1])

    if reseau is None:
        sys.exit(1)

    erreurs = verifier_reseau(reseau)

    if erreurs:
        print("\nERREURS DE CONFIGURATION :\n")

        for erreur in erreurs:
            print(f"- {erreur}")

        print(f"\n{len(erreurs)} erreur(s) détectée(s).")
        sys.exit(1)

    print("Configuration réseau valide !")
    sys.exit(0)


if __name__ == "__main__":
    main()
