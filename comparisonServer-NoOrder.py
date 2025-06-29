from socket import *
import pickle
from constMP import *
import time
import sys
from collections import defaultdict

serverSock = socket(AF_INET, SOCK_STREAM)
serverSock.bind(('0.0.0.0', SERVER_PORT))
serverSock.listen(6)

def mainLoop():
    cont = 1
    while 1:
        nMsgs = promptUser()
        if nMsgs == 0:
            break
        clientSock = socket(AF_INET, SOCK_STREAM)
        clientSock.connect((GROUPMNGR_ADDR,GROUPMNGR_TCP_PORT))
        req = {"op":"list"}
        msg = pickle.dumps(req)
        clientSock.send(msg)
        msg = clientSock.recv(2048)
        clientSock.close()
        peerList = pickle.loads(msg)
        print("📋 List of Peers: ", peerList)
        startPeers(peerList,nMsgs)
        print('⏳ Now, wait for the message logs from the communicating peers...')
        waitForLogsAndCompare(nMsgs)
    serverSock.close()

def promptUser():
    nMsgs = int(input('Enter the number of messages for each peer to send (0 to terminate)=> '))
    return nMsgs

def startPeers(peerList,nMsgs):
    peerNumber = 0
    print('🚀 Starting all peers...')
    for peer in peerList:
        clientSock = socket(AF_INET, SOCK_STREAM)
        clientSock.connect((peer, PEER_TCP_PORT))
        msg = (peerNumber,nMsgs)
        msgPack = pickle.dumps(msg)
        clientSock.send(msgPack)
        msgPack = clientSock.recv(512)
        print(f'✅ {pickle.loads(msgPack)}')
        clientSock.close()
        peerNumber = peerNumber + 1

def analyze_lamport_ordering(msgs):
    print("\n🔍 ANÁLISE DETALHADA DE ORDENAÇÃO LAMPORT")
    print("=" * 60)
    
    total_violations = 0
    all_peers_consistent = True
    disordered_set = set()  # Para garantir no máximo N * nMsgs

    for peer_id, peer_msgs in enumerate(msgs):
        prev_timestamp = -1
        prev_sender = -1

        for i, msg in enumerate(peer_msgs):
            timestamp, sender_id, msg_type, content, response_to = msg

            if timestamp < prev_timestamp or (timestamp == prev_timestamp and sender_id < prev_sender):
                # Identificador único da mensagem
                msg_uid = f"{sender_id}_{timestamp}"
                if msg_uid not in disordered_set:
                    disordered_set.add(msg_uid)
                    total_violations += 1
                    print(f"❌ VIOLAÇÃO: Msg {i} tem timestamp {timestamp} < anterior {prev_timestamp}")
                    print(f"   Conteúdo: [{msg_type}] {str(content)[:50]}...")
                    all_peers_consistent = False

            prev_timestamp = timestamp
            prev_sender = sender_id

    return all_peers_consistent, total_violations, len(disordered_set)

    return all_peers_consistent, total_violations, total_disordered_messages

def analyze_timestamp_distribution(msgs):
    if not msgs:
        return
    all_timestamps = []
    timestamp_senders = defaultdict(list)
    for msg in msgs[0]:
        timestamp, sender_id, msg_type, content, response_to = msg
        all_timestamps.append(timestamp)
        timestamp_senders[timestamp].append(sender_id)
    print(f"\n📈 Estatísticas:")
    print(f"   Range de timestamps: {min(all_timestamps)} - {max(all_timestamps)}")
    print(f"   Total de mensagens: {len(all_timestamps)}")
    print(f"   Timestamps únicos: {len(set(all_timestamps))}")

def compare_peer_consistency(msgs):
    print("\n🔄 ANÁLISE DE CONSISTÊNCIA ENTRE PEERS")
    print("=" * 60)
    
    if not msgs:
        print("❌ Nenhuma mensagem recebida!")
        return False

    reference_peer = msgs[0]
    reference_sequence = [(msg[0], msg[1]) for msg in reference_peer]
    print(f"📋 Usando Peer 0 como referência ({len(reference_sequence)} mensagens)")
    
    all_consistent = True
    inconsistent_peers = []
    
    for peer_id in range(1, len(msgs)):
        peer_sequence = [(msg[0], msg[1]) for msg in msgs[peer_id]]
        
        if peer_sequence != reference_sequence:
            all_consistent = False
            inconsistent_peers.append(peer_id)
            print(f"❌ Peer {peer_id}: Sequência DIFERENTE da referência")
            min_len = min(len(reference_sequence), len(peer_sequence))
            for i in range(min_len):
                if reference_sequence[i] != peer_sequence[i]:
                    ref_ts, ref_sender = reference_sequence[i]
                    peer_ts, peer_sender = peer_sequence[i]
                    print(f"   🔍 Primeira diferença na posição {i}:")
                    print(f"      Referência: LC:{ref_ts} de P{ref_sender}")
                    print(f"      Peer {peer_id}:   LC:{peer_ts} de P{peer_sender}")
                    break
        else:
            print(f"✅ Peer {peer_id}: Sequência IDÊNTICA à referência")

    return all_consistent, inconsistent_peers

