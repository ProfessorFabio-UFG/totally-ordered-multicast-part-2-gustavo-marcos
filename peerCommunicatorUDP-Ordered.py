from socket import *
from constMP import *
import threading
import random
import time
import pickle
from requests import get
import heapq

# Contador de handshakes
handShakeCount = 0
PEERS = []

# Relógio de Lamport e fila de mensagens ordenadas
lamport_clock = 0
message_queue = []
clock_and_queue_lock = threading.Lock()
message_counter = 0  # Contador sequencial para desempate

# Conjunto de tópicos de conversa para simular uma discussão
conversation_topics = [
    "Qual é a melhor linguagem de programação?",
    "Como implementar sistemas distribuídos eficientemente?",
    "Qual o futuro da computação em nuvem?",
    "Blockchain é realmente útil?",
    "IA vai substituir programadores?",
    "Qual a importância da cibersegurança?",
    "Microserviços vs Monolitos?",
    "Docker ou Kubernetes?",
    "Qual banco de dados escolher?",
    "Como otimizar performance de aplicações?"
]

# Respostas possíveis para cada tópico
topic_responses = {
    "Qual é a melhor linguagem de programação?": [
        "Python é mais legível e produtiva",
        "Java tem melhor performance empresarial",
        "JavaScript é versátil para web",
        "C++ oferece controle total de memória",
        "Go é excelente para concorrência"
    ],
    "Como implementar sistemas distribuídos eficientemente?": [
        "Use padrões como Circuit Breaker",
        "Implemente retry com backoff exponencial",
        "Monitore métricas de latência sempre",
        "Use cache distribuído inteligentemente",
        "Aplique princípios de eventual consistency"
    ],
    "Qual o futuro da computação em nuvem?": [
        "Serverless vai dominar o mercado",
        "Edge computing será fundamental",
        "Multi-cloud é a estratégia certa",
        "Containers continuarão evoluindo",
        "AI-ops vai automatizar operações"
    ],
    "Blockchain é realmente úil?": [
        "Útil para descentralização real",
        "Crypto tem casos de uso limitados",
        "Smart contracts são revolucionários",
        "Problema de escalabilidade persiste",
        "Web3 ainda é muito especulativo"
    ],
    "IA vai substituir programadores?": [
        "IA é ferramenta, não substituto",
        "Programadores vão evoluir com IA",
        "Código de baixo nível sempre precisará humanos",
        "IA ajuda na produtividade apenas",
        "Criatividade humana é insubstituível"
    ]
}

count = 0

sendSocket = socket(AF_INET, SOCK_DGRAM)
recvSocket = socket(AF_INET, SOCK_DGRAM)
recvSocket.bind(('0.0.0.0', PEER_UDP_PORT))

serverSock = socket(AF_INET, SOCK_STREAM)
serverSock.bind(('0.0.0.0', PEER_TCP_PORT))
serverSock.listen(1)

def get_public_ip():
    ipAddr = get('https://api.ipify.org').content.decode('utf8')
    print('🌐 My public IP address is: {}'.format(ipAddr))
    return ipAddr

def registerWithGroupManager():
    clientSock = socket(AF_INET, SOCK_STREAM)
    print('🔗 Connecting to group manager: ', (GROUPMNGR_ADDR, GROUPMNGR_TCP_PORT))
    clientSock.connect((GROUPMNGR_ADDR, GROUPMNGR_TCP_PORT))
    ipAddr = get_public_ip()
    req = {"op": "register", "ipaddr": ipAddr, "port": PEER_UDP_PORT}
    print('📝 Registering with group manager: ', req)
    clientSock.send(pickle.dumps(req))
    clientSock.close()

def getListOfPeers():
    clientSock = socket(AF_INET, SOCK_STREAM)
    print('🔗 Connecting to group manager: ', (GROUPMNGR_ADDR, GROUPMNGR_TCP_PORT))
    clientSock.connect((GROUPMNGR_ADDR, GROUPMNGR_TCP_PORT))
    req = {"op": "list"}
    print('📋 Getting list of peers from group manager: ', req)
    clientSock.send(pickle.dumps(req))
    PEERS = pickle.loads(clientSock.recv(2048))
    print('👥 Got list of peers: ', PEERS)
    clientSock.close()
    return PEERS

