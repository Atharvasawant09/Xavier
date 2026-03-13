# DocInt — Windows Setup Guide

Follow this guide to get the Document Intelligence (DocInt) system running on a Windows machine for your demo.

## 1. Prerequisites
Before starting, ensure you have the following software installed:

- **Python (3.10 or higher)**
  - Download from: [python.org](https://www.python.org/downloads/windows/)
  - **CRITICAL:** During the installation, make sure to check the box that says **"Add Python to PATH"** at the bottom of the installer window.
- **Visual Studio Code (VS Code)**
  - A free code editor. Download from: [code.visualstudio.com](https://code.visualstudio.com/)
- **Git (Optional but recommended)**
  - Download from: [git-scm.com/download/win](https://git-scm.com/download/win)

## 2. Opening the Project
1. Extract the project folder anywhere on your computer (e.g., your Desktop).
2. Open **VS Code**.
3. Go to **File > Open Folder...** and select the `DocInt` directory.

## 3. Setting Up the Environment
You should isolate the project dependencies using a virtual environment (`venv`).

1. Open an integrated terminal in VS Code:
   - Go to **Terminal > New Terminal** (or use the shortcut `` Ctrl + ` ``).
2. Ensure you are in the `DocInt` folder. 
3. Create the virtual environment by running:
   ```cmd
   python -m venv venv
   ```
4. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
   *(You should see `(venv)` appear at the beginning of your terminal prompt indicating it is active. If you encounter an execution policy error on PowerShell, run `Set-ExecutionPolicy Unrestricted -Scope CurrentUser` in an administrative PowerShell first).*

## 4. Installing Dependencies
With your virtual environment activated, install all the required Python packages:

```cmd
pip install -r requirements.txt
```
*Note: Your project uses Streamlit for the user interface. Just to ensure the frontend works flawlessly, install it explicitly along with its dependencies by running:*
```cmd
pip install streamlit watchdog
```

## 5. Environment Variables
Check the `.env` file in the root of the project. Ensure the `GROQ_API_KEY` is set correctly for your DEV environment. The existing configuration sets `LLM_USE_STUB=true` which interacts with the Groq API.
```env
LLM_USE_STUB=true
GROQ_API_KEY=your_actual_api_key_here
```

## 6. Running the Application
The DocInt system has two parts: the FastAPI Backend and the Streamlit Frontend. You will need **two separate terminals** running at the same time.

### Step A: Start the Backend server
1. In your currently active VS Code terminal (`venv` must be active), run the provided batch script:
   ```cmd
   run.bat
   ```
   *Alternatively, if `run.bat` doesn't work, manually run:*
   ```cmd
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Wait for it to say `Application startup complete.`

### Step B: Start the Frontend UI
1. Open a **second terminal** in VS Code (click the `+` icon in the terminal panel).
2. Activate the virtual environment in this new terminal too:
   ```cmd
   venv\Scripts\activate
   ```
3. Run the Streamlit User Interface:
   ```cmd
   streamlit run app_ui.py
   ```
4. A browser window will automatically pop open pointing to `http://localhost:8501`. If it doesn't, navigate to that URL manually in Chrome, Edge, or Firefox.

## 7. Using the App
- When prompted for an "Active User", you can type your name (e.g. `dev_user`).
- Go to the **Documents** tab to upload PDFs.
- Go to the **Query** tab to interact with your embedded documents.
- Remember to leave both terminal windows open and running while using the application. To stop them later, you can click into each terminal and press `Ctrl + C`.
