import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from image_processor import process_image
import time

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
BUFFER_SIZE = 4096

RECEIVED_DIR = Path("images/received")
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

def handle_client(client_socket, address):
    print(f"[+] Conexão de {address}")

    try:
        # Recebe o número de arquivos
        num_files_data = client_socket.recv(4)
        if not num_files_data:
            print("[ERRO] Nenhum dado recebido.")
            return
        num_files = int.from_bytes(num_files_data, 'big')

        print(f"[INFO] Número de arquivos a receber: {num_files}")

        for _ in range(num_files):
            # Recebe o nome do arquivo
            filename_length = int.from_bytes(client_socket.recv(4), 'big')
            filename = client_socket.recv(filename_length).decode()
            save_path = RECEIVED_DIR / filename

            # Recebe o conteúdo do arquivo
            file_size = int.from_bytes(client_socket.recv(8), 'big')
            print(f"[INFO] Recebendo {filename} ({file_size} bytes)")

            file_data = b''
            while len(file_data) < file_size:
                chunk = client_socket.recv(min(BUFFER_SIZE, file_size - len(file_data)))
                if not chunk:
                    break
                file_data += chunk

            with open(save_path, 'wb') as f:
                f.write(file_data)

            print(f"[SUCESSO] {filename} salvo em {save_path}")

            # Processa a imagem
            process_image(str(save_path))
            print(f"[PROCESSADO] {filename} processado com sucesso")

            # Confirma e envia imagem processada de volta
            confirm_msg = "PROCESSADO".encode()
            
            # Primeiro envia o tamanho da mensagem de confirmação
            client_socket.send(len(confirm_msg).to_bytes(4, 'big'))
            # Envia a mensagem de confirmação
            client_socket.sendall(confirm_msg)

            # Envia a imagem processada
            with open(save_path, 'rb') as f:
                processed_data = f.read()
                # Envia o tamanho dos dados
                client_socket.send(len(processed_data).to_bytes(8, 'big'))
                # Envia os dados da imagem
                client_socket.sendall(processed_data)

    except Exception as e:
        print(f"[ERRO] {e}")
        try:
            error_msg = f"ERRO: {e}".encode()
            client_socket.send(len(error_msg).to_bytes(4, 'big'))
            client_socket.sendall(error_msg)
        except:
            pass
    finally:
        client_socket.close()
        print(f"[DESCONECTADO] {address}")

def start_server():
    print(f"[INICIANDO] Servidor escutando em {SERVER_HOST}:{SERVER_PORT}")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)

    with ThreadPoolExecutor() as executor:
        while True:
            client_socket, address = server_socket.accept()
            executor.submit(handle_client, client_socket, address)

if __name__ == "__main__":
    start_server()