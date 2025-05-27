# Simulação de Transações Concorrentes com Deadlock

Este repositório implementa em Python uma simulação de transações concorrentes que disputam recursos compartilhados, com detecção e resolução de deadlocks usando o protocolo **wait-die** (timestamp).

---

## 1. Pré-requisitos

* **Python 3.7+** 
* **Instalação do Tkinter**

Embora venha com a maioria das distribuições Python, em algumas (Debian/Ubuntu) é preciso instalar:
```bash
sudo apt-get install python3-tk
```

```bash
pip install networkx
```
```bash
pip install matplotlib
```

## 2. Estrutura de arquivos

* `deadlock_simulation.py`: código-fonte principal, com suporte a linha de comando e interface gráfica opcional (Tkinter).
* `README.md`: instruções e casos de teste.

---

## 3. Uso via linha de comando (CLI)

```bash
python deadlock_simulation.py [-h] [-n N] [--seed SEED]
                               [--min-delay MIN_DELAY] [--max-delay MAX_DELAY][--force-deadlock]
                               [--gui]
```

| Opção         | Descrição                                                        |
| ------------- | ---------------------------------------------------------------- |
| `-n N`        | Número de transações (threads) a disparar. Default: 4            |
| `--seed SEED` | Semente para comportamento determinístico. Default: 42           |
| `--min-delay` | Delay mínimo (segundos) entre operações aleatórias. Default: 0.1 |
| `--max-delay` | Delay máximo (segundos) entre operações aleatórias. Default: 0.5 |
| `--force-deadlock` | Inverte a ordem de lock (Y→X) em transações pares para forçar deadlock.|
| `--gui`       | Exibe interface Tkinter com logs e status de cada requisito      |
| `-h, --help`  | Mostra ajuda                                                     |

**Exemplo:**

```bash
python deadlock_simulation.py -n 3 --seed 123 --min-delay 0.2 --max-delay 0.4 --gui
```

---

## 4. Interface Gráfica (Tkinter)

Se executado com `--gui`, abre uma janela dividida em:

1. **Painel de requisitos**: lista 7 requisitos do trabalho com ✓ ou ✗ indicando cumprimento em tempo real.
2. **Log de eventos**: área de texto rolável com todas as mensagens geradas pelas transações.

---
# Casos de Teste (UI)

Todos os testes abaixo devem ser executados com o parâmetro `--gui`. Para cada caso, verifique no **painel de requisitos** quais itens ficaram marcados (✔) e quais não (✖), além do **log de eventos**.

---

## Caso 1: Simulação Básica (1 transação, sem deadlock)

**Comando**  
```bash
python deadlock_simulation.py -n 1 --min-delay 0.5 --max-delay 1.0 --gui 
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✖ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✖ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

---

## Caso 2: Dois Threads Ordenados (sem deadlock)

**Comando**  
```bash
python deadlock_simulation.py -n 2 --seed 42 --min-delay 0.5 --max-delay 1.0 --gui
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✖ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✖ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

---

## Caso 3: Forçando Deadlock (2 transações)

**Comando**  
```bash
python deadlock_simulation.py -n 2 --force-deadlock --min-delay 0.5 --max-delay 1.0 --gui
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✔ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✔ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

---

## Caso 4: Três Threads com Deadlock Forçado

**Comando**  
```bash
python deadlock_simulation.py -n 3 --force-deadlock --min-delay 0.5 --max-delay 1.0 --gui
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✔ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✔ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

---

## Caso 5: Seed Determinístico (sem deadlock)

**Comando**  
```bash
python deadlock_simulation.py -n 3 --seed 7 --min-delay 0.5 --max-delay 1.0 --gui
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✖ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✖ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

---

## Caso 6: Delays Customizados (sem deadlock)

**Comando**  
```bash
python deadlock_simulation.py -n 3 --min-delay 0.2 --max-delay 0.8 --min-delay 0.5 --max-delay 1.0 --gui
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✖ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✖ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

---

## Caso 7: Stress Test (10 threads, deadlock forçado)

**Comando**  
```bash
python deadlock_simulation.py -n 10 --force-deadlock --min-delay 0.5 --max-delay 1.0 --gui
```

**Resultado esperado no painel**  
- ✔ 1. Simulação de Transações  
- ✔ 2. Controle de Acesso  
- ✔ 3. Identificação de Deadlock  
- ✔ 4. Execução com Múltiplas Threads  
- ✔ 5. Resolução de Deadlock  
- ✔ 6. Delays Aleatórios  
- ✔ 7. Logs Detalhados  

## 5. Casos de Teste + Critérios de Avaliação

Cada caso valida um ou mais critérios:

### Caso 1: Simulação Básica (Critério 1 e 4)

* **Parâmetros:** `-n 1`
* **Verificar:**

  * Apenas uma thread T1 executa todas as operações: lock(X), read(X), lock(Y), read(Y), write, unlock(x), unlock(y), commit.
  * Interface mostra ✓ em "Simulação de Transações Concorrentes" e "Execução com Múltiplas Threads".

### Caso 2: Conquista Ordenada (Critério 2 e 6)

* **Parâmetros:** `-n 2`
* **Verificar:**

  * Duas threads em ordem X → Y nunca deadlockam.
  * Delays aleatórios entre operações.
  * Interface mostra ✓ em "Controle de Acesso" e "Solicitações de Bloqueio Aleatórias".

### Caso 3: Forçando Deadlock (Critério 3 e 5)

* **Ajuste:** no código, altere a ordem de aquisição em transações pares (Y → X).
* **Parâmetros:** `-n 2`
* **Verificar:**

  * Deadlock detectado; protocolo wait-die aborta a transação mais jovem.
  * Transação abortada reinicia e finaliza.
  * Interface mostra ✓ em "Identificação de Deadlock" e "Resolução de Deadlock".

### Caso 4: Logs Detalhados (Critério 7)

* **Parâmetros:** `-n 3` (ou qualquer)
* **Verificar:**

  * Mensagens para: início, lock obtido, esperando, lock liberado, commit, abort.
  * Interface: todas as mensagens aparecem no log.

---

## 6. Observações

* O protocolo **wait-die** garante que não haja starvation: transações mais antigas sempre vencem.
* Delays aleatórios ajudam a criar cenários realistas de concorrência.
* A UI facilita visualizar o cumprimento de cada requisito em tempo real.

---

## 7. Execução sem GUI

Para rodar apenas no terminal, omita `--gui`:

```bash
python deadlock_simulation.py -n 5
```