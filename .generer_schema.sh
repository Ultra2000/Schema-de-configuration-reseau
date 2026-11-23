#!/bin/bash
# Utilisation : ./generer_schema.sh network_config.yml
# Resultat    : build/schema.png

if [ -z "$1" ]; then
    echo "Utilisation : ./generer_schema.sh network_config.yml"
    exit 1
fi

mkdir -p build

# Etape 1 : netlab -> reseau.json (adapter cette ligne si la commande est differente)
python extraire_donnees.py "$1" build/reseau.json || exit 1

# Etape 2 : verification (on s'arrete s'il y a des erreurs)
python verifier_donnees.py build/reseau.json || exit 1

# Etape 3 : topologie
python construire_topologie.py build/reseau.json build/topologie.json || exit 1

# Etape 4 : fichier Graphviz
python generer_dot.py build/topologie.json build/schema.dot || exit 1

# Etape 5 : image PNG
dot -Tpng build/schema.dot -o build/schema.png || exit 1

echo "Schema genere : build/schema.png"