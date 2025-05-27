#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import time
import random
import argparse
import queue
import tkinter as tk
from tkinter import scrolledtext
import networkx as nx
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -----------------------------------
# CLI: argparse
# -----------------------------------
parser = argparse.ArgumentParser(
    description="Simulação de transações concorrentes com detecção e resolução de deadlock"
)
parser.add_argument('--force-deadlock', action='store_true',
                    help='Força deadlock invertendo ordem de lock em transações pares')
parser.add_argument('-n', type=int, default=4,
                    help='Número de transações (threads)')
parser.add_argument('--seed', type=int, default=42,
                    help='Semente aleatória')
parser.add_argument('--min-delay', type=float, default=0.1,
                    help='Delay mínimo (s)')
parser.add_argument('--max-delay', type=float, default=0.5,
                    help='Delay máximo (s)')
parser.add_argument('--gui', action='store_true',
                    help='Ativa interface gráfica')
args = parser.parse_args()
random.seed(args.seed)

# -----------------------------------
# Logs e métricas globais
# -----------------------------------
log_queue     = queue.Queue()
event_queue   = []    # para Gantt: (timestamp, txn_name, msg)
deadlock_count = 0
abort_count    = 0
wait_times     = []

def log_event(msg, color=None):
    """Loga no terminal e envia para a UI."""
    ts = time.time()
    ts_str = time.strftime("%H:%M:%S", time.localtime(ts))
    entry = f"[{ts_str}] {msg}"
    print(entry)
    log_queue.put((entry, color))
    # extrai nome da transação
    parts = msg.split()
    txn_name = parts[0] if parts and parts[0].startswith("T") else None
    event_queue.append((ts, txn_name, msg))

# -----------------------------------
# Flags de requisitos
# -----------------------------------
flags = {
    'sim': False, 'control': False, 'deadlock': False,
    'threads': False, 'resolve': False,
    'random': False, 'logs': False
}
def mark(flag):
    if not flags[flag]:
        flags[flag] = True
        log_queue.put(('_FLAG_', flag))

# -----------------------------------
# Recursos e LockManager
# -----------------------------------
class Resource:
    def __init__(self, item_id):
        self.item_id   = item_id
        self.locked_by = None
        self.queue     = []
        self.cond      = threading.Condition()

class LockManager:
    def __init__(self, resources):
        self.resources = {rid: Resource(rid) for rid in resources}

    def acquire(self, txn, rid):
        mark('control')
        res = self.resources[rid]
        t0  = time.time()
        with res.cond:
            if res.locked_by is None:
                res.locked_by = txn
                txn.held.append(res)
                log_event(f"{txn.name} obteve lock({rid})", "green"); mark('logs')
                return
            if res.locked_by == txn:
                return
            res.queue.append(txn)
            log_event(f"{txn.name} está esperando por lock({rid})", "orange"); mark('logs')
            self._detect_and_resolve()
            while True:
                if getattr(txn, 'aborted', False):
                    txn.aborted = False
                    raise AbortException()
                if res.locked_by is None and res.queue[0] == txn:
                    res.queue.pop(0)
                    res.locked_by = txn
                    txn.held.append(res)
                    t1 = time.time()
                    wait_times.append(t1 - t0)
                    log_event(f"{txn.name} obteve lock({rid}) após espera", "green"); mark('logs')
                    return
                res.cond.wait()

    def release(self, txn, rid):
        res = self.resources[rid]
        with res.cond:
            if res.locked_by == txn:
                res.locked_by = None
                txn.held.remove(res)
                log_event(f"{txn.name} liberou lock({rid})", "blue"); mark('logs')
                res.cond.notify_all()

    def _detect_and_resolve(self):
        global deadlock_count
        mark('deadlock')
        graph = {}
        all_t = set()
        for r in self.resources.values():
            if r.locked_by: all_t.add(r.locked_by)
            all_t.update(r.queue)
        for t in all_t:
            graph[t] = []
        for r in self.resources.values():
            owner = r.locked_by
            for w in r.queue:
                if owner:
                    graph[w].append(owner)
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
                    to_abort = max(cycle, key=lambda tr: tr.ts)
                    log_event(f"Deadlock em {[tr.name for tr in cycle]}, abortando {to_abort.name}", "red")
                    mark('resolve')
                    deadlock_count += 1
                    self._abort(to_abort)
                    return

    def _abort(self, txn):
        global abort_count
        abort_count += 1
        txn.aborted = True
        for r in list(txn.held):
            with r.cond:
                r.locked_by = None
                txn.held.remove(r)
                r.cond.notify_all()
        for r in self.resources.values():
            if txn in r.queue:
                r.queue.remove(txn)
                with r.cond:
                    r.cond.notify_all()

class AbortException(Exception):
    pass

