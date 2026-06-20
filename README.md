# Karthikey - Python Web Merge (Termux-friendly)

This repo contains a small Flask app that reproduces the original index.html UI and provides a pipeline you can control remotely (useful from Termux).

Quick Termux setup (on your Android device):

1. Install Python in Termux:
   pkg update && pkg upgrade
   pkg install python git

2. Clone this repo or pull changes:
   git clone https://github.com/lezarexplainer-create/Karthikey.git
   cd Karthikey

3. Install dependencies:
   pip install -r requirements.txt

4. Make run.sh executable:
   chmod +x run.sh

5. Start the app:
   ./run.sh start

6. Open in browser (on device): http://127.0.0.1:5000
   Or from another machine on the same network: http://<device-ip>:5000

Remote control (from Termux or any other device):
- Add a site to pipeline (HTTP POST JSON):
  curl -X POST -H "Content-Type: application/json" -d '{"name":"Hugging Face", "url":"https://huggingface.co"}' http://localhost:5000/api/pipeline

- View pipeline:
  curl http://localhost:5000/api/pipeline

- Run pipeline:
  curl -X POST http://localhost:5000/api/run

- Remove item index 0:
  curl -X DELETE http://localhost:5000/api/pipeline/0

Persistence:
- The pipeline is saved to pipeline.json in the repo directory so it survives restarts.

Security note:
- This app is for local use. If you expose it to the internet, secure it (auth, firewall, HTTPS).
