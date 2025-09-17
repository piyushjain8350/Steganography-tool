# XOR encrypt/decrypt using a password
def xor_encrypt_decrypt(data, password):
    key = password.encode()
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

# Convert bytes to a binary string
def data_to_bits(data):
    return ''.join(f"{byte:08b}" for byte in data)

# Convert binary string to bytes
def bits_to_data(bits):
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))