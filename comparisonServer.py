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
    """Analisa se as mensagens estão ordenadas corretamente pelo relógio de Lamport"""
    print("\n🔍 ANÁLISE DETALHADA DE ORDENAÇÃO LAMPORT")
    print("=" * 60)
    
    total_violations = 0
    total_disordered_messages = 0  # Contador de mensagens desordenadas
    all_peers_consistent = True
    
    # Verifica cada peer individualmente
    for peer_id, peer_msgs in enumerate(msgs):
        
        violations = 0
        disordered_messages = 0
        prev_timestamp = -1
        prev_sender = -1
        
        for i, msg in enumerate(peer_msgs):
            timestamp, sender_id, msg_type, content, response_to = msg
            
            # Verifica ordenação de Lamport: (timestamp, sender_id) deve ser crescente
            if timestamp < prev_timestamp or (timestamp == prev_timestamp and sender_id <= prev_sender):
                # Só considera violação se timestamp for menor (não igual)
                if timestamp < prev_timestamp:
                    violations += 1
                    disordered_messages += 1
                    print(f"❌ VIOLAÇÃO: Msg {i} tem timestamp {timestamp} < anterior {prev_timestamp}")
                    print(f"   Conteúdo: [{msg_type}] {content[:50]}...")
                    all_peers_consistent = False
                elif timestamp == prev_timestamp and sender_id < prev_sender:
                    violations += 1
                    disordered_messages += 1
                    print(f"❌ VIOLAÇÃO: Msgs com timestamp {timestamp}: sender {sender_id} < anterior {prev_sender}")
                    print(f"   Conteúdo: [{msg_type}] {content[:50]}...")
                    all_peers_consistent = False
            
            prev_timestamp = timestamp
            prev_sender = sender_id
        
        if violations == 0:
            continue
        else:
            total_violations += violations
            total_disordered_messages += disordered_messages
    
    return all_peers_consistent, total_violations, total_disordered_messages

def analyze_timestamp_distribution(msgs):
    
    if not msgs:
        return
    
    # Coleta todos os timestamps
    all_timestamps = []
    timestamp_senders = defaultdict(list)
    
    for msg in msgs[0]:  # Usa primeiro peer como referência
        timestamp, sender_id, msg_type, content, response_to = msg
        all_timestamps.append(timestamp)
        timestamp_senders[timestamp].append(sender_id)
    
    # Estatísticas gerais
    print(f"\n📈 Estatísticas:")
    print(f"   Range de timestamps: {min(all_timestamps)} - {max(all_timestamps)}")
    print(f"   Total de mensagens: {len(all_timestamps)}")
    print(f"   Timestamps únicos: {len(set(all_timestamps))}")

def compare_peer_consistency(msgs):
    """Compara se todos os peers têm a mesma sequência de mensagens"""
    print("\n🔄 ANÁLISE DE CONSISTÊNCIA ENTRE PEERS")
    print("=" * 60)
    
    if not msgs:
        print("❌ Nenhuma mensagem recebida!")
        return False
    
    # Usa o primeiro peer como referência
    reference_peer = msgs[0]
    reference_sequence = [(msg[0], msg[1]) for msg in reference_peer]  # (timestamp, sender_id)
    
    print(f"📋 Usando Peer 0 como referência ({len(reference_sequence)} mensagens)")
    
    all_consistent = True
    inconsistent_peers = []
    
    for peer_id in range(1, len(msgs)):
        peer_sequence = [(msg[0], msg[1]) for msg in msgs[peer_id]]
        
        if peer_sequence != reference_sequence:
            all_consistent = False
            inconsistent_peers.append(peer_id)
            print(f"❌ Peer {peer_id}: Sequência DIFERENTE da referência")
            
            # Mostra as diferenças detalhadamente
            print(f"   📏 Tamanho: Referência={len(reference_sequence)}, Peer={len(peer_sequence)}")
            
            # Encontra primeira diferença
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
    """Analisa o conteúdo e distribuição das mensagens"""
    print("\n📈 ANÁLISE DE CONTEÚDO DAS MENSAGENS")
    print("=" * 60)
    
    if not msgs:
        return
    
    # Estatísticas gerais
    total_messages = len(msgs[0]) if msgs else 0
    message_types = defaultdict(int)
    senders_count = defaultdict(int)
    
    # Analisa mensagens do primeiro peer (referência)
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
    """Mostra trace detalhado das primeiras mensagens para debug"""
    print(f"\n🔬 TRACE DETALHADO (primeiras {max_messages} mensagens)")
    print("=" * 80)
    
    if not msgs:
        print("❌ Nenhuma mensagem para analisar!")
        return
    
    reference_msgs = msgs[0][:max_messages]
    
    for i, msg in enumerate(reference_msgs):
        timestamp, sender_id, msg_type, content, response_to = msg
        print(f"[{i:2d}] LC:{timestamp:3d} | P{sender_id} | {msg_type:8s} | {content[:40]}...")
        if response_to:
            print(f"     └─ Respondendo a: {response_to}")

def save_detailed_report(msgs, nMsgs):
    """Salva relatório detalhado em arquivo"""
    filename = f"ordering_analysis_report_{int(time.time())}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE ANÁLISE DE ORDENAÇÃO LAMPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Data: {time.ctime()}\n")
        f.write(f"Número de peers: {len(msgs)}\n")
        f.write(f"Mensagens por peer: {nMsgs}\n")
        f.write(f"Total esperado: {len(msgs) * nMsgs}\n\n")
        
        # Salva todas as mensagens de cada peer
        for peer_id, peer_msgs in enumerate(msgs):
            f.write(f"\n--- PEER {peer_id} ---\n")
            for i, msg in enumerate(peer_msgs):
                timestamp, sender_id, msg_type, content, response_to = msg
                f.write(f"[{i:3d}] LC:{timestamp:3d} | P{sender_id} | {msg_type:8s} | {content}\n")
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

    # 1. Análise de distribuição de timestamps
    analyze_timestamp_distribution(msgs)
    
    # 2. Análise de ordenação Lamport individual
    lamport_consistent, lamport_violations, total_disordered_messages = analyze_lamport_ordering(msgs)
    
    # 3. Análise de consistência entre peers
    peers_consistent, inconsistent_peers = compare_peer_consistency(msgs)
    
    # 4. Análise de conteúdo
    analyze_message_content(msgs)
    
    # 5. Trace detalhado
    detailed_message_trace(msgs)
    
    # 6. Relatório final
    print("\n🎯 RESULTADO FINAL")
    print("=" * 50)
    
    # NOVA LINHA: Mostra o número de mensagens desordenadas
    print(f"📊 Mensagens desordenadas encontradas: {total_disordered_messages}")
    
    if lamport_consistent and peers_consistent:
        print("🎉 SUCESSO TOTAL!")
        print("✅ Ordenação Lamport: Perfeita")
        print("✅ Consistência entre peers: Perfeita") 
        print("✅ Todos os peers entregaram mensagens na mesma ordem!")
    else:
        print("❌ PROBLEMAS DETECTADOS:")
            
        if not peers_consistent:
            print(f"❌ Consistência: {len(inconsistent_peers)} peers inconsistentes: {inconsistent_peers}")
        else:
            print("✅ Consistência entre peers: OK")
    
    # 7. Salva relatório detalhado
    save_detailed_report(msgs, nMsgs)
    
    print("\n" + "=" * 70)

mainLoop()