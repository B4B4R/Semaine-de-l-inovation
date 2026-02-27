import threading
import time
import json
import queue

data_queue = queue.Queue()

# Simulateur de flux
def simulate():
    seq = 0
    while True:
        payload = json.dumps({
            "seq": seq,
            "respiration": 500 + seq % 50,
            "ppg": 400 + seq % 30,
            "bpm": 75,
            "resp_rate": 15
        })
        data_queue.put(payload)
        seq += 1
        time.sleep(0.01)  # 100 Hz simulé

# Lancement du simulateur dans un thread
threading.Thread(target=simulate, daemon=True).start()

# Test simple : on lit 20 valeurs
for _ in range(20):
    data = data_queue.get()
    print(data)