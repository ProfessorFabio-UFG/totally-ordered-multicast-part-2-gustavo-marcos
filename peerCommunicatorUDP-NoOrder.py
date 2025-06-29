from socket import *
from constMP import *
import threading
import random
import time
import pickle
from requests import get

handShakeCount = 0
PEERS = []

conversation_topics = [
    "Qual é a melhor linguagem de programação?",
    "Como implementar sistemas distribuídos eficientemente?",
    "Qual o futuro da computação em nuvem?",
    "Blockchain é realmente útil?",
    "IA vai substituir programadores?"
]

topic_responses = {
    "Qual é a melhor linguagem de programação?": [
        "Python é mais legível e produtiva",
        "Java tem melhor performance empresarial",
    ],
    "Como implementar sistemas distribuídos eficientemente?": [
        "Use padrões como Circuit Breaker",
        "Implemente retry com backoff exponencial",
    ],
    "Qual o futuro da computação em nuvem?": [
        "Serverless vai dominar o mercado",
        "Edge computing será fundamental",
    ],
    "Blockchain é realmente útil?": [
        "Smart contracts são revolucionários",
        "Problema de escalabilidade persiste",
    ],
    "IA vai substituir programadores?": [
        "IA é ferramenta, não substituto",
        "Programadores vão evoluir com IA",
    ]
}

sendSocket = socket(AF_INET, SOCK_DGRAM)
recvSocket = socket(AF_INET, SOCK_DGRAM)
recvSocket.bind(('0.0.0.0', PEER_UDP_PORT))

serverSock = socket(AF_INET, SOCK_STREAM)
serverSock.bind(('0.0.0.0', PEER_TCP_PORT))
serverSock.listen(1)

def get_public_ip():
    return get('https://api.ipify.org').content.decode('utf8')

def registerWithGroupManager():
    clientSock = socket(AF_INET, SOCK_STREAM)
    clientSock.connect((GROUPMNGR_ADDR, GROUPMNGR_TCP_PORT))
    ipAddr = get_public_ip()
    req = {"op": "register", "ipaddr": ipAddr, "port": PEER_UDP_PORT}
    clientSock.send(pickle.dumps(req))
    clientSock.close()

def getListOfPeers():
    clientSock = socket(AF_INET, SOCK_STREAM)
    clientSock.connect((GROUPMNGR_ADDR, GROUPMNGR_TCP_PORT))
    req = {"op": "list"}
    clientSock.send(pickle.dumps(req))
    PEERS = pickle.loads(clientSock.recv(2048))
    clientSock.close()
    return PEERS

def waitToStart():
    conn, addr = serverSock.accept()
    myself, nMsgs = pickle.loads(conn.recv(1024))
    conn.send(pickle.dumps(f'Peer process {myself} started.'))
    conn.close()
    return myself, nMsgs

def generate_meaningful_message(myself, msg_number, history):
    if msg_number == 0:
        return ("TOPIC", random.choice(conversation_topics), None)
    if history:
        msg_ids = list(history.keys())
        response_to = random.choice(msg_ids)
        original_msg = history[response_to]
        if original_msg[1] == "TOPIC":
            topic = original_msg[2]
            return ("RESPONSE", random.choice(topic_responses.get(topic, ["Interessante..."])), response_to)
        return ("REACTION", random.choice(["Concordo!", "Interessante...", "Discordo."]), response_to)
    return ("TOPIC", random.choice(conversation_topics), None)

def listener(myself, nMsgs):
    logList = []
    history = {}
    received = 0
    while received < N * nMsgs:
        msgPack, addr = recvSocket.recvfrom(2048)
        msg = pickle.loads(msgPack)
        if msg[0] == -1:
            break
        sender_id, msg_type, content, response_to, timestamp = msg
        logList.append((sender_id, msg_type, content, response_to, timestamp))
        msg_id = f"{sender_id}_{timestamp}"
        history[msg_id] = (sender_id, msg_type, content, response_to)
        print(f"📨 Recebida de P{sender_id}: [{msg_type}] {content}")
        received += 1
    with open(f'conversation_log_no_order_{myself}.log', 'w', encoding='utf-8') as f:
        for entry in logList:
            f.write(f"{entry}\n")
    clientSock = socket(AF_INET, SOCK_STREAM)
    clientSock.connect((SERVER_ADDR, SERVER_PORT))
    clientSock.send(pickle.dumps(logList))
    clientSock.close()
    print('✅ Log enviado para o servidor.')

print('🚀 Iniciando peer...')
registerWithGroupManager()

while True:
    myself, nMsgs = waitToStart()
    if nMsgs == 0:
        print('🛑 Encerrando peer.')
        break

    PEERS = getListOfPeers()
    time.sleep(3)

    thread = threading.Thread(target=listener, args=(myself, nMsgs))
    thread.start()

    history = {}
    for i in range(nMsgs):
        time.sleep(random.uniform(0.1, 0.4))
        msg_type, content, response_to = generate_meaningful_message(myself, i, history)
        timestamp = int(time.time()*1000) % 100000
        msg = (myself, msg_type, content, response_to, timestamp)
        msgPack = pickle.dumps(msg)
        for addr in PEERS:
            sendSocket.sendto(msgPack, (addr, PEER_UDP_PORT))
        msg_id = f"{myself}_{timestamp}"
        history[msg_id] = (myself, msg_type, content, response_to)

    time.sleep(1)
    for addr in PEERS:
        msg = (-1, "STOP", "", None, 0)
        sendSocket.sendto(pickle.dumps(msg), (addr, PEER_UDP_PORT))

    thread.join()
    print('🏁 Peer finalizado.')