# -----------------------------------
# Thread de Transação
# -----------------------------------
class Transaction(threading.Thread):
    COLORS = [
        "#1f77b4","#ff7f0e","#2ca02c","#d62728",
        "#9467bd","#8c564b","#e377c2","#7f7f7f"
    ]
    def __init__(self, tid, ts, lm):
        super().__init__(name=f"T{tid}")
        self.ts        = ts
        self.lm        = lm
        self.held      = []
        self.committed = False
        self.aborted   = False
        self.color     = self.COLORS[(tid-1) % len(self.COLORS)]

    def run(self):
        mark('sim'); mark('threads')
        while not self.committed:
            try:
                log_event(f"{self.name} entrou em execução", self.color); mark('logs')
                d = random.uniform(args.min_delay, args.max_delay)
                time.sleep(d); mark('random')

                if args.force_deadlock and (self.ts % 2 == 0):
                    self.lm.acquire(self, 'Y')
                    log_event(f"{self.name} leu Y", self.color); mark('logs')
                    time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')
                    self.lm.acquire(self, 'X')
                    log_event(f"{self.name} leu X", self.color); mark('logs')
                else:
                    self.lm.acquire(self, 'X')
                    log_event(f"{self.name} leu X", self.color); mark('logs')
                    time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')
                    self.lm.acquire(self, 'Y')
                    log_event(f"{self.name} leu Y", self.color); mark('logs')

                time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')
                log_event(f"{self.name} escreveu X e Y", self.color); mark('logs')
                self.lm.release(self, 'X')
                self.lm.release(self, 'Y')
                log_event(f"{self.name} finalizou com sucesso", self.color); mark('logs')
                self.committed = True

            except AbortException:
                log_event(f"{self.name} abortada, reiniciando", "purple"); mark('logs')
                self.held.clear()
                time.sleep(random.uniform(args.min_delay, args.max_delay)); mark('random')

