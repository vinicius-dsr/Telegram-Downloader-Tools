#!/usr/bin/env python3

import asyncio
import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox
from telethon import TelegramClient
from telethon.errors import FloodWaitError

# Configuração do CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def safe_filename(s: str, max_length: int = 200) -> str:
    """Converte string em nome de arquivo seguro"""
    # Normalizar espaços e caracteres inválidos
    clean = "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip()
    # Substituir múltiplos espaços por um
    while "  " in clean:
        clean = clean.replace("  ", " ")
    # Limita o tamanho do nome
    if len(clean) > max_length:
        return clean[:max_length].rstrip()
    return clean or "untitled"


class DownloadConfig:
    """Classe para armazenar configurações de download"""

    def __init__(self):
        self.api_id: str = ""
        self.api_hash: str = ""
        self.target: str = ""
        self.tags: str = ""
        self.output_path: str = "./downloads"
        self.limit: str = "0"
        self.session: str = "session"
        self.max_flood_wait: str = "300"
        self.name_line: str = "última"
        self.use_emojis: bool = True

    def to_dict(self) -> Dict:
        """Converte configuração para dicionário"""
        return {
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "target": self.target,
            "tags": self.tags,
            "output_path": self.output_path,
            "limit": self.limit,
            "session": self.session,
            "max_flood_wait": self.max_flood_wait,
            "name_line": self.name_line,
            "use_emojis": self.use_emojis,
        }

    def from_dict(self, data: Dict):
        """Carrega configuração de dicionário"""
        self.api_id = data.get("api_id", "")
        self.api_hash = data.get("api_hash", "")
        self.target = data.get("target", "")
        self.tags = data.get("tags", "")
        self.output_path = data.get("output_path", "./downloads")
        self.limit = data.get("limit", "0")
        self.session = data.get("session", "session")
        self.max_flood_wait = data.get("max_flood_wait", "300")
        self.name_line = data.get("name_line", "última")
        self.use_emojis = data.get("use_emojis", True)


