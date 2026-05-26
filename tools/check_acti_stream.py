import socket, base64
IP = '192.168.15.200'
b64 = base64.b64encode(b'admin:123456').decode()
path = '/virtualcamera/channel1?media&streamid=0'
req = 'GET ' + path + ' HTTP/1.1\r\nHost: ' + IP + '\r\nAuthorization: Basic ' + b64 + '\r\nConnection: close\r\n\r\n'
s = socket.create_connection((IP, 80), timeout=10)
s.sendall(req.encode())
s.settimeout(8)
data = b''
try:
    while len(data) < 8000:
        c = s.recv(1024)
        if not c: break
        data += c
except:
    pass
s.close()
hend = data.find(b'\r\n\r\n')
print('HEADERS:', data[:hend].decode(errors='replace'))
body = data[hend+4:]
print('BODY bytes:', len(body))
print('HEX first 80:', body[:80].hex())
nals = sum(1 for i in range(len(body)-3) if body[i:i+4]==b'\x00\x00\x00\x01')
print('H264 NAL starts:', nals)
