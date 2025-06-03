import matplotlib.pyplot as plt
import networkx as nx
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

#Função para calcular a distância entre dois pontos no plano:
def calcDist(x0, y0, x1, y1):
    return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

#Cria a matriz de adjacência e calcula o peso (distância) para cada aresta com base nas coordenadas dos vértices:
def construirGrafo(vertices, arestas): 
    global matrizAdj
    matrizAdj = [[INF for _ in range(totalVertices)] for _ in range(totalVertices)]
    
    for a, b, _ in arestas:
        dist = calcDist(vertices[a].x, vertices[a].y, vertices[b].x, vertices[b].y)
        matrizAdj[a][b] = dist
        matrizAdj[b][a] = dist 

def exibir_grafo(vertices, arestas, caminho=[], nome_arquivo ='grafo.png'):
    G = nx.Graph()
    pos = {}

    #adiciona os vértices e posições
    for v in vertices:
        G.add_node(v.id)
        pos[v.id] = (v.x, v.y)

    #adiciona arestas com pesos
    for a, b, peso in arestas:
        G.add_edge(a, b, weight = peso)
    
    #define as cores das arestas
    cor_das_arestas = []
    lista_arestas = list(G.edges())
    caminho_arestas = list(zip(caminho, caminho[1:]))

    for u, v in lista_arestas:
        if caminho and ((u,v) in caminho_arestas or (v,u) in caminho_arestas):
            cor_das_arestas.append('r')
        else:
            cor_das_arestas.append('b')

    #define as cores dos nós
    cor_dos_nos = []
    for n in G.nodes():
        if caminho:
            if n == caminho[0]:
                cor_dos_nos.append('g')         #origem
            elif n == caminho[-1]:
                cor_dos_nos.append('r')         #destino
            elif n in caminho:
                cor_dos_nos.append('y')         #intermediário
            else:
                cor_dos_nos.append('grey')
        else:
            cor_dos_nos.append('grey')

    #desenha o grafo
    nx.draw(
        G, pos,
        with_labels = True,
        node_color = cor_dos_nos,
        edge_color = cor_das_arestas,
        node_size = 500,
        font_size = 10,
        width = 2
    )

    #Rótulos com pesos das arestas
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    plt.savefig(nome_arquivo)  #salva a imagem do grafo gerado
    plt.show()

def dijkstra(inicio, fim):
    dist = [INF] * totalVertices #vetor de distancias
    prev = [-1] * totalVertices #vetor para reconstrução do caminho
    visited = [0] * totalVertices #vetor de visitados



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
        print(f"Sem caminho entre {inicio} e {fim}.")
        return
    
    print("\nDistancia total: u.m.", dist[fim])

    #Reconstrução do caminho
    path = []
    #path_len = 0
    v = fim

    while v != -1:
        path.append(v)
        v = prev[v]

    print("Caminho (do início ao fim):\n")
    for i in reversed(path):
        print("{} (x={}, y={})".format(i, vertices[i].x, vertices[i].y))
        #print(f"{i} (x={vertices[i]['x']}, y={vertices[i]['y']})")
    return path

def main():
    global totalVertices, totalArestas, vertices, arestas
    
    # Definição dos vértices
    vertices = [
        Vertices(0, 149, 200),
        Vertices(1, 225, 200),
        Vertices(2, 156.175936136879, 193.978674634193),
        Vertices(3, 164.288445856511, 189.29491496376),
        Vertices(4, 173.091034656191, 186.09103465619),
        Vertices(5, 182.316240329567, 184.46438199339),
        Vertices(6, 191.683759670433, 184.46438199339),
        Vertices(7, 200.908965343809, 186.091034656191),
        Vertices(8, 209.711554143489, 189.29491496376),
        Vertices(9, 217.824063863121, 193.978674634193),
        Vertices(10, 217.824063863121, 206.021325365807),
        Vertices(11, 209.711554143489, 210.70508503624),
        Vertices(12, 200.908965343809, 213.908965343809),
        Vertices(13, 191.683759670433, 215.53561800661),
        Vertices(14, 182.316240329567, 215.53561800661),
        Vertices(15, 173.091034656191, 213.908965343809),
        Vertices(16, 164.288445856511, 210.70508503624),
        Vertices(17, 156.175936136879, 206.021325365807),
    ]
    totalVertices = len(vertices)
    
    # Definição das arestas (tuplas: u, v, peso placeholder)
    arestas = [
        (0, 2, 0),
        (2, 3, 0),
        (3, 4, 0),
        (4, 5, 0),
        (5, 6, 0),
        (6, 7, 0),
        (7, 8, 0),
        (8, 9, 0),
        (9, 0, 0),
        (9, 10, 0),
        (10, 11, 0),
        (11, 12, 0),
        (12, 13, 0),
        (13, 14, 0),
        (14, 15, 0),
        (15, 16, 0),
        (16, 17, 0),
        (17, 0, 0),
    ]
    totalArestas = len(arestas)
    
    construirGrafo(vertices, arestas)

    print("Menor caminho entre dois vértices - algoritmo de Dijkstra\n")
    print(f"Total de vértices: {totalVertices}")
    print(f"Total de arestas : {totalArestas}")

    origem = int(input(f"Digite o vértice de origem (0 a {totalVertices - 1}): "))
    destino = int(input(f"Digite o vértice de destino (0 a {totalVertices - 1}): "))

    if 0 <= origem < totalVertices and 0 <= destino < totalVertices:
        #dijkstra(origem, destino)
        exibir_grafo(vertices, arestas, caminho = dijkstra(origem, destino))
    else:
        print("Índices inválidos.")

if __name__ == "__main__":
    main()