class TelegramDownloaderGUI:
    """Interface gráfica para download de vídeos do Telegram"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Telegram Video Downloader")
        self.root.geometry("900x800")

        # Estado do aplicativo
        self.downloading = False
        self.last_progress_time = time.time()
        self.last_progress_bytes = 0

        # Configuração
        self.config = DownloadConfig()

        # Criar interface
        self._create_widgets()

    def _create_widgets(self):
        """Cria todos os widgets da interface"""
        # Frame principal com scroll
        main_frame = ctk.CTkScrollableFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Título
        self._create_title(main_frame)

        # Formulário de entrada
        self._create_input_form(main_frame)

        # Botões de configuração
        self._create_config_buttons(main_frame)

        # Botões de controle
        self._create_control_buttons(main_frame)

        # Barra de progresso
        self._create_progress_section(main_frame)

        # Área de log
        self._create_log_section(main_frame)

    def _create_title(self, parent):
        """Cria o título da aplicação"""
        title_label = ctk.CTkLabel(
            parent,
            text="Telegram Video Downloader",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

    def _create_input_form(self, parent):
        """Cria o formulário de entrada de dados"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=10, pady=5)

        # Configurar grid
        input_frame.columnconfigure(1, weight=1)

        # API ID
        self._create_form_field(
            input_frame, 0, "API ID:", "api_id_entry", placeholder="Digite seu API ID"
        )

        # API Hash
        self._create_form_field(
            input_frame,
            1,
            "API Hash:",
            "api_hash_entry",
            placeholder="Digite seu API Hash",
            show="*",
        )

        # Canal/Grupo
        self._create_form_field(
            input_frame,
            2,
            "Canal/Grupo:",
            "target_entry",
            placeholder="@nome ou https://t.me/nome",
        )

        # Tags
        self._create_form_field(
            input_frame, 3, "Tags:", "tags_entry", placeholder="#tag1,#tag2,#tag3"
        )

        # Pasta de saída com botão
        self._create_output_field(input_frame, 4)

        # Limite
        self._create_form_field(
            input_frame,
            5,
            "Limite por tag:",
            "limit_entry",
            placeholder="0 = sem limite",
            default="0",
        )

        # Nome da sessão
        self._create_form_field(
            input_frame,
            6,
            "Nome da sessão:",
            "session_entry",
            placeholder="session",
            default="session",
        )

        # Radio buttons para linha do nome
        self._create_name_line_field(input_frame, 7)

        # Max flood wait
        self._create_form_field(
            input_frame,
            8,
            "Max Flood Wait (s):",
            "max_flood_entry",
            placeholder="300",
            default="300",
        )

        # Opção usar emojis - fallback para ambientes que não mostram emoji
        ctk.CTkLabel(
            input_frame, text="Preferências:", font=ctk.CTkFont(weight="bold")
        ).grid(row=9, column=0, sticky="w", padx=10, pady=5)
        self.use_emojis_var = ctk.BooleanVar(value=True)
        self.emojis_check = ctk.CTkCheckBox(
            input_frame, text="Usar emojis (se suportado)", variable=self.use_emojis_var
        )
        self.emojis_check.grid(row=9, column=1, sticky="w", padx=10, pady=5)

    def _create_form_field(
        self,
        parent,
        row: int,
        label: str,
        attr_name: str,
        placeholder: str = "",
        default: str = "",
        show: str = "",
    ):
        """Cria um campo de formulário padrão"""
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )

        entry = ctk.CTkEntry(parent, width=300, placeholder_text=placeholder, show=show)
        if default:
            entry.insert(0, default)
        entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")

        setattr(self, attr_name, entry)

    def _create_output_field(self, parent, row: int):
        """Cria o campo de pasta de saída com botão de procurar"""
        ctk.CTkLabel(
            parent, text="Pasta de saída:", font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", padx=10, pady=5)

        output_frame = ctk.CTkFrame(parent, fg_color="transparent")
        output_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(output_frame, placeholder_text="./downloads")
        self.output_entry.insert(0, "./downloads")
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        browse_btn = ctk.CTkButton(
            output_frame, text="Procurar", width=100, command=self._browse_folder
        )
        browse_btn.grid(row=0, column=1)

    def _create_name_line_field(self, parent, row: int):
        """Cria o campo de seleção da linha do nome do vídeo"""
        ctk.CTkLabel(
            parent, text="Linha do nome do vídeo:", font=ctk.CTkFont(weight="bold")
        ).grid(row=row, column=0, sticky="w", padx=10, pady=5)

        self.name_line_var = ctk.StringVar(value="última")
        name_line_frame = ctk.CTkFrame(parent, fg_color="transparent")
        name_line_frame.grid(row=row, column=1, padx=10, pady=5, sticky="ew")

        options = ["primeira", "segunda", "terceira", "última"]
        for option in options:
            rb = ctk.CTkRadioButton(
                name_line_frame,
                text=option.capitalize(),
                variable=self.name_line_var,
                value=option,
            )
            rb.pack(side="left", padx=5)

    def _create_config_buttons(self, parent):
        """Cria os botões de salvar/carregar configuração"""
        config_btn_frame = ctk.CTkFrame(parent)
        config_btn_frame.pack(fill="x", padx=10, pady=5)

        save_btn = ctk.CTkButton(
            config_btn_frame,
            text=self._label_with_emoji("Salvar Configuração", "💾"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            command=self._save_config,
            fg_color="green",
            hover_color="darkgreen",
        )
        save_btn.pack(side="left", padx=5, fill="x", expand=True)

        load_btn = ctk.CTkButton(
            config_btn_frame,
            text=self._label_with_emoji("Carregar Configuração", "📂"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            command=self._load_config,
            fg_color="orange",
            hover_color="darkorange",
        )
        load_btn.pack(side="left", padx=5, fill="x", expand=True)

    def _create_control_buttons(self, parent):
        """Cria os botões de controle de download"""
        btn_frame = ctk.CTkFrame(parent)
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.download_btn = ctk.CTkButton(
            btn_frame,
            text=self._label_with_emoji("Iniciar Download", "▶"),
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            command=self._start_download,
        )
        self.download_btn.pack(side="left", padx=5, fill="x", expand=True)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text=self._label_with_emoji("Parar", "⏹"),
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            fg_color="red",
            hover_color="darkred",
            command=self._stop_download,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5, fill="x", expand=True)

    def _label_with_emoji(self, text: str, emoji: str) -> str:
        """Retorna label com emoji dependendo da preferência do usuário."""
        try:
            if getattr(self, "use_emojis_var", None) and self.use_emojis_var.get():
                return f"{emoji} {text}"
        except Exception:
            pass
        return text

    def _create_progress_section(self, parent):
        """Cria a seção de progresso"""
        progress_frame = ctk.CTkFrame(parent)
        progress_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            progress_frame, text="Progresso:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.current_file_label = ctk.CTkLabel(
            progress_frame,
            text="Nenhum arquivo em andamento",
            font=ctk.CTkFont(size=11, slant="italic"),
            anchor="w",
        )
        self.current_file_label.pack(fill="x", padx=10, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="Aguardando...", font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(anchor="w", padx=10, pady=(0, 5))

    def _create_log_section(self, parent):
        """Cria a seção de log colapsável"""
        log_frame = ctk.CTkFrame(parent)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Cabeçalho
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=5, pady=0)

        self.log_visible = ctk.BooleanVar(value=False)
        self.toggle_log_btn = ctk.CTkButton(
            log_header,
            text="📋 Mostrar Log ▼",
            command=self._toggle_log_visibility,
            width=150,
            height=28,
            font=ctk.CTkFont(weight="bold", size=12),
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            border_width=1,
        )
        self.toggle_log_btn.pack(side="left", padx=5, pady=2)

        # Conteúdo do log (inicialmente oculto)
        self.log_content_frame = ctk.CTkFrame(log_frame, fg_color="transparent")

        self.log_text = ctk.CTkTextbox(
            self.log_content_frame,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=11),
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        # Começa com log em estado normal para permitir escrita

    def _browse_folder(self):
        """Abre diálogo para selecionar pasta"""
        folder = filedialog.askdirectory(title="Selecionar Pasta de Saída")
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)

    def _toggle_log_visibility(self):
        """Alterna visibilidade do log"""
        if self.log_visible.get():
            self.log_content_frame.pack_forget()
            self.toggle_log_btn.configure(
                text=self._label_with_emoji("Mostrar Log ▼", "📋")
            )
            self.log_visible.set(False)
        else:
            self.log_content_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.toggle_log_btn.configure(
                text=self._label_with_emoji("Ocultar Log ▲", "📋")
            )
            self.log_visible.set(True)
        self.root.update_idletasks()

    def _log(self, message: str):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", formatted_message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            # Se algo falhar no widget, imprimir no console para diagnóstico
            print(formatted_message)

    def _validate_inputs(self) -> bool:
        """Valida os campos de entrada"""
        # API ID
        api_id = self.api_id_entry.get().strip()
        if not api_id:
            self._log("❌ Erro: API ID é obrigatório!")
            return False

        try:
            int(api_id)
        except ValueError:
            self._log("❌ Erro: API ID deve ser um número!")
            return False

        # API Hash
        if not self.api_hash_entry.get().strip():
            self._log("❌ Erro: API Hash é obrigatório!")
            return False

        # Target
        if not self.target_entry.get().strip():
            self._log("❌ Erro: Canal/Grupo é obrigatório!")
            return False

        # Tags
        tags_text = self.tags_entry.get().strip()
        if not tags_text:
            self._log("❌ Erro: Tags são obrigatórias!")
            return False

        # Processa tags
        tags_list = [
            tag.strip() for tag in tags_text.replace(" ", ",").split(",") if tag.strip()
        ]

        if not tags_list:
            self._log("❌ Erro: Nenhuma tag válida encontrada!")
            return False

        # Atualiza campo com tags formatadas
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, ", ".join(tags_list))

        # Diretório de saída
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            self._log("❌ Erro: Diretório de saída é obrigatório!")
            return False

        return True

    def _get_config_from_inputs(self) -> DownloadConfig:
        """Obtém configuração dos campos de entrada"""
        config = DownloadConfig()
        config.api_id = self.api_id_entry.get().strip()
        config.api_hash = self.api_hash_entry.get().strip()
        config.target = self.target_entry.get().strip()
        config.tags = self.tags_entry.get().strip()
        config.output_path = self.output_entry.get().strip()
        config.limit = self.limit_entry.get().strip()
        config.session = self.session_entry.get().strip()
        config.max_flood_wait = self.max_flood_entry.get().strip()
        config.name_line = self.name_line_var.get()
        config.use_emojis = bool(self.use_emojis_var.get())
        return config

    def _set_inputs_from_config(self, config: DownloadConfig):
        """Define campos de entrada a partir da configuração"""
        # Limpar campos
        for entry in [
            self.api_id_entry,
            self.api_hash_entry,
            self.target_entry,
            self.tags_entry,
            self.output_entry,
            self.limit_entry,
            self.session_entry,
            self.max_flood_entry,
        ]:
            entry.delete(0, "end")

        # Preencher
        self.api_id_entry.insert(0, config.api_id)
        self.api_hash_entry.insert(0, config.api_hash)
        self.target_entry.insert(0, config.target)
        self.tags_entry.insert(0, config.tags)
        self.output_entry.insert(0, config.output_path)
        self.limit_entry.insert(0, config.limit)
        self.session_entry.insert(0, config.session)
        self.max_flood_entry.insert(0, config.max_flood_wait)
        self.name_line_var.set(config.name_line)
        self.use_emojis_var.set(bool(config.use_emojis))

    def _save_config(self):
        """Salva configuração em arquivo JSON"""
        config = self._get_config_from_inputs()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Salvar Configuração",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config.to_dict(), f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Sucesso", f"Configuração salva em:\n{file_path}")
                self._log(f"✅ Configuração salva: {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar configuração:\n{e}")
                self._log(f"❌ Erro ao salvar configuração: {e}")

    def _load_config(self):
        """Carrega configuração de arquivo JSON"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Carregar Configuração",
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                config = DownloadConfig()
                config.from_dict(data)
                self._set_inputs_from_config(config)

                messagebox.showinfo(
                    "Sucesso", f"Configuração carregada de:\n{file_path}"
                )
                self._log(f"✅ Configuração carregada: {file_path}")

            except json.JSONDecodeError:
                messagebox.showerror("Erro", "Arquivo JSON inválido!")
                self._log("❌ Erro: Arquivo JSON inválido")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar configuração:\n{e}")
                self._log(f"❌ Erro ao carregar configuração: {e}")

    def _start_download(self):
        """Inicia o processo de download"""
        if not self._validate_inputs():
            return

        # Atualizar estado
        self.downloading = True
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        # Limpar log
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

        # Resetar progresso
        self.progress_bar.set(0)
        self.progress_label.configure(text="Iniciando...")
        self.current_file_label.configure(text="Preparando...")

        # Mostrar log
        if not self.log_visible.get():
            self._toggle_log_visibility()

        self.root.update_idletasks()

        # Iniciar thread de download
        download_thread = threading.Thread(target=self._run_download, daemon=True)
        download_thread.start()

    def _stop_download(self):
        """Para o processo de download"""
        self.downloading = False
        self._log("⏹ Parando download...")
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.root.update_idletasks()

    def _run_download(self):
        """Executa o download (thread separada)"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._download_videos_async())
        except Exception as e:
            self._log(f"❌ Erro fatal: {e}")
            import traceback

            self._log(traceback.format_exc())
        finally:
            # Garantir que UI seja atualizada no thread principal
            self.root.after(0, self._on_download_finished)

    def _on_download_finished(self):
        """Callback quando download termina"""
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        status = "Concluído" if not self.downloading else "Interrompido"
        self.progress_label.configure(text=status)
        self.current_file_label.configure(text="Nenhum arquivo em andamento")
        self.downloading = False

    def _progress_callback(
        self, current: int, total: int, filepath: Optional[str] = None
    ):
        """Callback de progresso do download"""
        if total <= 0:
            return

        progress = float(current) / float(total)

        # Calcular velocidade
        current_time = time.time()
        time_diff = current_time - self.last_progress_time
        bytes_diff = current - self.last_progress_bytes

        speed_mb = (bytes_diff / time_diff / (1024 * 1024)) if time_diff > 0 else 0

        self.last_progress_time = current_time
        self.last_progress_bytes = current

        # Tamanhos
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)

        # ETA
        if speed_mb > 0 and current > 0:
            bytes_remaining = total - current
            eta_seconds = bytes_remaining / (speed_mb * 1024 * 1024)
            eta_min = int(eta_seconds // 60)
            eta_sec = int(eta_seconds % 60)
            eta_str = f"ETA: {eta_min}m{eta_sec:02d}s"
        else:
            eta_str = "ETA: --"

        # Atualizar UI
        self.root.after(
            0,
            self._update_progress_ui,
            progress,
            current_mb,
            total_mb,
            speed_mb,
            eta_str,
            filepath,
        )

    def _update_progress_ui(
        self,
        progress: float,
        current_mb: float,
        total_mb: float,
        speed_mb: float,
        eta_str: str,
        filename: Optional[str] = None,
    ):
        """Atualiza UI com informações de progresso"""
        try:
            self.progress_bar.set(progress)

            progress_text = (
                f"{progress * 100:.1f}% ({current_mb:.1f}/{total_mb:.1f} MB) - "
                f"{speed_mb:.2f} MB/s - {eta_str}"
            )
            self.progress_label.configure(text=progress_text)

            if filename:
                self.current_file_label.configure(
                    text=f"📥 {os.path.basename(filename)}"
                )
            elif not self.downloading:
                self.current_file_label.configure(text="Nenhum arquivo em andamento")
        except Exception as e:
            print(f"Erro ao atualizar UI: {e}")

    def _extract_video_name(self, message_text: str, msg_id: int) -> str:
        """Extrai o nome do vídeo da mensagem"""
        lines = [l.strip() for l in (message_text or "").split("\n") if l.strip()]

        if not lines:
            return f"msg{msg_id}"

        line_choice = self.name_line_var.get()

        if line_choice == "primeira":
            video_name = lines[0]
        elif line_choice == "segunda":
            video_name = lines[1] if len(lines) > 1 else lines[0]
        elif line_choice == "terceira":
            video_name = lines[2] if len(lines) > 2 else lines[-1]
        else:  # última
            video_name = lines[-1]

        # Remove caracteres '=' do início
        while video_name.startswith("="):
            video_name = video_name[1:].strip()

        return video_name

    async def _download_videos_async(self):
        """Função assíncrona principal de download"""
        config = self._get_config_from_inputs()

        # Parâmetros
        api_id = int(config.api_id)
        api_hash = config.api_hash
        target = config.target
        out_path = config.output_path
        limit = int(config.limit) if config.limit else 0
        session = config.session
        max_flood_wait = int(config.max_flood_wait)

        # Criar pasta
        Path(out_path).mkdir(parents=True, exist_ok=True)

        # Processar tags
        tags = [t.strip() for t in config.tags.split(",") if t.strip()]
        if not tags:
            self._log("❌ Nenhuma tag válida informada!")
            return

        # Cliente Telegram
        client = TelegramClient(session, api_id, api_hash)

        try:
            await client.start()
            me = await client.get_me()
            user_repr = (
                getattr(me, "username", None)
                or getattr(me, "first_name", None)
                or str(me)
            )
            self._log(f"✅ Conectado como: {user_repr}")
        except Exception as e:
            self._log(f"❌ Erro ao conectar: {e}")
            return

        # Estatísticas
        csv_path = Path(out_path) / "videos_baixados.csv"
        registros = []
        total_baixados = 0
        total_encontrados = 0

        # Resolver entidade fora do loop para evitar múltiplas resoluções
        entity = await self._resolve_entity_with_retry(client, target, max_flood_wait)
        if not entity:
            await client.disconnect()
            return

        # Processar cada tag
        for tag in tags:
            if not self.downloading:
                self._log("⏹ Download cancelado pelo usuário.")
                break

            self._log(f"\n🔍 Procurando vídeos com a tag: {tag}")

            try:
                count_tag, tb, te = await self._process_messages_for_tag(
                    client,
                    entity,
                    tag,
                    limit,
                    out_path,
                    registros,
                    set(),
                    max_flood_wait,
                )
                total_baixados += tb
                total_encontrados += te
                self._log(f"✅ Tag {tag}: {count_tag} vídeos baixados.")
            except Exception as e:
                self._log(f"❌ Erro ao processar tag {tag}: {e}")

        await client.disconnect()

        # Salvar CSV
        if registros:
            try:
                df = pd.DataFrame(registros)
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                self._log(f"\n📄 CSV salvo em: {csv_path}")
            except Exception as e:
                self._log(f"❌ Erro ao salvar CSV: {e}")

        self._log(
            f"\n🚀 Finalizado: {total_baixados} vídeos baixados ({total_encontrados} mensagens verificadas)."
        )
        self.progress_bar.set(1)
        self.progress_label.configure(text="Concluído!")

    async def _resolve_entity_with_retry(
        self, client, target: str, max_flood_wait: int
    ):
        """Resolve entidade do Telegram com retry em caso de FloodWait"""
        while self.downloading:
            try:
                entity = await client.get_input_entity(target)
                return entity
            except FloodWaitError as e:
                self._log(f"⏳ Flood wait ao resolver target ({e.seconds}s)")
                if e.seconds > max_flood_wait:
                    self._log(f"❌ Flood wait muito longo ({e.seconds}s). Abortando.")
                    return None
                self._log(f"→ Aguardando {e.seconds}s...")
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:
                self._log(f"❌ Erro ao resolver entidade: {e}")
                return None
        return None

    async def _process_messages_for_tag(
        self,
        client,
        entity,
        tag: str,
        limit: int,
        out_path: str,
        registros: List[Dict],
        seen_msg_ids: set,
        max_flood_wait: int,
    ) -> Tuple[int, int, int]:
        """Processa mensagens para uma tag específica

        Retorna (count_tag, total_baixados_para_essa_tag, total_encontrados_para_essa_tag)
        """
        count_tag = 0
        total_baixados = 0
        total_encontrados = 0

        while self.downloading:
            try:
                async for msg in client.iter_messages(
                    entity, search=tag, limit=(limit or None)
                ):
                    if not self.downloading:
                        break

                    # Evitar duplicatas
                    if msg.id in seen_msg_ids:
                        continue
                    seen_msg_ids.add(msg.id)
                    total_encontrados += 1

                    # Verificar se tem a tag na mensagem (sensível a caixa)
                    if not msg.message or tag not in msg.message:
                        continue

                    # Verificar se tem mídia de vídeo
                    if not getattr(msg, "media", None):
                        continue

                    # Tentar detectar se é vídeo
                    is_video = getattr(msg, "video", None) is not None
                    mime = getattr(getattr(msg, "media", None), "mime_type", "") or ""

                    if not is_video and not mime.startswith("video"):
                        # também aceitar documents que contenham video mime
                        try:
                            # Telethon salva algumas mídias como Document; verificar attributes
                            d = getattr(msg.media, "document", None)
                            if d is None:
                                continue
                            attrs = getattr(d, "attributes", [])
                            # Se houver algum attribute relacionado a video, aceitar
                            if not any("video" in str(a).lower() for a in attrs):
                                continue
                        except Exception:
                            continue

                    # Extrair nome do vídeo
                    video_name = self._extract_video_name(msg.message, msg.id)
                    filename = safe_filename(video_name) + ".mp4"
                    file_path = os.path.join(out_path, filename)

                    # Verificar se já existe
                    if os.path.exists(file_path):
                        self._log(f"⏩ Já existe: {filename}")
                        continue

                    # Fazer download
                    success = await self._download_single_video(
                        client, msg, file_path, filename, max_flood_wait
                    )

                    if success:
                        total_baixados += 1
                        count_tag += 1

                        # Registrar no CSV
                        registros.append(
                            {
                                "tag": tag,
                                "msg_id": msg.id,
                                "data": (
                                    msg.date.strftime("%Y-%m-%d %H:%M:%S")
                                    if msg.date
                                    else ""
                                ),
                                "arquivo": filename,
                                "legenda": msg.message or "",
                            }
                        )

                # Se terminou a iteração sem FloodWait, sair do loop
                break

            except FloodWaitError as e:
                self._log(f"⏳ Flood wait durante iteração ({e.seconds}s)")
                if e.seconds > max_flood_wait:
                    self._log(f"❌ Flood wait muito longo ({e.seconds}s). Abortando.")
                    return count_tag, total_baixados, total_encontrados
                self._log(f"→ Aguardando {e.seconds}s e reiniciando...")
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:
                self._log(f"❌ Erro ao processar mensagens: {e}")
                break

        return count_tag, total_baixados, total_encontrados

    async def _download_single_video(
        self, client, msg, file_path: str, filename: str, max_flood_wait: int
    ) -> bool:
        """Faz download de um único vídeo com tratamento de erros"""
        try:
            self._log(f"⏬ Baixando: {filename}")

            # Resetar variáveis de progresso
            self.last_progress_time = time.time()
            self.last_progress_bytes = 0

            # Atualizar nome do arquivo na UI
            self.root.after(
                0, lambda: self.current_file_label.configure(text=f"📥 {filename}")
            )

            # Função wrapper para callback
            def progress_wrapper(current, total):
                # Alguns callbacks podem chamar com None; proteger
                try:
                    if current is None or total is None:
                        return
                    self._progress_callback(int(current), int(total), file_path)
                except Exception:
                    pass

            # Download
            await client.download_media(
                msg, file=file_path, progress_callback=progress_wrapper
            )

            self._log(f"✅ Concluído: {filename}")
            return True

        except FloodWaitError as e:
            self._log(f"⏳ Flood wait ({e.seconds}s) → aguardando...")
            if e.seconds <= max_flood_wait and self.downloading:
                await asyncio.sleep(e.seconds + 1)
                # Tentar novamente
                return await self._download_single_video(
                    client, msg, file_path, filename, max_flood_wait
                )
            else:
                self._log(f"❌ Flood wait muito longo, pulando arquivo")
                return False
        except Exception as e:
            self._log(f"❌ Erro ao baixar {filename}: {e}")
            # Remover arquivo parcial se existir
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            return False

    def run(self):
        """Inicia a aplicação"""
        self.root.mainloop()


def main():
    """Função principal"""
    app = TelegramDownloaderGUI()
    app.run()


if __name__ == "__main__":
    main()
