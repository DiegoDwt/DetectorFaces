import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import socket
import os

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000
BUFFER_SIZE = 4096

PROCESSED_DIR = Path("images/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Faces")
        self.root.geometry("520x650")
        self.root.configure(bg="#ecf0f1")

        self.image_path = None

        # Título estilizado
        self.title_label = tk.Label(
            root,
            text="Detector de Faces",
            font=("Helvetica", 20, "bold"),
            fg="#2c3e50",
            bg="#ecf0f1"
        )
        self.title_label.pack(pady=(20, 10))

        # Botão para selecionar imagem
        self.select_button = tk.Button(
            root,
            text="Selecionar Imagem",
            command=self.select_image,
            bg="#3498db",
            fg="white",
            font=("Arial", 11, "bold"),
            width=20,
            relief="raised"
        )
        self.select_button.pack(pady=10)

        # Área de visualização da imagem
        self.image_label = tk.Label(root, bg="#bdc3c7", relief="solid", bd=2, width=400, height=300)
        self.image_label.pack(pady=10)

        # Label para exibir nome do arquivo
        self.file_label = tk.Label(
            root,
            text="Nenhum arquivo selecionado.",
            font=("Arial", 10),
            fg="gray",
            bg="#ecf0f1"
        )
        self.file_label.pack()

        # Botão para enviar imagem
        self.send_button = tk.Button(
            root,
            text="Enviar e Processar",
            command=self.send_image,
            bg="#2ecc71",
            fg="white",
            font=("Arial", 11, "bold"),
            width=20,
            relief="raised"
        )
        self.send_button.pack(pady=20)

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Escolher imagem",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp")]
        )
        if not file_path:
            return

        self.image_path = Path(file_path)
        self.file_label.config(text=self.image_path.name)
        self.show_image()

    def show_image(self):
        img = Image.open(self.image_path)
        img.thumbnail((400, 300))
        photo = ImageTk.PhotoImage(img)
        self.image_label.configure(image=photo)
        self.image_label.image = photo

    def send_image(self):
        if not self.image_path:
            messagebox.showwarning("Atenção", "Selecione uma imagem primeiro.")
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SERVER_HOST, SERVER_PORT))
                s.sendall((1).to_bytes(4, 'big'))

                filename = self.image_path.name.encode()
                s.sendall(len(filename).to_bytes(4, 'big'))
                s.sendall(filename)

                with open(self.image_path, 'rb') as f:
                    file_data = f.read()
                    s.sendall(len(file_data).to_bytes(8, 'big'))
                    s.sendall(file_data)

                confirm_length = int.from_bytes(s.recv(4), 'big')
                confirm = s.recv(confirm_length).decode()

                if confirm != "PROCESSADO":
                    raise Exception(f"Resposta inválida do servidor: {confirm}")

                processed_size = int.from_bytes(s.recv(8), 'big')
                received_data = b''

                while len(received_data) < processed_size:
                    chunk = s.recv(min(BUFFER_SIZE, processed_size - len(received_data)))
                    if not chunk:
                        break
                    received_data += chunk

                save_path = PROCESSED_DIR / self.image_path.name
                with open(save_path, 'wb') as f:
                    f.write(received_data)

                messagebox.showinfo("Sucesso", f"Imagem processada salva em:\n{save_path}")
                self.image_path = save_path
                self.file_label.config(text=self.image_path.name)
                self.show_image()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha no processamento:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()
