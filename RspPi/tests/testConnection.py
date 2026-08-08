import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("192.168.4.1", 9999))
s.send(b"Yo ESP32\n")
print(s.recv(1024))
s.close()
#print('hello world')