import os
import sys
import json
import winreg

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".usd_hrn_monitor_settings.json")
APP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "USDRateMonitorSense"

DEFAULT_SETTINGS = {
    "update_interval_minutes": 60,
    "notification_threshold": 0.04,
    "notifications_enabled": True,
    "autostart": False,
    "minimize_to_tray": True,
    "close_to_tray": True,
    "last_notified_buy": None,
    "last_notified_sell": None,
    "last_notified_nbu": None,
}

def get_executable_path():
    """
    Returns the executable path or python script path formatted for autostart.
    """
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))
        py_exe = sys.executable
        # Use pythonw if possible so no console opens on autostart
        pyw_exe = py_exe.replace("python.exe", "pythonw.exe")
        if os.path.exists(pyw_exe):
            return f'"{pyw_exe}" "{main_py}"'
        return f'"{py_exe}" "{main_py}"'

def is_autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REG_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        print("Autostart check error:", e)
        return False

def set_autostart(enabled: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_executable_path()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print("Set autostart error:", e)
        return False

def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception as e:
            print("Error loading settings:", e)

    # Sync autostart state with registry
    settings["autostart"] = is_autostart_enabled()
    return settings

def save_settings(settings):
    try:
        # Sync autostart with registry
        if "autostart" in settings:
            set_autostart(settings["autostart"])

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving settings:", e)
