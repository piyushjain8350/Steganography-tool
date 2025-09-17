def xor_encrypt_decrypt(data: bytes, password: str) -> bytes:
    """Encrypt/decrypt data using a repeating-key XOR with the given password.

    If password is empty, data is returned unchanged. The function is symmetric:
    applying it twice with the same password yields the original data.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes or bytearray")

    if password is None:
        password = ""

    if password == "":
        # No-op if no password provided
        return bytes(data)

    key_bytes = password.encode("utf-8")
    key_length = len(key_bytes)

    # Use bytearray for efficient in-place writes
    output = bytearray(len(data))
    for index, byte_value in enumerate(data):
        output[index] = byte_value ^ key_bytes[index % key_length]

    return bytes(output)


