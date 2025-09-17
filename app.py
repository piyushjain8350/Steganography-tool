import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, after_this_request
from steg import encode_in_image, decode_from_image
from werkzeug.utils import secure_filename
from uuid import uuid4
import time
import logging
import traceback
from werkzeug.exceptions import RequestEntityTooLarge
from PIL import Image
import io
import os as _os
import gc
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = '/tmp'  # Use /tmp for Render
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload size
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}
ALLOWED_FILE_EXTENSIONS = {'txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allow larger images while still guarding memory. Configurable via env var.
MAX_IMAGE_DIM = int(_os.getenv('MAX_IMAGE_DIM', '5000'))  # width/height max

def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

def _wait_for_file_release(file_path, attempts=10, delay=0.15):
    """On Windows, recently-saved uploads can remain locked briefly. Retry open/close."""
    last_err = None
    for _ in range(attempts):
        try:
            with open(file_path, 'rb') as f:
                f.read(1)
            return True
        except Exception as e:
            last_err = e
            time.sleep(delay)
    if last_err:
        raise last_err
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hide', methods=['GET', 'POST'])
def hide():
    if request.method == 'POST':
        image = request.files.get('image')
        op_type = request.form.get('op_type')
        password = request.form.get('password')

        if not image or not password or not op_type:
            flash('All fields are required.')
            return redirect(request.url)

        if not allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            flash('Invalid image format.')
            return redirect(request.url)

        image_filename = f"{uuid4().hex}_{secure_filename(image.filename)}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image.save(image_path)
        try:
            if hasattr(image, 'close'):
                image.close()
            elif hasattr(image, 'stream') and hasattr(image.stream, 'close'):
                image.stream.close()
        except Exception:
            pass

        data_bytes = b''
        hidden_path = None
        if op_type == 'text':
            text_data = request.form.get('text_data', '')
            data_bytes = text_data.encode()
        elif op_type == 'file':
            hidden_file = request.files.get('hidden_file')
            if not hidden_file or not allowed_file(hidden_file.filename, ALLOWED_FILE_EXTENSIONS):
                flash('Invalid or missing file to hide.')
                return redirect(request.url)

            hidden_filename = f"{uuid4().hex}_{secure_filename(hidden_file.filename)}"
            hidden_path = os.path.join(app.config['UPLOAD_FOLDER'], hidden_filename)
            hidden_file.save(hidden_path)
            try:
                if hasattr(hidden_file, 'close'):
                    hidden_file.close()
                elif hasattr(hidden_file, 'stream') and hasattr(hidden_file.stream, 'close'):
                    hidden_file.stream.close()
            except Exception:
                pass

            with open(hidden_path, 'rb') as f:
                data_bytes = f.read()

        # Generate a unique internal filename for processing
        internal_filename = f"stego_{uuid4().hex}_{secure_filename(image.filename)}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], internal_filename)
        
        # Get original filename for file extension preservation
        original_filename = None
        if op_type == 'file' and 'hidden_file' in locals():
            original_filename = hidden_file.filename
        
        try:
            start_time = time.time()
            encode_in_image(image_path, data_bytes, password, output_path, original_filename)
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 2)
            # Get the actual filename that was saved (with .png extension)
            actual_internal_filename = os.path.basename(output_path)
            if not actual_internal_filename.endswith('.png'):
                actual_internal_filename = os.path.splitext(actual_internal_filename)[0] + '.png'
            
            # Create a user-friendly filename for download (same as original but with stego_ prefix)
            original_name = os.path.splitext(image.filename)[0]
            original_ext = os.path.splitext(image.filename)[1]
            # Keep original extension for user download, even though we save as PNG internally
            download_filename = f"stego_{original_name}{original_ext}"
            
            # Store the mapping for download
            app.config.setdefault('filename_mapping', {})
            app.config['filename_mapping'][actual_internal_filename] = download_filename
            
            # Clean up temp files
            if os.path.exists(image_path):
                os.remove(image_path)
            if hidden_path and os.path.exists(hidden_path):
                os.remove(hidden_path)
            # Explicit memory cleanup
            del image, data_bytes, hidden_path
            gc.collect()
            return render_template('result.html',
                message="Data successfully hidden inside the image. Click below to download the new image.",
                download_url=url_for('download_file', filename=actual_internal_filename),
                elapsed_time=elapsed_time
            )
        except Exception as e:
            logging.error(traceback.format_exc())
            flash(f"Error encoding image: {e}")
            # Clean up temp files on error
            if os.path.exists(image_path):
                os.remove(image_path)
            if hidden_path and os.path.exists(hidden_path):
                os.remove(hidden_path)
            # Explicit memory cleanup
            del image, data_bytes, hidden_path
            gc.collect()
            return redirect(request.url)

    return render_template('hide.html')

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    flash("File is too large. Maximum allowed size is 10MB.")
    return redirect(request.url)

