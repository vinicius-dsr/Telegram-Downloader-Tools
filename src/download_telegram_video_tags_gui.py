#!/usr/bin/env python3
import asyncio
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional

import pandas as pd
import ttkbootstrap as ttk
from plyer import notification
from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from ttkbootstrap.constants import *

import tcl_fix

# --- Paths: garantir que config/session fiquem em src/ (diretório do script) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # deve ser src/
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# --- ttkbootstrap theme setup ---


# ---------------- Utilities ----------------
def safe_filename(s: str, max_length: int = 200) -> str:
    if not s:
        return "untitled"
    clean = "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip()
    while "  " in clean:
        clean = clean.replace("  ", " ")
    return clean[:max_length].rstrip() if len(clean) > max_length else clean


def load_config() -> Optional[Dict]:
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: não foi possível ler config.json: {e}")
    return None


def save_config(cfg: Dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar config.json: {e}")


def delete_config_and_session(session_name: str = "session"):
    try:
        if os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
    except Exception:
        pass
    try:
        session_file = os.path.join(BASE_DIR, f"{session_name}.session")
        if os.path.exists(session_file):
            os.remove(session_file)
    except Exception:
        pass


# ---------------- GUI App ----------------
class TelegramDownloaderGUI(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self._setup_theme()
        self.title("Telegram Video Downloader")
        self.geometry("1000x850")
        self.minsize(900, 700)
        try:
            self.configure(background=self.color_bg)
        except Exception:
            pass

        # state & stats
        self.config = load_config() or {}
        self.client: Optional[TelegramClient] = None

        self.downloading = False
        self.last_progress_time = time.time()
        self.last_progress_bytes = 0
        self.last_ui_update_time = 0.0
        self._download_loop: Optional[asyncio.AbstractEventLoop] = None

        # Build initial UI depending on config/session
        if self.config and self._session_exists(
            self.config.get("session_name", "session")
        ):
            # show main UI directly
            self._build_main_interface()
        else:
            # show login UI
            self._build_login_interface()

    def _setup_theme(self):
        style = ttk.Style()
        self.font_title = ("JetBrains Mono", 24, "bold")
        self.font_subtitle = ("JetBrains Mono", 11)
        self.font_label = ("JetBrains Mono", 10, "bold")
        self.font_body = ("JetBrains Mono", 10)
        self.font_mono = ("JetBrains Mono", 10)
        self.color_bg = "#101010"
        self.color_panel = "#101010"
        self.color_panel_alt = "#161616"
        self.color_accent = "#FFC799"
        self.color_text = "#FFFFFF"
        self.color_muted = "#A0A0A0"
        self.color_border = "#101010"
        self.color_success = "#90B99F"
        self.color_danger = "#F5A191"

        style.configure("App.TFrame", background=self.color_bg)
        style.configure("Panel.TFrame", background=self.color_panel)
        style.configure("PanelAlt.TFrame", background=self.color_panel_alt)
        style.configure(
            "Title.TLabel", font=self.font_title, foreground=self.color_text
        )
        style.configure(
            "Subtitle.TLabel", font=self.font_subtitle, foreground=self.color_muted
        )
        style.configure(
            "Field.TLabel", font=self.font_label, foreground=self.color_muted
        )
        style.configure("App.TLabel", font=self.font_body, foreground=self.color_text)
        style.configure(
            "FieldConsole.TLabel",
            font=self.font_label,
            foreground=self.color_muted,
        )
        style.configure("Header.TFrame", background=self.color_panel_alt)
        style.configure(
            "Header.TLabel",
            font=self.font_title,
            foreground=self.color_text,
            background=self.color_panel_alt,
        )
        style.configure(
            "HeaderSub.TLabel",
            font=self.font_subtitle,
            foreground=self.color_muted,
            background=self.color_panel_alt,
        )
        style.configure(
            "Section.TLabelframe",
            padding=16,
            background=self.color_panel,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Section.TLabelframe.Label",
            font=("JetBrains Mono", 11, "bold"),
            foreground=self.color_accent,
            background=self.color_panel,
        )
        style.configure(
            "Log.TLabelframe",
            padding=12,
            background=self.color_panel,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Log.TLabelframe.Label",
            font=("JetBrains Mono", 10, "bold"),
            foreground=self.color_accent,
            background=self.color_panel,
        )
        style.configure("TButton", font=("JetBrains Mono", 10, "bold"), padding=(12, 6))
        style.configure(
            "TEntry",
            fieldbackground=self.color_panel_alt,
            borderwidth=1,
            relief="solid",
        )

    # ---------- Login UI & Flow ----------
    def _build_login_interface(self):
        frame = ttk.Frame(self, padding=18, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        header = ttk.Frame(frame, padding=(20, 16), style="Header.TFrame")
        header.pack(fill="x", pady=(8, 20))
        ttk.Label(header, text="// Telegram Video Downloader", style="Header.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            header,
            text="// Conecte sua conta para iniciar os downloads.",
            style="HeaderSub.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        # API ID
        ttk.Label(frame, text="// API ID:", style="FieldConsole.TLabel").pack(
            anchor="w", pady=(8, 4)
        )
        self.login_api_id = ttk.Entry(frame, width=40)
        self.login_api_id.pack(fill="x", pady=(0, 12))
        if self.config.get("api_id"):
            self.login_api_id.insert(0, str(self.config.get("api_id")))

        # API Hash
        ttk.Label(frame, text="// API Hash:", style="FieldConsole.TLabel").pack(
            anchor="w", pady=(8, 4)
        )
        self.login_api_hash = ttk.Entry(frame, show="*", width=40)
        self.login_api_hash.pack(fill="x", pady=(0, 12))
        if self.config.get("api_hash"):
            self.login_api_hash.insert(0, self.config.get("api_hash"))

        # Phone
        ttk.Label(
            frame, text="// Telefone (ex: +55XXXXXXXXXXX):", style="FieldConsole.TLabel"
        ).pack(anchor="w", pady=(8, 4))
        self.login_phone = ttk.Entry(frame, width=25)
        self.login_phone.pack(fill="x", pady=(0, 12))
        if self.config.get("phone"):
            self.login_phone.insert(0, self.config.get("phone"))

        # status
        self.login_status = ttk.Label(frame, text="", style="App.TLabel")
        self.login_status.pack(pady=(8, 16))

        # buttons
        btn_frame = ttk.Frame(frame, style="App.TFrame")
        btn_frame.pack(pady=(8, 16), fill="x")
        ttk.Button(
            btn_frame,
            text="[CONECTAR E ENVIAR CÓDIGO]",
            bootstyle="success",
            command=self._start_login_thread,
        ).pack(side="left", expand=True, padx=8)
        ttk.Button(
            btn_frame, text="[SAIR]", bootstyle="danger", command=self.destroy
        ).pack(side="left", padx=8)

    def _start_login_thread(self):
        api_id = self.login_api_id.get().strip()
        api_hash = self.login_api_hash.get().strip()
        phone = self.login_phone.get().strip()

        if not api_id or not api_hash or not phone:
            messagebox.showwarning(
                "Aviso", "Preencha todos os campos (API ID, API Hash e telefone)."
            )
            return
        try:
            int(api_id)
        except ValueError:
            messagebox.showerror("Erro", "API ID deve ser um número.")
            return

        print(f"[DEBUG] Iniciando login com phone: {phone}")
        self.login_status.configure(text="Conectando...")
        self.update_idletasks()
        
        threading.Thread(
            target=lambda: asyncio.run(self._login_flow(api_id, api_hash, phone)),
            daemon=True,
        ).start()

    async def _login_flow(self, api_id: str, api_hash: str, phone: str):
        session_name = self.config.get("session_name", "session")
        print(f"[DEBUG] Criando TelegramClient para session: {session_name}")
        client = TelegramClient(
            os.path.join(BASE_DIR, session_name), int(api_id), api_hash
        )
        try:
            print(f"[DEBUG] Conectando ao Telegram...")
            await client.connect()
            print(f"[DEBUG] Conectado. Verificando autorização...")
        except Exception as e:
            print(f"[DEBUG] Erro ao conectar: {e}")
            self.after(
                0,
                lambda err=e: self.login_status.configure(
                    text=f"Erro ao conectar: {err}"
                ),
            )
            return

        try:
            if not await client.is_user_authorized():
                print(f"[DEBUG] Usuário não autorizado. Enviando código para {phone}...")
                try:
                    await client.send_code_request(phone)
                    print(f"[DEBUG] Código enviado com sucesso!")
                except Exception as e:
                    print(f"[DEBUG] Erro ao enviar código: {e}")
                    await client.disconnect()
                    self.after(
                        0,
                        lambda err=e: self.login_status.configure(
                            text=f"Erro ao enviar código: {err}"
                        ),
                    )
                    return

                code = await self._ask_modal_input_async(
                    "Código de verificação", "Digite o código enviado ao Telegram:"
                )
                if code is None:
                    await client.disconnect()
                    self.after(
                        0, lambda: self.login_status.configure(text="Login cancelado.")
                    )
                    return

                try:
                    await client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    # ask for 2FA password
                    pwd = await self._ask_modal_input_async(
                        "Senha 2FA", "Digite sua senha (2FA):", hide=True
                    )
                    if pwd is None:
                        await client.disconnect()
                        self.after(
                            0,
                            lambda: self.login_status.configure(text="2FA cancelada."),
                        )
                        return
                    try:
                        await client.sign_in(password=pwd)
                    except Exception as e:
                        await client.disconnect()
                        self.after(
                            0,
                            lambda err=e: self.login_status.configure(
                                text=f"Erro 2FA: {err}"
                            ),
                        )
                        return
                except Exception as e:
                    await client.disconnect()
                    self.after(
                        0,
                        lambda err=e: self.login_status.configure(
                            text=f"Erro ao autenticar: {err}"
                        ),
                    )
                    return

            # success: save config in src/
            cfg = {
                "api_id": int(api_id),
                "api_hash": api_hash,
                "phone": phone,
                "session_name": session_name,
                # defaults for UI fields (can be overridden later)
                "target": "",
                "tags": "",
                "output_path": "./downloads",
                "limit": "0",
                "max_flood_wait": "300",
                "name_line": "última",
            }
            save_config(cfg)
            self.config = cfg
            await client.disconnect()
            # switch to main UI on main thread
            self.after(0, self._build_main_interface)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _ask_modal_input_async(
        self, title: str, prompt: str, hide: bool = False
    ) -> Optional[str]:
        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        def _set_result_threadsafe(val: Optional[str]):
            if fut.done():
                return
            try:
                loop.call_soon_threadsafe(
                    lambda: fut.set_result(val) if not fut.done() else None
                )
            except Exception:
                if not fut.done():
                    fut.set_result(val)

        def show_dialog():
            dlg = ttk.Toplevel(self)
            dlg.title(title)
            dlg.geometry("400x200")
            dlg.transient(self)
            dlg.grab_set()

            ttk.Label(dlg, text=prompt).pack(padx=12, pady=(12, 6))
            entry = ttk.Entry(dlg, show="*" if hide else "")
            entry.pack(padx=12, pady=6, fill="x")
            entry.focus_set()

            def _ok():
                val = entry.get().strip()
                dlg.grab_release()
                dlg.destroy()
                _set_result_threadsafe(val)

            def _cancel():
                dlg.grab_release()
                dlg.destroy()
                _set_result_threadsafe(None)

            btns = ttk.Frame(dlg)
            btns.pack(pady=12)
            ttk.Button(
                btns, text="OK", width=12, bootstyle="primary", command=_ok
            ).pack(side="left", padx=8)
            ttk.Button(
                btns, text="Cancelar", width=12, bootstyle="secondary", command=_cancel
            ).pack(side="left", padx=8)

        self.after(0, show_dialog)
        try:
            return await fut
        except Exception:
            return None

    def _session_exists(self, session_name: str) -> bool:
        path = os.path.join(BASE_DIR, f"{session_name}.session")
        return os.path.exists(path)

    # ---------- Main Interface ----------
    def _build_main_interface(self):
        # clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        # main container with padding
        main_frame = ttk.Frame(self, padding=20, style="App.TFrame")
        main_frame.pack(fill="both", expand=True)

        header = ttk.Frame(main_frame, padding=(20, 16), style="Header.TFrame")
        header.pack(fill="x", pady=(8, 20))
        ttk.Label(header, text="// Telegram Video Downloader", style="Header.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            header,
            text="// Baixe vídeos por tags com controle total e histórico em CSV.",
            style="HeaderSub.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        # Create two-column layout for better organization
        config_container = ttk.Frame(main_frame, style="App.TFrame")
        config_container.pack(fill="x", pady=(0, 20))
        config_container.columnconfigure(0, weight=1)
        config_container.columnconfigure(1, weight=1)

        # Left column - Main settings
        left_frame = ttk.Labelframe(
            config_container,
            text="// CONFIGURAÇÕES PRINCIPAIS",
            style="Section.TLabelframe",
        )
        left_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")

        # Target
        ttk.Label(left_frame, text="// Canal/Grupo:", style="FieldConsole.TLabel").grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.target_entry = ttk.Entry(left_frame, width=35)
        self.target_entry.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self.target_entry.insert(0, self.config.get("target", ""))

        # Tags
        ttk.Label(left_frame, text="// Tags:", style="FieldConsole.TLabel").grid(
            row=2, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.tags_entry = ttk.Entry(left_frame, width=35)
        self.tags_entry.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="ew")
        self.tags_entry.insert(0, self.config.get("tags", ""))

        # Output path with browse
        ttk.Label(left_frame, text="// Pasta de saída:", style="FieldConsole.TLabel").grid(
            row=4, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        output_frame = ttk.Frame(left_frame, style="Panel.TFrame")
        output_frame.grid(row=5, column=0, padx=8, pady=(0, 8), sticky="ew")
        output_frame.columnconfigure(0, weight=1)
        self.output_entry = ttk.Entry(output_frame)
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.output_entry.insert(0, self.config.get("output_path", "./downloads"))
        ttk.Button(
            output_frame,
            text="[PROCURAR]",
            command=self._browse_output,
            bootstyle="secondary",
        ).grid(row=0, column=1)

        left_frame.columnconfigure(0, weight=1)

        # Right column - Advanced settings
        right_frame = ttk.Labelframe(
            config_container,
            text="// CONFIGURAÇÕES AVANÇADAS",
            style="Section.TLabelframe",
        )
        right_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")

        # Limit
        ttk.Label(right_frame, text="// Limite por tag:", style="FieldConsole.TLabel").grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.limit_entry = ttk.Entry(right_frame, width=20)
        self.limit_entry.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="w")
        self.limit_entry.insert(0, str(self.config.get("limit", "0")))

        # Session name
        ttk.Label(right_frame, text="// Nome da sessão:", style="FieldConsole.TLabel").grid(
            row=2, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.session_entry = ttk.Entry(right_frame, width=20)
        self.session_entry.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="w")
        self.session_entry.insert(
            0, self.config.get("session_name", self.config.get("session", "session"))
        )

        # Max flood wait
        ttk.Label(right_frame, text="// Max Flood Wait (s):", style="FieldConsole.TLabel").grid(
            row=4, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.max_flood_entry = ttk.Entry(right_frame, width=20)
        self.max_flood_entry.grid(row=5, column=0, padx=8, pady=(0, 8), sticky="w")
        self.max_flood_entry.insert(0, str(self.config.get("max_flood_wait", "60")))

        # Name line
        ttk.Label(
            right_frame, text="// Linha do nome do vídeo:", style="FieldConsole.TLabel"
        ).grid(row=6, column=0, sticky="w", padx=8, pady=(8, 4))
        self.name_line_var = ttk.StringVar(value=self.config.get("name_line", "última"))
        name_line_frame = ttk.Frame(right_frame, style="Panel.TFrame")
        name_line_frame.grid(row=7, column=0, padx=8, pady=(0, 8), sticky="w")
        for opt in ["primeira", "segunda", "terceira", "última"]:
            rb = ttk.Radiobutton(
                name_line_frame,
                text=opt.capitalize(),
                variable=self.name_line_var,
                value=opt,
            )
            rb.pack(side="left", padx=(0, 12))

        # Config buttons
        cfg_btn_frame = ttk.Frame(main_frame, style="App.TFrame")
        cfg_btn_frame.pack(fill="x", pady=(0, 20))
        ttk.Button(
            cfg_btn_frame,
            text="[SALVAR CONFIGURAÇÃO]",
            command=self._save_ui_config,
            bootstyle="success",
        ).pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(
            cfg_btn_frame,
            text="[CARREGAR CONFIGURAÇÃO]",
            command=self._load_config_file,
            bootstyle="info",
        ).pack(side="left", padx=8, fill="x", expand=True)

        # Action buttons
        btn_frame = ttk.Frame(main_frame, style="App.TFrame")
        btn_frame.pack(fill="x", pady=(0, 20))
        self.download_btn = ttk.Button(
            btn_frame,
            text="[INICIAR DOWNLOAD]",
            command=self._start_download,
            bootstyle="success",
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.stop_btn = ttk.Button(
            btn_frame,
            text="[PARAR DOWNLOAD]",
            command=self._stop_download,
            bootstyle="danger",
            state="disabled",
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Progress frame
        prog_frame = ttk.Labelframe(
            main_frame, text="// PROGRESSO", style="Section.TLabelframe"
        )
        prog_frame.pack(fill="x", pady=(0, 20))
        self.current_file_label = ttk.Label(
            prog_frame, text="// Nenhum arquivo em andamento", style="Subtitle.TLabel"
        )
        self.current_file_label.pack(fill="x", padx=8, pady=(8, 4))
        self.progress_bar = ttk.Progressbar(
            prog_frame, mode="determinate", bootstyle="success-striped"
        )
        self.progress_bar.pack(fill="x", padx=8, pady=6)
        self.progress_label = ttk.Label(
            prog_frame, text="// Aguardando...", style="Subtitle.TLabel"
        )
        self.progress_label.pack(anchor="w", padx=8, pady=(0, 8))

        # Log area (collapsible)
        log_frame = ttk.Labelframe(
            main_frame, text="// LOG DE OPERAÇÕES", style="Log.TLabelframe"
        )
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        log_header = ttk.Frame(log_frame, style="Panel.TFrame")
        log_header.pack(fill="x", padx=8, pady=(8, 4))
        self.log_visible = ttk.BooleanVar(value=False)
        self.toggle_log_btn = ttk.Button(
            log_header,
            text="[MOSTRAR LOG]",
            command=self._toggle_log,
            bootstyle="secondary",
        )
        self.toggle_log_btn.pack(side="left", padx=8)
        self.log_content_frame = ttk.Frame(log_frame, style="Panel.TFrame")
        self.log_text = ttk.Text(
            self.log_content_frame,
            wrap="word",
            font=self.font_mono,
            height=10,
            background=self.color_panel_alt,
            foreground=self.color_text,
            insertbackground=self.color_text,
            borderwidth=1,
            relief="solid",
        )
        scrollbar = ttk.Scrollbar(
            self.log_content_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(
            side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8)
        )
        scrollbar.pack(side="right", fill="y", pady=(0, 8))
        self.log_content_frame.pack_forget()

        # Logout button
        ttk.Button(
            main_frame, text="[LOGOUT]", command=self._logout, bootstyle="secondary"
        ).pack(pady=(12, 8))

        self.update_idletasks()

    # ---------- UI helpers ----------
    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Selecionar pasta de saída")
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)

    def _toggle_log(self):
        if self.log_visible.get():
            self.log_content_frame.pack_forget()
            self.toggle_log_btn.configure(text="[MOSTRAR LOG]")
            self.log_visible.set(False)
        else:
            self.log_content_frame.pack(fill="both", expand=True, padx=6, pady=4)
            self.toggle_log_btn.configure(text="[OCULTAR LOG]")
            self.log_visible.set(True)
        self.update_idletasks()

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        if threading.current_thread() is threading.main_thread():
            self._append_log_line(line)
        else:
            self.after(0, self._append_log_line, line)

    def _append_log_line(self, line: str):
        try:
            if not hasattr(self, "log_text"):
                print(line)
                return
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            print(line)

    # ---------- Config saving/loading from main UI ----------
    def _save_ui_config(self):
        cfg = load_config() or {}
        cfg.update(
            {
                "target": self.target_entry.get().strip(),
                "tags": self.tags_entry.get().strip(),
                "output_path": self.output_entry.get().strip(),
                "limit": self.limit_entry.get().strip(),
                "session_name": self.session_entry.get().strip()
                or cfg.get("session_name", "session"),
                "max_flood_wait": self.max_flood_entry.get().strip(),
                "name_line": self.name_line_var.get(),
            }
        )
        save_config(cfg)
        self.config = cfg
        messagebox.showinfo("Sucesso", "Configuração salva em config.json (pasta src/)")
        self._log("Configuração salva em config.json")

    def _load_config_file(self):
        file_path = filedialog.askopenfilename(
            title="Carregar Configuração",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # apply to fields
            if "target" in cfg:
                self.target_entry.delete(0, "end")
                self.target_entry.insert(0, cfg.get("target", ""))
            if "tags" in cfg:
                self.tags_entry.delete(0, "end")
                self.tags_entry.insert(0, cfg.get("tags", ""))
            if "output_path" in cfg:
                self.output_entry.delete(0, "end")
                self.output_entry.insert(0, cfg.get("output_path", "./downloads"))
            if "limit" in cfg:
                self.limit_entry.delete(0, "end")
                self.limit_entry.insert(0, str(cfg.get("limit", "0")))
            if "session_name" in cfg:
                self.session_entry.delete(0, "end")
                self.session_entry.insert(0, cfg.get("session_name", "session"))
            if "max_flood_wait" in cfg:
                self.max_flood_entry.delete(0, "end")
                self.max_flood_entry.insert(0, str(cfg.get("max_flood_wait", "300")))
            if "name_line" in cfg:
                self.name_line_var.set(cfg.get("name_line", "última"))
            messagebox.showinfo("Sucesso", f"Configuração carregada de:\n{file_path}")
            self._log(f"Configuração carregada: {file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar configuração:\n{e}")
            self._log(f"Erro ao carregar configuração: {e}")

    # ---------- Logout ----------
    def _logout(self):
        session_name = self.session_entry.get().strip() or self.config.get(
            "session_name", "session"
        )
        if messagebox.askyesno(
            "Confirmar logout", "Deseja limpar config.json e a sessão local?"
        ):
            delete_config_and_session(session_name)
            messagebox.showinfo(
                "Logout",
                "Sessão e config removidos. O app será reiniciado para o login.",
            )
            # restart UI to login
            self.config = {}
            self._build_login_interface()

    # ---------- Validate main inputs ----------
    def _validate_main_inputs(self) -> bool:
        target = self.target_entry.get().strip()
        if not target:
            self._log("Erro: Canal/Grupo é obrigatório!")
            return False
        tags_text = self.tags_entry.get().strip()
        if not tags_text:
            self._log("Erro: Tags são obrigatórias!")
            return False
        tags_list = [
            t.strip() for t in tags_text.replace(" ", ",").split(",") if t.strip()
        ]
        if not tags_list:
            self._log("Erro: Nenhuma tag válida encontrada!")
            return False
        # update formatted tags
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, ", ".join(tags_list))
        out = self.output_entry.get().strip()
        if not out:
            self._log("Erro: Diretório de saída é obrigatório!")
            return False
        # try create dir if not exists
        try:
            Path(out).mkdir(parents=True, exist_ok=True)
        except Exception:
            self._log("Erro: Diretório de saída inválido ou não pode ser criado!")
            return False
        try:
            int(self.limit_entry.get().strip())
        except Exception:
            self._log("Erro: Limite deve ser um número!")
            return False
        try:
            int(self.max_flood_entry.get().strip())
        except Exception:
            self._log("Erro: Max Flood Wait deve ser um número!")
            return False
        if not self.session_entry.get().strip():
            self._log("Erro: Nome da sessão é obrigatório!")
            return False
        return True

    # ---------- Download threading & async wrapper ----------
    def _start_download(self):
        if not self._validate_main_inputs():
            return
        self.downloading = True
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        # clear log box
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass
        self.progress_bar.config(value=0)
        self.progress_label.configure(text="Iniciando...")
        self.current_file_label.configure(text="Preparando...")
        if not self.log_visible.get():
            self._toggle_log()
        self.update_idletasks()
        threading.Thread(
            target=lambda: asyncio.run(self._download_videos_async()), daemon=True
        ).start()

    def _stop_download(self):
        self.downloading = False
        self._log("Parando download...")
        if self.client and self._download_loop:

            def _disconnect():
                try:
                    asyncio.create_task(self.client.disconnect())
                except Exception:
                    pass

            try:
                self._download_loop.call_soon_threadsafe(_disconnect)
            except Exception:
                pass
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_idletasks()

    # ---------- Core download logic (async) ----------
    async def _download_videos_async(self):
        self._download_loop = asyncio.get_running_loop()
        cfg = load_config() or self.config or {}
        if not cfg.get("api_id") or not cfg.get("api_hash"):
            msg_err = (
                "api_id/api_hash não encontrados no config.json.\nFaça login novamente."
            )
            self._log(f"Erro: {msg_err}")
            self._show_notification("Erro de Configuração", msg_err, "error")
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            return

        api_id = int(cfg["api_id"])
        api_hash = cfg["api_hash"]

        # UI fields override config fields
        target = self.target_entry.get().strip()
        tags_str = self.tags_entry.get().strip()
        out_path = self.output_entry.get().strip()
        limit = int(self.limit_entry.get().strip() or 0)
        session_name = self.session_entry.get().strip() or cfg.get(
            "session_name", "session"
        )
        max_flood_wait = int(
            self.max_flood_entry.get().strip() or cfg.get("max_flood_wait", 300)
        )
        name_line_choice = self.name_line_var.get()

        # Ensure output dir
        Path(out_path).mkdir(parents=True, exist_ok=True)

        # Prepare CSV path in output and a backup in src
        csv_path_out = os.path.join(out_path, "videos_baixados.csv")
        csv_backup_path = os.path.join(
            BASE_DIR, f"videos_baixados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        if not tags:
            self._log("Nenhuma tag válida informada!")
            self._show_notification(
                "Erro de Input", "Nenhuma tag válida informada!", "error"
            )
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            return

        client = TelegramClient(os.path.join(BASE_DIR, session_name), api_id, api_hash)
        self.client = client
        try:
            await client.start()
            me = await client.get_me()
            self._log(
                f"Conectado como: {getattr(me, 'username', None) or getattr(me, 'first_name', str(me))}"
            )
        except Exception as e:
            self._log(f"Erro ao conectar: {e}")
            self._show_notification(
                "Erro de Conexão",
                f"Não foi possível conectar ao Telegram:\n{e}",
                "error",
            )
            return

        registros: List[Dict] = []
        total_baixados = 0
        total_encontrados = 0
        total_erros = 0

        for tag in tags:
            if not self.downloading:
                self._log("Download cancelado pelo usuário.")
                break

            self._log(f"\nProcurando vídeos com a tag: {tag}")
            count_tag = 0

            # resolve entity with FloodWait handling
            entity = None
            while self.downloading and entity is None:
                try:
                    entity = await client.get_input_entity(target)
                except FloodWaitError as e:
                    self._log(f"Flood wait ao resolver target ({e.seconds}s)")
                    if e.seconds > max_flood_wait:
                        self._log(f"Flood wait muito longo ({e.seconds}s). Abortando.")
                        await client.disconnect()
                        return
                    self._log(f"Aguardando {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    self._log(f"Erro ao resolver entidade: {e}")
                    self._show_notification(
                        "Erro de Target",
                        f"Não foi possível encontrar o canal/grupo:\n{target}\n\nErro: {e}",
                        "error",
                    )
                    await client.disconnect()
                    return

            if not self.downloading:
                break

            seen_msg_ids = set()
            while self.downloading:
                try:
                    async for msg in client.iter_messages(entity, search=tag):
                        if not self.downloading:
                            break

                        if msg.id in seen_msg_ids:
                            continue
                        seen_msg_ids.add(msg.id)
                        total_encontrados += 1

                        if not msg.message or tag not in msg.message:
                            continue
                        if not getattr(msg, "media", None):
                            continue

                        is_video = getattr(msg, "video", None) is not None
                        mime = getattr(msg.media, "mime_type", "") if msg.media else ""
                        if not is_video and not mime.startswith("video"):
                            # document heuristic
                            try:
                                d = getattr(msg.media, "document", None)
                                if d is None:
                                    continue
                                attrs = getattr(d, "attributes", [])
                                if not any("video" in str(a).lower() for a in attrs):
                                    continue
                            except Exception:
                                continue

                        # extract video name
                        lines = [
                            l.strip()
                            for l in (msg.message or "").split("\n")
                            if l.strip()
                        ]
                        if not lines:
                            video_name = f"msg{msg.id}"
                        else:
                            if name_line_choice == "primeira":
                                video_name = lines[0]
                            elif name_line_choice == "segunda":
                                video_name = lines[1] if len(lines) > 1 else lines[0]
                            elif name_line_choice == "terceira":
                                video_name = lines[2] if len(lines) > 2 else lines[-1]
                            else:
                                video_name = lines[-1]
                        while video_name.startswith("="):
                            video_name = video_name[1:].strip()

                        filename = safe_filename(video_name) + ".mp4"
                        file_path = os.path.join(out_path, filename)

                        if os.path.exists(file_path):
                            self._log(f"Já existe: {filename}")
                            continue

                        try:
                            self._log(f"Baixando: {filename}")

                            # reset progress counters
                            self.last_progress_time = time.time()
                            self.last_progress_bytes = 0

                            # update UI filename
                            self.after(
                                0,
                                lambda f=file_path: self.current_file_label.configure(
                                    text=f"Arquivo: {os.path.basename(f)}"
                                ),
                            )

                            def progress_wrapper(current, total):
                                try:
                                    if current is None or total is None:
                                        return
                                    self._progress_callback(current, total, file_path)
                                except Exception:
                                    pass

                            await client.download_media(
                                msg, file=file_path, progress_callback=progress_wrapper
                            )

                            self._log(f"Concluído: {filename}")
                            total_baixados += 1
                            count_tag += 1
                            registros.append(
                                {
                                    "tag": tag,
                                    "msg_id": msg.id,
                                    "data": msg.date.strftime("%Y-%m-%d %H:%M:%S")
                                    if msg.date
                                    else "",
                                    "arquivo": filename,
                                    "legenda": msg.message or "",
                                }
                            )

                        except FloodWaitError as e:
                            self._log(f"Flood wait ({e.seconds}s) → aguardando...")
                            if e.seconds <= max_flood_wait:
                                await asyncio.sleep(e.seconds + 1)
                                continue
                            else:
                                self._log("Flood wait muito longo, pulando arquivo.")
                                continue
                        except Exception as e:
                            self._log(f"Erro ao baixar msg {msg.id}: {e}")
                            total_erros += 1
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception:
                                pass
                            continue

                        if limit and count_tag >= limit:
                            break

                    break  # finished iter_messages
                except FloodWaitError as e:
                    self._log(f"Flood wait durante iteração ({e.seconds}s)")
                    if e.seconds > max_flood_wait:
                        self._log(f"Flood wait muito longo ({e.seconds}s). Abortando.")
                        await client.disconnect()
                        return
                    self._log(f"Aguardando {e.seconds}s e reiniciando...")
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    self._log(f"Erro ao processar mensagens: {e}")
                    break

            if self.downloading:
                self._log(f"Tag {tag}: {count_tag} vídeos baixados.")

        # disconnect
        try:
            await client.disconnect()
        except Exception:
            pass
        self.client = None
        self._download_loop = None

        # save CSV in output and backup in src/
        if registros:
            try:
                df = pd.DataFrame(registros)
                df.to_csv(csv_path_out, index=False, encoding="utf-8-sig")
                df.to_csv(csv_backup_path, index=False, encoding="utf-8-sig")
                self._log(f"\nCSV salvo em: {csv_path_out}")
                self._log(f"Cópia do CSV salva em: {csv_backup_path}")
            except Exception as e:
                self._log(f"Erro ao salvar CSV: {e}")

        self._log(
            f"\nFinalizado: {total_baixados} vídeos baixados ({total_encontrados} mensagens verificadas). Erros: {total_erros}"
        )
        self.after(0, lambda: self.progress_bar.config(value=100))
        self.after(0, lambda: self.progress_label.configure(text="Concluído!"))

        # Notification
        if total_erros > 0:
            msg = f"Download concluído com alertas!\n\nBaixados: {total_baixados}\nErros: {total_erros}\nVerifique o log para detalhes."
            self._show_notification("Concluído (com erros)", msg, "warning")
        else:
            msg = f"Download concluído com sucesso!\n\nBaixados: {total_baixados}\nTotal verificado: {total_encontrados}"
            self._show_notification("Concluído", msg, "info")

        self.downloading = False
        self.after(0, lambda: self.download_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))

    # ---------- Progress helpers ----------
    def _progress_callback(
        self, current: int, total: int, filepath: Optional[str] = None
    ):
        if total <= 0:
            return
        try:
            progress = float(current) / float(total) if total else 0.0
            current_time = time.time()
            if current < total and (current_time - self.last_ui_update_time) < 0.2:
                return
            time_diff = current_time - self.last_progress_time
            bytes_diff = current - self.last_progress_bytes
            speed_mb = (
                (bytes_diff / time_diff / (1024 * 1024)) if time_diff > 0 else 0.0
            )
            self.last_progress_time = current_time
            self.last_progress_bytes = current
            self.last_ui_update_time = current_time
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            if speed_mb > 0 and current > 0:
                bytes_remaining = total - current
                # speed_mb is MB/s; convert to bytes/s for ETA calc or use MB units consistently
                # bytes_remaining / (speed_mb * 1024*1024)
                eta_seconds = (
                    int(bytes_remaining / (speed_mb * 1024 * 1024))
                    if speed_mb > 0
                    else 0
                )
                eta_min = eta_seconds // 60
                eta_sec = eta_seconds % 60
                eta_str = f"ETA: {eta_min}m{eta_sec:02d}s"
            else:
                eta_str = "ETA: --"
            # schedule UI update
            self.after(
                0,
                self._update_progress_ui,
                progress,
                current_mb,
                total_mb,
                speed_mb,
                eta_str,
                filepath,
            )
        except Exception:
            pass

    def _update_progress_ui(
        self, progress, current_mb, total_mb, speed_mb, eta_str, filename=None
    ):
        try:
            self.progress_bar["value"] = progress * 100
            progress_text = f"{progress * 100:.1f}% ({current_mb:.1f}/{total_mb:.1f} MB) - {speed_mb:.2f} MB/s - {eta_str}"
            self.progress_label.configure(text=progress_text)
            if filename:
                self.current_file_label.configure(
                    text=f"Arquivo: {os.path.basename(filename)}"
                )
            elif not self.downloading:
                self.current_file_label.configure(text="Nenhum arquivo em andamento")
        except Exception as e:
            print(f"Erro ao atualizar UI: {e}")

    # ---------- run ----------
    def _show_notification(self, title: str, message: str, type_: str = "info"):
        """
        Thread-safe helper to show system notification using plyer.
        It launches the notification in a separate thread to avoid freezing the GUI.
        """

        def _notify():
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Telegram Downloader",
                    timeout=10,
                )
            except Exception as e:
                print(f"Erro ao exibir notificação: {e}")
                # Fallback to tkinter if plyer fails (e.g. missing dependencies on linux)
                self.after(
                    0,
                    lambda: (
                        messagebox.showinfo(title, message)
                        if type_ == "info"
                        else messagebox.showwarning(title, message)
                        if type_ == "warning"
                        else messagebox.showerror(title, message)
                    ),
                )

        threading.Thread(target=_notify, daemon=True).start()

    def run(self):
        self.mainloop()


# ---------- Entrypoint ----------
if __name__ == "__main__":
    app = TelegramDownloaderGUI()
    app.run()
