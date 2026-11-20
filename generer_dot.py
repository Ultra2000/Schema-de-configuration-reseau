"""Produit un fichier Graphviz (DOT) à partir de topologie.json.

Étape 4 de la chaîne :
    python generer_dot.py build/topologie.json build/schema.dot
    dot -Tpng build/schema.dot -o build/schema.png

Contenu du schéma :
    - une icône par machine selon son type (dossier icones/) ;
    - un nœud par sous-réseau ;
    - un trait entre chaque machine et son sous-réseau, avec l'interface et l'adresse IP.
    - la table de routage sous chaque routeur qui en a une.

Format d'entrée : celui produit par construire_topologie.py
    noeuds     : {"id", "type": "machine", "nom", "role", "routes"}
                 {"id", "type": "sous-reseau", "cidr"}
    connexions : {"source", "cible", "type": "logique", "interface", "ip"}
                 {"source", "cible", "type": "physique", ...}

Seules les connexions "logique" sont dessinées : les connexions "physique" décrivent
les mêmes câbles, les dessiner aussi ferait apparaître chaque connexion en double.
"""

import html
import json
import sys
from pathlib import Path


DOSSIER_ICONES = Path(__file__).resolve().parent / "icones"
ICONES = {
    "host": "pc.png",
    "server": "serveur.png",
    "router": "routeur.png",
    "bridge": "switch.png",
}


def texte_dot(texte):
    """Met un texte entre guillemets pour DOT (échappe \\ et ", retour à la ligne -> \\n)."""
    texte = str(texte).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + texte + '"'


def lire_topologie(chemin):
    try:
        with open(chemin, encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        sys.exit(f"Erreur : fichier introuvable : {chemin}")
    except json.JSONDecodeError as erreur:
        sys.exit(f"Erreur : {chemin} n'est pas un JSON valide ({erreur})")


def ligne_noeud(noeud):
    """Une ligne DOT pour une machine ou un sous-réseau."""
    identifiant = texte_dot(noeud["id"])

    if noeud["type"] == "sous-reseau":
        style = 'shape=box, style="rounded,dashed", color=gray40, fontcolor=gray20'
        return f'  {identifiant} [label={texte_dot(noeud["cidr"])}, {style}];'

    icone = ICONES.get(noeud.get("role"))
    if icone is None:
        
        return f'  {identifiant} [label={texte_dot(noeud["nom"])}, shape=box];'

  
    chemin = html.escape((DOSSIER_ICONES / icone).as_posix())
    nom = html.escape(noeud["nom"])
    label = (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'
        f'<TR><TD FIXEDSIZE="TRUE" WIDTH="56" HEIGHT="56"><IMG SRC="{chemin}" SCALE="TRUE"/></TD></TR>'
        f"<TR><TD>{nom}</TD></TR>"
        + table_routage(noeud)
        + "</TABLE>>"
    )
    return f"  {identifiant} [label={label}, shape=plain];"


def table_routage(noeud):
    """Table de routage affichée sous un routeur (ligne HTML vide sinon).

    Seuls les routeurs l'affichent : la route par défaut des PC alourdirait
    le schéma sans rien apprendre de plus.
    """
    routes = noeud.get("routes", [])
    if noeud.get("role") != "router" or not routes:
        return ""

    def cellule(texte, gras=False):
        texte = html.escape(texte or "-")
        if gras:
            texte = f"<B>{texte}</B>"
        return f'<TD ALIGN="LEFT"><FONT POINT-SIZE="9">{texte}</FONT></TD>'

    lignes = ["<TR>" + cellule("Destination", True) + cellule("Passerelle", True)
              + cellule("Interface", True) + "</TR>"]
    for route in routes:
        destination = "défaut" if route["destination"] == "0.0.0.0/0" else route["destination"]
        lignes.append(
            "<TR>"
            + cellule(destination)
            + cellule(route.get("passerelle") or "directe")
            + cellule(route.get("interface") or "")
            + "</TR>"
        )

    tableau = (
        '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" '
        'COLOR="gray50" BGCOLOR="#FFF8EE">' + "".join(lignes) + "</TABLE>"
    )
    return f"<TR><TD>{tableau}</TD></TR>"


def ordonner_liens(noeuds, liens):
    """Oriente chaque lien de gauche à droite, dans l'ordre d'un parcours du réseau.

    Dans DOT (avec rankdir=LR), le premier nœud d'un lien est placé à gauche du second.
    On part de la première machine et on avance de voisin en voisin
    (parcours en largeur) : pc1 -> son réseau -> routeur -> autre réseau -> pc2.
    Le schéma suit ainsi le chemin réseau, de gauche à droite.

    Renvoie une liste de (gauche, droite, lien).
    """
    voisins = {}
    for lien in liens:
        voisins.setdefault(lien["source"], []).append((lien["cible"], lien))
        voisins.setdefault(lien["cible"], []).append((lien["source"], lien))

    ordonnes, visites, places = [], set(), set()
    for depart in (n["id"] for n in noeuds):   # boucle : gère aussi les morceaux isolés
        if depart in visites:
            continue
        visites.add(depart)
        file = [depart]
        while file:
            courant = file.pop(0)
            for voisin, lien in voisins.get(courant, []):
                if id(lien) in places:
                    continue
                places.add(id(lien))
                ordonnes.append((courant, voisin, lien))
                if voisin not in visites:
                    visites.add(voisin)
                    file.append(voisin)
    return ordonnes


def ligne_lien(haut, bas, lien):
    """Une ligne DOT pour un lien machine -- sous-réseau, étiqueté interface + IP.

    Un switch n'a ni interface ni IP sur ce lien : le trait est alors sans étiquette.
    """
    morceaux = [lien.get("interface"), lien.get("ip")]
    etiquette = texte_dot("\n".join(m for m in morceaux if m))
    return f"  {texte_dot(haut)} -- {texte_dot(bas)} [label={etiquette}];"


def generer_dot(topologie):
    liens = [c for c in topologie["connexions"] if c["type"] == "logique"]

    lignes = [
        "graph reseau {",
        f'  label={texte_dot(topologie.get("nom", "Réseau"))};',
        "  labelloc=t;",
        "  rankdir=LR;   // disposition en paysage : de gauche à droite",
        "  dpi=150;      // résolution du PNG : petits textes nets",
        '  fontname="Helvetica"; node [fontname="Helvetica"]; edge [fontname="Helvetica", fontsize=10];',
        "",
    ]
    lignes += [ligne_noeud(noeud) for noeud in topologie["noeuds"]]
    lignes.append("")
    lignes += [
        ligne_lien(haut, bas, lien)
        for haut, bas, lien in ordonner_liens(topologie["noeuds"], liens)
    ]
    lignes.append("}")
    return "\n".join(lignes) + "\n"


def main():
    if len(sys.argv) != 3:
        sys.exit("Utilisation : python generer_dot.py build/topologie.json build/schema.dot")

    entree, sortie = sys.argv[1], sys.argv[2]
    dot = generer_dot(lire_topologie(entree))

    with open(sortie, "w", encoding="utf-8") as fichier:
        fichier.write(dot)
    print(f"{sortie} écrit. Pour l'image : dot -Tpng {sortie} -o schema.png")


if __name__ == "__main__":
    main()