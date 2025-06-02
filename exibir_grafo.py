import matplotlib.pyplot as plt
import networkx as nx

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
