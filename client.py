import socket
import math
import time
import re  

HOST = "localhost"
PORT = 5065
TIMEOUT = 1

modes = ["em_rajada", "individual"]
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
client.settimeout(TIMEOUT)

def calcular_checksum(payload):
    return sum(ord(c) for c in payload)

tipo = None
while True:
    try:
        mode_code = int(input(
            "Digite [1] para o modo Em Rajada (Go-Back-N)\n"
            "Digite [2] para o modo Individual (Repetição Seletiva)\n"
            "Digite: "
        ))
        if mode_code not in [1, 2]:
            print("\nDigite apenas [1] ou [2]\n")
        else:
            tipo = modes[mode_code - 1]
            break
    except ValueError:
        print("\nEntrada inválida! Digite um número\n")

max_length = 0
while True:
    try:
        max_length = int(input("Digite o tamanho máximo da mensagem (Máx 3): "))
        if not 1 <= max_length <= 3:
            print("\nO tamanho máximo precisa estar entre 1 e 3\n")
        else:
            break
    except ValueError:
        print("\nEntrada inválida! Digite um número\n")

window_size = 4  

data = f"{tipo};{max_length};{window_size}\n"
client.send(data.encode())
print(f"[CLIENTE] Handshake enviado: modo={tipo}, max_length={max_length}, janela={window_size}")
confirmation = client.recv(1024).decode().strip()
print(f"[CLIENTE] Confirmação recebida: {confirmation}\n")

texto = input("Digite a mensagem a ser enviada: ")
num_packets = math.ceil(len(texto) / max_length)

base = 0
next_seq = 0
acked = [False] * num_packets  

timer_start = None

acksRecebidos = []

finished = False

while not finished and len(acksRecebidos) < num_packets:
    
    while next_seq < num_packets and next_seq < base + window_size:
        start = next_seq * max_length
        payload = texto[start:start + max_length]
        checksum = calcular_checksum(payload)
        if next_seq + 1 == num_packets and tipo == "em_rajada":
            packet = f"seq={next_seq}|data={payload}|sum={checksum}&\n"
        else:
            packet = f"seq={next_seq}|data={payload}|sum={checksum}\n"

        client.send(packet.encode())
        inicio = time.time()
        print(f"[CLIENTE] Pacote enviado: {packet.strip()}\n")
        if base == next_seq:
            timer_start = time.time()
        next_seq += 1

    try:
        data = client.recv(1024).decode()
        for ack_msg in data.splitlines():
            fim = time.time()
            tempo_execucao = fim - inicio

            if ack_msg.startswith("ACK"):
                window_size += 1
                print(f"[CLIENTE] ACK recebido: {ack_msg} ✅")
                ack_value = int(ack_msg.split("|")[1])  
                print(f"[CLIENTE] Tempo de Resposta: {tempo_execucao:.4f}s ⏰\n")

                if tipo == "em_rajada" and ack_value == num_packets:
                    finished = True
                    break

                if tipo == "em_rajada":
                    if ack_value not in acksRecebidos:
                        if not acksRecebidos or max(acksRecebidos) < ack_value:
                            acksRecebidos.append(ack_value)
                        else:
                            acksRecebidos.append(ack_value)
                else:
                    acksRecebidos.append(ack_value)

                acks = re.findall(r'ACK\|(\d+)', ack_msg)
                if not acks:
                    print(f"[CLIENTE] Formato de ACK inválido: {ack_msg}")
                    continue
                ack_seq = int(acks[-1])

                if tipo == "individual":
                    acked[ack_seq] = True
                    while base < num_packets and acked[base]:
                        base += 1
                else:
                    base = ack_seq

                if base != next_seq:
                    timer_start = time.time()
            else:
                print(f"[CLIENTE] NACK recebido: {ack_msg} ❌")
                print(f"[CLIENTE] Servidor congestionado")
                finished = True

    except socket.timeout:
        if finished:
            break
        print(f"[CLIENTE] Timeout. Reenviando janela base={base}")
        for seq in range(base, min(base + window_size, num_packets)):
            if tipo == "individual" and acked[seq]:
                continue
            start = seq * max_length
            payload = texto[start:start + max_length]
            checksum = calcular_checksum(payload)
            packet = f"seq={seq}|data={payload}|sum={checksum}\n"
            client.send(packet.encode())
            print(f"[CLIENTE] Reenviado: {packet.strip()}")
        print("\n")
        inicio = time.time()
        timer_start = time.time()

client.close()
print("[CLIENTE] Conexão encerrada.")
