# DocInt — NVIDIA AGX Jetson Xavier Setup Guide

This guide provides step-by-step instructions to get the **DocInt** application running on an NVIDIA AGX Jetson Xavier with GPU acceleration for the LLM (using `llama.cpp` and Qwen).

## 1. System Dependencies and Preparation

Before setting up Python packages, you must install system-level packages required for building `llama-cpp-python`, processing PDFs, and performing OCR.

Open a terminal on your Xavier and run:
```bash
sudo apt update
sudo apt install -y python3-pip python3-dev python3-venv build-essential cmake 
sudo apt install -y poppler-utils tesseract-ocr libgl1
```
*Note: `poppler-utils` is for PDF conversion and `tesseract-ocr` is for image text extraction.*

## 2. Setting Up the Project folder

1. If you haven't already, transfer or clone the `DocInt` folder onto the Xavier. 
2. Open a terminal and navigate to the project directory:
   ```bash
   cd /path/to/DocInt
   ```

## 3. Creating a Virtual Environment

It's highly recommended to use a virtual environment to avoid conflicts with system Python packages.

1. Create the virtual environment:
   ```bash
   python3 -m venv venv
   ```
2. Activate it:
   ```bash
   source venv/bin/activate
   ```
*(You will need to activate this `venv` every time you run the application or install packages).*

## 4. Installing Python Dependencies

With the virtual environment activated `(venv)`, install application dependencies:

1. **Install core packages:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: Since you are running the UI as well, install Streamlit:*
   ```bash
   pip install streamlit watchdog
   ```

2. **Install GPU-Accelerated LLM Engine (`llama-cpp-python`):**
   For the Jetson Xavier to utilize its GPU for inference, you must compile `llama-cpp-python` with CUDA enabled:
   ```bash
   CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
   ```

## 5. Downloading the Qwen Model

Your `.env` file references a specific model path. You need to download the Qwen GGUF file.
We suggest placing models on an SSD if you have one mounted (e.g., `/mnt/ssd/models/`), or in a dedicated models folder inside the project.

Create the models directory and download it:
```bash
mkdir -p /mnt/ssd/models/
cd /mnt/ssd/models/
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
cd /path/to/DocInt
```
*(Ensure the filename matches what is in your `.env` exactly).*

## 6. Configuring the `.env` File

Open the `.env` file in the root of the project to switch from Groq API (Dev Mode) to Local LLM (Xavier Mode).

Change these specific lines in `.env`:
```env
# Switch off the Dev Stub to use the local LLM
LLM_USE_STUB=false

# Make sure this path matches exactly where you downloaded the model
MODEL_PATH=/mnt/ssd/models/qwen2.5-7b-instruct-q4_k_m.gguf

# Optional: Set the data folder to your SSD if you have one mounted for faster memory
# DATA_DIR=/mnt/ssd/docint/data
```

## 7. Running the Application

The system requires two separate terminal windows (or tabs) to handle the Backend (FastAPI) and Frontend (Streamlit) services. 

### Terminal 1: Start the Backend
1. Open a terminal, navigate to the `DocInt` folder, and activate the virtual environment:
   ```bash
   cd /path/to/DocInt
   source venv/bin/activate
   ```
2. Run the FastAPI server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   *Wait until you see `Application startup complete.`*

### Terminal 2: Start the Frontend UI
1. Open a **new** terminal window, navigate to the `DocInt` folder, and activate the virtual environment:
   ```bash
   cd /path/to/DocInt
   source venv/bin/activate
   ```
2. Run the Streamlit application:
   ```bash
   streamlit run app_ui.py --server.address 0.0.0.0 --server.port 8501
   ```

## 8. Accessing the Application

Since the Xavier might be running headlesly or you might be interacting with it from your laptop, you can access the application over the network:

1. Find the Xavier's IP address (run `ip a` or `hostname -I` on the Xavier).
2. On your Windows laptop, open a web browser and navigate to:
   ```
   http://<XAVIER_IP_ADDRESS>:8501
   ```
*(Replace `<XAVIER_IP_ADDRESS>` with the actual IP, for instance `http://192.168.1.50:8501`).*
