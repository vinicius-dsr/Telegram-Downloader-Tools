#!/usr/bin/env python3
"""
Download Telegram Video Tags GUI
Integração: login -> salvar config.json -> interface principal (download)
"""
import os
import sys
import json
import time
import threading
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# --- Config paths (absolute) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# --- CTk appearance ---
ctk.set_appearance_mode("dark")

VESPER_COLORS = {
    "bg": "#101010",
    "panel": "#161616",
    "text": "#FFFFFF",
    "muted": "#A0A0A0",
    "accent": "#FFC799",
    "success": "#90B99F",
    "danger": "#F5A191",
}


# --- Utils ---
def safe_filename(s: str, max_length: int = 200) -> str:
    """Converte string em nome de arquivo seguro"""
    if not s:
        return "untitled"
    clean = "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip()
    while "  " in clean:
        clean = clean.replace("  ", " ")
    if len(clean) > max_length:
        return clean[:max_length].rstrip()
    return clean or "untitled"


def load_config() -> Optional[Dict]:
    """Carrega config.json se existir e for válido"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
    except Exception:
        # problema ao ler config => ignorar e tratar como None
        print("Warning: não foi possível ler config.json (pode estar corrompido).")
    return None


def save_config(data: Dict):
    """Salva config.json"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar config.json: {e}")


def delete_session_file(session_name: str):
    """Remove arquivo de sessão (se existir)"""
    try:
        session_path = os.path.join(BASE_DIR, f"{session_name}.session")
        if os.path.exists(session_path):
            os.remove(session_path)
    except Exception:
        pass


