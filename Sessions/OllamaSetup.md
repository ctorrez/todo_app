# Local Ollama Setup Guide

This guide documents how local **Ollama** was installed, verified, and integrated with the Clean Architecture TODO application to provide 100% private, self-hosted natural language task ingestion.

---

## 1. Overview & Architecture Motivation

Instead of calling cloud APIs (like OpenAI or Gemini) which require payment, API keys, and transmit personal task data over the internet, we integrated **Ollama** running locally on the machine.

* **Privacy**: 100% air-gapped; zero data leaves the machine.
* **Cost**: $0 forever.
* **Integration**: Follows Clean Architecture by implementing the `TaskParserPort` interface inside `src/todo/infrastructure/ai/ollama_parser.py`.

---

## 2. Hardware Context & Model Selection

* **CPU**: Intel Core i7-4720HQ (4 Cores / 8 Threads, AVX2 support)
* **RAM**: 16 GB (~6.4 GB free)
* **GPU**: Intel HD Graphics 4600 (Inference runs on CPU)

### Model Choice: `llama3.2:1b`
Meta's **Llama 3.2 1B** parameter model was selected as the sweet spot:
* **Download Size**: ~1.3 GB
* **Memory Footprint**: ~1.8 GB RAM (fits comfortably within available memory)
* **Speed**: ~15–25 tokens/second on CPU
* **Accuracy**: Excellent at deterministic JSON schema extraction and relative date calculations (e.g., "tomorrow", "this Friday").

---

## 3. Installation Steps

### Step 1: Install Ollama on Windows
The official installation script was run in PowerShell:

```powershell
irm https://ollama.com/install.ps1 | iex
```

* **Default Installation Path**:
  `$env:LOCALAPPDATA\Programs\Ollama\ollama.exe`
  *(e.g., `C:\Users\<Username>\AppData\Local\Programs\Ollama\ollama.exe`)*
* **Background Service**:
  The installer automatically launches the Ollama background daemon and system tray icon listening on `http://localhost:11434`.

---

### Step 2: Verify Ollama Service

Verify the CLI is installed and running:

```powershell
ollama --version
```

Verify the local REST endpoint is active:

```powershell
(Invoke-RestMethod -Uri "http://localhost:11434/api/tags").models
```

---

### Step 3: Download (Pull) the Model

Download the lightweight `llama3.2:1b` model:

```powershell
ollama pull llama3.2:1b
```

Once completed, confirm the model is available:

```powershell
ollama list
```

Output:
```text
NAME           ID              SIZE      MODIFIED
llama3.2:1b    baf6a787fdff    1.3 GB    Just now
```

---

## 4. How the App Integrates with Ollama

The application communicates with the local Ollama daemon via its REST API:

* **Endpoint**: `POST http://localhost:11434/api/generate`
* **JSON Mode**: `"format": "json"` ensures the model strictly returns valid JSON matching our schema.
* **Low Temperature**: `"temperature": 0.1` ensures deterministic outputs.
* **Relative Date Resolution**: The current reference date (`YYYY-MM-DD` and day of week) is injected into the system prompt so terms like *"tomorrow"* or *"this Friday"* are accurately calculated.

---

## 5. Usage Commands

Ensure your virtual environment is active, then run:

### A. Preview Extraction (No Database Save)
```powershell
python app.py ai parse "Urgent meeting with Sarah tomorrow at 2pm to review quarterly budget"
```

Output:
```text
AI Extracted Task Details (Preview - Not Saved):
  Title:       Urgent meeting with Sarah
  Description: to review quarterly budget
  Due Date:    2026-10-20
  Priority:    URGENT
```

### B. Extract and Save Task Directly
```powershell
python app.py ai add "Dentist appointment this Friday morning"
```

Output:
```text
AI Task Created: #1 [LOW] - Dentist Appointment (Due: 2026-10-23)
   Description: Book a dentist appointment for this Friday morning
```

### C. Agent / JSON Output
```powershell
python app.py ai add "Submit taxes next Monday" --json
```

---

## 6. Troubleshooting

1. **`ollama: The term 'ollama' is not recognized`**:
   Restart your terminal or run directly using:
   ```powershell
   & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" <command>
   ```
2. **`Could not connect to local Ollama at http://localhost:11434`**:
   Make sure the Ollama application is running in your Windows system tray. You can launch it by running:
   ```powershell
   Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe"
   ```