class MsgHandler(threading.Thread):
    def __init__(self, sock, myself, nMsgs):
        threading.Thread.__init__(self)
        self.sock = sock
        self.myself = myself
        self.nMsgs = nMsgs
        self.delivered_messages = {}

    def run(self):
        print('🚀 Handler is ready. Waiting for the handshakes...')
        
        global handShakeCount, lamport_clock, message_counter
        logList = []
        expected_total = N * self.nMsgs
        received_messages = 0
        stopCount = 0

        # Aguarda handshakes de todos os processos
        while handShakeCount < N:
            msgPack = self.sock.recv(1024)
            msg = pickle.loads(msgPack)
            if msg[0] == 'READY':
                with clock_and_queue_lock:
                    lamport_clock = max(lamport_clock, msg[2]) + 1
                handShakeCount += 1
                print('🤝 --- Handshake received from process: ', msg[1])

        print('🎯 Secondary Thread: Received all handshakes. Entering message loop.')

        while True:
            msgPack = self.sock.recv(2048)
            msg = pickle.loads(msgPack)

            if msg[0] == -1:  # Mensagem de parada
                stopCount += 1
                print(f'🛑 Stop signal received ({stopCount}/{N})')
                if stopCount == N:
                    print('🏁 All stop signals received. Finishing...')
                    break
            else:
                # msg: (sender_id, msg_type, content, response_to_msg_id, lamport_timestamp)
                sender_id, msg_type, content, response_to_msg_id, msg_timestamp = msg
                
                with clock_and_queue_lock:
                    lamport_clock = max(lamport_clock, msg_timestamp) + 1
                    message_counter += 1
                    # Use tuple (timestamp, sender_id, message_counter) para ordenação total
                    heapq.heappush(message_queue, (msg_timestamp, sender_id, message_counter, msg_type, content, response_to_msg_id))
                
                print(f'🔄 Received message from process {sender_id} (LC: {msg_timestamp})')
                received_messages += 1

        # Entrega todas as mensagens restantes ordenadamente
        while message_queue:
            self.deliver_ordered_messages(logList)

        print(f'💾 Saving ordered conversation log for process {self.myself}...')
        with open(f'conversation_log_ordered_{self.myself}.log', 'w', encoding='utf-8') as f:
            for entry in logList:
                f.write(f"{entry}\n")

        print('📤 Sending ordered conversation log to server for comparison...')
        clientSock = socket(AF_INET, SOCK_STREAM)
        clientSock.connect((SERVER_ADDR, SERVER_PORT))
        clientSock.send(pickle.dumps(logList))
        clientSock.close()
        
        handShakeCount = 0
        print('✅ Handler finished successfully!')
        exit(0)

    def deliver_ordered_messages(self, logList):
        """Entrega mensagens na ordem do relógio de Lamport com desempate por sender_id"""
        global message_queue
        
        while message_queue:
            # Pega a mensagem com menor timestamp (ordem de Lamport)
            with clock_and_queue_lock:
                if not message_queue:
                    break
                # Tupla: (timestamp, sender_id, counter, msg_type, content, response_to)
                delivered_msg = heapq.heappop(message_queue)
            
            msg_timestamp, sender_id, counter, msg_type, content, response_to_msg_id = delivered_msg
            
            # Cria ID único para a mensagem
            msg_id = f"P{sender_id}_{msg_timestamp}_{counter}"
            
            # Armazena para contexto futuro
            self.delivered_messages[msg_id] = (sender_id, msg_type, content, response_to_msg_id)
            
            # Log da mensagem entregue ordenadamente com emojis e formatação visual
            if msg_type == "TOPIC":
                log_entry = f"[ORDERED-TOPIC] LC:{msg_timestamp} - Processo {sender_id}: {content}"
                print(f"📢 {log_entry}")
                
            elif msg_type == "RESPONSE":
                log_entry = f"[ORDERED-RESPONSE] LC:{msg_timestamp} - Processo {sender_id}: {content}"
                if response_to_msg_id:
                    log_entry += f" (respondendo a {response_to_msg_id})"
                print(f"💬 {log_entry}")
                
            elif msg_type == "REACTION":
                log_entry = f"[ORDERED-REACTION] LC:{msg_timestamp} - Processo {sender_id}: {content}"
                if response_to_msg_id:
                    log_entry += f" (reagindo a {response_to_msg_id})"
                print(f"😊 {log_entry}")
            
            # Adiciona ao log (timestamp, sender_id, msg_type, content, response_to_msg_id)
            logList.append((msg_timestamp, sender_id, msg_type, content, response_to_msg_id))