# --- App ---
class TelegramDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.configure(fg_color=VESPER_COLORS["bg"])
        self.title("Telegram Video Downloader")
        self.geometry("900x800")
        self.resizable(True, True)

        # state
        self.config = load_config() or {}
        self.client: Optional[TelegramClient] = None

        # download control
        self.downloading = False
        self.last_progress_time = time.time()
        self.last_progress_bytes = 0

        # build according to config existence
        if self.config and self._session_file_exists():
            # config and session exist -> open main interface
            self._build_main_interface()
        else:
            # show login flow
            self._build_login_interface()

    # ---------- LOGIN UI & FLOW ----------
    def _build_login_interface(self):
        self._clear()
        frame = ctk.CTkFrame(self, fg_color=VESPER_COLORS["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame, 
            text="// Telegram Video Downloader", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=VESPER_COLORS["accent"]
        ).pack(pady=(6, 12))

        ctk.CTkLabel(
            frame, 
            text="// Conecte sua conta para iniciar os downloads.", 
            text_color=VESPER_COLORS["muted"]
        ).pack(pady=(0, 12))

        # API ID
        ctk.CTkLabel(
            frame, 
            text="// API ID:", 
            text_color=VESPER_COLORS["muted"],
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=6)
        self.login_api_id = ctk.CTkEntry(
            frame, 
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["border"] if hasattr(VESPER_COLORS, "border") else VESPER_COLORS["muted"]
        )
        self.login_api_id.pack(fill="x", padx=6, pady=(0, 8))
        if self.config.get("api_id"):
            self.login_api_id.insert(0, str(self.config.get("api_id")))

        # API Hash
        ctk.CTkLabel(
            frame, 
            text="// API Hash:", 
            text_color=VESPER_COLORS["muted"],
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=6)
        self.login_api_hash = ctk.CTkEntry(
            frame, 
            show="*",
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.login_api_hash.pack(fill="x", padx=6, pady=(0, 8))
        if self.config.get("api_hash"):
            self.login_api_hash.insert(0, self.config.get("api_hash"))

        # Phone
        ctk.CTkLabel(
            frame, 
            text="// Telefone (ex: +55XXXXXXXXXXX):", 
            text_color=VESPER_COLORS["muted"],
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=6)
        self.login_phone = ctk.CTkEntry(
            frame,
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.login_phone.pack(fill="x", padx=6, pady=(0, 8))
        if self.config.get("phone"):
            self.login_phone.insert(0, self.config.get("phone"))

        # status
        self.login_status = ctk.CTkLabel(frame, text="", text_color=VESPER_COLORS["muted"])
        self.login_status.pack(pady=(6, 0))

        # buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=6, pady=12)

        ctk.CTkButton(
            btn_frame, 
            text="[CONECTAR E ENVIAR CÓDIGO]", 
            fg_color=VESPER_COLORS["success"],
            text_color=VESPER_COLORS["bg"],
            command=self._start_login_thread
        ).pack(side="left", expand=True, padx=6)
        ctk.CTkButton(
            btn_frame, 
            text="[SAIR]", 
            fg_color=VESPER_COLORS["danger"],
            text_color=VESPER_COLORS["bg"],
            command=self.destroy
        ).pack(side="left", padx=6)

    def _start_login_thread(self):
        # ensure entries updated (fix for Wayland/Hyprland)
        self.update_idletasks()

        api_id = self.login_api_id.get().strip()
        api_hash = self.login_api_hash.get().strip()
        phone = self.login_phone.get().strip()

        if not api_id or not api_hash or not phone:
            messagebox.showwarning("Aviso", "Preencha todos os campos de login.")
            return
        try:
            int(api_id)
        except ValueError:
            messagebox.showerror("Erro", "API ID deve ser um número.")
            return

        self.login_status.configure(text="Conectando...", text_color="gray")
        # run login flow in background thread (async inside)
        threading.Thread(target=lambda: asyncio.run(self._login_flow(api_id, api_hash, phone)), daemon=True).start()

    async def _login_flow(self, api_id: str, api_hash: str, phone: str):
        """
        Conecta via Telethon, envia código, solicita confirmação.
        Ao final salva config.json e abre a interface principal.
        """
        try:
            session_name = self.config.get("session_name", "session")
            client = TelegramClient(session_name, int(api_id), api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                # send code
                try:
                    await client.send_code_request(phone)
                except Exception as e:
                    # update status on main thread
                    self.after(0, lambda err=e: self.login_status.configure(text=f"Erro ao enviar código: {err}", text_color="red"))
                    await client.disconnect()
                    return

                # ask for code via a small CTk Toplevel on main thread
                code = await self._ask_code_dialog_async("Código enviado", "Digite o código recebido no Telegram:")
                if code is None:
                    await client.disconnect()
                    self.after(0, lambda: self.login_status.configure(text="Login cancelado pelo usuário.", text_color="red"))
                    return

                # try sign in
                try:
                    await client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    # 2FA required: ask for password
                    pwd = await self._ask_code_dialog_async("Senha 2FA", "Autenticação de dois fatores ativada. Digite sua senha:")
                    if pwd is None:
                        await client.disconnect()
                        self.after(0, lambda: self.login_status.configure(text="2FA cancelada.", text_color="red"))
                        return
                    try:
                        await client.sign_in(password=pwd)
                    except Exception as e:
                        await client.disconnect()
                        self.after(0, lambda err=e: self.login_status.configure(text=f"Erro 2FA: {err}", text_color="red"))
                        return
                except Exception as e:
                    await client.disconnect()
                    self.after(0, lambda err=e: self.login_status.configure(text=f"Erro ao autenticar: {err}", text_color="red"))
                    return

            # sucesso: salvar config (api_id, api_hash, phone, session_name)
            cfg = {
                "api_id": int(api_id),
                "api_hash": api_hash,
                "phone": phone,
                "session_name": session_name,
                # valores padrão da interface principal (podem ser sobrescritos por salvar config)
                "target": "",
                "tags": "",
                "output_path": "./downloads",
                "limit": "0",
                "max_flood_wait": "300",
                "name_line": "última",
            }
            save_config(cfg)
            self.config = cfg
            # close client but keep session file
            await client.disconnect()

            # abrir interface principal (na thread principal)
            self.after(0, lambda: self._build_main_interface())
        except Exception as e:
            self.after(0, lambda err=e: self.login_status.configure(text=f"Erro: {err}", text_color="red"))

    async def _ask_code_dialog_async(self, title: str, prompt: str) -> Optional[str]:
        """
        Cria uma janela modal CTk para pedir código/senha e retorna o valor.
        Executa no thread principal via self.after e aguarda resposta usando Future.
        """
        future = asyncio.get_event_loop().create_future()

        def _show():
            dlg = ctk.CTkToplevel(self)
            dlg.title(title)
            dlg.geometry("360x160")
            dlg.transient(self)
            dlg.grab_set()

            ctk.CTkLabel(dlg, text=prompt).pack(padx=16, pady=(12, 6))
            entry = ctk.CTkEntry(dlg)
            entry.pack(padx=16, pady=(0, 12), fill="x")

            def on_ok():
                val = entry.get().strip()
                dlg.grab_release()
                dlg.destroy()
                if not future.done():
                    future.set_result(val)

            def on_cancel():
                dlg.grab_release()
                dlg.destroy()
                if not future.done():
                    future.set_result(None)

            btn_frame = ctk.CTkFrame(dlg)
            btn_frame.pack(pady=(0, 12))
            ctk.CTkButton(btn_frame, text="OK", width=12, command=on_ok).pack(side="left", padx=8)
            ctk.CTkButton(btn_frame, text="Cancelar", width=12, command=on_cancel).pack(side="left", padx=8)

        # schedule dialog on main thread
        self.after(0, _show)

        try:
            return await future
        except Exception:
            return None

    def _session_file_exists(self) -> bool:
        name = self.config.get("session_name", "session")
        return os.path.exists(os.path.join(BASE_DIR, f"{name}.session"))

    # ---------- MAIN INTERFACE (Downloader) ----------
    def _build_main_interface(self):
        self._clear()
        # reload config (in case changed)
        self.config = load_config() or self.config or {}

        # main scrollable frame
        main_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color=VESPER_COLORS["bg"]
        )
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # title
        ctk.CTkLabel(
            main_frame, 
            text="// Telegram Video Downloader", 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=VESPER_COLORS["accent"]
        ).pack(pady=(10, 20))

        ctk.CTkLabel(
            main_frame, 
            text="// Baixe vídeos por tags com controle total e histórico em CSV.", 
            text_color=VESPER_COLORS["muted"]
        ).pack(pady=(0, 20))

        # inputs frame (grid)
        input_frame = ctk.CTkFrame(main_frame, fg_color=VESPER_COLORS["panel"])
        input_frame.pack(fill="x", padx=10, pady=5)
        input_frame.columnconfigure(1, weight=1)

        # NOTE: no API ID / API HASH / PHONE fields here (they're in config.json handled by login)

        # Target
        ctk.CTkLabel(
            input_frame, 
            text="// Canal/Grupo:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.target_entry = ctk.CTkEntry(
            input_frame, 
            width=400, 
            placeholder_text="@nome ou https://t.me/nome",
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.target_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        if self.config.get("target"):
            self.target_entry.insert(0, self.config.get("target"))

        # Tags
        ctk.CTkLabel(
            input_frame, 
            text="// Tags:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.tags_entry = ctk.CTkEntry(
            input_frame, 
            width=400, 
            placeholder_text="#tag1,#tag2,#tag3",
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.tags_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        if self.config.get("tags"):
            self.tags_entry.insert(0, self.config.get("tags"))

        # Output path with browse
        ctk.CTkLabel(
            input_frame, 
            text="// Pasta de saída:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        output_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        output_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            output_frame, 
            placeholder_text="./downloads",
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.output_entry.insert(0, self.config.get("output_path", "./downloads"))
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkButton(
            output_frame, 
            text="[PROCURAR]", 
            width=100, 
            fg_color=VESPER_COLORS["muted"],
            text_color=VESPER_COLORS["bg"],
            command=self._browse_folder
        ).grid(row=0, column=1)

        # Limit
        ctk.CTkLabel(
            input_frame, 
            text="// Limite por tag:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.limit_entry = ctk.CTkEntry(
            input_frame, 
            width=200,
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.limit_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.limit_entry.insert(0, str(self.config.get("limit", "0")))

        # Session name (editable, pre-filled from config)
        ctk.CTkLabel(
            input_frame, 
            text="// Nome da sessão:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.session_entry = ctk.CTkEntry(
            input_frame, 
            width=200,
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.session_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.session_entry.insert(0, self.config.get("session_name", self.config.get("session", "session")))

        # Name line radio
        ctk.CTkLabel(
            input_frame, 
            text="// Linha do nome do vídeo:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.name_line_var = ctk.StringVar(value=self.config.get("name_line", "última"))
        name_line_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        name_line_frame.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        options = ["primeira", "segunda", "terceira", "última"]
        for option in options:
            rb = ctk.CTkRadioButton(
                name_line_frame, 
                text=option.capitalize(), 
                variable=self.name_line_var, 
                value=option,
                text_color=VESPER_COLORS["text"]
            )
            rb.pack(side="left", padx=5)

        # Max flood wait
        ctk.CTkLabel(
            input_frame, 
            text="// Max Flood Wait (s):", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["muted"]
        ).grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.max_flood_entry = ctk.CTkEntry(
            input_frame, 
            width=200,
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.max_flood_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.max_flood_entry.insert(0, str(self.config.get("max_flood_wait", "300")))

        # Config save/load buttons
        config_btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        config_btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            config_btn_frame, 
            text="[SALVAR CONFIGURAÇÃO]", 
            command=self._save_current_config, 
            fg_color=VESPER_COLORS["success"],
            text_color=VESPER_COLORS["bg"]
        ).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(
            config_btn_frame, 
            text="[CARREGAR CONFIGURAÇÃO]", 
            command=self._load_config_file, 
            fg_color=VESPER_COLORS["muted"],
            text_color=VESPER_COLORS["bg"]
        ).pack(side="left", padx=5, fill="x", expand=True)

        # Download control buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.download_btn = ctk.CTkButton(
            btn_frame, 
            text="[INICIAR DOWNLOAD]", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            height=40, 
            fg_color=VESPER_COLORS["success"],
            text_color=VESPER_COLORS["bg"],
            command=self._start_download
        )
        self.download_btn.pack(side="left", padx=5, fill="x", expand=True)

        self.stop_btn = ctk.CTkButton(
            btn_frame, 
            text="[PARAR DOWNLOAD]", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            height=40, 
            fg_color=VESPER_COLORS["danger"],
            text_color=VESPER_COLORS["bg"],
            command=self._stop_download, 
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5, fill="x", expand=True)

        # progress section
        progress_frame = ctk.CTkFrame(main_frame, fg_color=VESPER_COLORS["panel"])
        progress_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            progress_frame, 
            text="// Progresso:", 
            font=ctk.CTkFont(weight="bold"),
            text_color=VESPER_COLORS["accent"]
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.current_file_label = ctk.CTkLabel(
            progress_frame, 
            text="// Nenhum arquivo em andamento", 
            font=ctk.CTkFont(size=11, slant="italic"), 
            anchor="w",
            text_color=VESPER_COLORS["muted"]
        )
        self.current_file_label.pack(fill="x", padx=10, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, progress_color=VESPER_COLORS["accent"])
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame, 
            text="// Aguardando...", 
            font=ctk.CTkFont(size=12),
            text_color=VESPER_COLORS["text"]
        )
        self.progress_label.pack(anchor="w", padx=10, pady=(0, 5))

        # log area (collapsible)
        log_frame = ctk.CTkFrame(main_frame, fg_color=VESPER_COLORS["panel"])
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=5, pady=0)

        self.log_visible = ctk.BooleanVar(value=False)
        self.toggle_log_btn = ctk.CTkButton(
            log_header, 
            text="[MOSTRAR LOG]", 
            command=self._toggle_log_visibility, 
            width=150, 
            height=28, 
            font=ctk.CTkFont(weight="bold", size=12), 
            fg_color=VESPER_COLORS["muted"],
            text_color=VESPER_COLORS["bg"],
            hover_color=VESPER_COLORS["accent"]
        )
        self.toggle_log_btn.pack(side="left", padx=5, pady=2)

        self.log_content_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        self.log_text = ctk.CTkTextbox(
            self.log_content_frame, 
            wrap="word", 
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            fg_color=VESPER_COLORS["bg"],
            text_color=VESPER_COLORS["text"],
            border_color=VESPER_COLORS["muted"]
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        # start hidden
        self.log_content_frame.pack_forget()

        # final UI update
        self.update_idletasks()

    # ---------- UI utilities ----------
    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Selecionar Pasta de Saída")
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)

    def _toggle_log_visibility(self):
        if self.log_visible.get():
            self.log_content_frame.pack_forget()
            self.toggle_log_btn.configure(text="[MOSTRAR LOG]")
            self.log_visible.set(False)
        else:
            self.log_content_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.toggle_log_btn.configure(text="[OCULTAR LOG]")
            self.log_visible.set(True)
        self.update_idletasks()

    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            print(line)

    # ---------- Config save/load for main interface ----------
    def _save_current_config(self):
        """Salva os campos atuais em config.json (mantém api_id/api_hash/phone)"""
        cfg = load_config() or {}
        cfg.update({
            "target": self.target_entry.get().strip(),
            "tags": self.tags_entry.get().strip(),
            "output_path": self.output_entry.get().strip(),
            "limit": self.limit_entry.get().strip(),
            "session_name": self.session_entry.get().strip() or cfg.get("session_name", "session"),
            "max_flood_wait": self.max_flood_entry.get().strip(),
            "name_line": self.name_line_var.get(),
        })
        save_config(cfg)
        self.config = cfg
        messagebox.showinfo("Sucesso", "Configuração salva em config.json")
        self._log("✅ Configuração salva em config.json")

    def _load_config_file(self):
        """Abre diálogo para carregar um arquivo de configuração (substitui campos atuais)"""
        file_path = filedialog.askopenfilename(title="Carregar Configuração", filetypes=[("JSON files","*.json"), ("All files","*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # apply to fields (only those present)
            if "target" in cfg:
                self.target_entry.delete(0, "end"); self.target_entry.insert(0, cfg.get("target",""))
            if "tags" in cfg:
                self.tags_entry.delete(0, "end"); self.tags_entry.insert(0, cfg.get("tags",""))
            if "output_path" in cfg:
                self.output_entry.delete(0, "end"); self.output_entry.insert(0, cfg.get("output_path","./downloads"))
            if "limit" in cfg:
                self.limit_entry.delete(0, "end"); self.limit_entry.insert(0, str(cfg.get("limit","0")))
            if "session_name" in cfg:
                self.session_entry.delete(0, "end"); self.session_entry.insert(0, cfg.get("session_name","session"))
            if "max_flood_wait" in cfg:
                self.max_flood_entry.delete(0, "end"); self.max_flood_entry.insert(0, str(cfg.get("max_flood_wait","300")))
            if "name_line" in cfg:
                self.name_line_var.set(cfg.get("name_line", "última"))
            messagebox.showinfo("Sucesso", f"Configuração carregada de:\n{file_path}")
            self._log(f"✅ Configuração carregada: {file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar configuração:\n{e}")
            self._log(f"❌ Erro ao carregar configuração: {e}")

    # ---------- Download control ----------
    def _start_download(self):
        # Validate inputs (only main UI fields)
        if not self._validate_main_inputs():
            return

        # set state
        self.downloading = True
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        # clear log
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

        # reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="Iniciando...")
        self.current_file_label.configure(text="Preparando...")

        # show log
        if not self.log_visible.get():
            self._toggle_log_visibility()

        self.update_idletasks()

        # start download in background thread
        threading.Thread(target=self._download_thread_worker, daemon=True).start()

    def _stop_download(self):
        self.downloading = False
        self._log("⏹ Parando download...")
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_idletasks()

    def _download_thread_worker(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._download_videos_async())
        except Exception as e:
            self._log(f"❌ Erro fatal: {e}")
            import traceback
            self._log(traceback.format_exc())
        finally:
            # ensure UI update on main thread
            self.after(0, self._on_download_finished)

    def _on_download_finished(self):
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        status = "Concluído" if not self.downloading else "Interrompido"
        self.progress_label.configure(text=status)
        self.current_file_label.configure(text="Nenhum arquivo em andamento")
        self.downloading = False

    def _validate_main_inputs(self) -> bool:
        # target
        target = self.target_entry.get().strip()
        if not target:
            self._log("❌ Erro: Canal/Grupo é obrigatório!")
            return False
        # tags
        tags_text = self.tags_entry.get().strip()
        if not tags_text:
            self._log("❌ Erro: Tags são obrigatórias!")
            return False
        tags_list = [t.strip() for t in tags_text.replace(" ", ",").split(",") if t.strip()]
        if not tags_list:
            self._log("❌ Erro: Nenhuma tag válida encontrada!")
            return False
        # update formatted
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, ", ".join(tags_list))
        # output folder
        out = self.output_entry.get().strip()
        if not out:
            self._log("❌ Erro: Diretório de saída é obrigatório!")
            return False
        if not os.path.isdir(out):
            try:
                os.makedirs(out, exist_ok=True)
            except Exception:
                self._log("❌ Erro: Diretório de saída não encontrado e não foi possível criar!")
                return False
        # session name
        sess = self.session_entry.get().strip()
        if not sess:
            self._log("❌ Erro: Nome da sessão é obrigatório!")
            return False
        # numeric fields
        try:
            int(self.limit_entry.get().strip())
        except Exception:
            self._log("❌ Erro: Limite deve ser um número!")
            return False
        try:
            int(self.max_flood_entry.get().strip())
        except Exception:
            self._log("❌ Erro: Max Flood Wait deve ser um número!")
            return False

        # OK
        return True

    # ---------- Core download logic (adapted from your version) ----------
    async def _download_videos_async(self):
        """
        Função principal de download (async).
        Usa api_id/api_hash/phone salvo em config.json (não pede novamente).
        """
        # reload config
        cfg = load_config() or self.config or {}
        if not cfg.get("api_id") or not cfg.get("api_hash"):
            self._log("❌ Erro: api_id/api_hash não encontrados no config.json. Faça login novamente.")
            return

        api_id = int(cfg["api_id"])
        api_hash = cfg["api_hash"]
        # target/tags/out_path/limit/session etc - prefer UI values
        target = self.target_entry.get().strip()
        tags_str = self.tags_entry.get().strip()
        out_path = self.output_entry.get().strip()
        limit = int(self.limit_entry.get().strip() or 0)
        session = self.session_entry.get().strip() or cfg.get("session_name", "session")
        max_flood_wait = int(self.max_flood_entry.get().strip() or cfg.get("max_flood_wait", 300))

        # ensure output dir
        Path(out_path).mkdir(parents=True, exist_ok=True)

        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        if not tags:
            self._log("❌ Nenhuma tag válida informada!")
            return

        # Telethon client using session name
        client = TelegramClient(session, api_id, api_hash)

        try:
            await client.start()
            me = await client.get_me()
            self._log(f"✅ Conectado como: {getattr(me,'username',None) or getattr(me,'first_name',str(me))}")
        except Exception as e:
            self._log(f"❌ Erro ao conectar: {e}")
            return

        csv_path = os.path.join(out_path, "videos_baixados.csv")
        registros = []
        total_baixados = 0
        total_encontrados = 0

        for tag in tags:
            if not self.downloading:
                self._log("⏹ Download cancelado pelo usuário.")
                break

            self._log(f"\n🔍 Procurando vídeos com a tag: {tag}")
            count_tag = 0

            # resolve entity with FloodWait handling
            entity = None
            while self.downloading and entity is None:
                try:
                    entity = await client.get_input_entity(target)
                except FloodWaitError as e:
                    self._log(f"⏳ Flood wait ao resolver target ({e.seconds}s)")
                    if e.seconds > max_flood_wait:
                        self._log(f"❌ Flood wait muito longo ({e.seconds}s). Abortando.")
                        await client.disconnect()
                        return
                    self._log(f"→ Aguardando {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    self._log(f"❌ Erro ao resolver entidade: {e}")
                    await client.disconnect()
                    return

            if not self.downloading:
                break

            seen_msg_ids = set()
            while self.downloading:
                try:
                    async for msg in client.iter_messages(entity, search=tag, limit=(limit or None)):
                        if not self.downloading:
                            break

                        if msg.id in seen_msg_ids:
                            continue
                        seen_msg_ids.add(msg.id)
                        total_encontrados += 1

                        # check message contains tag and media
                        if not msg.message or tag not in msg.message:
                            continue
                        if not getattr(msg, "media", None):
                            continue

                        is_video = getattr(msg, "video", None) is not None
                        mime = getattr(msg.media, "mime_type", "") if msg.media else ""
                        if not is_video and not mime.startswith("video"):
                            # try document attributes heuristic
                            try:
                                d = getattr(msg.media, "document", None)
                                if d is None:
                                    continue
                                attrs = getattr(d, "attributes", [])
                                if not any("video" in str(a).lower() for a in attrs):
                                    continue
                            except Exception:
                                continue

                        # extract video name based on name_line_var
                        lines = [l.strip() for l in (msg.message or "").split("\n") if l.strip()]
                        if not lines:
                            video_name = f"msg{msg.id}"
                        else:
                            choice = self.name_line_var.get()
                            if choice == "primeira":
                                video_name = lines[0]
                            elif choice == "segunda":
                                video_name = lines[1] if len(lines) > 1 else lines[0]
                            elif choice == "terceira":
                                video_name = lines[2] if len(lines) > 2 else lines[-1]
                            else:
                                video_name = lines[-1]
                        while video_name.startswith("="):
                            video_name = video_name[1:].strip()

                        filename = safe_filename(video_name) + ".mp4"
                        file_path = os.path.join(out_path, filename)

                        if os.path.exists(file_path):
                            self._log(f"⏩ Já existe: {filename}")
                            continue

                        try:
                            self._log(f"⏬ Baixando: {filename}")
                            # reset progress counters
                            self.last_progress_time = time.time()
                            self.last_progress_bytes = 0

                            # update filename label in UI
                            self.after(0, lambda f=file_path: self.current_file_label.configure(text=f"Arquivo: {os.path.basename(f)}"))

                            def progress_wrapper(current, total):
                                try:
                                    if current is None or total is None:
                                        return
                                    self._progress_callback(current, total, file_path)
                                except Exception:
                                    pass

                            await client.download_media(msg, file=file_path, progress_callback=progress_wrapper)

                            self._log(f"✅ Concluído: {filename}")
                            total_baixados += 1
                            count_tag += 1
                            registros.append({
                                "tag": tag,
                                "msg_id": msg.id,
                                "data": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else "",
                                "arquivo": filename,
                                "legenda": msg.message or "",
                            })

                        except FloodWaitError as e:
                            self._log(f"⏳ Flood wait ({e.seconds}s) → aguardando...")
                            if e.seconds <= max_flood_wait:
                                await asyncio.sleep(e.seconds + 1)
                                continue
                            else:
                                self._log("❌ Flood wait muito longo, pulando arquivo.")
                                continue
                        except Exception as e:
                            self._log(f"❌ Erro ao baixar msg {msg.id}: {e}")
                            # remove parcial
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception:
                                pass
                            continue

                    # finished iter_messages loop
                    break

                except FloodWaitError as e:
                    self._log(f"⏳ Flood wait durante iteração ({e.seconds}s)")
                    if e.seconds > max_flood_wait:
                        self._log(f"❌ Flood wait muito longo ({e.seconds}s). Abortando.")
                        await client.disconnect()
                        return
                    self._log(f"→ Aguardando {e.seconds}s e reiniciando...")
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    self._log(f"❌ Erro ao processar mensagens: {e}")
                    break

            if self.downloading:
                self._log(f"✅ Tag {tag}: {count_tag} vídeos baixados.")

        # done for all tags
        try:
            await client.disconnect()
        except Exception:
            pass

        # save CSV
        if registros:
            try:
                df = pd.DataFrame(registros)
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                self._log(f"\n📄 CSV salvo em: {csv_path}")
            except Exception as e:
                self._log(f"❌ Erro ao salvar CSV: {e}")

        self._log(f"\n🚀 Finalizado: {total_baixados} vídeos baixados ({total_encontrados} mensagens verificadas).")
        self.after(0, lambda: self.progress_bar.set(1))
        self.after(0, lambda: self.progress_label.configure(text="Concluído!"))

    # ---------- Progress helpers ----------
    def _progress_callback(self, current: int, total: int, filepath: Optional[str] = None):
        if total <= 0:
            return
        try:
            progress = float(current) / float(total) if total else 0.0
            current_time = time.time()
            time_diff = current_time - self.last_progress_time
            bytes_diff = current - self.last_progress_bytes
            speed_mb = (bytes_diff / time_diff / (1024 * 1024)) if time_diff > 0 else 0.0
            self.last_progress_time = current_time
            self.last_progress_bytes = current
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            if speed_mb > 0 and current > 0:
                bytes_remaining = total - current
                eta_seconds = bytes_remaining / (speed_mb * 1024 * 1024)
                eta_min = int(eta_seconds // 60)
                eta_sec = int(eta_seconds % 60)
                eta_str = f"ETA: {eta_min}m{eta_sec:02d}s"
            else:
                eta_str = "ETA: --"
            # schedule UI update on main thread
            self.after(0, self._update_progress_ui, progress, current_mb, total_mb, speed_mb, eta_str, filepath)
        except Exception:
            pass

    def _update_progress_ui(self, progress, current_mb, total_mb, speed_mb, eta_str, filename=None):
        try:
            self.progress_bar.set(progress)
            progress_text = f"{progress * 100:.1f}% ({current_mb:.1f}/{total_mb:.1f} MB) - {speed_mb:.2f} MB/s - {eta_str}"
            self.progress_label.configure(text=progress_text)
            if filename:
                self.current_file_label.configure(text=f"Arquivo: {os.path.basename(filename)}")
            elif not self.downloading:
                self.current_file_label.configure(text="Nenhum arquivo em andamento")
        except Exception as e:
            print(f"Erro ao atualizar UI: {e}")

    # ---------- run ----------
    def run(self):
        self.mainloop()


# ---------- Entrypoint ----------
if __name__ == "__main__":
    # prepare csv_path variable used in download function
    # use default output dir if config exists, else current dir
    cfg = load_config() or {}
    default_out = cfg.get("output_path", "./downloads")
    csv_path = os.path.join(default_out, "videos_baixados.csv")

    app = TelegramDownloaderApp()
    app.run()
