import subprocess
import sys

def install_requirements():
    print("Instalando dependencias...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    if result.returncode != 0:
        print("Error al instalar dependencias. Revisa requirements.txt.")
        sys.exit(1)

def run_dashboard():
    # Opcional: Cambia dashboard.py por el nombre de tu archivo principal
    subprocess.run(["streamlit", "run", "dashboard.py"]) 

if __name__ == "__main__":
    install_requirements()
    run_dashboard()
