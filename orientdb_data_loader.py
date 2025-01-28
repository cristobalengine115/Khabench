import os
import requests
import json
import base64
import csv

# Configuración de nodos y carpetas
nodes = {
    "1": "http://localhost:2480",
    "2": "http://localhost:2481",
    "3": "http://localhost:2482",
    "4": "http://localhost:2483"
}

orientdb_user = "root"
orientdb_password = "rootpwd"
orientdb_auth_header = base64.b64encode(f"{orientdb_user}:{orientdb_password}".encode()).decode()
orientdb_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {orientdb_auth_header}"
}

fragment_base_path = "./data/Fragmentos"

def create_orientdb_database(node_url, database):
    """Crea una base de datos en OrientDB si no existe."""
    print(f"Creando/verificando base de datos {database} en OrientDB ({node_url})...")
    response = requests.post(f"{node_url}/database/{database}/plocal", headers=orientdb_headers)
    if response.status_code == 200:
        print(f"Base de datos {database} creada exitosamente en OrientDB ({node_url}).")
    elif response.status_code == 409:
        print(f"Base de datos {database} ya existe en OrientDB ({node_url}).")
    else:
        print(f"Error al crear la base de datos {database} en OrientDB: {response.text}")

def ensure_orientdb_class(node_url, database, class_name):
    """Crea una clase en OrientDB si no existe."""
    response = requests.post(
        f"{node_url}/command/{database}/sql",
        headers=orientdb_headers,
        data=json.dumps({"command": f"SELECT FROM (SELECT expand(classes) FROM metadata:schema) WHERE name = '{class_name}'"})
    )
    if response.status_code == 200 and response.json().get("result"):
        print(f"Clase {class_name} ya existe en OrientDB ({node_url}).")
    else:
        response = requests.post(
            f"{node_url}/command/{database}/sql",
            headers=orientdb_headers,
            data=json.dumps({"command": f"CREATE CLASS {class_name} EXTENDS V"})
        )
        if response.status_code == 200:
            print(f"Clase {class_name} creada exitosamente en OrientDB ({node_url}).")
        else:
            print(f"Error al crear la clase {class_name} en OrientDB: {response.text}")

def csv_to_json(file_path):
    """Convierte un archivo CSV en una lista de objetos JSON."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as file:
        delimiter = '|' if file_path.endswith("RESEÑAS.csv") else ','
        reader = csv.DictReader(file, delimiter=delimiter)
        for row in reader:
            data.append(row)
    return data

def load_to_orientdb(node_url, database, file_path, class_name):
    """Carga datos a OrientDB desde un archivo."""
    ensure_orientdb_class(node_url, database, class_name)
    data = []
    if file_path.endswith('.csv'):
        data = csv_to_json(file_path)
    else:
        with open(file_path, 'r') as file:
            data = [json.loads(line.strip()) for line in file if line.strip()]

    for document in data:
        response = requests.post(
            f"{node_url}/command/{database}/sql",
            headers=orientdb_headers,
            data=json.dumps({"command": f"INSERT INTO {class_name} CONTENT {json.dumps(document)}"})
        )
        if response.status_code == 200:
            print(f"Documento insertado en {class_name} en OrientDB ({node_url}).")
        else:
            print(f"Error al insertar en OrientDB: {response.text} (status: {response.status_code})")

def process_orient_fragments():
    """Procesa y carga todos los fragmentos en OrientDB."""
    for fragment_id, node_url in nodes.items():
        fragment_path = os.path.join(fragment_base_path, fragment_id)
        if not os.path.exists(fragment_path):
            print(f"Carpeta {fragment_path} no encontrada. Skipping...")
            continue

        create_orientdb_database(node_url, "khabench")

        print(f"Cargando datos del fragmento {fragment_id} a través del nodo {node_url}...")

        for root, _, files in os.walk(fragment_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file.startswith("RESEÑAS"):
                    load_to_orientdb(node_url, "khabench", file_path, "Resenas")
                elif file.startswith("CLIENTES"):
                    load_to_orientdb(node_url, "khabench", file_path, "Clientes")
                elif file.startswith("ORDENES"):
                    load_to_orientdb(node_url, "khabench", file_path, "Ordenes")
                elif file.startswith("post_hasCreator_person"):
                    load_to_orientdb(node_url, "khabench", file_path, "HasCreator")
                else:
                    print(f"Archivo {file} no reconocido para carga automática en OrientDB.")

if __name__ == "__main__":
    process_orient_fragments()
