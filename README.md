# CogniCompanion — Complete Setup & Run Guide
**AI-Based Cognitive Assistance & Caregiver Platform for Elderly Dementia Patients**

---

## ⚡ Quick 3-Step Start

```
[ Terminal 1: Backend ]   --> uvicorn app.main:app --host 0.0.0.0 --port 8000
[ Terminal 2: Web Portal ] --> npm run dev (http://localhost:5173)
[ Android Studio: Phone ]  --> Select Physical Phone -> Click Run (Shift + F10)
```

---

## 1. Step 1: Start the Backend Server (FastAPI)

Open **PowerShell** or Command Prompt and navigate to the backend folder:

```powershell
cd c:\Projects\sih\cognicompanion\backend
```

Activate the Python 3.12 virtual environment:
```powershell
.\venv312\Scripts\Activate.ps1
```

*(Optional - First time only)* If you want to populate the database with demo patient, medications, and memories:
```powershell
python seed_demo_patient.py
```

Run the backend server:
```powershell
cd c:\Projects\sih\cognicompanion\backend
.\venv312\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> ⚠️ **IMPORTANT**: You **must** use `--host 0.0.0.0` (not `127.0.0.1`). This instructs Windows to accept incoming API requests from both your laptop browser and your physical mobile phone over your Wi-Fi network.

---

## 2. Step 2: Start the Caregiver Web Portal

Open a second terminal and navigate to the frontend folder:

```powershell
cd c:\Projects\sih\cognicompanion\frontend
```

Start the Vite development server:
```powershell
npm run dev
```

Open your browser and navigate to:
👉 **`http://localhost:5173`**

---

## 3. Step 3: Run the Patient App on Your Physical Android Phone

Open **Android Studio** with the project folder:
`c:\Projects\sih\cognicompanion\patient_app`

### Connection Method A: Over Wi-Fi (Pre-Configured)
1. Ensure your laptop and your physical phone are connected to the **same Wi-Fi network**.
2. Your laptop's current Wi-Fi IP is already set in:  
   `patient_app/lib/services/api_service.dart` (`static const String serverIp = '192.168.1.105';`)
3. Connect your phone to your PC via USB cable (or wireless ADB).
4. Select your phone from the device dropdown in Android Studio.
5. Click **Run** (or press `Shift + F10`).

### Connection Method B: Over USB Cable (Fastest & Most Reliable)
If you are running connected to your laptop via USB cable with USB Debugging enabled:
Open a terminal in Android Studio or PowerShell:
```powershell
adb reverse tcp:8000 tcp:8000
```
*(If `adb` is not recognized in your PATH, run:*  
`& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" reverse tcp:8000 tcp:8000`*)*

This tunnels port 8000 directly through the USB wire so your phone communicates with your laptop instantly even without Wi-Fi!

---

## 4. What If Your Laptop's Wi-Fi IP Changes?

When you connect to a new Wi-Fi router, your laptop's IP address might change. To update it:

1. Open PowerShell on your laptop and run:
   ```powershell
   ipconfig
   ```
   Look for **IPv4 Address** under your Wi-Fi adapter (e.g. `192.168.1.xxx`).

2. Open [`patient_app/lib/services/api_service.dart`](file:///c:/Projects/sih/cognicompanion/patient_app/lib/services/api_service.dart) line 13:
   ```dart
   static const String serverIp = 'YOUR_NEW_IP_HERE';
   ```

---

## 5. Live Two-Way Sync Demo (How to Test Everything Together)

Once both the website and phone app are running:

### Test 1: Caregiver Logs a Memory → Patient Asks by Voice
1. On your **Laptop Browser** (`http://localhost:5173`):
   - Click on **Memories** in the sidebar.
   - Click **+ Log Memory**.
   - Title: `Rahul's Afternoon Visit`
   - Description: `Rahul brought sweet mangoes and sat on the veranda enjoying tea with you.`
   - Click **Save**.
2. On your **Phone App**:
   - Tap the central **Voice Orb** (turns to *"Listening..."*).
   - Say: *"Who visited me yesterday?"* or *"What did Rahul bring?"*
   - The AI Assistant will answer aloud using device Text-to-Speech with the exact memory you just logged on the laptop!
3. On your **Laptop Browser**:
   - Click **Assistant Logs** on the website to see the transparent explainability provenance showing the exact memory source used.

### Test 2: Medication Adherence Sync
1. On your **Phone App**:
   - On the Home screen under **Today's Plan**, tap **"Mark as Taken"** next to your morning medication.
   - A subtle haptic confirmation triggers, and a green `✓ Taken [Timestamp]` badge appears.
2. On your **Laptop Browser**:
   - Look at the **Caregiver Dashboard** (click **Sync**).
   - The dose immediately updates in real time to **Taken** with the recorded timestamp!

---

## 6. Troubleshooting Checklist

| Issue | Solution |
| :--- | :--- |
| **Phone says "Offline Mode" or fails to reach server** | 1. Verify backend terminal has `--host 0.0.0.0` running.<br>2. Check both devices are on the same Wi-Fi.<br>3. Check Windows Firewall allows Python/uvicorn on private networks.<br>4. Or run `adb reverse tcp:8000 tcp:8000` over USB cable. |
| **Android blocks HTTP traffic** | `android:usesCleartextTraffic="true"` is already added to `AndroidManifest.xml` to allow local `http://` calls. |
| **Voice speech not speaking on phone** | Make sure your phone's media/TTS volume is turned up and Google Text-to-Speech is enabled in phone settings. |

---

## 7. Production Deployment (Docker & Compose)

To run the complete production stack (PostgreSQL + pgvector, FastAPI Backend, Nginx + Vite Frontend) containerized:

```bash
# Build and run all services in background
docker compose up -d --build

# Run database migrations inside the backend container
docker compose exec backend alembic upgrade head

# (Optional) Seed demo patient and initial data
docker compose exec backend python seed_demo_patient.py

# Check running status
docker compose ps

# View service logs
docker compose logs -f backend
```

- **Frontend Portal**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432`

