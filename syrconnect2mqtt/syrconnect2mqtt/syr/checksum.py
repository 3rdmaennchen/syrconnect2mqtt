import xmltodict


class SYRChecksum:
    def __init__(self, base_characters: str, key: str):
        self.base_characters = base_characters
        self.key = key
        self.checksum_value = 0

    def compute_checksum_value(self, value: str) -> int:
        normalized = (value or "").strip()
        if not normalized:
            return 0

        buf = normalized.encode("utf-8")
        bytes_list = list(buf)

        total_bits = len(bytes_list) * 8
        num_chunks = (total_bits + 4) // 5

        contribution = 0
        bit_offset = 0
        byte_index = 0

        for chunk_index in range(num_chunks):
            if bit_offset >= 8:
                byte_index += 1
                bit_offset = bit_offset % 8

            current_byte = bytes_list[byte_index] if byte_index < len(bytes_list) else 0
            shifted = (current_byte << bit_offset) & 0xFF

            if bit_offset > 3:
                next_byte = bytes_list[byte_index + 1] if (byte_index + 1) < len(bytes_list) else 0
                shift_amt = 8 - (bit_offset - 3)
                next_part = ((next_byte >> shift_amt) << 3) & 0xFF
                shifted |= next_part

            five_bit_value = shifted >> 3

            key_char = self.key[chunk_index % len(self.key)]
            offset = self.base_characters.find(key_char)
            if offset < 0:
                offset = 0

            sum_val = five_bit_value + offset
            if sum_val >= len(self.base_characters):
                sum_val = sum_val - len(self.base_characters) + 1

            contribution += ord(self.base_characters[sum_val]) & 0xFF

            bit_offset += 5

        return contribution

    def add_to_checksum(self, input_str: str):
        self.checksum_value += self.compute_checksum_value(input_str)

    def add_xml_to_checksum(self, xml_string: str):
        try:
            json_obj = xmltodict.parse(xml_string)
            values = []

            def extract(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, (dict, list)):
                            extract(v)
                        else:
                            if k != "n":
                                values.append(str(v))
                elif isinstance(obj, list):
                    for item in obj:
                        extract(item)

            extract(json_obj)

            for v in values:
                self.add_to_checksum(v)

        except Exception as e:
            print("Error parsing XML:", e)

    def reset_checksum(self):
        self.checksum_value = 0

    def get_checksum(self) -> str:
        return format(self.checksum_value, "X").upper()

    def set_checksum(self, hex_string: str):
        self.checksum_value = int(hex_string, 16)
