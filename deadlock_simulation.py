#!/usr/bin/env python3
import threading
import time
import random
import argparse
import queue
import tkinter as tk
from tkinter import scrolledtext

# -----------------------------------
# CLI: argparse
# -----------------------------------
parser = argparse.ArgumentParser(
    description="Simulação de transações concorrentes com detecção e resolução de deadlock"
)
parser.add_argument('--force-deadlock', action='store_true', help='Força deadlock invertendo ordem de lock em transações pares')
parser.add_argument('-n', type=int, default=4, help='Número de transações (threads)')
parser.add_argument('--seed', type=int, default=42, help='Semente aleatória')
parser.add_argument('--min-delay', type=float, default=0.1, help='Delay mínimo (s)')
parser.add_argument('--max-delay', type=float, default=0.5, help='Delay máximo (s)')
parser.add_argument('--gui', action='store_true', help='Ativa interface gráfica')
args = parser.parse_args()

random.seed(args.seed)

# -----------------------------------
# Callback de log (fila pra UI)
# -----------------------------------
log_queue = queue.Queue()
def log_event(msg):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    log_queue.put(entry)

# Flags de requisitos
flags = {
    'sim': False,        # requisito 1
    'control': False,    # requisito 2
    'deadlock': False,   # requisito 3
    'threads': False,    # requisito 4
    'resolve': False,    # requisito 5
    'random': False,     # requisito 6
    'logs': False        # requisito 7
}

def mark(flag):
    if not flags[flag]:
        flags[flag] = True
        # notifica UI
        log_queue.put(('_FLAG_', flag))

# -----------------------------------
# Recursos e LockManager
# -----------------------------------
class Resource:
    def __init__(self, item_id):
        self.item_id = item_id
        self.locked_by = None
        self.queue = []
        self.cond = threading.Condition()

class LockManager:
    def __init__(self, resources):
        self.resources = {rid: Resource(rid) for rid in resources}

    def acquire(self, txn, rid):
        mark('control')
        res = self.resources[rid]
        with res.cond:
            if res.locked_by is None:
                res.locked_by = txn
                txn.held.append(res)
                log_event(f"{txn.name} obteve lock({rid})")
                mark('logs')
                return
            if res.locked_by == txn:
                return
            res.queue.append(txn)
            log_event(f"{txn.name} está esperando por lock({rid})")
            mark('logs')
            self._detect_and_resolve()
            while True:
                if getattr(txn, 'aborted', False):
                    txn.aborted = False
                    raise AbortException()
                if res.locked_by is None and res.queue[0] == txn:
                    res.queue.pop(0)
                    res.locked_by = txn
                    txn.held.append(res)
                    log_event(f"{txn.name} obteve lock({rid}) após espera")
                    mark('logs')
                    return
                res.cond.wait()

    def release(self, txn, rid):
        res = self.resources[rid]
        with res.cond:
            if res.locked_by == txn:
                res.locked_by = None
                txn.held.remove(res)
                log_event(f"{txn.name} liberou lock({rid})")
                mark('logs')
                res.cond.notify_all()

    def _detect_and_resolve(self):
        mark('deadlock')
        # constrói grafo
        graph = {}
        all_t = set()
        for r in self.resources.values():
            if r.locked_by: all_t.add(r.locked_by)
            all_t.update(r.queue)
        for t in all_t: graph[t] = []
        for r in self.resources.values():
            owner = r.locked_by
            for w in r.queue:
                if owner: graph[w].append(owner)
        # dfs ciclo
        visited, stack = set(), set()
        def dfs(v):
            visited.add(v); stack.add(v)
            for nb in graph[v]:
                if nb not in visited:
                    cyc = dfs(nb)
                    if cyc: return cyc
                elif nb in stack:
                    return list(stack)
            stack.remove(v)
            return None
        for t in graph:
            if t not in visited:
                cycle = dfs(t)
                if cycle:
                    # aborta mais jovem
                    to_abort = max(cycle, key=lambda tr: tr.ts)
                    log_event(f"Deadlock detectado em {[tr.name for tr in cycle]}. Abortando {to_abort.name}")
                    mark('resolve')
                    self._abort(to_abort)
                    return

    def _abort(self, txn):
        txn.aborted = True
        for r in list(txn.held):
            with r.cond:
                r.locked_by = None
                txn.held.remove(r)
                r.cond.notify_all()
        for r in self.resources.values():
            if txn in r.queue:
                r.queue.remove(txn)
                with r.cond: r.cond.notify_all()

