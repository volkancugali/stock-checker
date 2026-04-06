"""
Stok Takipçisi — Kivy + Plyer (Android APK) versiyonu
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp

import threading
import re
import ssl
import urllib.request
from datetime import datetime

try:
    from plyer import notification, vibrator
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False


def notify(title, message):
    if not HAS_PLYER:
        return
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=30
        )
    except Exception:
        pass


def vibrate(duration=1.0):
    if not HAS_PLYER:
        return
    try:
        vibrator.vibrate(duration)
    except Exception:
        pass


def check_stock(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 14; SM-S911B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9",
    })

    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    m = re.search(r'"stock_status"\s*:\s*"([^"]+)"', html)
    if m and m.group(1).lower() != "outofstock":
        return True, f"stock_status={m.group(1)}"

    m = re.search(r'"in_stock"\s*:\s*"([^"]+)"', html)
    if m and m.group(1).lower() == "yes":
        return True, "in_stock=yes"

    m = re.search(r'"stock"\s*:\s*"(\d+)"', html)
    if m and int(m.group(1)) > 0:
        return True, f"stock={m.group(1)}"

    if "STOK GELİNCE HABER VER" not in html.upper():
        if re.search(r'SEPETE\s+EKLE', html, re.IGNORECASE):
            return True, "Sepete Ekle butonu bulundu"

    return False, "Stok yok"


class StockCheckerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.running = False
        self.check_count = 0
        self.scheduled_event = None

    def build(self):
        self.title = "Stok Takipçisi"
        Window.clearcolor = (0.12, 0.12, 0.14, 1)

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        root.add_widget(Label(
            text="[b]Stok Takipçisi[/b]", markup=True,
            font_size=dp(22), size_hint_y=None, height=dp(40),
            color=(1, 1, 1, 1)
        ))

        root.add_widget(Label(
            text="Ürün URL:", font_size=dp(13),
            size_hint_y=None, height=dp(22), halign="left",
            color=(0.7, 0.7, 0.7, 1)
        ))
        self.url_input = TextInput(
            hint_text="https://www.sanalcadir.com/...",
            multiline=False, size_hint_y=None, height=dp(44),
            font_size=dp(12), background_color=(0.2, 0.2, 0.22, 1),
            foreground_color=(1, 1, 1, 1), cursor_color=(0.3, 0.6, 1, 1),
            padding=[dp(10), dp(10)]
        )
        root.add_widget(self.url_input)

        interval_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        interval_row.add_widget(Label(
            text="Her", font_size=dp(14), size_hint_x=0.15,
            color=(0.7, 0.7, 0.7, 1)
        ))
        self.interval_input = TextInput(
            text="10", multiline=False, input_filter="int",
            size_hint_x=0.25, font_size=dp(16),
            background_color=(0.2, 0.2, 0.22, 1),
            foreground_color=(1, 1, 1, 1),
            halign="center", padding=[dp(10), dp(10)]
        )
        interval_row.add_widget(self.interval_input)
        interval_row.add_widget(Label(
            text="dk'da bir kontrol et", font_size=dp(14),
            size_hint_x=0.6, color=(0.7, 0.7, 0.7, 1)
        ))
        root.add_widget(interval_row)

        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        self.start_btn = Button(
            text="Baslat", font_size=dp(16),
            background_color=(0.18, 0.55, 0.34, 1),
            background_normal=""
        )
        self.start_btn.bind(on_press=self.start_checking)
        btn_row.add_widget(self.start_btn)

        self.stop_btn = Button(
            text="Durdur", font_size=dp(16),
            background_color=(0.6, 0.15, 0.15, 1),
            background_normal="", disabled=True
        )
        self.stop_btn.bind(on_press=self.stop_checking)
        btn_row.add_widget(self.stop_btn)
        root.add_widget(btn_row)

        self.status_label = Label(
            text="Bekleniyor...", font_size=dp(14),
            size_hint_y=None, height=dp(30),
            bold=True, color=(0.4, 0.7, 1, 1)
        )
        root.add_widget(self.status_label)

        scroll = ScrollView(size_hint_y=1)
        self.log_label = Label(
            text="", font_size=dp(11), halign="left", valign="top",
            color=(0.65, 0.65, 0.65, 1), markup=True,
            text_size=(Window.width - dp(40), None),
            size_hint_y=None
        )
        self.log_label.bind(texture_size=self.log_label.setter("size"))
        scroll.add_widget(self.log_label)
        root.add_widget(scroll)

        return root

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        current = self.log_label.text
        self.log_label.text = f"{current}\n{entry}" if current else entry

    def start_checking(self, *args):
        url = self.url_input.text.strip()
        if not url or not url.startswith("http"):
            self.show_popup("Uyari", "Gecerli bir URL girin.")
            return

        try:
            interval = max(1, int(self.interval_input.text))
        except ValueError:
            interval = 10
            self.interval_input.text = "10"

        self.running = True
        self.check_count = 0
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.status_label.text = "Takip aktif..."
        self.status_label.color = (0.4, 0.7, 1, 1)
        self.log(f"Takip basladi - her {interval} dk")

        self.do_check()

    def stop_checking(self, *args):
        self.running = False
        if self.scheduled_event:
            self.scheduled_event.cancel()
            self.scheduled_event = None
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = "Durduruldu"
        self.status_label.color = (0.7, 0.7, 0.7, 1)
        self.log("Takip durduruldu.")

    def do_check(self, *args):
        if not self.running:
            return
        self.check_count += 1
        self.status_label.text = f"Kontrol #{self.check_count}..."
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        url = self.url_input.text.strip()
        try:
            in_stock, detail = check_stock(url)
            if in_stock:
                Clock.schedule_once(lambda dt: self._on_stock_found(detail))
            else:
                Clock.schedule_once(lambda dt: self._on_no_stock(detail))
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): self._on_error(err))

    def _on_stock_found(self, detail):
        self.running = False
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = "STOKTA!"
        self.status_label.color = (0.2, 0.9, 0.3, 1)
        self.log(f"STOKTA! ({detail})")

        vibrate(2.0)
        notify("Urun Stoga Girdi!", f"{detail} - Hemen kontrol et!")
        self.show_popup("STOKTA!", f"Urun stoga girdi!\n{detail}\n\nHemen kontrol edin!")

    def _on_no_stock(self, detail):
        if not self.running:
            return
        self.log(f"#{self.check_count} - {detail}")
        ts = datetime.now().strftime("%H:%M:%S")
        self.status_label.text = f"Aktif - #{self.check_count} ({ts})"
        self._schedule_next()

    def _on_error(self, err):
        if not self.running:
            return
        self.log(f"#{self.check_count} - Hata: {err}")
        self.status_label.text = "Hata - tekrar denenecek"
        self._schedule_next()

    def _schedule_next(self):
        try:
            interval = max(1, int(self.interval_input.text)) * 60
        except ValueError:
            interval = 600
        self.scheduled_event = Clock.schedule_once(self.do_check, interval)

    def show_popup(self, title, msg):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=msg, font_size=dp(14)))
        btn = Button(text="Tamam", size_hint_y=None, height=dp(44))
        content.add_widget(btn)
        popup = Popup(
            title=title, content=content,
            size_hint=(0.85, 0.4), auto_dismiss=True
        )
        btn.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    StockCheckerApp().run()
