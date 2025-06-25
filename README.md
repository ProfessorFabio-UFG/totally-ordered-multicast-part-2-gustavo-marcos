# 📡 Totally Ordered Multicast - Parte 2 (Sistemas Distribuídos)

Este projeto é a segunda parte do trabalho prático da disciplina de **Sistemas Distribuídos**, com o objetivo de implementar um sistema de troca de mensagens multicast entre processos distribuídos com e sem ordenação total, utilizando **relógios de Lamport**.

---

## 🔧 Tecnologias Utilizadas

- Python 3.9+
- Sockets TCP/UDP
- AWS EC2 (para simulação distribuída)
- pickle (serialização)
- threading

---

## 🧠 Descrição

O sistema é composto por:

- **Peers** que se comunicam por UDP, enviando mensagens entre si.
- Um **Group Manager** (TCP) responsável por registrar os peers e distribuir a lista de participantes.
- Um **Servidor Comparador** que coleta os logs de execução de todos os peers e compara a ordem das mensagens.

São demonstradas duas versões:

- `sem_ordenacao`: entrega mensagens conforme ordem de chegada.
- `com_ordenacao`: utiliza relógios de Lamport e fila de prioridade para garantir ordenação total.

As mensagens simulam uma conversa lógica entre processos (por exemplo: perguntas sobre linguagens, RPCs, etc).

---

## 🚀 Execução

### 1. Suba as instâncias (mínimo 8):
- 1 para o Group Manager
- 1 para o Comparison Server
- 6 para os Peers

### 2. Inicie os componentes na seguinte ordem:

#### a. Group Manager
```bash
python3 GroupMngr.py
```
#### b. Comparison Server
```bash
python3 comparisonServer.py
```
#### Quando solicitado, informe o número de mensagens por peer (ex: 3)

#### c. Peers (em cada uma das 6 instâncias)
```bash
python3 peerCommunicatorUDP.py
```
