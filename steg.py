import os
from PIL import Image
import numpy as np
from utils import xor_encrypt_decrypt

# Converts bytes to a string of binary digits
def data_to_bits(data):
    return ''.join(f"{byte:08b}" for byte in data)

# Converts binary string back to bytes
def bits_to_data(bits):
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))

# Hides data in image using LSB steganography + XOR encryption
def encode_in_image(image_path, data_bytes, password, output_path, original_filename=None):
    img = Image.open(image_path).convert("RGBA")
    encrypted_data = xor_encrypt_decrypt(data_bytes, password)
    
    # Add file extension info and stop marker
    if original_filename:
        ext = os.path.splitext(original_filename)[1]
        ext_bytes = ext.encode()
        ext_length = len(ext_bytes).to_bytes(1, 'big')
        encrypted_data = ext_length + ext_bytes + encrypted_data
    
    # Add stop marker to indicate end of data
    marker = '00000011' * 4
    binary_data = data_to_bits(encrypted_data) + marker

    # Convert image to numpy array for faster processing
    img_array = np.array(img, dtype=np.uint8)
    
    # Flatten the RGB channels for easier bit manipulation
    height, width, channels = img_array.shape
    flat_pixels = img_array[:, :, :3].reshape(-1)
    
    # Calculate how many pixels we need
    bits_needed = len(binary_data)
    pixels_needed = (bits_needed + 2) // 3  # 3 bits per pixel (R,G,B)
    
    if pixels_needed > len(flat_pixels):
        raise ValueError("Image too small to hide this data!")
    
    # Convert binary data to integers
    binary_array = np.array([int(bit) for bit in binary_data])
    
    # Set LSB of each color channel
    for i in range(min(len(binary_array), len(flat_pixels))):
        # Clear the LSB and set it to our data bit
        pixel_value = int(flat_pixels[i])
        new_value = (pixel_value & ~1) | binary_array[i]
        # Ensure the value stays within uint8 bounds (0-255)
        flat_pixels[i] = np.uint8(max(0, min(255, new_value)))
    
    # Reshape back to image dimensions
    img_array[:, :, :3] = flat_pixels.reshape(height, width, 3)
    
    # Convert back to PIL Image
    result_img = Image.fromarray(img_array)
    
    # Save output as PNG for lossless compression (but keep original path for mapping)
    png_output_path = os.path.splitext(output_path)[0] + ".png"
    result_img.save(png_output_path)
    print(f"[INFO] Stego image saved to {png_output_path}")

# Extracts hidden data from an image using XOR decryption
def decode_from_image(image_path, password):
    img = Image.open(image_path).convert("RGBA")
    
    # Convert to numpy array for faster processing
    img_array = np.array(img, dtype=np.uint8)
    
    # Extract LSB from RGB channels
    flat_pixels = img_array[:, :, :3].reshape(-1)
    binary_data = ''.join(str(int(pixel) & 1) for pixel in flat_pixels)
    
    # Find the marker
    marker = '00000011' * 4
    marker_index = binary_data.find(marker)
    
    if marker_index == -1:
        raise ValueError("No hidden data found!")
    
    # Extract the encrypted data
    encrypted_bits = binary_data[:marker_index]
    encrypted_data = bits_to_data(encrypted_bits)
    
    # Check if we have file extension info
    if len(encrypted_data) > 1:
        ext_length = encrypted_data[0]
        if ext_length > 0 and len(encrypted_data) > ext_length + 1:
            ext_bytes = encrypted_data[1:1+ext_length]
            actual_data = encrypted_data[1+ext_length:]
            decrypted_data = xor_encrypt_decrypt(actual_data, password)
            return decrypted_data, ext_bytes.decode()
    
    # Fallback for old format or no extension
    decrypted_data = xor_encrypt_decrypt(encrypted_data, password)
    return decrypted_data, None
