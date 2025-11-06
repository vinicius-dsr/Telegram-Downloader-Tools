#!/usr/bin/env python3
import os
import json
import time
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd
import customtkinter as ctk
from tkinter import messagebox, filedialog

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# --- Paths: garantir que config/session fiquem em src/ (diretório do script) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # deve ser src/
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# --- CTk appearance ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


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
class TelegramDownloaderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Telegram Video Downloader")
        self.geometry("900x800")
        self.minsize(800, 600)

        # state & stats
        self.config = load_config() or {}
        self.client: Optional[TelegramClient] = None

        self.downloading = False
        self.last_progress_time = time.time()
        self.last_progress_bytes = 0

        # Build initial UI depending on config/session
        if self.config and self._session_exists(self.config.get("session_name", "session")):
            # show main UI directly
            self._build_main_interface()
        else:
            # show login UI
            self._build_login_interface()

    # ---------- Login UI & Flow ----------
    def _build_login_interface(self):
        self._clear()
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(frame, text="Configurar conta Telegram", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(4, 12))

        # API ID
        ctk.CTkLabel(frame, text="API ID:").pack(anchor="w")
        self.login_api_id = ctk.CTkEntry(frame)
        self.login_api_id.pack(fill="x", pady=(0, 8))
        if self.config.get("api_id"):
            self.login_api_id.insert(0, str(self.config.get("api_id")))

        # API Hash
        ctk.CTkLabel(frame, text="API Hash:").pack(anchor="w")
        self.login_api_hash = ctk.CTkEntry(frame, show="*")
        self.login_api_hash.pack(fill="x", pady=(0, 8))
        if self.config.get("api_hash"):
            self.login_api_hash.insert(0, self.config.get("api_hash"))

        # Phone
        ctk.CTkLabel(frame, text="Telefone (ex: +55XXXXXXXXXXX):").pack(anchor="w")
        self.login_phone = ctk.CTkEntry(frame)
        self.login_phone.pack(fill="x", pady=(0, 8))
        if self.config.get("phone"):
            self.login_phone.insert(0, self.config.get("phone"))

        # status
        self.login_status = ctk.CTkLabel(frame, text="")
        self.login_status.pack(pady=(4, 8))

        # buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=6)
        ctk.CTkButton(btn_frame, text="Conectar e enviar código", command=self._start_login_thread).pack(side="left", expand=True, padx=6)
        ctk.CTkButton(btn_frame, text="Sair", fg_color="red", hover_color="#a30000", command=self.destroy).pack(side="left", padx=6)

    def _start_login_thread(self):
        # read fields
        api_id = self.login_api_id.get().strip()
        api_hash = self.login_api_hash.get().strip()
        phone = self.login_phone.get().strip()

        if not api_id or not api_hash or not phone:
            messagebox.showwarning("Aviso", "Preencha todos os campos (API ID, API Hash e telefone).")
            return
        try:
            int(api_id)
        except ValueError:
            messagebox.showerror("Erro", "API ID deve ser um número.")
            return

        self.login_status.configure(text="Conectando...", text_color="gray")
        # run async login flow in background thread
        threading.Thread(target=lambda: asyncio.run(self._login_flow(api_id, api_hash, phone)), daemon=True).start()

    async def _login_flow(self, api_id: str, api_hash: str, phone: str):
        session_name = self.config.get("session_name", "session")
        client = TelegramClient(os.path.join(BASE_DIR, session_name), int(api_id), api_hash)
        try:
            await client.connect()
        except Exception as e:
            self.after(0, lambda err=e: self.login_status.configure(text=f"Erro ao conectar: {err}", text_color="red"))
            return

        try:
            if not await client.is_user_authorized():
                # send code
                try:
                    await client.send_code_request(phone)
                except Exception as e:
                    await client.disconnect()
                    self.after(0, lambda err=e: self.login_status.configure(text=f"Erro ao enviar código: {err}", text_color="red"))
                    return

                code = await self._ask_modal_input_async("Código de verificação", "Digite o código enviado ao Telegram:")
                if code is None:
                    await client.disconnect()
                    self.after(0, lambda: self.login_status.configure(text="Login cancelado.", text_color="red"))
                    return

                try:
                    await client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    # ask for 2FA password
                    pwd = await self._ask_modal_input_async("Senha 2FA", "Digite sua senha (2FA):", hide=True)
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

    async def _ask_modal_input_async(self, title: str, prompt: str, hide: bool = False) -> Optional[str]:
        """
        Show a simple modal CTk dialog to get input from user and return it.
        Works by scheduling the dialog in the main thread and awaiting a future.
        """
        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        def show_dialog():
            dlg = ctk.CTkToplevel(self)
            dlg.title(title)
            dlg.geometry("360x140")
            dlg.transient(self)
            dlg.grab_set()

            ctk.CTkLabel(dlg, text=prompt).pack(padx=12, pady=(12, 6))
            entry = ctk.CTkEntry(dlg, show="*" if hide else "")
            entry.pack(padx=12, pady=(0, 12), fill="x")

            def _ok():
                val = entry.get().strip()
                dlg.grab_release()
                dlg.destroy()
                if not fut.done():
                    fut.set_result(val)

            def _cancel():
                dlg.grab_release()
                dlg.destroy()
                if not fut.done():
                    fut.set_result(None)

            btns = ctk.CTkFrame(dlg)
            btns.pack(pady=(0, 12))
            ctk.CTkButton(btns, text="OK", width=100, command=_ok).pack(side="left", padx=8)
            ctk.CTkButton(btns, text="Cancelar", width=100, command=_cancel).pack(side="left", padx=8)

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
        self._clear()
        # reload config in case changed
        self.config = load_config() or self.config or {}

        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main_frame, text="Telegram Video Downloader", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(8, 12))

        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=8, pady=6)
        input_frame.columnconfigure(1, weight=1)

        # Target
        ctk.CTkLabel(input_frame, text="Canal/Grupo:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=6, pady=5)
        self.target_entry = ctk.CTkEntry(input_frame, width=400, placeholder_text="@nome ou https://t.me/nome")
        self.target_entry.grid(row=0, column=1, padx=6, pady=5, sticky="ew")
        if self.config.get("target"):
            self.target_entry.insert(0, self.config.get("target"))

        # Tags
        ctk.CTkLabel(input_frame, text="Tags:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=6, pady=5)
        self.tags_entry = ctk.CTkEntry(input_frame, width=400, placeholder_text="#tag1,#tag2")
        self.tags_entry.grid(row=1, column=1, padx=6, pady=5, sticky="ew")
        if self.config.get("tags"):
            self.tags_entry.insert(0, self.config.get("tags"))

        # Output path with browse
        ctk.CTkLabel(input_frame, text="Pasta de saída:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=6, pady=5)
        output_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        output_frame.grid(row=2, column=1, sticky="ew", padx=6, pady=5)
        output_frame.columnconfigure(0, weight=1)
        self.output_entry = ctk.CTkEntry(output_frame, placeholder_text="./downloads")
        self.output_entry.insert(0, self.config.get("output_path", "./downloads"))
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(output_frame, text="Procurar", width=100, command=self._browse_output).grid(row=0, column=1)

        # Limit
        ctk.CTkLabel(input_frame, text="Limite por tag:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", padx=6, pady=5)
        self.limit_entry = ctk.CTkEntry(input_frame, width=120)
        self.limit_entry.grid(row=3, column=1, sticky="w", padx=6, pady=5)
        self.limit_entry.insert(0, str(self.config.get("limit", "0")))

        # Session name
        ctk.CTkLabel(input_frame, text="Nome da sessão:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", padx=6, pady=5)
        self.session_entry = ctk.CTkEntry(input_frame, width=160)
        self.session_entry.grid(row=4, column=1, sticky="w", padx=6, pady=5)
        self.session_entry.insert(0, self.config.get("session_name", self.config.get("session", "session")))

        # Name line
        ctk.CTkLabel(input_frame, text="Linha do nome do vídeo:", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, sticky="w", padx=6, pady=5)
        self.name_line_var = ctk.StringVar(value=self.config.get("name_line", "última"))
        name_line_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        name_line_frame.grid(row=5, column=1, sticky="w", padx=6, pady=5)
        for opt in ["primeira", "segunda", "terceira", "última"]:
            rb = ctk.CTkRadioButton(name_line_frame, text=opt.capitalize(), variable=self.name_line_var, value=opt)
            rb.pack(side="left", padx=4)

        # Max flood wait
        ctk.CTkLabel(input_frame, text="Max Flood Wait (s):", font=ctk.CTkFont(weight="bold")).grid(row=6, column=0, sticky="w", padx=6, pady=5)
        self.max_flood_entry = ctk.CTkEntry(input_frame, width=120)
        self.max_flood_entry.grid(row=6, column=1, sticky="w", padx=6, pady=5)
        self.max_flood_entry.insert(0, str(self.config.get("max_flood_wait", "300")))

        # Save / Load config buttons (affect config.json in src/)
        cfg_btn_frame = ctk.CTkFrame(main_frame)
        cfg_btn_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(cfg_btn_frame, text="💾 Salvar Configuração", command=self._save_ui_config, fg_color="green").pack(side="left", padx=6, fill="x", expand=True)
        ctk.CTkButton(cfg_btn_frame, text="📂 Carregar Configuração", command=self._load_config_file, fg_color="orange").pack(side="left", padx=6, fill="x", expand=True)

        # Download control
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", padx=8, pady=6)
        self.download_btn = ctk.CTkButton(btn_frame, text="▶ Iniciar Download", command=self._start_download, height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.download_btn.pack(side="left", padx=6, fill="x", expand=True)
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ Parar", command=self._stop_download, height=40, fg_color="red", hover_color="darkred", state="disabled")
        self.stop_btn.pack(side="left", padx=6, fill="x", expand=True)

        # Progress section
        prog_frame = ctk.CTkFrame(main_frame)
        prog_frame.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(prog_frame, text="Progresso:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=6)
        self.current_file_label = ctk.CTkLabel(prog_frame, text="Nenhum arquivo em andamento", font=ctk.CTkFont(size=11, slant="italic"))
        self.current_file_label.pack(fill="x", padx=6, pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(prog_frame)
        self.progress_bar.pack(fill="x", padx=6, pady=4)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(prog_frame, text="Aguardando...", font=ctk.CTkFont(size=12))
        self.progress_label.pack(anchor="w", padx=6, pady=(0, 6))

        # Log area (collapsible)
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=8, pady=6)
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=6)
        self.log_visible = ctk.BooleanVar(value=False)
        self.toggle_log_btn = ctk.CTkButton(log_header, text="📋 Mostrar Log ▼", command=self._toggle_log, width=150, fg_color="transparent", hover_color=("gray80","gray30"))
        self.toggle_log_btn.pack(side="left", padx=6)
        self.log_content_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        self.log_text = ctk.CTkTextbox(self.log_content_frame, wrap="word", font=ctk.CTkFont(family="Courier", size=11))
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_content_frame.pack_forget()

        # Logout button
        ctk.CTkButton(main_frame, text="Sair (logout)", fg_color="gray", command=self._logout).pack(pady=8)

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
            self.toggle_log_btn.configure(text="📋 Mostrar Log ▼")
            self.log_visible.set(False)
        else:
            self.log_content_frame.pack(fill="both", expand=True, padx=6, pady=4)
            self.toggle_log_btn.configure(text="📋 Ocultar Log ▲")
            self.log_visible.set(True)
        self.update_idletasks()

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            print(line)

    # ---------- Config saving/loading from main UI ----------
    def _save_ui_config(self):
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
        messagebox.showinfo("Sucesso", "Configuração salva em config.json (pasta src/)")
        self._log("✅ Configuração salva em config.json")

    def _load_config_file(self):
        file_path = filedialog.askopenfilename(title="Carregar Configuração", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # apply to fields
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
                self.name_line_var.set(cfg.get("name_line","última"))
            messagebox.showinfo("Sucesso", f"Configuração carregada de:\n{file_path}")
            self._log(f"✅ Configuração carregada: {file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar configuração:\n{e}")
            self._log(f"❌ Erro ao carregar configuração: {e}")

    # ---------- Logout ----------
    def _logout(self):
        session_name = (self.session_entry.get().strip() or self.config.get("session_name", "session"))
        if messagebox.askyesno("Confirmar logout", "Deseja limpar config.json e a sessão local?"):
            delete_config_and_session(session_name)
            messagebox.showinfo("Logout", "Sessão e config removidos. O app será reiniciado para o login.")
            # restart UI to login
            self.config = {}
            self._build_login_interface()

    # ---------- Validate main inputs ----------
    def _validate_main_inputs(self) -> bool:
        target = self.target_entry.get().strip()
        if not target:
            self._log("❌ Erro: Canal/Grupo é obrigatório!")
            return False
        tags_text = self.tags_entry.get().strip()
        if not tags_text:
            self._log("❌ Erro: Tags são obrigatórias!")
            return False
        tags_list = [t.strip() for t in tags_text.replace(" ", ",").split(",") if t.strip()]
        if not tags_list:
            self._log("❌ Erro: Nenhuma tag válida encontrada!")
            return False
        # update formatted tags
        self.tags_entry.delete(0, "end"); self.tags_entry.insert(0, ", ".join(tags_list))
        out = self.output_entry.get().strip()
        if not out:
            self._log("❌ Erro: Diretório de saída é obrigatório!")
            return False
        # try create dir if not exists
        try:
            Path(out).mkdir(parents=True, exist_ok=True)
        except Exception:
            self._log("❌ Erro: Diretório de saída inválido ou não pode ser criado!")
            return False
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
        if not self.session_entry.get().strip():
            self._log("❌ Erro: Nome da sessão é obrigatório!")
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
        self.progress_bar.set(0)
        self.progress_label.configure(text="Iniciando...")
        self.current_file_label.configure(text="Preparando...")
        if not self.log_visible.get():
            self._toggle_log()
        self.update_idletasks()
        threading.Thread(target=lambda: asyncio.run(self._download_videos_async()), daemon=True).start()

    def _stop_download(self):
        self.downloading = False
        self._log("⏹ Parando download...")
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_idletasks()

    # ---------- Core download logic (async) ----------
    async def _download_videos_async(self):
        cfg = load_config() or self.config or {}
        if not cfg.get("api_id") or not cfg.get("api_hash"):
            self._log("❌ Erro: api_id/api_hash não encontrados no config.json. Faça login novamente.")
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            return

        api_id = int(cfg["api_id"])
        api_hash = cfg["api_hash"]

        # UI fields override config fields
        target = self.target_entry.get().strip()
        tags_str = self.tags_entry.get().strip()
        out_path = self.output_entry.get().strip()
        limit = int(self.limit_entry.get().strip() or 0)
        session_name = self.session_entry.get().strip() or cfg.get("session_name", "session")
        max_flood_wait = int(self.max_flood_entry.get().strip() or cfg.get("max_flood_wait", 300))
        name_line_choice = self.name_line_var.get()

        # Ensure output dir
        Path(out_path).mkdir(parents=True, exist_ok=True)

        # Prepare CSV path in output and a backup in src
        csv_path_out = os.path.join(out_path, "videos_baixados.csv")
        csv_backup_path = os.path.join(BASE_DIR, f"videos_baixados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        if not tags:
            self._log("❌ Nenhuma tag válida informada!")
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            return

        client = TelegramClient(os.path.join(BASE_DIR, session_name), api_id, api_hash)
        try:
            await client.start()
            me = await client.get_me()
            self._log(f"✅ Conectado como: {getattr(me,'username',None) or getattr(me,'first_name',str(me))}")
        except Exception as e:
            self._log(f"❌ Erro ao conectar: {e}")
            return

        registros: List[Dict] = []
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
                        lines = [l.strip() for l in (msg.message or "").split("\n") if l.strip()]
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
                            self._log(f"⏩ Já existe: {filename}")
                            continue

                        try:
                            self._log(f"⏬ Baixando: {filename}")

                            # reset progress counters
                            self.last_progress_time = time.time()
                            self.last_progress_bytes = 0

                            # update UI filename
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
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception:
                                pass
                            continue

                    break  # finished iter_messages
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

        # disconnect
        try:
            await client.disconnect()
        except Exception:
            pass

        # save CSV in output and backup in src/
        if registros:
            try:
                df = pd.DataFrame(registros)
                df.to_csv(csv_path_out, index=False, encoding="utf-8-sig")
                df.to_csv(csv_backup_path, index=False, encoding="utf-8-sig")
                self._log(f"\n📄 CSV salvo em: {csv_path_out}")
                self._log(f"📄 Cópia do CSV salva em: {csv_backup_path}")
            except Exception as e:
                self._log(f"❌ Erro ao salvar CSV: {e}")

        self._log(f"\n🚀 Finalizado: {total_baixados} vídeos baixados ({total_encontrados} mensagens verificadas).")
        self.after(0, lambda: self.progress_bar.set(1))
        self.after(0, lambda: self.progress_label.configure(text="Concluído!"))
        self.downloading = False
        self.after(0, lambda: self.download_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))

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
                # speed_mb is MB/s; convert to bytes/s for ETA calc or use MB units consistently
                # bytes_remaining / (speed_mb * 1024*1024)
                eta_seconds = int(bytes_remaining / (speed_mb * 1024 * 1024)) if speed_mb > 0 else 0
                eta_min = eta_seconds // 60
                eta_sec = eta_seconds % 60
                eta_str = f"ETA: {eta_min}m{eta_sec:02d}s"
            else:
                eta_str = "ETA: --"
            # schedule UI update
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
    app = TelegramDownloaderGUI()
    app.run()
