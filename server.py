import socket
import time

HOST = "localhost"
PORT = 5065

while True:
    try:
        mode_code = int(input(
            "Digite [1] para simular perda de pacote\n"
            "Digite [2] para continuar normalmente\n"
            "Digite: "
        ))
        if mode_code not in [1, 2]:
            print("\nDigite apenas [1] ou [2]\n")
        else:
            if mode_code == 1:
                perderPacote = True

                while True:
                    try:
                        pacotePerdido = int(input(
                            "Digite o número do pacote que será perdido: "
                        ))
                        break
                    except ValueError:
                        print("\nEntrada inválida! Digite um número\n")
            else:
                pacotePerdido = None
                perderPacote = False
            break
    except ValueError:
        print("\nEntrada inválida! Digite um número\n")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)
print(f"[SERVIDOR] Aguardando conexão na porta {PORT}...")
conn, addr = server.accept()
print(f"[SERVIDOR] Conectado a {addr}")

def calcular_checksum(payload):
    return sum(ord(c) for c in payload)

buffer = ""

while "\n" not in buffer:
    data = conn.recv(1024).decode()
    if not data:
        break
    buffer += data

header, buffer = buffer.split("\n", 1)
mode, max_len_str, window_str = header.split(";")
max_length = int(max_len_str)
window_size = int(window_str)
print(f"[SERVIDOR] Handshake: modo={mode}, max_payload={max_length}, janela={window_size}\n")
conn.send("HANDSHAKE_OK\n".encode())

expected_seq = 0
received = {}

while True:
    data = conn.recv(1024).decode()
    if not data:
        break
    buffer += data
    
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        try:
            if "&" in line:
                lastPacket = True
                line = line.replace("&", "")
            else:
                lastPacket = False

            parts = line.strip().split("|")
            data_dict = {}
            for part in parts:
                key, value = part.split("=", 1)
                data_dict[key] = value

            seq = int(data_dict["seq"])
            if seq == pacotePerdido and perderPacote:
                perderPacote = False
                continue
            payload = data_dict["data"]
            checksum_recv = int(data_dict["sum"])
        except ValueError:
            print(f"[SERVIDOR] Pacote mal formado: {line}")
            continue

        if checksum_recv != calcular_checksum(payload):
            print(f"[SERVIDOR] Checksum inválido seq={seq}")
            continue

        print(f"[SERVIDOR] Pacote recebido {line}")
        print(f"[SERVIDOR] Checksum válido {line}")
        if seq in received.keys():
                print(f"[SERVIDOR] Pacote repetido\n")
                continue

        if seq < expected_seq or seq >= expected_seq + window_size:
            ack = f"ACK|{expected_seq}\n" if mode == "em_rajada" else f"ACK|{seq}\n"
            conn.send(ack.encode())
            continue

        received[seq] = payload
        if mode == "individual":
            ack = f"ACK|{seq}|[{abs(4-window_size)}-{window_size-1}]\n"
            window_size += 1
            conn.send(ack.encode())
            print(f"[SERVIDOR] Enviado {ack.strip()}\n")
        else:
            if seq == expected_seq:
                while expected_seq in received:
                    expected_seq += 1
            if lastPacket:
                ack = f"ACK|{expected_seq}|[{abs(4-window_size)}-{window_size-1}]\n"
                window_size += 1
                conn.send(ack.encode())
                print(f"[SERVIDOR] Enviado {ack.strip()}\n")
            else:
                if window_size <= len(received):
                    ack = f"NACK|{expected_seq}|[{abs(4-window_size)}-{window_size-1}]\n"
                    conn.send(ack.encode())
                    print(f"[SERVIDOR] Enviado {ack.strip()}\n")

txt = ''.join(received[i] for i in sorted(received))
print(f"[SERVIDOR] Mensagem completa: '{txt}'")
conn.close()
server.close()
print("\n[SERVIDOR] Conexão encerrada.")
