import math
from dataclasses import dataclass

@dataclass #apenas teste
class Vertices:
    id: int
    x: float
    y: float


INF = 1e9
MAX_VERTICES = 18

# Estes devem ser definidos em outro lugar no seu código:
totalVertices = 0  # Número total de vértices no grafo
matrizAdj = []     # Matriz de adjacência com pesos das arestas
vertices = []      # Lista de vértices com coordenadas (ex: {'x': 0.0, 'y': 0.0})

def dijkstra(inicio, fim):
    dist = [] #[MAX_VERTICES]
    prev = [] #[MAX_VERTICES]
    visited = [] #[MAX_VERTICES]

    for i in range (totalVertices): #poderia fazer com .append() também
        dist[i] = INF
        prev[i] = -1
        visited[i] = 0

    dist[inicio] = 0

    for i in range(totalVertices):
        u = -1
        min = INF
        for j in range(totalVertices):
            if not visited[j] and dist[j] < min:
                u = j
                min = dist[j]
            
        if u == -1:
            break

        visited[u] = 1

        for v in range (totalVertices): #essa parte aqui ta meio nebulosa na minha cabeça pq precia de matrizAdj[][]
            if matrizAdj[u][v] < INF and dist[u] + matrizAdj[u][v] < dist[v]:
                dist[v] = dist[u] + matrizAdj[u][v]
                prev[v] = u
    
    if dist[fim] == INF:
        print("Sem caminho entre {} e {}.", inicio, fim)
        return
    
    print("\nDistancia total: u.m.", dist[fim])

    #Reconstrução do caminho
    path = [MAX_VERTICES]
    #path_len = 0
    v = fim

    while v != -1:
        path.append(v)
        v = prev[v]

    print("Caminho (do início ao fim):\n")
    for i in reversed(path):
        print("{} (x={}, y={})".format(i, vertices[i].x, vertices[i].y))
        #print(f"{i} (x={vertices[i]['x']}, y={vertices[i]['y']})")
