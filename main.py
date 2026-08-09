"""
====================================================================
 FRIDAY AI - Iron Man style personal AI assistant (Flet)
 Groq only
====================================================================
 Kaise chalayein (VS Code terminal me):
   pip install flet==0.84.6 flet-audio-recorder flet-audio groq
   python main.py

 Android APK banane ke liye:
   flet build apk

 API KEY: Niche GROQ_API_KEY variable me apna key daal do.
 App sirf Groq API se chalega.
====================================================================
"""
import flet as ft
import flet.canvas as cv
import flet_audio_recorder as far
import flet_audio as fta
import os
import json
import math
import time
import threading
import tempfile
from datetime import datetime

# =====================================================================
# 1. CONFIGURATION
# =====================================================================
# ==== API KEY ====
def load_api_key():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("groq_api_key", "")
    except Exception as e:
        print("Error loading api key:", e)
    return ""
# Dynamic key loading
GROQ_API_KEY = load_api_key()

# ---- Groq models ----
GROQ_CHAT_MODEL = "llama-3.3-70b-versatile"
GROQ_STT_MODEL  = "whisper-large-v3-turbo"
GROQ_TTS_MODEL  = "playai-tts"
GROQ_TTS_VOICE  = "Fritz-PlayAI"

HISTORY_FILE  = "friday_memory.json"
SETTINGS_FILE = "friday_settings.json"

SYSTEM_PROMPT = (
    "You are FRIDAY, Tony Stark's advanced AI assistant from Iron Man. "
    "You are witty, brilliant, calm and helpful. Address the user as 'Sir' or 'Boss'. "
    "Keep spoken answers concise (2-4 sentences) unless the user asks for detail. "
    "You can answer in Hindi, Hinglish or English -- follow the user's language."
)

# arc-reactor colours (Iron Man hologram feel)
COLOR_BG          = "#000000"
COLOR_CORE        = "#E8FBFF"
COLOR_INNER       = "#7EE8FF"
COLOR_MID         = "#3AC7FF"
COLOR_OUTER       = "#1E90FF"
COLOR_GLOW        = "#4FC3F7"
COLOR_WHITE       = "#FFFFFF"
COLOR_USER_BUBBLE = "#0A2540"
COLOR_AI_BUBBLE   = "#0E1A26"
COLOR_INPUT_BG    = "#0A1420"