# -----------------------------------
# Exceção de abort
# -----------------------------------
class AbortException(Exception):
    pass

# -----------------------------------
# Transação (Thread)
# -----------------------------------
class Transaction(threading.Thread):
    def __init__(self, tid, ts, lm):
        super().__init__(name=f"T{tid}")
        self.ts = ts
        self.lm = lm
        self.held = []
        self.committed = False
        self.aborted = False

    def run(self):
        mark('sim')
        mark('threads')
        while not self.committed:
            try:
                log_event(f"{self.name} entrou em execução")
                mark('logs')
                # espera aleatória
                d = random.uniform(args.min_delay, args.max_delay)
                time.sleep(d); mark('random')
                # operação X→Y
                # operação X→Y (ou Y→X se estiver forçando deadlock)
                if args.force_deadlock and (self.ts % 2 == 0):
                    # transações pares: Y→X
                    self.lm.acquire(self, 'Y')
                    log_event(f"{self.name} leu Y"); mark('logs')
                    time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')
                    self.lm.acquire(self, 'X')
                    log_event(f"{self.name} leu X"); mark('logs')
                else:
                    # transações ímpares (ou sem --force-deadlock): X→Y
                    self.lm.acquire(self, 'X')
                    log_event(f"{self.name} leu X"); mark('logs')
                    time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')
                    self.lm.acquire(self, 'Y')
                    log_event(f"{self.name} leu Y"); mark('logs')
                time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')
                log_event(f"{self.name} escreveu X e Y"); mark('logs')
                self.lm.release(self, 'X')
                self.lm.release(self, 'Y')
                log_event(f"{self.name} finalizou com sucesso"); mark('logs')
                self.committed = True
            except AbortException:
                log_event(f"{self.name} foi abortada e reiniciará"); mark('logs')
                self.held.clear()
                time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')

# -----------------------------------
# Interface Gráfica (Tkinter)
# -----------------------------------
class UI:
    def __init__(self, root):
        self.root = root
        root.title("Deadlock Simulation")
        # quadro flags
        reqs = [
            ("1. Simulação de Transações", 'sim'),
            ("2. Controle de Acesso", 'control'),
            ("3. Identificação de Deadlock", 'deadlock'),
            ("4. Execução com Múltiplas Threads", 'threads'),
            ("5. Resolução de Deadlock", 'resolve'),
            ("6. Delays Aleatórios", 'random'),
            ("7. Logs Detalhados", 'logs'),
        ]
        frm = tk.Frame(root)
        frm.pack(side=tk.TOP, fill=tk.X)
        self.labels = {}
        for text, key in reqs:
            var = tk.StringVar(value=f"✗ {text}")
            lbl = tk.Label(frm, textvariable=var, anchor='w')
            lbl.pack(fill=tk.X)
            self.labels[key] = var
        # text log
        self.log = scrolledtext.ScrolledText(root, height=20)
        self.log.pack(fill=tk.BOTH, expand=True)
        # loop de atualização
        self._update_loop()

    def _update_loop(self):
        try:
            while True:
                item = log_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == '_FLAG_':
                    flag = item[1]
                    text = self.labels[flag].get()[2:]
                    self.labels[flag].set(f"✔ {text}")
                else:
                    self.log.insert(tk.END, item + "\n")
                    self.log.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self._update_loop)

# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    lm = LockManager(['X', 'Y'])
    txns = [Transaction(i, ts=i, lm=lm) for i in range(1, args.n + 1)]
    for t in txns: t.start()
    for t in txns: t.join()
    log_event("Todas as transações concluídas.")

if __name__ == "__main__":
    if args.gui:
        root = tk.Tk()
        ui = UI(root)
        threading.Thread(target=main, daemon=True).start()
        root.mainloop()
    else:
        main()
