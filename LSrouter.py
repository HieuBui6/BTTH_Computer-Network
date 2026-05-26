####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################
import json
import heapq
from router import Router
from packet import Packet


class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        self.neighbors = {}  # port -> (endpoint, cost)
        self.topology = {}  # addr -> (seq_num, neighbors)
        self.forwarding_table = {}  # dst_addr -> (next_hop, cost)
        self.seq_num = 0
    
    def flood_lsp(self, expect_port = None):
        self.seq_num += 1
        neighbors_dict = {}
        for port in self.neighbors:
            neighbor, cost = self.neighbors[port]
            neighbors_dict[neighbor] = cost
        self.topology[self.addr] = {
            "seq" : self.seq_num,
            "neighbors" : neighbors_dict
        }
        msg = {
            "src" : self.addr,
            "seq" : self.seq_num,
            "neighbors" : neighbors_dict
        }
        pkt = Packet(
            Packet.ROUTING,
            self.addr,
            None,
            json.dumps(msg)
        )
        for port in self.neighbors:
            if port != expect_port:
                self.send(port, pkt)
    def run_dijkstra(self):
        graph = {}

        for router in self.topology:
            if router not in graph:
                graph[router] = {}
            for neighbor in self.topology[router]["neighbors"]:
                cost = self.topology[router]["neighbors"][neighbor]
                graph[router][neighbor] = cost
                if neighbor not in graph:
                    graph[neighbor] = {}
                graph[neighbor][router] = cost
        dist = {}
        prev = {}
        pq = []
        dist[self.addr] = 0
        heapq.heappush(pq, (0, self.addr))
        while pq:
            current_dist, node = heapq.heappop(pq)
            if node not in graph:
                continue
            for neighbor in graph[node]:
                cost = graph[node][neighbor]
                new_dist = current_dist + cost
                if neighbor not in dist or new_dist < dist[neighbor]:
                    dist[neighbor] = new_dist
                    prev[neighbor] = node
                    heapq.heappush(pq, (new_dist, neighbor))
        self.forwarding_table = {}

        for port in self.neighbors:
            neighbor, _ = self.neighbors[port]
            if neighbor in dist:
                self.forwarding_table[neighbor] = port

        for dst in dist:
            if dst == self.addr:
                    continue
            if dst not in prev:
                    continue
            cur = dst
            while prev[cur] != self.addr:
                    cur = prev[cur]
            next_hop = cur
            for port in self.neighbors:
                neighbor, _ = self.neighbors[port]
                if neighbor == next_hop:
                    self.forwarding_table[dst] = port
    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            dst = packet.dst_addr
            if dst in self.forwarding_table:
                out_port = self.forwarding_table[dst]
                self.send(out_port, packet)
        else:
            msg = json.loads(packet.content)
            src = msg["src"]
            seq = msg["seq"]
            neighbors = msg["neighbors"]
            if src in self.topology:
                if seq <= self.topology[src]["seq"]:
                    return
            self.topology[src] = {
                "seq" : seq,
                "neighbors" : neighbors
            }
            for p in self.neighbors:
                if p != port:
                    self.send(p, packet)
            self.run_dijkstra()
    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.neighbors[port] = (endpoint, cost)
        neighbors_dict = {}
        for p in self.neighbors:
            neighbor, c = self.neighbors[p]
            neighbors_dict[neighbor] = c
        self.topology[self.addr] = {
            "seq" : self.seq_num,
            "neighbors" : neighbors_dict
        }
        self.flood_lsp()
        self.run_dijkstra()

    def handle_remove_link(self, port):
        """Handle removed link."""
        if port not in self.neighbors:
            return
        del self.neighbors[port]
        self.flood_lsp()
        self.run_dijkstra()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.flood_lsp()
    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return str(self.forwarding_table)