# =====================================================================
# 2. ARC-REACTOR ANIMATION WIDGET
# =====================================================================
class ArcReactor(ft.Container):
    def __init__(self, size: int = 260):
        super().__init__()
        self.size = size
        self.angle_outer = 0.0
        self.angle_inner = 0.0
        self.pulse = 0.0
        self.intensity = 0.0
        self.running = True
        self.mode = "idle"  # idle | listen | process | speak
        self.app_page = None

        c = size / 2

        self.core = cv.Circle(
            c, c, size * 0.10,
            paint=ft.Paint(color=COLOR_CORE, style=ft.PaintingStyle.FILL),
        )
        self.core_glow = cv.Circle(
            c, c, size * 0.16,
            paint=ft.Paint(color=COLOR_INNER + "55", style=ft.PaintingStyle.FILL),
        )

        self.inner_shapes = []
        inner_r = size * 0.24
        for i in range(8):
            a = i * (2 * math.pi / 8)
            x = c + inner_r * math.cos(a)
            y = c + inner_r * math.sin(a)
            self.inner_shapes.append(
                cv.Circle(
                    x, y, size * 0.028,
                    paint=ft.Paint(color=COLOR_INNER, style=ft.PaintingStyle.FILL),
                )
            )

        self.inner_ring = cv.Circle(
            c, c, size * 0.24,
            paint=ft.Paint(
                color=COLOR_MID,
                style=ft.PaintingStyle.STROKE,
                stroke_width=size * 0.012,
            ),
        )

        self.outer_segments = []
        outer_r = size * 0.40
        for i in range(12):
            a1 = i * (2 * math.pi / 12) + 0.05
            a2 = a1 + (2 * math.pi / 12) - 0.18
            self.outer_segments.append(
                cv.Arc(
                    x=c - outer_r, y=c - outer_r,
                    width=outer_r * 2, height=outer_r * 2,
                    start_angle=a1, sweep_angle=(a2 - a1),
                    paint=ft.Paint(
                        color=COLOR_OUTER,
                        style=ft.PaintingStyle.STROKE,
                        stroke_width=size * 0.02,
                    ),
                )
            )

        self.outer_ring_bg = cv.Circle(
            c, c, size * 0.44,
            paint=ft.Paint(
                color=COLOR_GLOW + "44",
                style=ft.PaintingStyle.STROKE,
                stroke_width=size * 0.006,
            ),
        )

        self.inner_canvas = cv.Canvas(
            shapes=[self.inner_ring, *self.inner_shapes],
            width=size, height=size,
            rotate=ft.Rotate(0, alignment=ft.Alignment(0, 0)),
        )
        self.outer_canvas = cv.Canvas(
            shapes=[self.outer_ring_bg, *self.outer_segments],
            width=size, height=size,
            rotate=ft.Rotate(0, alignment=ft.Alignment(0, 0)),
        )
        self.core_canvas = cv.Canvas(
            shapes=[self.core_glow, self.core],
            width=size, height=size,
        )

        self.content = ft.Stack(
            controls=[self.outer_canvas, self.inner_canvas, self.core_canvas],
            width=size, height=size,
        )
        self.width = size
        self.height = size
        self.alignment = ft.Alignment(0, 0)

    def start(self, page: ft.Page):
        self.app_page = page
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def set_mode(self, mode: str):
        self.mode = mode

    def set_intensity(self, v: float):
        self.intensity = max(0.0, min(1.0, v))

    def _loop(self):
        while self.running:
            try:
                self.angle_outer += 0.02
                self.angle_inner -= 0.035
                self.pulse += 0.12

                if self.mode == "listen":
                    scale = 1.0 + 0.05 * math.sin(self.pulse) + 0.15 * self.intensity
                    self.core.paint.color = COLOR_WHITE
                elif self.mode == "process":
                    scale = 1.0 + 0.03 * math.sin(self.pulse * 2)
                    self.core.paint.color = COLOR_INNER
                elif self.mode == "speak":
                    scale = 1.0 + 0.08 * math.sin(self.pulse * 1.6)
                    self.core.paint.color = COLOR_CORE
                else:
                    scale = 1.0 + 0.02 * math.sin(self.pulse * 0.6)
                    self.core.paint.color = COLOR_CORE

                self.outer_canvas.rotate = ft.Rotate(
                    self.angle_outer, alignment=ft.Alignment(0, 0)
                )
                self.inner_canvas.rotate = ft.Rotate(
                    self.angle_inner, alignment=ft.Alignment(0, 0)
                )
                self.core_canvas.scale = ft.Scale(
                    scale=scale, alignment=ft.Alignment(0, 0)
                )

                if self.app_page is not None:
                    try:
                        self.app_page.update()
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1 / 30)