@app.route('/extract', methods=['GET', 'POST'])
def extract():
    if request.method == 'POST':
        image = request.files.get('image')
        password = request.form.get('password')

        if not image or not password:
            flash('Please provide both image and password.')
            return redirect(request.url)

        if not allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            flash('Invalid image format.')
            return redirect(request.url)

        image_filename = f"{uuid4().hex}_{secure_filename(image.filename)}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image.save(image_path)
        try:
            if hasattr(image, 'close'):
                image.close()
            elif hasattr(image, 'stream') and hasattr(image.stream, 'close'):
                image.stream.close()
        except Exception:
            pass

        # Check image dimensions to prevent memory issues
        try:
            _wait_for_file_release(image_path)
            # Load via bytes buffer to avoid keeping file handle locked by PIL
            with open(image_path, 'rb') as fp:
                img_bytes = fp.read()
            with Image.open(io.BytesIO(img_bytes)) as img_check:
                if img_check.width > MAX_IMAGE_DIM or img_check.height > MAX_IMAGE_DIM:
                    os.remove(image_path)
                    flash(f"Image dimensions are too large (max {MAX_IMAGE_DIM}x{MAX_IMAGE_DIM}).")
                    return redirect(request.url)
        except Exception as e:
            if os.path.exists(image_path):
                os.remove(image_path)
            flash(f"Error reading image: {e}")
            return redirect(request.url)

        try:
            start_time = time.time()
            _wait_for_file_release(image_path)
            data, file_extension = decode_from_image(image_path, password)
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 2)

            # List of known text file extensions
            text_exts = ['.txt', '.md', '.json', '.xml', '.html', '.css', '.js', '.py', '.java', '.cpp', '.c', '.h', '.sql', '.csv']

            # If file_extension is present and NOT a known text extension, treat as file
            if file_extension and file_extension.lower() not in text_exts:
                output_filename = f"extracted_{uuid4().hex}{file_extension}"
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
                with open(output_path, 'wb') as f:
                    f.write(data)
                # Clean up temp image file
                if os.path.exists(image_path):
                    os.remove(image_path)
                # Explicit memory cleanup
                del image, data, file_extension
                gc.collect()
                return render_template('result.html',
                    message="Hidden file extracted successfully. Click below to download it.",
                    download_url=url_for('download_file', filename=output_filename),
                    elapsed_time=elapsed_time
                )

            # If it's a known text extension, or no extension, try to decode as text
            try:
                text_content = data.decode('utf-8')
                # Additional check: if it looks like text (mostly printable characters)
                if all(32 <= ord(char) <= 126 or char in '\n\r\t' for char in text_content[:1000]):
                    # Clean up temp image file
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    # Explicit memory cleanup
                    del image, data
                    gc.collect()
                    return render_template('text_result.html',
                        message="Hidden text extracted successfully!",
                        text_content=text_content,
                        elapsed_time=elapsed_time
                    )
            except UnicodeDecodeError:
                pass

            # Fallback: treat as file
            if file_extension:
                output_filename = f"extracted_{uuid4().hex}{file_extension}"
            else:
                output_filename = f"extracted_{uuid4().hex}.bin"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            with open(output_path, 'wb') as f:
                f.write(data)
            # Clean up temp image file
            if os.path.exists(image_path):
                os.remove(image_path)
            # Explicit memory cleanup
            del image
            gc.collect()
            return render_template('result.html',
                message="Hidden file extracted successfully. Click below to download it.",
                download_url=url_for('download_file', filename=output_filename),
                elapsed_time=elapsed_time
            )

        except Exception as e:
            logging.error(traceback.format_exc())
            flash(f"Failed to extract hidden data: {e}")
            # Clean up temp image file on error
            if os.path.exists(image_path):
                os.remove(image_path)
            # Explicit memory cleanup
            del image
            gc.collect()
            return redirect(request.url)

    return render_template('extract.html')

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            import logging
            logging.error(f"Error deleting file {file_path}: {e}")
        return response

    # Check if we have a user-friendly filename mapping
    if 'filename_mapping' in app.config and filename in app.config['filename_mapping']:
        download_filename = app.config['filename_mapping'][filename]
        return send_file(file_path, as_attachment=True, download_name=download_filename)
    else:
        return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) 