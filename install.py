import subprocess
import sys

def install_dependencies():
    print("Installation des dépendances du projet...")

    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        "requirements.txt"
    ])

    print("Installation terminée !")

if __name__ == "__main__":
    install_dependencies() 