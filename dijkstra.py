import matplotlib.pyplot as plt
import networkx as nx
import math
from dataclasses import dataclass

INF = 1e9

@dataclass
class Vertices:
    id: int
    x: float
    y: float

@dataclass
class Arestas:
    orig: int
    dest: int
    dist: float

vertices = []
arestas = []

matrizAdj = []
totalVertices = 0
totalArestas = 0


#Função para calcular a distância entre dois pontos no plano:
def calcDist(x0, y0, x1, y1):
    return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

#Cria a matriz de adjacência e calcula o peso (distância) para cada aresta com base nas coordenadas dos vértices:
def construirGrafo(vertices, arestas): 
    global matrizAdj, totalVertices
    totalVertices = len(vertices)
    matrizAdj = [[INF for _ in range(totalVertices)] for _ in range(totalVertices)]
    
    for aresta in arestas:
        if aresta.orig < totalVertices and aresta.dest < totalVertices:
            dist = calcDist(vertices[aresta.orig].x, vertices[aresta.orig].y, vertices[aresta.dest].x, vertices[aresta.dest].y)
            matrizAdj[aresta.orig][aresta.dest] = dist
            matrizAdj[aresta.dest][aresta.orig] = dist
        else:
            print(f"Aviso: Aresta ignorada - origem {aresta.orig} ou destino {aresta.dest} fora do intervalo válido (0 a {totalVertices-1})")


def exibir_grafo(vertices, arestas, caminho=[], nome_arquivo ='grafo.png'):
    G = nx.Graph()
    pos = {}

    #adiciona os vértices e posições
    for v in vertices:
        G.add_node(v.id)
        pos[v.id] = (v.x, v.y)

    #adiciona arestas com pesos
    for aresta in arestas:
        G.add_edge(aresta.orig, aresta.dest)
    
    #define as cores das arestas
    cor_das_arestas = []
    lista_arestas = list(G.edges())
    caminho_arestas = criar_arestas_caminho(caminho)

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
        node_size = 0,
        font_size = 0,
        width = 2
    )

    #Rótulos com pesos das arestas
    #edge_labels = nx.get_edge_attributes(G, 'weight')
    #nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    plt.savefig(nome_arquivo)  #salva a imagem do grafo gerado
    plt.show()

def criar_arestas_caminho(caminho):
    if caminho is None or len(caminho) < 2:
        return []
    return list(zip(caminho, caminho[1:]))


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


def ler_arquivo():
    global totalVertices, totalArestas, vertices, arestas
    caminhoArquivo = 'map.poly' #substituir por comando que vai receber o endereço do arquivo através da interface
    linhas = []
    with open(caminhoArquivo, 'r') as arquivo:
        for linha in arquivo:
            linhas.append(linha.strip())
    
    totalVertices = int(linhas[0].split()[0]) # Lê a quantidade de vértices (primeiro número da primeira linha)
    # Lê os vértices
    for i in range(1, totalVertices + 1):
        dados = linhas[i].split()
        vertice = Vertices(
            id=int(dados[0]),
            x=float(dados[1]),
            y=float(dados[2])
        )
        vertices.append(vertice)
    
    # Encontra a posição onde começam as arestas
    pos_arestas = totalVertices + 1
    totalArestas = int(linhas[pos_arestas].split()[0])

    # Lê as arestas
    for i in range(pos_arestas + 1, pos_arestas + totalArestas + 1):
        dados = linhas[i].split()
        aresta = Arestas(
            orig=int(dados[1]),  # Segundo número é a origem
            dest=int(dados[2]),  # Terceiro número é o destino
            dist=float(dados[3]) if len(dados) > 3 else 0.0  # Quarto número é a distância, se existir
        )
        arestas.append(aresta)

def main():

    global totalVertices, totalArestas, vertices, arestas
    
    # Definição dos vértices
    ler_arquivo()
    
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


main()
