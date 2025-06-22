import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import socket
import threading
import json
import os
from datetime import datetime

class IRCClient:
    def __init__(self, root):
        self.root = root
        self.root.title("XDchat")
        
        # Настройки по умолчанию
        self.default_settings = {
            "nickname": "XDchatUser" + str(os.getpid())[-4:],  # Уникальный ник
            "channel": "#XDchatOnly",
            "server": "irc.libera.chat",
            "port": 6667
        }
        
        # Текущие настройки
        self.settings_file = "XDchatSettingsSave.txt"
        self.settings = self.load_settings()
        
        # Состояние клиента
        self.connected = False
        self.socket = None
        self.receive_thread = None
        
        # Создание интерфейса
        self.create_ui()
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        """Загрузка настроек из файла"""
        settings = self.default_settings.copy()
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    for line in f:
                        if ":" in line:
                            key, value = line.strip().split(":", 1)
                            settings[key.strip()] = value.strip()
        except Exception as e:
            self.log_message(f"Ошибка загрузки настроек: {e}")
        return settings

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(self.settings_file, "w") as f:
                f.write(f"nickname: {self.settings['nickname']}\n")
                f.write(f"channel: {self.settings['channel']}\n")
                f.write(f"server: {self.settings['server']}\n")
                f.write(f"port: {self.settings['port']}\n")
                f.write(f"last_updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            self.log_message(f"Ошибка сохранения настроек: {e}")

    def create_ui(self):
        """Создание пользовательского интерфейса"""
        # Меню
        menubar = tk.Menu(self.root)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Изменить имя пользователя", command=self.change_nickname)
        settings_menu.add_command(label="Изменить канал", command=self.change_channel)
        settings_menu.add_separator()
        settings_menu.add_command(label="Показать текущие настройки XDchat", command=self.show_settings)
        menubar.add_cascade(label="Настройки", menu=settings_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О XDchat", command=self.show_about)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        
        self.root.config(menu=menubar)
        
        # Лог чата
        self.chat_log = scrolledtext.ScrolledText(
            self.root, 
            state='disabled',
            height=20,
            width=70,
            wrap=tk.WORD,
            font=('Courier New', 10)
        )
        self.chat_log.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        
        # Панель ввода
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5, fill=tk.X)
        
        self.message_entry = tk.Entry(
            input_frame,
            font=('Arial', 12)
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", self.send_message)
        
        self.send_button = tk.Button(
            input_frame,
            text="Отправить",
            command=self.send_message
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # Панель статуса
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=5, fill=tk.X)
        
        self.connect_button = tk.Button(
            status_frame,
            text="Подключиться",
            command=self.toggle_connection,
            bg="#d4edda"
        )
        self.connect_button.pack(side=tk.LEFT)
        
        self.status_label = tk.Label(
            status_frame,
            text=f"Имя пользователя: {self.settings['nickname']} | Имя канала: {self.settings['channel']} | Отключен",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def change_nickname(self):
        """Изменение ника пользователя"""
        if self.connected:
            messagebox.showwarning("Упс...", "Отключитесь от сервера что бы сменить имя пользователя")
            return
            
        new_nick = simpledialog.askstring(
            "Изменение ника",
            "Введите новый ник:",
            initialvalue=self.settings['nickname'],
            parent=self.root
        )
        
        if new_nick and new_nick != self.settings['nickname']:
            self.settings['nickname'] = new_nick
            self.save_settings()
            self.status_label.config(
                text=f"Имя поьзователя: {self.settings['nickname']} | Имя канала: {self.settings['channel']} | Отключен"
            )
            messagebox.showinfo("Успех", f"Ник изменен на: {new_nick}")

    def change_channel(self):
        """Изменение канала"""
        if self.connected:
            messagebox.showwarning("Упс...", "Отключитесь от текущего серера что бы изменить канал")
            return
            
        new_channel = simpledialog.askstring(
            "Изменение канала",
            "Введите новый канал (начинается с #):",
            initialvalue=self.settings['channel'],
            parent=self.root
        )
        
        if new_channel and new_channel != self.settings['channel']:
            self.settings['channel'] = new_channel
            self.save_settings()
            self.status_label.config(
                text=f"Имя пользователя: {self.settings['nickname']} | Имя канала: {self.settings['channel']} | Отключен"
            )
            messagebox.showinfo("Успех", f"Канал изменен на: {new_channel}")

    def show_settings(self):
        """Показать текущие настройки"""
        settings_info = (
            f"Текущие настройки XDchat:\n\n"
            f"Имя пользователя: {self.settings['nickname']}\n"
            f"Текущий канал: {self.settings['channel']}\n"
            f"Подключаемый сервер: {self.settings['server']}\n"
            f"Порт: {self.settings['port']}\n\n"
            f"Файл настроек XDchat: {os.path.abspath(self.settings_file)}"
        )
        messagebox.showinfo("Настройки", settings_info)

    def show_about(self):
        """Показать информацию о программе"""
        about_info = (
            "XDchat 1.0 \n\n"
            "Возможности клиента:\n"
            "- Сохранения настроек в файл\n"
            "- Изменения ника и канала\n"
            "- Подключения к IRC-серверам\n\n"
            "Использует стандартные библиотеки Python"
        )
        messagebox.showinfo("О программе", about_info)

    def toggle_connection(self):
        """Подключение/отключение от сервера"""
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Подключемся к серверу..."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.settings['server'], int(self.settings['port'])))
            
            # Регистрация на сервере
            self.socket.send(f"NICK {self.settings['nickname']}\r\n".encode())
            self.socket.send(f"USER {self.settings['nickname']} 0 * :Python IRC Client\r\n".encode())
            self.socket.send(f"JOIN {self.settings['channel']}\r\n".encode())
            
            self.connected = True
            self.connect_button.config(text="Отключиться", bg="#f8d7da")
            self.status_label.config(
                text=f"Ник: {self.settings['nickname']} | Канал: {self.settings['channel']} | Подключен"
            )
            
            # Поток для приема сообщений
            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()
            
            self.log_message(f"=== Подключено к {self.settings['server']}:{self.settings['port']} ===")
            self.log_message(f"Ник: {self.settings['nickname']}")
            self.log_message(f"Канал: {self.settings['channel']}")
            
        except Exception as e:
            messagebox.showerror("Хоба!", f"Не удалось подключится к серверу!: {str(e)}")
            if self.socket:
                self.socket.close()
                self.socket = None

    def disconnect(self):
        """Отключение от сервера"""
        if not self.connected:
            return
            
        try:
            self.socket.send("QUIT :Python IRC Client\r\n".encode())
            self.socket.close()
        except:
            pass
            
        self.connected = False
        self.socket = None
        self.connect_button.config(text="Подключиться", bg="#d4edda")
        self.status_label.config(
            text=f"Ник: {self.settings['nickname']} | Канал: {self.settings['channel']} | Отключен"
        )
        self.log_message("=== Вы отключились от сервера ===")

    def receive_messages(self):
        """Получение сообщений от сервера"""
        while self.connected:
            try:
                data = self.socket.recv(2048).decode('utf-8', errors='ignore')
                if not data:
                    break
                    
                for line in data.split('\n'):
                    line = line.strip()
                    if line:
                        self.log_message(line)
                        
                        # Обработка PING (обязательно для поддержания соединения)
                        if line.startswith("PING"):
                            self.socket.send(f"PONG {line[5:]}\r\n".encode())
                            
            except Exception as e:
                self.log_message(f"Ошибка: {str(e)}")
                break
                
        self.disconnect()

    def send_message(self, event=None):
        """Отправка сообщения в канал"""
        if not self.connected:
            messagebox.showwarning("Ой... Вы еще не подключены", "Сначала подключитесь к серверу")
            return
            
        message = self.message_entry.get().strip()
        if message:
            try:
                self.socket.send(f"PRIVMSG {self.settings['channel']} :{message}\r\n".encode())
                self.log_message(f"<{self.settings['nickname']}> {message}")
                self.message_entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Ошибка отправки: {str(e)}")

    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, message + "\n")
        self.chat_log.config(state='disabled')
        self.chat_log.see(tk.END)

    def on_closing(self):
        """Обработка закрытия окна"""
        self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = IRCClient(root)
    root.mainloop()