def analyze_message_content(msgs):
    print("\n📈 ANÁLISE DE CONTEÚDO DAS MENSAGENS")
    print("=" * 60)
    
    if not msgs:
        return

    total_messages = len(msgs[0]) if msgs else 0
    message_types = defaultdict(int)
    senders_count = defaultdict(int)
    
    for msg in msgs[0]:
        timestamp, sender_id, msg_type, content, response_to = msg
        message_types[msg_type] += 1
        senders_count[sender_id] += 1
    
    print(f"📊 Total de mensagens: {total_messages}")
    for msg_type, count in message_types.items():
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        print(f"   {msg_type}: {count} ({percentage:.1f}%)")
    print(f"👥 Mensagens por sender:")
    for sender_id, count in sorted(senders_count.items()):
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        print(f"   Processo {sender_id}: {count} ({percentage:.1f}%)")

def detailed_message_trace(msgs, max_messages=15):
    print(f"\n🔬 TRACE DETALHADO (primeiras {max_messages} mensagens)")
    print("=" * 80)
    
    if not msgs:
        print("❌ Nenhuma mensagem para analisar!")
        return

    reference_msgs = msgs[0][:max_messages]
    for i, msg in enumerate(reference_msgs):
        timestamp, sender_id, msg_type, content, response_to = msg
        print(f"[{i:2d}] LC:{timestamp:3d} | P{sender_id} | {msg_type:8s} | {str(content)[:40]}...")
        if response_to:
            print(f"     └─ Respondendo a: {response_to}")

def save_detailed_report(msgs, nMsgs):
    filename = f"ordering_analysis_report_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE ANÁLISE DE ORDENAÇÃO LAMPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Data: {time.ctime()}\n")
        f.write(f"Número de peers: {len(msgs)}\n")
        f.write(f"Mensagens por peer: {nMsgs}\n")
        f.write(f"Total esperado: {len(msgs) * nMsgs}\n\n")
        for peer_id, peer_msgs in enumerate(msgs):
            f.write(f"\n--- PEER {peer_id} ---\n")
            for i, msg in enumerate(peer_msgs):
                timestamp, sender_id, msg_type, content, response_to = msg
                f.write(f"[{i:3d}] LC:{timestamp:3d} | P{sender_id} | {msg_type:8s} | {str(content)}\n")
                if response_to:
                    f.write(f"      └─ Resp. a: {response_to}\n")
    print(f"💾 Relatório detalhado salvo em: {filename}")

def waitForLogsAndCompare(nMsgs):
    numPeers = 0
    msgs = []
    print(f"⏳ Aguardando logs de {N} peers...")
    while numPeers < N:
        (conn, addr) = serverSock.accept()
        msgPack = conn.recv(32768)
        print(f'📥 Received log from peer {numPeers + 1}/{N} (from {addr[0]})')
        conn.close()
        msgs.append(pickle.loads(msgPack))
        numPeers += 1
    print(f"\n✅ Todos os {N} logs recebidos! Iniciando análise...")
    print("=" * 70)
    analyze_timestamp_distribution(msgs)
    lamport_consistent, lamport_violations, total_disordered_messages = analyze_lamport_ordering(msgs)
    peers_consistent, inconsistent_peers = compare_peer_consistency(msgs)
    analyze_message_content(msgs)
    detailed_message_trace(msgs)
    print("\n🎯 RESULTADO FINAL")
    print("=" * 50)
    print(f"📊 Mensagens desordenadas encontradas: {total_disordered_messages}")
    if lamport_consistent and peers_consistent:
        print("🎉 SUCESSO TOTAL!")
        print("✅ Ordenação Lamport: Perfeita")
        print("✅ Consistência entre peers: Perfeita") 
    else:
        print("❌ PROBLEMAS DETECTADOS:")
        if not peers_consistent:
            print(f"❌ Consistência: {len(inconsistent_peers)} peers inconsistentes: {inconsistent_peers}")
        else:
            print("✅ Consistência entre peers: OK")
    save_detailed_report(msgs, nMsgs)
    print("\n" + "=" * 70)

mainLoop()
