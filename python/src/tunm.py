from ast import pattern
import enum
from enum import IntEnum
from math import floor

from .bytebuffer import ByteBuffer
 
@enum.unique
class TP_DATA_TYPE(IntEnum):
    TYPE_NIL = 0,
    TYPE_BOOL = 1,
    TYPE_U8 = 2,
    TYPE_I8 = 3,
    TYPE_U16 = 4,
    TYPE_I16 = 5,
    TYPE_U32 = 6,
    TYPE_I32 = 7,
    TYPE_U64 = 8,
    TYPE_I64 = 9,
    TYPE_VARINT = 10,
    TYPE_FLOAT = 11,
    TYPE_DOUBLE = 12,
    TYPE_STR = 13,
    TYPE_STR_IDX = 14,
    TYPE_RAW = 15,
    TYPE_ARR = 16,
    TYPE_MAP = 17,
    
class TPPacker:
    
    @staticmethod
    def get_type_by_ref(ref_type):
        if ref_type == str:
            return TP_DATA_TYPE.TYPE_STR
        elif ref_type == bytes:
            return TP_DATA_TYPE.TYPE_RAW
        elif ref_type == dict:
            return TP_DATA_TYPE.TYPE_MAP
        elif ref_type == list:
            return TP_DATA_TYPE.TYPE_ARR
        elif ref_type == int:
            return TP_DATA_TYPE.TYPE_I64
        elif ref_type == float:
            return TP_DATA_TYPE.TYPE_DOUBLE
        return TP_DATA_TYPE.TYPE_NIL
    
    @staticmethod        
    def decode_varint(buffer: ByteBuffer):
        real = 0
        shl_num = 0
        while True:
            data = buffer.read_u8()
            real += (data & 0x7F) << shl_num
            shl_num += 7
            if (data & 0x80) == 0:
                break
        is_left = real % 2 == 1
        if is_left:
            return -floor(real / 2) - 1
        else:
            return floor(real / 2)
        
    @staticmethod        
    def decode_type(buffer: ByteBuffer):
        return buffer.read_u8()
    
    
    @staticmethod        
    def decode_number(buffer: ByteBuffer, pattern):
        if pattern == TP_DATA_TYPE.TYPE_U8:
            return buffer.read_u8()
        elif pattern == TP_DATA_TYPE.TYPE_I8:
            return buffer.read_i8()
        elif pattern == TP_DATA_TYPE.TYPE_U16:
            return buffer.read_u16()
        elif pattern == TP_DATA_TYPE.TYPE_I16:
            return buffer.read_i16()
        elif pattern == TP_DATA_TYPE.TYPE_U32:
            return buffer.read_u32()
        elif pattern == TP_DATA_TYPE.TYPE_I32:
            return buffer.read_i32()
        elif pattern == TP_DATA_TYPE.TYPE_U64:
            return buffer.read_u64()
        elif pattern == TP_DATA_TYPE.TYPE_I64:
            return buffer.read_i64()
        elif pattern == TP_DATA_TYPE.TYPE_FLOAT:
            return buffer.read_i32() / 1000.0
        elif pattern == TP_DATA_TYPE.TYPE_DOUBLE:
            return buffer.read_i64() / 1000000.0
        else:
            raise Exception(f"Unknow decode number type {pattern}")
        
    @staticmethod        
    def decode_str_raw(buffer: ByteBuffer, pattern):
        if pattern == TP_DATA_TYPE.TYPE_STR:
            length = TPPacker.decode_varint(buffer)
            if length == 0:
                return ""
            return buffer.read_str(length)
        elif pattern == TP_DATA_TYPE.TYPE_RAW:
            length = TPPacker.decode_varint(buffer)
            if length == 0:
                return ""
            return buffer.read_bytes(length)
        else:
            raise Exception(f"Unknow decode str type {pattern}")
    
    
    @staticmethod        
    def decode_field(buffer: ByteBuffer):
        pattern = TPPacker.decode_type(buffer)
        if pattern == TP_DATA_TYPE.TYPE_NIL:
            return None
        elif pattern == TP_DATA_TYPE.TYPE_BOOL:
            return True if buffer.read_u8() != 0 else False
        elif pattern >= TP_DATA_TYPE.TYPE_U8 and pattern <= TP_DATA_TYPE.TYPE_I64:
            return TPPacker.decode_varint(buffer)
        elif pattern == TP_DATA_TYPE.TYPE_FLOAT:
            return TPPacker.decode_varint(buffer) / 1000.0
        elif pattern == TP_DATA_TYPE.TYPE_DOUBLE:
            return TPPacker.decode_varint(buffer) / 1000000.0
        elif pattern == TP_DATA_TYPE.TYPE_VARINT:
            return TPPacker.decode_varint(buffer) 
        elif pattern == TP_DATA_TYPE.TYPE_STR_IDX:
            idx = TPPacker.decode_varint(buffer)
            return buffer.get_str(idx)
        elif pattern == TP_DATA_TYPE.TYPE_STR or pattern == TP_DATA_TYPE.TYPE_RAW:
            return TPPacker.decode_str_raw(buffer, pattern)
        elif pattern == TP_DATA_TYPE.TYPE_ARR:
            return TPPacker.decode_arr(buffer, pattern)
        elif pattern == TP_DATA_TYPE.TYPE_ARR:
            return TPPacker.decode_map(buffer, pattern)
        else:
            raise Exception("unknow type")
        
    
    
    @staticmethod        
    def decode_arr(buffer: ByteBuffer):
        size = TPPacker.decode_varint(buffer)
        arr = []
        for _idx in range(size):
            sub = TPPacker.decode_field(buffer)
            arr.append(sub)
        return arr
    
    
    @staticmethod        
    def decode_map(buffer: ByteBuffer):
        size = TPPacker.decode_varint(buffer)
        map = {}
        for _idx in range(size):
            key = TPPacker.decode_field(buffer)
            val = TPPacker.decode_field(buffer)
            map[key] = val
        return map
    
    @staticmethod        
    def decode_proto(buffer: ByteBuffer):
        name = TPPacker.decode_str_raw(buffer, TP_DATA_TYPE.TYPE_STR)
        str_len = TPPacker.decode_varint(buffer)
        for _ in range(str_len):
            value = TPPacker.decode_str_raw(buffer, TPPacker.TYPE_STR);
            buffer.add_str(value);
        sub_value = TPPacker.decode_field(buffer);
        return {"proto": name, "list": sub_value};
    
    
    @staticmethod
    def encode_varint(buffer: ByteBuffer, value):
        if type(value) == bool:
            value = 1 if value else 0
        
        for _i in range(12):
            b = value & 0x7F
            value >>= 7
            if value:
                buffer.write_u8(b | 0x80)
            else:
                buffer.write_u8(b)
        
    @staticmethod
    def encode_type(buffer: ByteBuffer, value):
        buffer.write_u8(value)
        
    @staticmethod
    def encode_bool(buffer: ByteBuffer, value):
        buffer.write_u8(1 if value else 0)
        
    @staticmethod
    def encode_number(buffer: ByteBuffer, value, pattern):
        if pattern == TP_DATA_TYPE.TYPE_U8:
            return buffer.write_u8(value)
        elif pattern == TP_DATA_TYPE.TYPE_I8:
            return buffer.write_i8(value)
        elif pattern == TP_DATA_TYPE.TYPE_U16:
            return buffer.write_u16(value)
        elif pattern == TP_DATA_TYPE.TYPE_I16:
            return buffer.write_i16(value)
        elif pattern == TP_DATA_TYPE.TYPE_U32:
            return buffer.write_u32(value)
        elif pattern == TP_DATA_TYPE.TYPE_I32:
            return buffer.write_i32(value)
        elif pattern == TP_DATA_TYPE.TYPE_U64:
            return buffer.write_u64(value)
        elif pattern == TP_DATA_TYPE.TYPE_I64:
            return buffer.write_i64(value)
        elif pattern == TP_DATA_TYPE.TYPE_FLOAT:
            return buffer.write_i32(value * 1000.0)
        elif pattern == TP_DATA_TYPE.TYPE_DOUBLE:
            return buffer.write_i64(value * 1000000.0)
        else:
            raise Exception(f"Unknow decode number type {pattern}")
            
    @staticmethod
    def encode_str_idx(buffer: ByteBuffer, value):
        idx = buffer.add_str(value)
        TPPacker.encode_type(buffer, TP_DATA_TYPE.TYPE_STR_IDX)
        TPPacker.encode_varint(buffer, idx);
        
    @staticmethod
    def encode_str_raw(buffer: ByteBuffer, value):
        if pattern == TP_DATA_TYPE.TYPE_STR:
            b = value.encode("utf-8")
            TPPacker.encode_varint(buffer, len(b))
            buffer.write_bytes(b)
        elif pattern == TP_DATA_TYPE.TYPE_RAW:
            TPPacker.encode_varint(buffer, len(value))
            buffer.write_bytes(value)
        else:
            raise Exception(f"Unknow decode str type {pattern}")
        
    @staticmethod        
    def encode_field(buffer: ByteBuffer, value):
        pattern = TPPacker.get_type_by_ref(value)
        if pattern == TP_DATA_TYPE.TYPE_NIL:
            return None
        elif pattern == TP_DATA_TYPE.TYPE_BOOL:
            TPPacker.encode_type(buffer, pattern);
            TPPacker.encode_bool(buffer, value)
        elif pattern >= TP_DATA_TYPE.TYPE_U8 and pattern <= TP_DATA_TYPE.TYPE_I64:
            TPPacker.encode_type(buffer, TP_DATA_TYPE.TYPE_VARINT);
            TPPacker.encode_varint(buffer, value)
        elif pattern == TP_DATA_TYPE.TYPE_FLOAT:
            TPPacker.encode_type(buffer, pattern);
            value = floor(value * 1000)
            TPPacker.encode_varint(buffer, value)
        elif pattern == TP_DATA_TYPE.TYPE_DOUBLE:
            TPPacker.encode_type(buffer, pattern);
            value = floor(value * 1000000)
            TPPacker.encode_varint(buffer, value)
        elif pattern == TP_DATA_TYPE.TYPE_STR:
            TPPacker.encode_str_idx(buffer, value)
        elif pattern == TP_DATA_TYPE.TYPE_RAW:
            TPPacker.encode_type(buffer, pattern);
            TPPacker.encode_str_raw(buffer, value)
        elif pattern == TP_DATA_TYPE.TYPE_ARR:
            TPPacker.encode_type(buffer, pattern);
            TPPacker.encode_arr(buffer, value)
        elif pattern == TP_DATA_TYPE.TYPE_MAP:
            TPPacker.encode_type(buffer, pattern);
            TPPacker.encode_map(buffer, value)
        else:
            raise Exception("unknow type")
        
    @staticmethod
    def encode_arr(buffer: ByteBuffer, value):
        TPPacker.encode_varint(buffer, len(value))
        for v in value:
            TPPacker.encode_field(buffer, v)
            
    @staticmethod
    def encode_map(buffer: ByteBuffer, value):
        TPPacker.encode_varint(buffer, len(value))
        for k in value:
            TPPacker.encode_field(buffer, k)
            TPPacker.encode_field(buffer, value[k])

    @staticmethod
    def encode_proto(buffer: ByteBuffer, name, infos):
        sub_buffer = ByteBuffer.allocate(1024)
        TPPacker.encode_field(sub_buffer, infos)

        TPPacker.encode_str_raw(buffer, name, TP_DATA_TYPE.TYPE_STR)
        TPPacker.encode_varint(buffer, len(sub_buffer.str_arr))
        for val in sub_buffer.str_arr:
            TPPacker.encode_str_raw(buffer, val, TP_DATA_TYPE.TYPE_STR)

        buffer.write_bytes(sub_buffer.all_bytes())