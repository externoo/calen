import os 
import time 
import uuid

def uuid7():
    """Generate a UUID7 (time-ordered) based on the current time in milliseconds."""
    ts_ms = time.time_ns() // 1_000_000
    value = (ts_ms & 0xFFFFFFFFFFFF) << 80  # timestamp in milliseconds (48 bits)
    value |= int.from_bytes(os.urandom(10), "big")

    value &= ~(0xF << 76)    # clear the version nibble               
    value |= 0x7 << 76       # stamp version = 7                  
    value &= ~(0b11 << 62)   # clear the variant bits            
    value |= 0b10 << 62      # stamp RFC 9562 variant    

    return uuid.UUID(int=value)               