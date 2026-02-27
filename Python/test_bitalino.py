import platform
import sys

osDic = {
    "Darwin": f"MacOS/Intel{''.join(platform.python_version().split('.')[:2])}",
    "Linux": "Linux64",
    "Windows": f"Win{platform.architecture()[0][:2]}_{''.join(platform.python_version().split('.')[:2])}",
}

sys.path.append(f"PLUX-API-Python3/{osDic[platform.system()]}")
import plux

class NewDevice(plux.SignalsDev):

    def __init__(self, address):
        plux.SignalsDev.__init__(address)
    
    def onRawFrame(self, nSeq, data):
        respiration = data[0]
        ppg = data[1]

        print(f"{nSeq} | Resp: {respiration} | PPG: {ppg}")

        return False  # acquisition infinie


def main():
    address = "98:D3:C1:FE:04:BB"
    frequency = 1000
    active_ports = [1, 2]

    device = NewDevice(address)

    try:
        device.start(frequency, active_ports, 16)
        device.loop()
    except KeyboardInterrupt:
        print("Stopping acquisition...")
    finally:
        device.stop()
        device.close()


if __name__ == "__main__":
    main()