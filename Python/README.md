# Python API sample

The API files in these samples are meant to be run using Python.

This repository includes the following **3 Examples**:

- `OneDeviceAcquisitionExample.py` | Demonstrates how-to trigger the start of a real-time acquisition from **1 Device**;
- `OneDeviceSpecialChannelsExample.py` | Demonstrates how-to trigger the start of a real-time acquisition from **1 Device** that has a **Digital Channel** (SpO2, fNIRS,...) connected to the bottom-left port of the hub (:arrow_down:);
- `MultipleDeviceThreadingExample.py` | Demonstrates how-to trigger the start of a real-time acquisition from **2 Devices** using separate **Threads**.

### 🛠 macOS Setup for PLUX Python API

When running the **PLUX Python API** for the first time on **macOS**, you might see errors like:

```
RuntimeError: The communication port could not be initialized.
[BTH_MACOS] Spawn Status 13
```

This happens because **macOS Gatekeeper** blocks unsigned binaries and libraries downloaded from the internet.

The **PLUX API** uses:

- **`plux.so`** — the Python/C++ API library
- **`bth_macprocess`** — a helper executable for Bluetooth communication

You need to give these files permission to run.

---

## Step 1: Locate the Files

These files are usually in your project’s `python_api` folder (in the current repository they are stored inside the `PLUX-API-Python3` folder, in the respective **Python** and **Operating System** directory):

```
python_api/plux.so
python_api/bth_macprocess
```

---

## Step 2: Remove Quarantine Attribute

**macOS** tags downloaded files with a `com.apple.quarantine` flag.
Remove it with:

```bash
xattr -d com.apple.quarantine /path/to/python_api/plux.so
xattr -d com.apple.quarantine /path/to/python_api/bth_macprocess
```

---

## Step 3: Make the Helper Executable

`bth_macprocess` must have execute permissions:

```bash
chmod +x /path/to/python_api/bth_macprocess
```

_(You do **not** need to do this for `plux.so` — it’s a library, not an executable.)_

---

## Step 4: Ad-hoc Code Signing

Sign both files so **macOS** allows them to run:

```bash
codesign -s - --timestamp --force /path/to/python_api/plux.so
codesign -s - --timestamp --force /path/to/python_api/bth_macprocess
```

This uses an **ad-hoc signature** (`-s -`) — no **Apple Developer ID** required.

---

## Step 5: Verify

You can check that the quarantine attribute is gone and signatures are applied:

```bash
xattr /path/to/python_api/plux.so
codesign -dv /path/to/python_api/plux.so
```

If `xattr` shows nothing and `codesign` returns signature info, you’re ready to go.

---
