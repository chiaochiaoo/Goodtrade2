import socket
import time

# def send_file_with_ids(file_path, port, ip="localhost"):
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**20)  # 1MB send buffer

#     c = 0
#     max_size = 1024
#     start_time = time.time()
#     total_bytes = 0

#     with open(file_path, 'r') as f:
#         for i, line in enumerate(f):
#             line = line.strip()
#             if not line:
#                 continue

#             msg = f"MessageID={i},{line}"
#             encoded = msg.encode()

#             if len(encoded) > max_size:
#                 encoded = encoded[:max_size]  # Ensure max UDP packet size

#             sock.sendto(encoded, (ip, port))
#             total_bytes += len(encoded)
#             c += 1

#             if c % 1000 == 0:
#                 elapsed = time.time() - start_time
#                 mb_sent = total_bytes / (1024 * 1024)
#                 speed_kbps = (total_bytes / elapsed) / 1024
#                 print(f"Sent {c} messages in {elapsed:.2f} sec | {mb_sent:.2f} MB | {speed_kbps:.2f} KB/s")

#     sock.close()
#     total_elapsed = time.time() - start_time
#     print(f"✅ Done. Sent {c} messages | {total_bytes / (1024 * 1024):.2f} MB "
#           f"in {total_elapsed:.2f} sec | Speed: {total_bytes / total_elapsed / 1024:.2f} KB/s")
# # Example usage
# send_file_with_ids("N_02-16.csv", port=4339)

# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**20)

# msg = b"x" * 1024
# start = time.time()
# count = 100000
# for _ in range(count):
#     sock.sendto(msg, ("127.0.0.1", 4339))
# elapsed = time.time() - start
# print(f"Sent {count} messages of 1024 bytes: "
#       f"{count*1024/1024/1024:.2f} GB in {elapsed:.2f}s = "
#       f"{count*1024/elapsed/1024/1024:.2f} MB/s")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**20)

fixed_payload = b",Symbol=ABC,Side=B,Price=25.3,Shares=200,MarketDateTime=20240623T120000"
start = time.time()
c = 0
total_bytes = 0

for i in range(500000):
    c += 1
    prefix = f"MessageID={i}".encode()
    msg = prefix + fixed_payload  # Resulting msg is bytes
    sock.sendto(msg, ("127.0.0.1", 4339))
    total_bytes += len(msg)
    

elapsed = time.time() - start
print(f"Sent {c} messages | {total_bytes / 1024:.2f} KB "
      f"in {elapsed:.2f} sec | {total_bytes / elapsed / 1024:.2f} KB/s")