# -----------------------------------
# UI com legendas fixas
# -----------------------------------
class UI:
    def __init__(self, root, lm, txns):
        self.root   = root
        self.lm     = lm
        self.txns   = txns
        root.title("Deadlock Simulation")

        # intervalo de update gráfico
        self.last_graph     = 0
        self.graph_interval = 1.75

        # layout primário
        top = tk.Frame(root); top.pack(side=tk.TOP, fill=tk.X)
        mid = tk.Frame(root); mid.pack(fill=tk.BOTH, expand=True)
        bot = tk.Frame(root); bot.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # ─────────── Frame de legendas ───────────
        legend_frame = tk.Frame(top)
        legend_frame.pack(side=tk.LEFT, expand=True, pady=5)

        # Grafo
        tk.Label(legend_frame, text="• Transação", bg="lightblue", width=12).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="• Recurso",    bg="lightgreen", width=12).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="• Ciclo de Deadlock", fg="red").pack(side=tk.LEFT, padx=3)

        # espaçamento
        tk.Label(legend_frame, text="   ").pack(side=tk.LEFT)

        # Gantt
        tk.Label(legend_frame, text="■ Entrou",    bg="#1f77b4", width=10).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="■ Esperando", bg="#ff7f0e", width=10).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="■ Obteve",    bg="#2ca02c", width=10).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="■ Abortada",  bg="#d62728", width=10).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="■ Finalizou", bg="#9467bd", width=10).pack(side=tk.LEFT, padx=3)
        tk.Label(legend_frame, text="■ Operação", bg="gray", width=10).pack(side=tk.LEFT, padx=3)
        # ────────────────────────────────────────────

        # 1) Flags
        left = tk.Frame(top); left.pack(side=tk.LEFT, padx=5)
        self.labels = {}
        for text, key in [
            ("1. Simulação de Transações", 'sim'),
            ("2. Controle de Acesso",        'control'),
            ("3. Identificação de Deadlock",  'deadlock'),
            ("4. Múltiplas Threads",          'threads'),
            ("5. Resolução de Deadlock",      'resolve'),
            ("6. Delays Aleatórios",          'random'),
            ("7. Logs Detalhados",            'logs'),
        ]:
            var = tk.StringVar(value=f"✗ {text}")
            lbl = tk.Label(left, textvariable=var, anchor='w')
            lbl.pack(fill=tk.X)
            self.labels[key] = var

        # 2) Métricas
        right = tk.Frame(top); right.pack(side=tk.RIGHT, padx=5)
        self.metrics = tk.Label(
            right,
            text="Métricas:\nDeadlocks: 0\nAborts: 0\nAvg wait: 0.00s",
            justify='left'
        )
        self.metrics.pack()

        # 3) Wait-For Graph
        gframe = tk.LabelFrame(mid, text="Wait-For Graph")
        gframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.fig_g = Figure(figsize=(3,3))
        self.ax_g  = self.fig_g.add_subplot(111)
        self.canvas_g = FigureCanvasTkAgg(self.fig_g, master=gframe)
        self.canvas_g.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 4) Recursos
        rframe = tk.LabelFrame(mid, text="Recursos")
        rframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.res_canvas = tk.Canvas(rframe, width=200, height=100)
        self.res_canvas.pack()
        self.res_canvas.create_rectangle(20,20,80,80,   fill="lightgray", tags="X")
        self.res_canvas.create_text(50,50,  text="X")
        self.res_canvas.create_rectangle(120,20,180,80, fill="lightgray", tags="Y")
        self.res_canvas.create_text(150,50, text="Y")
        self.res_canvas.create_text(50,90, text="", tags="queueX")
        self.res_canvas.create_text(150,90,text="",  tags="queueY")

        # 5) Gantt Chart
        cframe = tk.LabelFrame(mid, text="Gantt Chart")
        cframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.fig_c = Figure(figsize=(4,3))
        self.ax_c  = self.fig_c.add_subplot(111)
        self.canvas_c = FigureCanvasTkAgg(self.fig_c, master=cframe)
        self.canvas_c.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 6) Log
        self.log = scrolledtext.ScrolledText(bot, height=10)
        self.log.pack(fill=tk.BOTH, expand=True)

        # inicia loop de atualização
        self.root.after(500, self.update_ui)


    def update_ui(self):
        now = time.time()

        # flags e métricas
        for key, done in flags.items():
            if done:
                txt = self.labels[key].get()[2:]
                self.labels[key].set(f"✔ {txt}")

        avg_wait = sum(wait_times)/len(wait_times) if wait_times else 0.0
        self.metrics.config(text=(
            f"Métricas:\nDeadlocks: {deadlock_count}\n"
            f"Aborts: {abort_count}\nAvg wait: {avg_wait:.2f}s"
        ))

        # redesenha grafo e gantt
        if now - self.last_graph >= self.graph_interval:
            self.last_graph = now

            # — Wait-For Graph —
            G = nx.DiGraph()
            for t in self.txns:
                G.add_node(t.name)
            for r in self.lm.resources.values():
                G.add_node(r.item_id)
                if r.locked_by:
                    G.add_edge(r.item_id, r.locked_by.name)
                for w in r.queue:
                    G.add_edge(w.name, r.item_id)

            self.ax_g.clear()
            pos = nx.spring_layout(G)
            nx.draw(
                G, pos, ax=self.ax_g,
                node_color=[
                    'lightblue' if n in [t.name for t in self.txns]
                    else 'lightgreen'
                    for n in G.nodes()
                ],
                with_labels=True, arrows=True
            )
            for cycle in nx.simple_cycles(G):
                edges = list(zip(cycle, cycle[1:]+[cycle[0]]))
                nx.draw_networkx_edges(
                    G, pos, edgelist=edges,
                    edge_color='red', width=2, ax=self.ax_g
                )
            self.canvas_g.draw()

            # — Recursos —
            for rid in ("X","Y"):
                res = self.lm.resources[rid]
                fill = res.locked_by.color if res.locked_by else 'lightgray'
                self.res_canvas.itemconfig(rid, fill=fill)
                names = " ".join(t.name for t in res.queue)
                self.res_canvas.itemconfig(f"queue{rid}", text=names)

            # — Gantt Chart —
            self.ax_c.clear()
            start_ts = event_queue[0][0] if event_queue else now
            state_colors = {
                'entrou':'#1f77b4','esperando':'#ff7f0e',
                'obteve':'#2ca02c','abortada':'#d62728','finalizou':'#9467bd'
            }
            for i,txn in enumerate(self.txns):
                evs = [(ts,msg) for ts,name,msg in event_queue if name==txn.name]
                for ts,msg in evs:
                    st = msg.split()[1]
                    self.ax_c.barh(i, 0.1, left=ts-start_ts,
                                   color=state_colors.get(st,'gray'))

            self.ax_c.set_yticks(range(len(self.txns)))
            self.ax_c.set_yticklabels([t.name for t in self.txns])
            self.canvas_c.draw()

        # log colorido
        try:
            while True:
                tag, val = log_queue.get_nowait()
                if tag == '_FLAG_': continue
                entry, color = tag, val
                if color:
                    self.log.tag_configure(entry, foreground=color)
                    self.log.insert(tk.END, entry+"\n", entry)
                else:
                    self.log.insert(tk.END, entry+"\n")
                self.log.see(tk.END)
        except queue.Empty:
            pass

        self.root.after(100, self.update_ui)

# -----------------------------------
# Execução principal
# -----------------------------------
if __name__ == "__main__":
    lm   = LockManager(['X','Y'])
    txns = [Transaction(i, i, lm) for i in range(1, args.n+1)]

    if args.gui:
        root = tk.Tk()
        ui   = UI(root, lm, txns)
        for t in txns:
            t.start()
        root.mainloop()
        for t in txns:
            t.join()
    else:
        for t in txns:
            t.start()
        for t in txns:
            t.join()
        log_event("Todas as transações concluídas.", "blue")