def waitToStart():
    print('⏳ Waiting for server signal...')
    conn, addr = serverSock.accept()
    msgPack = conn.recv(1024)
    myself, nMsgs = pickle.loads(msgPack)
    conn.send(pickle.dumps(f'Peer process {myself} started.'))
    conn.close()
    return myself, nMsgs

def generate_meaningful_message(myself, msg_number, delivered_messages):
    """Gera mensagens significativas baseadas no contexto da conversa ordenada"""
    
    # Primeira mensagem: inicia um tópico
    if msg_number == 0:
        return ("TOPIC", random.choice(conversation_topics), None)
    
    # Mensagens subsequentes: responde ou reage a mensagens anteriores
    if delivered_messages:
        msg_ids = list(delivered_messages.keys())
        if msg_ids:
            msg_to_respond = random.choice(msg_ids)
            original_msg = delivered_messages[msg_to_respond]
            
            if original_msg[1] == "TOPIC":  # Responde a um tópico
                topic = original_msg[2]
                if topic in topic_responses:
                    return ("RESPONSE", random.choice(topic_responses[topic]), msg_to_respond)
            
            # Reação geral
            return ("REACTION", random.choice([
                "Concordo plenamente!", "Interessante perspectiva...", "Não tinha pensado nisso antes",
                "Discordo respeitosamente", "Excelente ponto!", "Preciso pesquisar mais sobre isso",
                "Isso faz muito sentido", "Experiência similar aqui"
            ]), msg_to_respond)
    
    # Fallback: inicia novo tópico
    return ("TOPIC", random.choice(conversation_topics), None)

# Código principal
print('🎬 Starting peer communicator...')
registerWithGroupManager()

while True:
    print('⏳ Waiting for signal to start...')
    myself, nMsgs = waitToStart()
    print(f'🆔 I am up, and my ID is: {myself}')
    
    if nMsgs == 0:
        print('🔚 Terminating.')
        exit(0)

    print('⏱️  Waiting 5 seconds for other peers...')
    time.sleep(5)
    
    print('🧵 Starting message handler thread...')
    msgHandler = MsgHandler(recvSocket, myself, nMsgs)
    msgHandler.start()
    print('✅ Handler started')
    
    PEERS = getListOfPeers()
    
    # Envia handshakes
    print('🤝 Sending handshakes to all peers...')
    for addrToSend in PEERS:
        print(f'🤝 Sending handshake to {addrToSend}')
        with clock_and_queue_lock:
            lamport_clock += 1
            msg = ('READY', myself, lamport_clock)
        sendSocket.sendto(pickle.dumps(msg), (addrToSend, PEER_UDP_PORT))

    print(f'🎯 Main Thread: Sent all handshakes. handShakeCount={handShakeCount}')
    
    # Aguarda todos os handshakes
    while handShakeCount < N:
        pass
    
    print('🚀 All handshakes received! Starting message exchange...')
    
    # Contexto das mensagens entregues
    delivered_messages = {}
    
    # Envia sequência de mensagens significativas com delay maior para evitar timestamps iguais
    for msgNumber in range(nMsgs):
        # Delay maior e mais variável para evitar timestamps idênticos
        time.sleep(random.uniform(0.1, 0.5))
        
        # Gera mensagem com significado
        msg_type, content, response_to = generate_meaningful_message(myself, msgNumber, delivered_messages)
        
        with clock_and_queue_lock:
            lamport_clock += 1
            current_timestamp = lamport_clock
        
        msg = (myself, msg_type, content, response_to, current_timestamp)
        msgPack = pickle.dumps(msg)
        
        for addrToSend in PEERS:
            sendSocket.sendto(msgPack, (addrToSend, PEER_UDP_PORT))
        
        print(f'📤 Sent [{msg_type}] LC:{current_timestamp} from process {myself}: {content}')

    # Delay antes de enviar sinais de parada
    time.sleep(1)

    # Envia mensagem de parada
    print('🛑 Sending stop signals to all peers...')
    for addrToSend in PEERS:
        with clock_and_queue_lock:
            lamport_clock += 1
            msg = (-1, "STOP", "", None, lamport_clock)
        sendSocket.sendto(pickle.dumps(msg), (addrToSend, PEER_UDP_PORT))
    
    print('✅ All messages sent. Waiting for handler to finish...')