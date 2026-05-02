SiapGuru

Cara menjalankan:
1. Install dependency:
   pip install -r requirements.txt
2. Jalankan aplikasi:
   python main.py

Build EXE:
pyinstaller --onefile --windowed --icon=assets/icon.ico --add-data "ui/styles.qss;ui" --name SiapGuru main.py
