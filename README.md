# steganography-tool
🔍 A simple Python Flask-based Steganography Tool for hiding and extracting secret messages and file inside images. Free and open source.

# 🖼️ Steganography Tool

A lightweight **steganography web application** built with **Python Flask**, allowing you to **hide secret message and file inside images and extract them**. Useful for learning and demonstrating how data can be concealed in media files.

---

## 🚀 Features
- 📥 **Encode**: Hide text and file inside image files (PNG/JPEG).
- 🔍 **Decode**: Extract hidden messages and file from images.
- 🌐 Web interface built with Flask for easy use.

---

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/your-username/steganography-tool.git
cd steganography-tool

# Create virtual environment & install dependencies
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

# Run the app
python app.py
