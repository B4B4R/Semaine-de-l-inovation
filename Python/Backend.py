import platform
import sys
import subprocess
from os import linesep
import threading
import queue
import json
import time
import csv
from datetime import datetime
from flask import Flask, render_template, Response

# --- Détection OS pour PLUX ---
osDic = {
    "Darwin": f"MacOS/Intel{''.join(platform.python_version().split('.')[:2])}",
    "Linux": "Linux64",
    "Windows": f"Win{platform.architecture()[0][:2]}_{''.join(platform.python_version().split('.')[:2])}",
}
if platform.mac_ver()[0] != "":
    p = subprocess.Popen("sw_vers", stdout=subprocess.PIPE)
    result = p.communicate()[0].decode("utf-8").split(str("\t"))[2].split(linesep)[0]
    if result.startswith("12."):
        osDic["Darwin"] = "MacOS/Intel310"

sys.path.append(f"PLUX-API-Python3/{osDic.get(platform.system(), 'Linux64')}")
import plux

# --- Paramètres Réglables ---
NIVEAU_LISSAGE = 150 
SEUIL_BAS = 425
SEUIL_HAUT = 550
INTERVALLE_RECORD = 1.0 # Enregistre une ligne par seconde

data_queue = queue.Queue()
device_instance = None

class NewDevice(plux.SignalsDev):
    def __init__(self, address):
        plux.SignalsDev.__init__(self)
        self.address = address
        self.frequency = 1000 
        
        # BPM
        self.ppg_buffer = []
        self.sample_counter = 0    
        self.bpm = 0
        self.waiting_for_dip = False 

        # Respiration
        self.resp_smooth_buffer = []
        self.phase = "apnee" 
        self.last_resp_time = time.time()
        self.resp_rate = 0

        # Recording
        self.is_recording = False
        self.record_data = []
        self.last_record_time = 0
        self.history_60s = {"bpm": [], "rr": [], "phases": [], "resp": []}

    def onRawFrame(self, nSeq, data):
        resp_raw, ppg_raw = data[0], data[1]

        # --- LOGIQUE BPM ---
        self.ppg_buffer.append(ppg_raw)
        if len(self.ppg_buffer) > 2000: self.ppg_buffer.pop(0)
        self.sample_counter += 1
        if len(self.ppg_buffer) > 500:
            min_v, max_v = min(self.ppg_buffer), max(self.ppg_buffer)
            threshold = min_v + (max_v - min_v) * 0.75
            if ppg_raw > threshold and not self.waiting_for_dip:
                if self.sample_counter > 400:
                    self.bpm = int((self.frequency / self.sample_counter) * 60)
                    self.sample_counter = 0
                    self.waiting_for_dip = True
            if ppg_raw < (min_v + (max_v - min_v) * 0.60):
                self.waiting_for_dip = False

        # --- LOGIQUE RESPIRATION ---
        self.resp_smooth_buffer.append(resp_raw)
        if len(self.resp_smooth_buffer) > NIVEAU_LISSAGE: self.resp_smooth_buffer.pop(0)
        current_smooth = sum(self.resp_smooth_buffer) / len(self.resp_smooth_buffer)
        
        prev_phase = self.phase
        if SEUIL_BAS <= current_smooth <= SEUIL_HAUT: self.phase = "apnee"
        elif current_smooth > SEUIL_HAUT: self.phase = "inspire"
        elif current_smooth < SEUIL_BAS: self.phase = "expire"

        if prev_phase == "apnee" and self.phase == "inspire":
            now = time.time()
            self.resp_rate = round(60 / (now - self.last_resp_time), 1)
            self.last_resp_time = now

        # --- GESTION HISTORIQUE (60s) ---
        self.history_60s["bpm"].append(self.bpm)
        self.history_60s["rr"].append(self.resp_rate)
        self.history_60s["phases"].append(self.phase)
        self.history_60s["resp"].append(current_smooth)
        for key in self.history_60s:
            if len(self.history_60s[key]) > 60000: self.history_60s[key].pop(0)

        # --- ENREGISTREMENT ---
        if self.is_recording and (time.time() - self.last_record_time) >= INTERVALLE_RECORD:
            self.record_line()
            self.last_record_time = time.time()

        if nSeq % 10 == 0:
            payload = json.dumps({
                "seq": nSeq, "respiration": int(current_smooth), "ppg": ppg_raw,
                "bpm": self.bpm, "resp_rate": self.resp_rate, "phase": self.phase
            })
            data_queue.put(payload)
        return False

    def record_line(self):
        bpm_avg = round(sum(self.history_60s["bpm"]) / len(self.history_60s["bpm"]))
        rr_avg = round(sum(self.history_60s["rr"]) / len(self.history_60s["rr"]), 1)
        dom_phase = max(set(self.history_60s["phases"]), key=self.history_60s["phases"].count)
        amp_resp = int(max(self.history_60s["resp"]) - min(self.history_60s["resp"]))
        
        self.record_data.append({
            "Horodatage": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "BPM_Moyen": bpm_avg,
            "RR_Moyen": rr_avg,
            "Phase_Dominante": dom_phase,
            "Amplitude_Resp": amp_resp
        })

def exampleAcquisition(address):
    global device_instance
    device_instance = NewDevice(address)
    device_instance.start(1000, [1, 2], 16)
    device_instance.loop()
    device_instance.stop()
    device_instance.close()

app = Flask(__name__)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            try: yield f"data: {data_queue.get(timeout=0.1)}\n\n"
            except queue.Empty: yield "\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/start_record")
def start_record():
    if device_instance:
        device_instance.record_data = []
        device_instance.is_recording = True
    return "OK"

import requests # N'oublie pas d'ajouter 'import requests' en haut du fichier

# Remplace par l'URL de ton Web App Google Script
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwRat-0_B9SwR7aGZtDAbhgbe9G7EnkCXfQc1v3uHNS8biVFz5ZY6ClUdud9q8Glj4FgA/exec"

def send_to_google_sheets(participant_name, record_data):
    """Envoie les données formatées vers Google Sheets"""
    payload = {
        "participantName": participant_name,
        "sessionId": f"SESS_{int(time.time())}",
        "sessionStart": record_data[0]["Horodatage"] if record_data else "",
        "sessionEnd": record_data[-1]["Horodatage"] if record_data else "",
        "physiologicalData": [
            {
                "timestamp": d["Horodatage"],
                "bpm": d["BPM_Moyen"],
                "rr": d["RR_Moyen"],
                "phase": d["Phase_Dominante"],
                "amplitude": d["Amplitude_Resp"]
            } for d in record_data
        ]
    }
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        return response.json()
    except Exception as e:
        print(f"Erreur envoi Google Sheets: {e}")
        return None

@app.route("/stop_record/<filename>")
def stop_record(filename):
    if device_instance:
        device_instance.is_recording = False
        
        # 1. Sauvegarde locale CSV (ton code actuel)
        with open(f"{filename}.csv", "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Horodatage", "BPM_Moyen", "RR_Moyen", "Phase_Dominante", "Amplitude_Resp"])
            writer.writeheader()
            writer.writerows(device_instance.record_data)
        
        # 2. Envoi vers Google Sheets (Utilise le 'filename' comme 'participantName')
        threading.Thread(target=send_to_google_sheets, args=(filename, device_instance.record_data)).start()
        
    return "OK"


if __name__ == "__main__":
    threading.Thread(target=exampleAcquisition, args=("98:D3:C1:FE:04:BB",), daemon=True).start()
    app.run(debug=True, threaded=True, use_reloader=False)