# =====================================================================
# 3. MAIN APP
# =====================================================================
class FridayApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "FRIDAY AI"
        self.page.bgcolor = COLOR_BG
        self.page.padding = 0
        self.page.spacing = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_bgcolor = COLOR_BG
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.vertical_alignment = ft.MainAxisAlignment.START

        self.settings = self._load_settings()
        self.messages = self._load_history()
        # Check key from settings file if global is empty
        global GROQ_API_KEY
        if not GROQ_API_KEY:
            GROQ_API_KEY = self.settings.get("groq_api_key", "")
        self.is_voice_mode = False
        self.is_recording = False
        self.busy = False
        self.audio_path = os.path.join(tempfile.gettempdir(), "friday_input.wav")
        # ---- Groq ----
        self.groq = None
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq = Groq(api_key=GROQ_API_KEY)
                print("[FRIDAY] Groq ready")
            except Exception as e:
                print("Groq init error:", e)
        self.any_provider = self.groq is not None

        # ---- audio services ----
        self.recorder = far.AudioRecorder(
            configuration=far.AudioRecorderConfiguration(
                encoder=far.AudioEncoder.WAV,
                suppress_noise=True,
                cancel_echo=True,
                auto_gain=True,
                sample_rate=16000,
                channels=1,
            )
        )
        self.player = fta.Audio(
            src="", autoplay=False, on_state_change=self._on_audio_state
        )
        self.page.services.append(self.recorder)
        self.page.services.append(self.player)

        self._build_splash()

    # -----------------------------------------------------------------
    def _load_settings(self):
        default = {
            "chat_model": GROQ_CHAT_MODEL,
            "tts_voice": GROQ_TTS_VOICE,
            "tts_model": GROQ_TTS_MODEL,
            "memory_on": True,
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    default.update(json.load(f))
        except Exception:
            pass
        return default

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print("settings save error:", e)

    def _load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self):
        if not self.settings.get("memory_on", True):
            return
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("history save error:", e)

    # -----------------------------------------------------------------
    def _build_splash(self):
        splash_reactor = ArcReactor(size=300)
        splash_reactor.start(self.page)

        title = ft.Text(
            "F R I D A Y",
            size=28, weight=ft.FontWeight.W_700, color=COLOR_CORE,
            text_align=ft.TextAlign.CENTER,
            style=ft.TextStyle(letter_spacing=8),
        )
        subtitle = ft.Text(
            "A.I. // BOOTING SYSTEMS",
            size=11, color=COLOR_INNER,
            style=ft.TextStyle(letter_spacing=4),
        )

        self.page.controls.clear()
        self.page.add(
            ft.Container(
                bgcolor=COLOR_BG,
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=24,
                    controls=[
                        splash_reactor,
                        title,
                        subtitle,
                        ft.ProgressBar(width=160, color=COLOR_INNER, bgcolor="#0A2540"),
                    ],
                ),
            )
        )
        self.page.update()
        threading.Thread(
            target=self._splash_wait, args=(splash_reactor,), daemon=True
        ).start()

    def _splash_wait(self, splash_reactor):
        time.sleep(2.5)
        splash_reactor.stop()
        self._build_chat_screen()
        self.page.update()

    # -----------------------------------------------------------------
    def _build_chat_screen(self):
        self.mini_reactor = ArcReactor(size=90)
        self.mini_reactor.start(self.page)

        header = ft.Container(
            padding=10,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(width=8),
                            ft.Text(
                                "FRIDAY", size=18,
                                weight=ft.FontWeight.W_700,
                                color=COLOR_CORE,
                                style=ft.TextStyle(letter_spacing=4),
                            ),
                            ft.Container(width=6),
                            ft.Container(
                                width=8, height=8,
                                bgcolor=COLOR_INNER,
                                border_radius=4,
                            ),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS_ROUNDED,
                        icon_color=COLOR_INNER,
                        on_click=lambda e: self._open_settings(),
                    ),
                ],
            ),
        )

        self.chat_list = ft.ListView(
            expand=True, spacing=10, auto_scroll=True, padding=10,
        )
        for m in self.messages:
            if m["role"] in ("user", "assistant"):
                self.chat_list.controls.append(self._bubble(m["role"], m["content"]))

        self.input_field = ft.TextField(
            hint_text="Ask FRIDAY anything...",
            hint_style=ft.TextStyle(color="#4A6C85"),
            border_color="transparent",
            focused_border_color="transparent",
            bgcolor="transparent",
            cursor_color=COLOR_INNER,
            color=COLOR_WHITE,
            text_size=15,
            multiline=True,
            min_lines=1, max_lines=4,
            expand=True,
            on_submit=lambda e: self._send_text(),
        )

        send_btn = self._lightning_button(
            icon=ft.Icons.SEND_ROUNDED,
            on_click=lambda e: self._send_text(),
            tooltip="Send",
        )
        voice_btn = self._lightning_button(
            icon=ft.Icons.GRAPHIC_EQ_ROUNDED,
            on_click=lambda e: self._open_voice_mode(),
            tooltip="Voice mode",
        )

        input_bar = ft.Container(
            margin=10,
            padding=10,
            bgcolor=COLOR_INPUT_BG,
            border=ft.border.BorderSide(1, COLOR_INNER + "55"),
            border_radius=26,
            shadow=ft.BoxShadow(
                blur_radius=18, spread_radius=1, color=COLOR_INNER + "33",
            ),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=6),
                    self.input_field,
                    voice_btn,
                    ft.Container(width=6),
                    send_btn,
                    ft.Container(width=4),
                ],
            ),
        )

        top_reactor = ft.Container(
            alignment=ft.Alignment(0, 0),
            padding=4,
            content=self.mini_reactor,
        )

        if not self.chat_list.controls:
            self.chat_list.controls.append(
                ft.Container(
                    padding=20,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Text(
                                "Online, sir.",
                                color=COLOR_INNER, size=14,
                                style=ft.TextStyle(letter_spacing=3),
                            ),
                            ft.Text(
                                "How can I assist you today?",
                                color="#6B8AA6", size=12,
                            ),
                        ],
                    ),
                )
            )

        self.page.controls.clear()
        self.page.add(
            ft.Container(
                bgcolor=COLOR_BG,
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[header, top_reactor, self.chat_list, input_bar],
                ),
            )
        )
        self.page.update()

    # -----------------------------------------------------------------
    def _lightning_button(self, icon, on_click, tooltip=""):
        return ft.Container(
            width=44, height=44,
            border_radius=22,
            alignment=ft.Alignment(0, 0),
            bgcolor="#0A1E30",
            border=ft.border.BorderSide(1, COLOR_INNER),
            shadow=ft.BoxShadow(blur_radius=14, color=COLOR_INNER + "88"),
            content=ft.IconButton(
                icon=icon, icon_color=COLOR_CORE, icon_size=20,
                tooltip=tooltip, on_click=on_click,
            ),
        )

    def _bubble(self, role: str, text: str):
        is_user = role == "user"
        bubble_width = 320
        try:
            if self.page.width:
                bubble_width = min(int(self.page.width) - 60, 320)
        except Exception:
            pass
        return ft.Row(
            alignment=(
                ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
            ),
            controls=[
                ft.Container(
                    padding=10,
                    bgcolor=(COLOR_USER_BUBBLE if is_user else COLOR_AI_BUBBLE),
                    border_radius=16,
                    border=ft.border.BorderSide(
                        1,
                        (COLOR_INNER + "66" if is_user else COLOR_OUTER + "55"),
                    ),
                    content=ft.Text(
                        text, color=COLOR_WHITE, size=14, selectable=True,
                    ),
                    width=bubble_width,
                )
            ],
        )

    def _add_message(self, role: str, text: str):
        self.messages.append({
            "role": role, "content": text,
            "ts": datetime.now().isoformat(),
        })
        # remove the empty-state placeholder if present
        if (self.chat_list.controls
                and isinstance(self.chat_list.controls[0], ft.Container)
                and not isinstance(self.chat_list.controls[0].content, ft.Row)):
            self.chat_list.controls.pop(0)
        self.chat_list.controls.append(self._bubble(role, text))
        self._save_history()
        self.page.update()

    def _snack(self, text, err=False):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(text, color=COLOR_WHITE),
            bgcolor="#C62828" if err else "#0A2540",
        )
        self.page.snack_bar.open = True
        self.page.update()

    # -----------------------------------------------------------------
    def _send_text(self):
        text = (self.input_field.value or "").strip()
        if not text or self.busy:
            return
        self.input_field.value = ""
        self._add_message("user", text)
        threading.Thread(
            target=self._ask_ai, args=(text, False), daemon=True
        ).start()

    def _build_api_msgs(self):
        api_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in self.messages[-20:]:
            if m["role"] in ("user", "assistant"):
                api_msgs.append({"role": m["role"], "content": m["content"]})
        return api_msgs


    def _chat_with_groq(self, api_msgs):
        resp = self.groq.chat.completions.create(
            model=self.settings.get("chat_model", GROQ_CHAT_MODEL),
            messages=api_msgs,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    def _ask_ai(self, prompt: str, is_voice: bool):
        self.busy = True
        if not self.any_provider:
            self._add_message(
                "assistant",
                "API key set nahi hai, sir. main.py kholiye aur GROQ_API_KEY "
                "me apna key daaliye.",
            )
            self.busy = False
            return

        placeholder = self._bubble("assistant", "• • •")
        self.chat_list.controls.append(placeholder)
        self.page.update()

        api_msgs = self._build_api_msgs()
        answer = None
        errors = []

        try:
            answer = self._chat_with_groq(api_msgs)
            print("[FRIDAY] via Groq")
        except Exception as e:
            errors.append(f"Groq: {e}")

        if answer is None:
            err_str = " | ".join(errors).lower()
            if "quota" in err_str or "credit" in err_str or "429" in err_str:
                answer = "Sir, Groq ka quota khatam hai. Groq console pe check karein."
            elif "invalid" in err_str or "401" in err_str or "403" in err_str:
                answer = "Sir, Groq API key invalid hai. main.py me check karein."
            else:
                answer = f"System error, sir: {' | '.join(errors)}"

        try:
            self.chat_list.controls.remove(placeholder)
        except ValueError:
            pass

        self._add_message("assistant", answer)
        self.page.update()

        if is_voice:
            self._speak(answer)
        else:
            self.busy = False

    # -----------------------------------------------------------------
    def _open_voice_mode(self):
        self.is_voice_mode = True
        self.big_reactor = ArcReactor(size=300)
        self.big_reactor.start(self.page)

        self.voice_status = ft.Text(
            "TAP TO SPEAK", size=13, color=COLOR_INNER,
            style=ft.TextStyle(letter_spacing=5),
        )
        self.voice_hint = ft.Text(
            "FRIDAY is listening... // tap again to stop",
            size=11, color="#6B8AA6",
        )

        reactor_tap = ft.GestureDetector(
            on_tap=lambda e: self._toggle_recording(),
            content=self.big_reactor,
        )
        close_btn = ft.IconButton(
            icon=ft.Icons.CLOSE_ROUNDED, icon_color=COLOR_INNER,
            on_click=lambda e: self._close_voice_mode(),
        )

        self.voice_view = ft.Container(
            bgcolor=COLOR_BG,
            expand=True,
            content=ft.Stack(
                controls=[
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=28,
                            controls=[
                                reactor_tap,
                                self.voice_status,
                                self.voice_hint,
                            ],
                        ),
                    ),
                    ft.Container(
                        alignment=ft.Alignment(1, -1),
                        padding=10, content=close_btn,
                    ),
                ],
            ),
        )
        self.page.controls.clear()
        self.page.add(self.voice_view)
        self.page.update()

    def _close_voice_mode(self):
        try:
            if self.is_recording:
                self.recorder.stop_recording()
        except Exception:
            pass
        try:
            self.player.pause()
        except Exception:
            pass
        self.is_recording = False
        self.is_voice_mode = False
        self.busy = False
        if hasattr(self, "big_reactor"):
            self.big_reactor.stop()
        self._build_chat_screen()

    def _toggle_recording(self):
        if self.busy and not self.is_recording:
            return
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording_and_process()

    def _start_recording(self):
        if self.groq is None:
            # Voice pipeline needs Groq (Whisper STT + PlayAI TTS)
            self._snack(
                "Voice mode ke liye GROQ_API_KEY chahiye (Whisper + PlayAI).",
                err=True,
            )
            return
        try:
            if os.path.exists(self.audio_path):
                os.remove(self.audio_path)
        except Exception:
            pass
        try:
            self.recorder.start_recording(output_path=self.audio_path)
            self.is_recording = True
            self.big_reactor.set_mode("listen")
            self.voice_status.value = "LISTENING…"
            self.voice_hint.value = "tap reactor to stop"
            self.page.update()
            threading.Thread(target=self._amp_loop, daemon=True).start()
        except Exception as e:
            self._snack(f"Mic error: {e}", err=True)

    def _amp_loop(self):
        while self.is_recording:
            self.big_reactor.set_intensity(
                0.4 + 0.6 * abs(math.sin(time.time() * 6))
            )
            time.sleep(0.05)
        self.big_reactor.set_intensity(0)

    def _stop_recording_and_process(self):
        self.is_recording = False
        try:
            self.recorder.stop_recording()
        except Exception as e:
            self._snack(f"stop error: {e}", err=True)
            return
        self.big_reactor.set_mode("process")
        self.voice_status.value = "PROCESSING…"
        self.voice_hint.value = "analysing your voice"
        self.page.update()
        threading.Thread(target=self._voice_pipeline, daemon=True).start()

    def _voice_pipeline(self):
        self.busy = True

        # ---- STT via Groq Whisper ----
        try:
            with open(self.audio_path, "rb") as f:
                tr = self.groq.audio.transcriptions.create(
                    model=GROQ_STT_MODEL,
                    file=(os.path.basename(self.audio_path), f.read()),
                )
            user_text = (getattr(tr, "text", "") or "").strip()
        except Exception as e:
            self._voice_error(f"STT error: {e}")
            return

        if not user_text:
            self._voice_error("Sir, I did not catch that.")
            return

        self._add_message("user", user_text)

        # ---- Chat with Groq ----
        api_msgs = self._build_api_msgs()
        answer = None
        errors = []

        try:
            answer = self._chat_with_groq(api_msgs)
            print("[FRIDAY] voice via Groq")
        except Exception as e:
            errors.append(f"Groq: {e}")

        if answer is None:
            self._voice_error(f"LLM error: {' | '.join(errors)}")
            return

        self._add_message("assistant", answer)
        self._speak(answer)

    def _voice_error(self, msg):
        self.busy = False
        if self.is_voice_mode:
            self.voice_status.value = "ERROR"
            self.voice_hint.value = msg
            self.big_reactor.set_mode("idle")
            self.page.update()

    def _speak(self, text: str):
        if self.groq is None:
            self.busy = False
            if self.is_voice_mode:
                self._voice_error("TTS ke liye GROQ_API_KEY chahiye, sir.")
            return

        out = os.path.join(tempfile.gettempdir(), "friday_out.wav")
        try:
            resp = self.groq.audio.speech.create(
                model=self.settings.get("tts_model", GROQ_TTS_MODEL),
                voice=self.settings.get("tts_voice", GROQ_TTS_VOICE),
                input=text[:4000],
                response_format="wav",
            )
            # Groq SDK: write to file
            if hasattr(resp, "write_to_file"):
                resp.write_to_file(out)
            elif hasattr(resp, "stream_to_file"):
                resp.stream_to_file(out)
            else:
                # binary fallback
                data = getattr(resp, "content", None) or resp.read()
                with open(out, "wb") as f:
                    f.write(data)
        except Exception as e:
            print("TTS error:", e)
            self.busy = False
            if self.is_voice_mode:
                self._voice_error(f"TTS error: {e}")
            return

        if self.is_voice_mode:
            self.big_reactor.set_mode("speak")
            self.voice_status.value = "SPEAKING…"
            self.voice_hint.value = "listening mode will resume automatically"
            self.page.update()

        try:
            self.player.src = out
            self.player.update()
            self.player.play()
        except Exception as e:
            print("audio play error:", e)
            self.busy = False

    def _on_audio_state(self, e):
        state = str(getattr(e, "data", "")).lower()
        if "complete" in state or "finish" in state or "stopped" in state:
            self.busy = False
            if self.is_voice_mode:
                self.big_reactor.set_mode("idle")
                self.voice_status.value = "TAP TO SPEAK"
                self.voice_hint.value = "auto-listening…"
                self.page.update()
                # auto-resume mic after AI finishes speaking
                threading.Timer(0.4, self._start_recording).start()

    # -----------------------------------------------------------------
    def _open_settings(self):
        # API Key input field
        api_key_field = ft.TextField(
            label="Groq API Key",
            value=self.settings.get("groq_api_key", ""),
            password=True,
            can_reveal_password=True,
            color=COLOR_WHITE,
        )
        chat_dd = ft.Dropdown(
            label="Groq chat model",
            value=self.settings.get("chat_model", GROQ_CHAT_MODEL),
            color=COLOR_WHITE,
            options=[
                ft.dropdown.Option(x) for x in [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it",
                ]
            ],
        )
        voice_dd = ft.Dropdown(
            label="TTS voice (Groq PlayAI)",
            value=self.settings.get("tts_voice", GROQ_TTS_VOICE),
            color=COLOR_WHITE,
            options=[
                ft.dropdown.Option(x) for x in [
                    "Fritz-PlayAI", "Arista-PlayAI", "Atlas-PlayAI",
                    "Basil-PlayAI", "Briggs-PlayAI", "Calum-PlayAI",
                    "Celeste-PlayAI", "Cheyenne-PlayAI",
                ]
            ],
        )
        tts_dd = ft.Dropdown(
            label="TTS model",
            value=self.settings.get("tts_model", GROQ_TTS_MODEL),
            color=COLOR_WHITE,
            options=[ft.dropdown.Option(x) for x in ["playai-tts"]],
        )
        memory_sw = ft.Switch(
            label="Persistent memory",
            value=self.settings.get("memory_on", True),
            active_color=COLOR_INNER,
        )
        def save(e):
            # Save settings including API Key
            self.settings["groq_api_key"] = api_key_field.value.strip()
            self.settings["chat_model"] = chat_dd.value
            self.settings["tts_voice"] = voice_dd.value
            self.settings["tts_model"] = tts_dd.value
            self.settings["memory_on"] = memory_sw.value
            self._save_settings()
            # Global and instance groq re-initialize
            global GROQ_API_KEY
            GROQ_API_KEY = self.settings["groq_api_key"]
            if GROQ_API_KEY:
                try:
                    from groq import Groq
                    self.groq = Groq(api_key=GROQ_API_KEY)
                    self.any_provider = True
                except Exception:
                    pass
            self._snack("Settings saved successfully.")
            self._build_chat_screen()
        def clear_memory(e):
            self.messages = []
            try:
                os.remove(HISTORY_FILE)
            except Exception:
                pass
            self._snack("Memory cleared.")
            self._build_chat_screen()
        back = ft.IconButton(
            icon=ft.Icons.ARROW_BACK_ROUNDED,
            icon_color=COLOR_INNER,
            on_click=lambda e: self._build_chat_screen(),
        )
        header = ft.Container(
            padding=10,
            content=ft.Row(controls=[
                back,
                ft.Text(
                    "SETTINGS", size=16, color=COLOR_CORE,
                    weight=ft.FontWeight.W_700,
                    style=ft.TextStyle(letter_spacing=4),
                ),
            ]),
        )
        body = ft.Container(
            expand=True,
            padding=20,
            content=ft.Column(
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    api_key_field,  # <-- Yahan API key field add ho gaya hai
                    chat_dd, voice_dd, tts_dd, memory_sw,
                    ft.Container(height=6),
                    ft.ElevatedButton(
                        "Save settings", icon=ft.Icons.SAVE_ROUNDED,
                        on_click=save,
                        bgcolor=COLOR_INNER, color=COLOR_BG,
                    ),
                    ft.OutlinedButton(
                        "Clear memory (delete all chat history)",
                        icon=ft.Icons.DELETE_FOREVER_ROUNDED,
                        on_click=clear_memory,
                        style=ft.ButtonStyle(color=COLOR_OUTER),
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        "FRIDAY AI • Iron Man inspired • Groq only",
                        size=10, color="#5A7A93",
                    ),
                ],
            ),
        )
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                bgcolor=COLOR_BG, expand=True,
                content=ft.Column(controls=[header, body], expand=True),
            )
        )
        self.page.update()


# =====================================================================
# 4. ENTRY POINT
# =====================================================================
def main(page: ft.Page):
    FridayApp(page)


if __name__ == "__main__":
    ft.app(target=main)
