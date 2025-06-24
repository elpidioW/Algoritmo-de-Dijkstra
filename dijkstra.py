import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
import numpy as np
import math
from dataclasses import dataclass
import os
import time
from PIL import Image, ImageTk
import io
import xml.etree.ElementTree as ET

INF = 1e9

# Parâmetros da zona UTM 23S (baseado no código C)
A = 6378137.0            # Semi-eixo maior WGS84
F = 1.0 / 298.257223563  # Achatamento
K0 = 0.9996
LON0_DEG = -45.0         # longitude central da zona 23S
PI = 3.14159265358979323846

def converter_para_utm(lat_deg, lon_deg):
    """Converte coordenadas geográficas para UTM (baseado no código C)"""
    e2 = F * (2 - F)                    # excentricidade ao quadrado
    ep2 = e2 / (1 - e2)                 # excentricidade secundária ao quadrado
    lat = lat_deg * PI / 180.0
    lon = lon_deg * PI / 180.0
    lon0 = LON0_DEG * PI / 180.0

    N = A / math.sqrt(1 - e2 * math.sin(lat) * math.sin(lat))
    T = math.tan(lat) * math.tan(lat)
    C = ep2 * math.cos(lat) * math.cos(lat)
    A_val = (lon - lon0) * math.cos(lat)

    # Cálculo do arco meridional com mais termos
    M = A * ((1 - e2/4 - 3*e2*e2/64 - 5*e2*e2*e2/256) * lat
      - (3*e2/8 + 3*e2*e2/32 + 45*e2*e2*e2/1024) * math.sin(2*lat)
      + (15*e2*e2/256 + 45*e2*e2*e2/1024) * math.sin(4*lat)
      - (35*e2*e2*e2/3072) * math.sin(6*lat))

    # Coordenada leste (X)
    x = K0 * N * (A_val + (1 - T + C) * math.pow(A_val,3)/6
         + (5 - 18*T + T*T + 72*C - 58*ep2) * math.pow(A_val,5)/120) + 500000.0

    # Coordenada norte (Y)
    y = K0 * (M + N * math.tan(lat) * (A_val*A_val/2 + (5 - T + 9*C + 4*C*C) * math.pow(A_val,4)/24
         + (61 - 58*T + T*T + 600*C - 330*ep2) * math.pow(A_val,6)/720))

    # Ajusta para hemisfério sul
    if lat_deg < 0:
        y += 10000000.0
    
    return x, y

def reduzir_escala(pontos, redutor=2):
    """Reduz a escala dos pontos (baseado no código C)"""
    if not pontos:
        return
    
    min_x = min(ponto['x'] for ponto in pontos)
    min_y = min(ponto['y'] for ponto in pontos)
    
    for ponto in pontos:
        ponto['x'] = (ponto['x'] - min_x) / redutor
        ponto['y'] = (ponto['y'] - min_y) / redutor
    
    # Rotação vertical para que (0,0) seja no canto superior esquerdo
    max_y = max(ponto['y'] for ponto in pontos)
    for ponto in pontos:
        ponto['y'] = max_y - ponto['y']

def processar_arquivo_osm(caminho_arquivo):
    """Processa arquivo OSM e retorna dados no formato .poly"""
    try:
        tree = ET.parse(caminho_arquivo)
        root = tree.getroot()
        
        # Dicionários para armazenar nós e vias
        nodes = {}  # id_original -> {lat, lon, x, y, id_interno}
        ways = []   # lista de vias com nós
        
        # Processar nós
        id_interno = 0
        for node in root.findall('.//node'):
            node_id_attr = node.get('id')
            lat_attr = node.get('lat')
            lon_attr = node.get('lon')
            
            if node_id_attr is None or lat_attr is None or lon_attr is None:
                continue
                
            node_id = int(node_id_attr)
            lat = float(lat_attr)
            lon = float(lon_attr)
            
            # Converter para UTM
            x, y = converter_para_utm(lat, lon)
            
            nodes[node_id] = {
                'lat': lat,
                'lon': lon,
                'x': x,
                'y': y,
                'id_interno': id_interno
            }
            id_interno += 1
        
        # Processar vias
        for way in root.findall('.//way'):
            way_nodes = []
            for nd in way.findall('nd'):
                ref_attr = nd.get('ref')
                if ref_attr is None:
                    continue
                    
                ref_id = int(ref_attr)
                if ref_id in nodes:
                    way_nodes.append(nodes[ref_id]['id_interno'])
            
            if len(way_nodes) > 1:
                ways.append(way_nodes)
        
        # Reduzir escala
        reduzir_escala(nodes.values())
        
        # Converter para formato .poly
        vertices = []
        arestas = []
        
        # Criar lista de vértices ordenados por id_interno
        vertices_ordenados = sorted(nodes.values(), key=lambda x: x['id_interno'])
        
        for node in vertices_ordenados:
            vertices.append({
                'id': node['id_interno'],
                'x': node['x'],
                'y': node['y']
            })
        
        # Criar arestas a partir das vias
        aresta_id = 0
        for way in ways:
            for i in range(len(way) - 1):
                from_node = way[i]
                to_node = way[i + 1]
                # Calcular distância
                v1 = vertices[from_node]
                v2 = vertices[to_node]
                distancia = math.sqrt((v2['x'] - v1['x'])**2 + (v2['y'] - v1['y'])**2)
                arestas.append({
                    'id': aresta_id,
                    'orig': from_node,
                    'dest': to_node,
                    'dist': distancia
                })
                aresta_id += 1
        
        return vertices, arestas
        
    except Exception as e:
        raise Exception(f"Erro ao processar arquivo OSM: {str(e)}")

@dataclass
class Vertices:
    id: int
    x: float
    y: float

@dataclass
class Arestas:
    orig: int
    dest: int
    dist: float  # Peso da aresta (último campo)

class InterfaceDijkstra:
    def __init__(self, root):
        self.root = root
        self.root.title("Algoritmo de Dijkstra - Interface Gráfica")
        self.root.geometry("1600x1200")  # Janela ainda maior para acomodar todos os controles
        
        # Variáveis globais
        self.vertices = []
        self.arestas = []
        self.matrizAdj = []
        self.totalVertices = 0
        self.totalArestas = 0
        self.arquivo_carregado = False
        self.caminho_atual = []
        
        # Variáveis para seleção de vértices
        self.vertice_origem = None
        self.vertice_destino = None
        self.vertices_selecionados = []  # Para armazenar os vértices clicados
        
        # Variáveis para edição do grafo
        self.modo_edicao = "navegacao"  # navegacao, adicionar_vertice, adicionar_aresta, remover_vertice, remover_aresta
        self.vertice_temporario = None  # Para adicionar arestas
        self.proximo_id_vertice = 0  # Para gerar IDs únicos para novos vértices
        
        # Variável para tamanho dos vértices
        self.tamanho_vertices = 10 # Tamanho padrão dos vértices
        
        # NOVO: Variáveis para tamanho da fonte
        self.tamanho_fonte_vertices = 5  # Tamanho padrão da fonte dos vértices
        self.tamanho_fonte_arestas = 5   # Tamanho padrão da fonte das arestas
        
        # NOVO: Variável para tipo global do grafo
        self.grafo_direcionado = tk.BooleanVar(value=False)
        
        # Configurar interface
        self.criar_interface()
        
    def criar_interface(self):
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Painel esquerdo (botões) - maior largura
        left_panel = ttk.Frame(main_frame, relief=tk.RAISED, borderwidth=2, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)  # Impede que o painel seja redimensionado
        
        # Criar um canvas com scrollbar para o painel esquerdo
        left_canvas = tk.Canvas(left_panel, width=400, height=900)
        left_scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=left_canvas.yview)
        left_scrollable_frame = ttk.Frame(left_canvas)
        
        left_scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Configurar scroll com mouse
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")
        
        # Título do painel esquerdo
        ttk.Label(left_scrollable_frame, text="Controles", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Botão para carregar arquivo
        self.btn_carregar = ttk.Button(left_scrollable_frame, text="Carregar Arquivo", 
                                      command=self.carregar_arquivo, width=25)
        self.btn_carregar.pack(pady=5)
        
        # Frame para informações do arquivo
        info_frame = ttk.LabelFrame(left_scrollable_frame, text="Informações do Arquivo", padding=10)
        info_frame.pack(pady=10, fill=tk.X, padx=5)
        
        self.lbl_vertices = ttk.Label(info_frame, text="Vértices: 0")
        self.lbl_vertices.pack(anchor=tk.W)
        
        self.lbl_arestas = ttk.Label(info_frame, text="Arestas: 0")
        self.lbl_arestas.pack(anchor=tk.W)
        
        # Frame para seleção de vértices
        vertices_frame = ttk.LabelFrame(left_scrollable_frame, text="Seleção de Vértices", padding=10)
        vertices_frame.pack(pady=10, fill=tk.X, padx=5)
        
        # Instruções para seleção por clique
        ttk.Label(vertices_frame, text="Clique nos vértices do grafo para selecionar:", 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(vertices_frame, text="• Primeiro clique: Vértice de origem", 
                 font=("Arial", 8)).pack(anchor=tk.W)
        ttk.Label(vertices_frame, text="• Segundo clique: Vértice de destino", 
                 font=("Arial", 8)).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(vertices_frame, text="Ou use os comboboxes abaixo:").pack(anchor=tk.W, pady=(10, 0))
        
        ttk.Label(vertices_frame, text="Vértice de origem:").pack(anchor=tk.W, pady=(5, 0))
        self.origem_var = tk.StringVar()
        self.combo_origem = ttk.Combobox(vertices_frame, textvariable=self.origem_var, state="readonly")
        self.combo_origem.pack(fill=tk.X, pady=2)
        
        ttk.Label(vertices_frame, text="Vértice de destino:").pack(anchor=tk.W, pady=(10, 0))
        self.destino_var = tk.StringVar()
        self.combo_destino = ttk.Combobox(vertices_frame, textvariable=self.destino_var, state="readonly")
        self.combo_destino.pack(fill=tk.X, pady=2)
        
        # Labels para mostrar vértices selecionados
        self.lbl_origem_selecionada = ttk.Label(vertices_frame, text="Origem: Nenhuma", 
                                               font=("Arial", 9, "bold"), foreground="green")
        self.lbl_origem_selecionada.pack(anchor=tk.W, pady=(5, 0))
        
        self.lbl_destino_selecionado = ttk.Label(vertices_frame, text="Destino: Nenhum", 
                                                font=("Arial", 9, "bold"), foreground="red")
        self.lbl_destino_selecionado.pack(anchor=tk.W, pady=(2, 0))
        
        # Botão para calcular caminho
        self.btn_calcular = ttk.Button(left_scrollable_frame, text="Calcular Menor Caminho", 
                                      command=self.calcular_caminho, width=25, state="disabled")
        self.btn_calcular.pack(pady=10)
        
        # Botão para limpar caminho
        self.btn_limpar = ttk.Button(left_scrollable_frame, text="Limpar Caminho", 
                                    command=self.limpar_caminho, width=25, state="disabled")
        self.btn_limpar.pack(pady=5)
        
        # Botão para copiar imagem do grafo
        self.btn_copiar_imagem = ttk.Button(left_scrollable_frame, text="Copiar Imagem do Grafo", 
                                           command=self.copiar_imagem_grafo, width=25, state="disabled")
        self.btn_copiar_imagem.pack(pady=5)
        
        # Frame para resultados
        resultado_frame = ttk.LabelFrame(left_scrollable_frame, text="Resultado", padding=10)
        resultado_frame.pack(pady=10, fill=tk.X, padx=5)
        
        # Criar um frame com scrollbar para o caminho
        caminho_frame = ttk.Frame(resultado_frame)
        caminho_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(caminho_frame, text="Caminho:").pack(anchor=tk.W)
        
        # Text widget com scrollbar para o caminho
        self.text_caminho = tk.Text(caminho_frame, height=4, width=25, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(caminho_frame, orient="vertical", command=self.text_caminho.yview)
        self.text_caminho.configure(yscrollcommand=scrollbar.set)
        
        self.text_caminho.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configurar como somente leitura
        self.text_caminho.config(state=tk.DISABLED)
        
        # Frame para estatísticas
        estatisticas_frame = ttk.LabelFrame(left_scrollable_frame, text="Estatísticas de Execução", padding=10)
        estatisticas_frame.pack(pady=10, fill=tk.X, padx=5)
        
        self.lbl_tempo = ttk.Label(estatisticas_frame, text="Tempo: -")
        self.lbl_tempo.pack(anchor=tk.W)
        
        self.lbl_nos_explorados = ttk.Label(estatisticas_frame, text="Nós explorados: -")
        self.lbl_nos_explorados.pack(anchor=tk.W)
        
        self.lbl_custo_total = ttk.Label(estatisticas_frame, text="Custo total: -")
        self.lbl_custo_total.pack(anchor=tk.W)
        
        # Mover o checkbox do grafo direcionado para cá
        ttk.Checkbutton(estatisticas_frame, text="Grafo Direcionado", variable=self.grafo_direcionado, command=self.exibir_grafo).pack(anchor=tk.W, pady=(5, 2))
        
        # Frame para edição do grafo
        edicao_frame = ttk.LabelFrame(left_scrollable_frame, text="Edição do Grafo", padding=10)
        edicao_frame.pack(pady=10, fill=tk.X, padx=5)
        # Instruções
        ttk.Label(edicao_frame, text="Modifique o grafo usando os botões abaixo:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))
        # 1. Marcação do tipo de aresta
        self.tipo_aresta_var = tk.StringVar(value="mão dupla")
        tipo_frame = ttk.Frame(edicao_frame)
        tipo_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tipo_frame, text="Tipo de aresta:").pack(side=tk.LEFT)
        ttk.Radiobutton(tipo_frame, text="Mão dupla", variable=self.tipo_aresta_var, value="mão dupla").pack(side=tk.LEFT)
        ttk.Radiobutton(tipo_frame, text="Mão única", variable=self.tipo_aresta_var, value="mão única").pack(side=tk.LEFT)
        # 2 e 3. Botões de arestas (adicionar/remover) lado a lado
        aresta_frame = ttk.Frame(edicao_frame)
        aresta_frame.pack(fill=tk.X, pady=2)
        self.btn_adicionar_aresta = ttk.Button(aresta_frame, text="+ Aresta", command=lambda: self.definir_modo("adicionar_aresta"), width=12)
        self.btn_adicionar_aresta.pack(side=tk.LEFT, padx=2)
        self.btn_remover_aresta = ttk.Button(aresta_frame, text="- Aresta", command=lambda: self.definir_modo("remover_aresta"), width=12)
        self.btn_remover_aresta.pack(side=tk.LEFT, padx=2)
        # 4. Botões de vértices (adicionar/remover)
        vertice_frame = ttk.Frame(edicao_frame)
        vertice_frame.pack(fill=tk.X, pady=2)
        self.btn_adicionar_vertice = ttk.Button(vertice_frame, text="+ Vértice", command=lambda: self.definir_modo("adicionar_vertice"), width=12)
        self.btn_adicionar_vertice.pack(side=tk.LEFT, padx=2)
        self.btn_remover_vertice = ttk.Button(vertice_frame, text="- Vértice", command=lambda: self.definir_modo("remover_vertice"), width=12)
        self.btn_remover_vertice.pack(side=tk.LEFT, padx=2)
        # 5. Botão de navegação embaixo, ocupando o dobro da largura
        self.btn_navegacao = ttk.Button(edicao_frame, text="Navegação", command=lambda: self.definir_modo("navegacao"), width=26)
        self.btn_navegacao.pack(fill=tk.X, pady=(10, 2))
        # Label para mostrar modo atual
        self.lbl_modo_atual = ttk.Label(edicao_frame, text="Modo: Navegação", font=("Arial", 9, "bold"), foreground="blue")
        self.lbl_modo_atual.pack(anchor=tk.W, pady=(5, 0))
        
        # Frame para opções de visualização
        visualizacao_frame = ttk.LabelFrame(left_scrollable_frame, text="Opções de Visualização", padding=10)
        visualizacao_frame.pack(pady=10, fill=tk.X, padx=5)
        
        # Checkbox para mostrar numeração dos vértices
        self.mostrar_numeracao_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(visualizacao_frame, text="Mostrar numeração dos vértices", 
                       variable=self.mostrar_numeracao_var,
                       command=self.exibir_grafo).pack(anchor=tk.W, pady=2)
        
        # Checkbox para mostrar rótulos das arestas
        self.mostrar_rotulos_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(visualizacao_frame, text="Mostrar pesos das arestas", 
                       variable=self.mostrar_rotulos_var,
                       command=self.exibir_grafo).pack(anchor=tk.W, pady=2)
        
        # Separador
        ttk.Separator(visualizacao_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Controle de tamanho dos vértices
        ttk.Label(visualizacao_frame, text="Tamanho dos Vértices:", 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
        
        # Label para mostrar tamanho atual dos vértices
        self.lbl_tamanho = ttk.Label(visualizacao_frame, text=f"Tamanho: {self.tamanho_vertices}", 
                                    font=("Arial", 8))
        self.lbl_tamanho.pack(anchor=tk.W, pady=(0, 2))
        
        # Frame para botões de controle dos vértices
        botoes_tamanho_frame = ttk.Frame(visualizacao_frame)
        botoes_tamanho_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botão para diminuir tamanho dos vértices
        ttk.Button(botoes_tamanho_frame, text="Diminuir", 
                  command=self.diminuir_tamanho_vertices, width=8).pack(side=tk.LEFT, padx=(0, 5))
        
        # Botão para aumentar tamanho dos vértices
        ttk.Button(botoes_tamanho_frame, text="Aumentar", 
                  command=self.aumentar_tamanho_vertices, width=8).pack(side=tk.LEFT)
        
        # Controle de tamanho da fonte dos vértices
        ttk.Label(visualizacao_frame, text="Tamanho da Numeração dos Vértices:", 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
        
        # Label para mostrar tamanho atual da fonte dos vértices
        self.lbl_tamanho_fonte_vertices = ttk.Label(visualizacao_frame, text=f"Tamanho: {self.tamanho_fonte_vertices}", 
                                                   font=("Arial", 8))
        self.lbl_tamanho_fonte_vertices.pack(anchor=tk.W, pady=(0, 2))
        
        # Frame para botões de controle da fonte dos vértices
        botoes_fonte_vertices_frame = ttk.Frame(visualizacao_frame)
        botoes_fonte_vertices_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botão para diminuir tamanho da fonte dos vértices
        ttk.Button(botoes_fonte_vertices_frame, text="Diminuir", 
                  command=self.diminuir_tamanho_fonte_vertices, width=8).pack(side=tk.LEFT, padx=(0, 5))
        
        # Botão para aumentar tamanho da fonte dos vértices
        ttk.Button(botoes_fonte_vertices_frame, text="Aumentar", 
                  command=self.aumentar_tamanho_fonte_vertices, width=8).pack(side=tk.LEFT)
        
        # Controle de tamanho da fonte das arestas
        ttk.Label(visualizacao_frame, text="Tamanho dos Pesos das Arestas:", 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
        
        # Label para mostrar tamanho atual da fonte das arestas
        self.lbl_tamanho_fonte_arestas = ttk.Label(visualizacao_frame, text=f"Tamanho: {self.tamanho_fonte_arestas}", 
                                                  font=("Arial", 8))
        self.lbl_tamanho_fonte_arestas.pack(anchor=tk.W, pady=(0, 2))
        
        # Frame para botões de controle da fonte das arestas
        botoes_fonte_arestas_frame = ttk.Frame(visualizacao_frame)
        botoes_fonte_arestas_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Botão para diminuir tamanho da fonte das arestas
        ttk.Button(botoes_fonte_arestas_frame, text="Diminuir", 
                  command=self.diminuir_tamanho_fonte_arestas, width=8).pack(side=tk.LEFT, padx=(0, 5))
        
        # Botão para aumentar tamanho da fonte das arestas
        ttk.Button(botoes_fonte_arestas_frame, text="Aumentar", 
                  command=self.aumentar_tamanho_fonte_arestas, width=8).pack(side=tk.LEFT)
        
        # Painel direito (grafo)
        right_panel = ttk.Frame(main_frame, relief=tk.RAISED, borderwidth=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Título do painel direito
        ttk.Label(right_panel, text="Visualização do Grafo", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Frame para o canvas do matplotlib
        self.canvas_frame = ttk.Frame(right_panel)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Criar figura do matplotlib - maior
        self.fig, self.ax = plt.subplots(figsize=(16, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, self.canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Conectar evento de clique uma única vez
        print("Conectando evento de clique na inicialização...")
        self.canvas.mpl_connect('button_press_event', self.on_click)
        print("Evento de clique conectado na inicialização!")
        
        # Texto inicial
        self.ax.text(0.5, 0.5, "Carregue um arquivo .poly para visualizar o grafo", 
                    ha='center', va='center', transform=self.ax.transAxes, fontsize=12)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.canvas.draw()
        
    def carregar_arquivo(self):
        """Carrega o arquivo .poly ou .osm selecionado pelo usuário"""
        arquivo = filedialog.askopenfilename(
            title="Selecione um arquivo .poly ou .osm",
            filetypes=[("Arquivos .poly", "*.poly"), ("Arquivos .osm", "*.osm"), ("Todos os arquivos", "*.*")]
        )
        if arquivo:
            try:
                # Verificar se é arquivo .osm
                if arquivo.lower().endswith('.osm'):
                    print(f"Processando arquivo OSM: {arquivo}")
                    vertices_osm, arestas_osm = processar_arquivo_osm(arquivo)
                    self.vertices = []
                    self.arestas = []
                    for v in vertices_osm:
                        vertice = Vertices(id=v['id'], x=v['x'], y=v['y'])
                        self.vertices.append(vertice)
                    for a in arestas_osm:
                        aresta = Arestas(orig=a['orig'], dest=a['dest'], dist=a['dist'])
                        self.arestas.append(aresta)
                    self.totalVertices = len(self.vertices)
                    self.totalArestas = len(self.arestas)
                    # Desmarcar checkbox de grafo direcionado para arquivos OSM
                    self.grafo_direcionado.set(False)
                    self.construir_grafo()
                    self.arquivo_carregado = True
                    self.atualizar_interface()
                    self.exibir_grafo()
                    messagebox.showinfo("Sucesso", 
                        f"Arquivo OSM processado com sucesso!\n"
                        f"Vértices: {self.totalVertices}\n"
                        f"Arestas: {self.totalArestas}\n"
                        f"Coordenadas convertidas para UTM zona 23S\n"
                        f"Grafo configurado como não direcionado por padrão")
                else:
                    # Processar arquivo .poly normalmente
                    self.ler_arquivo(arquivo)
                    self.arquivo_carregado = True
                    self.atualizar_interface()
                    self.exibir_grafo()
                    messagebox.showinfo("Sucesso", f"Arquivo carregado com sucesso!\nVértices: {self.totalVertices}\nArestas: {self.totalArestas}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar arquivo: {str(e)}")
    
    def ler_arquivo(self, caminho_arquivo):
        """Lê o arquivo .poly e carrega os dados"""
        self.vertices = []
        self.arestas = []
        with open(caminho_arquivo, 'r') as arquivo:
            linhas = [linha.strip() for linha in arquivo.readlines()]
        self.totalVertices = int(linhas[0].split()[0])
        for i in range(1, self.totalVertices + 1):
            dados = linhas[i].split()
            vertice = Vertices(
                id=int(dados[0]),
                x=float(dados[1]),
                y=float(dados[2])
            )
            self.vertices.append(vertice)
        pos_arestas = self.totalVertices + 1
        self.totalArestas = int(linhas[pos_arestas].split()[0])
        for i in range(pos_arestas + 1, pos_arestas + self.totalArestas + 1):
            dados = linhas[i].split()
            aresta = Arestas(
                orig=int(dados[1]),
                dest=int(dados[2]),
                dist=float(dados[3]) if len(dados) > 3 else 0.0
            )
            self.arestas.append(aresta)
        self.construir_grafo()
    
    def construir_grafo(self):
        """Constrói a matriz de adjacência"""
        self.matrizAdj = [[INF for _ in range(self.totalVertices)] for _ in range(self.totalVertices)]
        for aresta in self.arestas:
            if aresta.orig < self.totalVertices and aresta.dest < self.totalVertices:
                dist = self.calc_dist(aresta.orig, aresta.dest)
                self.matrizAdj[aresta.orig][aresta.dest] = dist
                # Se o grafo não é direcionado, adicionar também no sentido contrário
                if not self.grafo_direcionado.get():
                    self.matrizAdj[aresta.dest][aresta.orig] = dist
    
    def calc_dist(self, v1_id, v2_id):
        """Calcula a distância entre dois vértices pelos seus IDs"""
        v1 = next((v for v in self.vertices if v.id == v1_id), None)
        v2 = next((v for v in self.vertices if v.id == v2_id), None)
        
        if v1 and v2:
            return math.sqrt((v1.x - v2.x)**2 + (v1.y - v2.y)**2)
        else:
            return INF
    
    def atualizar_interface(self):
        """Atualiza as informações na interface"""
        self.lbl_vertices.config(text=f"Vértices: {self.totalVertices}")
        self.lbl_arestas.config(text=f"Arestas: {self.totalArestas}")
        self.lbl_tamanho.config(text=f"Tamanho: {self.tamanho_vertices}")
        
        # Atualizar comboboxes
        opcoes = []
        if self.vertices:
            opcoes = [f"{v.id} ({v.x:.1f}, {v.y:.1f})" for v in self.vertices]
            self.combo_origem['values'] = opcoes
            self.combo_destino['values'] = opcoes
            
            # Habilitar botões
            self.btn_calcular.config(state="normal")
            self.btn_limpar.config(state="normal")
            self.btn_copiar_imagem.config(state="normal")
            
            # Habilitar botões de edição
            self.btn_adicionar_vertice.config(state="normal")
            self.btn_adicionar_aresta.config(state="normal")
            self.btn_remover_vertice.config(state="normal")
            self.btn_remover_aresta.config(state="normal")
        else:
            # Desabilitar botões
            self.btn_calcular.config(state="disabled")
            self.btn_limpar.config(state="disabled")
            self.btn_copiar_imagem.config(state="disabled")
            
            # Desabilitar botões de edição (exceto adicionar vértice)
            self.btn_adicionar_aresta.config(state="disabled")
            self.btn_remover_vertice.config(state="disabled")
            self.btn_remover_aresta.config(state="disabled")
        
        if opcoes:
            self.combo_origem.set(opcoes[0])
            self.combo_destino.set(opcoes[-1])
        
        # Exibir grafo inicial
        self.exibir_grafo()
    
    def get_normalized_positions(self):
        """Retorna um dicionário com as posições dos vértices normalizadas para [0, 1]"""
        if not self.vertices:
            return {}
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        def norm(val, minv, maxv):
            if maxv - minv == 0:
                return 0.5
            return (val - minv) / (maxv - minv)
        return {v.id: (norm(v.x, min_x, max_x), norm(v.y, min_y, max_y)) for v in self.vertices}

    def exibir_grafo(self, caminho=None):
        """Exibe o grafo no canvas"""
        print(f"Exibindo grafo - caminho: {caminho}")
        print(f"Caminho atual: {self.caminho_atual}")
        self.ax.clear()
        if not self.vertices:
            self.ax.text(0.5, 0.5, "Nenhum grafo carregado", 
                        ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return
        pos = self.get_normalized_positions()
        
        # Criar dois grafos: um para arestas bidirecionais e outro para unidirecionais
        G_bidirecional = nx.DiGraph()  # Mudança: usar DiGraph para poder desenhar setas nos dois sentidos
        G_unidirecional = nx.DiGraph()  # Para mão única (com setas)
        
        for v in self.vertices:
            G_bidirecional.add_node(v.id, pos=pos[v.id])
            G_unidirecional.add_node(v.id, pos=pos[v.id])
        
        # Separar arestas por tipo
        arestas_bidirecionais = []
        arestas_unidirecionais = []
        
        for aresta in self.arestas:
            if self.grafo_direcionado.get():
                # Se o grafo é direcionado, todas as arestas são unidirecionais
                arestas_unidirecionais.append(aresta)
            else:
                # Se o grafo não é direcionado, verificar o tipo da aresta
                if self.tipo_aresta_var.get() == "mão única":
                    arestas_unidirecionais.append(aresta)
                else:
                    arestas_bidirecionais.append(aresta)
        
        # Adicionar arestas aos grafos correspondentes
        for aresta in arestas_bidirecionais:
            # Para mão dupla, adicionar aresta nos dois sentidos
            G_bidirecional.add_edge(aresta.orig, aresta.dest)
            G_bidirecional.add_edge(aresta.dest, aresta.orig)
        
        for aresta in arestas_unidirecionais:
            G_unidirecional.add_edge(aresta.orig, aresta.dest)
        
        # Cores dos vértices (usar o mesmo para ambos os grafos)
        node_colors = []
        for node in G_bidirecional.nodes():
            if caminho:
                if node == caminho[0]:
                    node_colors.append('green')  # Origem
                elif node == caminho[-1]:
                    node_colors.append('red')    # Destino
                elif node in caminho:
                    node_colors.append('yellow') # Intermediário
                else:
                    node_colors.append('lightblue')
            else:
                if node == self.vertice_origem:
                    node_colors.append('green')
                elif node == self.vertice_destino:
                    node_colors.append('red')
                else:
                    node_colors.append('lightblue')
        
        # Cores das arestas
        caminho_arestas = self.criar_arestas_caminho(caminho) if caminho else []
        
        # Desenhar arestas bidirecionais (com setas nos dois sentidos)
        if len(arestas_bidirecionais) > 0:
            # Para arestas bidirecionais, usar Graph (sem setas) em vez de DiGraph
            G_bidirecional_sem_setas = nx.Graph()
            for v in self.vertices:
                G_bidirecional_sem_setas.add_node(v.id, pos=pos[v.id])
            for aresta in arestas_bidirecionais:
                G_bidirecional_sem_setas.add_edge(aresta.orig, aresta.dest)
            
            edge_colors_bidirecional = []
            edges_bidirecionais_list = list(G_bidirecional_sem_setas.edges())
            
            for edge in edges_bidirecionais_list:
                # Verificar se a aresta está no caminho (em qualquer direção)
                no_caminho = False
                if caminho:
                    for caminho_edge in caminho_arestas:
                        if (edge[0] == caminho_edge[0] and edge[1] == caminho_edge[1]) or \
                           (edge[0] == caminho_edge[1] and edge[1] == caminho_edge[0]):
                            no_caminho = True
                            break
                
                if no_caminho:
                    edge_colors_bidirecional.append('red')
                else:
                    edge_colors_bidirecional.append('black')  # Cor preta para mão dupla
            
            # Verificar se temos cores para todas as arestas
            if len(edge_colors_bidirecional) == len(edges_bidirecionais_list):
                nx.draw(G_bidirecional_sem_setas, pos, ax=self.ax,
                        node_color=node_colors,
                        edge_color=edge_colors_bidirecional,
                        with_labels=self.mostrar_numeracao_var.get(),
                        node_size=self.tamanho_vertices,
                        font_size=self.tamanho_fonte_vertices,
                        font_weight='bold',
                        width=1.5,  # Linha mais fina para mão dupla
                        arrows=False)  # Sem setas para arestas bidirecionais
        
        # Desenhar arestas unidirecionais (com setas)
        if len(arestas_unidirecionais) > 0:
            edge_colors_unidirecional = []
            edges_unidirecionais_list = list(G_unidirecional.edges())
            
            for edge in edges_unidirecionais_list:
                # Verificar se a aresta está no caminho
                no_caminho = False
                if caminho:
                    for caminho_edge in caminho_arestas:
                        if edge[0] == caminho_edge[0] and edge[1] == caminho_edge[1]:
                            no_caminho = True
                            break
                
                if no_caminho:
                    edge_colors_unidirecional.append('red')
                else:
                    edge_colors_unidirecional.append('black')
            
            # Verificar se temos cores para todas as arestas
            if len(edge_colors_unidirecional) == len(edges_unidirecionais_list):
                nx.draw(G_unidirecional, pos, ax=self.ax,
                        node_color=node_colors,
                        edge_color=edge_colors_unidirecional,
                        with_labels=False,  # Não desenhar labels duas vezes
                        node_size=self.tamanho_vertices,
                        font_size=self.tamanho_fonte_vertices,
                        font_weight='bold',
                        width=2,
                        arrows=True)  # Com setas para arestas unidirecionais
        
        # Adicionar rótulos das arestas se checkbox estiver marcado
        if self.mostrar_rotulos_var.get():
            edge_labels = {}
            for aresta in self.arestas:
                edge_labels[(aresta.orig, aresta.dest)] = f"{aresta.dist:.1f}"
                if not self.grafo_direcionado.get() and self.tipo_aresta_var.get() == "mão dupla":
                    edge_labels[(aresta.dest, aresta.orig)] = f"{aresta.dist:.1f}"
            nx.draw_networkx_edge_labels(G_bidirecional if len(arestas_bidirecionais) > 0 else G_unidirecional, 
                                        pos, edge_labels=edge_labels, font_size=self.tamanho_fonte_arestas)
        
        self.canvas.draw()
        self.canvas.flush_events()
        print("Grafo desenhado com sucesso")
    
    def criar_arestas_caminho(self, caminho):
        """Cria lista de arestas do caminho"""
        if not caminho or len(caminho) < 2:
            return []
        arestas = []
        for i in range(len(caminho) - 1):
            arestas.append((caminho[i], caminho[i + 1]))
        return arestas
    
    def calcular_caminho(self):
        """Calcula o menor caminho usando Dijkstra"""
        if not self.arquivo_carregado:
            messagebox.showwarning("Aviso", "Carregue um arquivo primeiro!")
            return
        
        # Verificar se há vértices selecionados por clique
        if self.vertice_origem is not None and self.vertice_destino is not None:
            origem_id = self.vertice_origem
            destino_id = self.vertice_destino
            print(f"Usando vértices selecionados por clique: {origem_id} -> {destino_id}")
        else:
            # Usar comboboxes como fallback
            origem_str = self.origem_var.get()
            destino_str = self.destino_var.get()
            
            if not origem_str or not destino_str:
                messagebox.showwarning("Aviso", "Selecione origem e destino!")
                return
            
            # Extrair IDs dos vértices
            origem_id = int(origem_str.split()[0])
            destino_id = int(destino_str.split()[0])
        
        print(f"Calculando caminho de {origem_id} para {destino_id}")
        
        # Executar Dijkstra
        caminho, distancia, estatisticas = self.dijkstra(origem_id, destino_id)
        
        print(f"Caminho encontrado: {caminho}")
        print(f"Distância: {distancia}")
        
        if caminho:
            self.caminho_atual = caminho
            print("Exibindo grafo com caminho...")
            
            # Atualizar resultados primeiro
            caminho_str = " → ".join(map(str, caminho))
            self.text_caminho.config(state=tk.NORMAL)
            self.text_caminho.delete(1.0, tk.END)
            self.text_caminho.insert(tk.END, caminho_str)
            self.text_caminho.config(state=tk.DISABLED)
            
            # Atualizar estatísticas
            self.lbl_tempo.config(text=f"Tempo: {estatisticas['tempo_ms']:.2f} ms")
            self.lbl_nos_explorados.config(text=f"Nós explorados: {estatisticas['nos_explorados']}")
            self.lbl_custo_total.config(text=f"Custo total: {estatisticas['custo_total']:.2f}")
            
            # Depois exibir o grafo com o caminho
            self.exibir_grafo(caminho)
            
            print("Grafo atualizado com sucesso!")
        else:
            messagebox.showinfo("Resultado", "Não há caminho entre os vértices selecionados!")
            
            # Atualizar estatísticas mesmo quando não há caminho
            self.lbl_tempo.config(text=f"Tempo: {estatisticas['tempo_ms']:.2f} ms")
            self.lbl_nos_explorados.config(text=f"Nós explorados: {estatisticas['nos_explorados']}")
            self.lbl_custo_total.config(text=f"Custo total: {estatisticas['custo_total']}")
    
    def dijkstra(self, inicio, fim):
        """Implementação do algoritmo de Dijkstra com estatísticas"""
        import time
        
        # Iniciar cronômetro
        tempo_inicio = time.time()
        
        dist = [INF] * self.totalVertices
        prev = [-1] * self.totalVertices
        visited = [False] * self.totalVertices
        
        dist[inicio] = 0
        nos_explorados = 0
        
        for _ in range(self.totalVertices):
            # Encontrar vértice não visitado com menor distância
            u = -1
            min_dist = INF
            for j in range(self.totalVertices):
                if not visited[j] and dist[j] < min_dist:
                    u = j
                    min_dist = dist[j]
            
            if u == -1:
                break
            
            visited[u] = True
            nos_explorados += 1
            
            # Atualizar distâncias dos vizinhos
            for v in range(self.totalVertices):
                if (self.matrizAdj[u][v] < INF and 
                    dist[u] + self.matrizAdj[u][v] < dist[v]):
                    dist[v] = dist[u] + self.matrizAdj[u][v]
                    prev[v] = u
        
        # Calcular tempo de processamento
        tempo_fim = time.time()
        tempo_processamento = (tempo_fim - tempo_inicio) * 1000  # Converter para milissegundos
        
        if dist[fim] == INF:
            return None, INF, {
                'tempo_ms': tempo_processamento,
                'nos_explorados': nos_explorados,
                'custo_total': INF
            }
        
        # Reconstruir caminho
        path = []
        v = fim
        while v != -1:
            path.append(v)
            v = prev[v]
        
        caminho_final = list(reversed(path))
        custo_total = dist[fim]
        
        estatisticas = {
            'tempo_ms': tempo_processamento,
            'nos_explorados': nos_explorados,
            'custo_total': custo_total
        }
        
        return caminho_final, custo_total, estatisticas
    
    def limpar_caminho(self):
        """Limpa o caminho atual e as seleções de vértices"""
        self.caminho_atual = []
        self.vertice_origem = None
        self.vertice_destino = None
        
        # Limpar labels
        self.lbl_origem_selecionada.config(text="Origem: Nenhuma")
        self.lbl_destino_selecionado.config(text="Destino: Nenhum")
        
        # Limpar comboboxes
        if self.vertices:
            self.origem_var.set("")
            self.destino_var.set("")
        
        self.exibir_grafo()
        self.text_caminho.config(state=tk.NORMAL)
        self.text_caminho.delete(1.0, tk.END)
        self.text_caminho.config(state=tk.DISABLED)
        
        # Limpar estatísticas
        self.lbl_tempo.config(text="Tempo: -")
        self.lbl_nos_explorados.config(text="Nós explorados: -")
        self.lbl_custo_total.config(text="Custo total: -")
    
    def on_click(self, event):
        print(f"Clique detectado: x={event.xdata}, y={event.ydata}")
        if event.inaxes != self.ax:
            print("Clique fora do gráfico")
            return
        
        x, y = event.xdata, event.ydata
        print(f"Coordenadas do clique: ({x}, {y})")
        
        # Verificar se há um arquivo carregado ou se estamos no modo de adicionar vértice
        if not self.arquivo_carregado and self.modo_edicao != "adicionar_vertice":
            print("Arquivo não carregado e não no modo de adicionar vértice")
            return
        
        # Lidar com diferentes modos de edição
        if self.modo_edicao == "navegacao":
            self.on_click_navegacao(x, y)
        elif self.modo_edicao == "adicionar_vertice":
            self.on_click_adicionar_vertice(x, y)
        elif self.modo_edicao == "adicionar_aresta":
            self.on_click_adicionar_aresta(x, y)
        elif self.modo_edicao == "remover_vertice":
            self.on_click_remover_vertice(x, y)
        elif self.modo_edicao == "remover_aresta":
            self.on_click_remover_aresta(x, y)
    
    def on_click_navegacao(self, x, y):
        """Manipula cliques no modo de navegação (seleção de origem/destino)"""
        if not self.arquivo_carregado:
            return
        
        # Normalizar coordenadas do clique
        pos = self.get_normalized_positions()
        if not pos:
            return
        xs = [vx for vx, vy in pos.values()]
        ys = [vy for vx, vy in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        def norm(val, minv, maxv):
            if maxv - minv == 0:
                return 0.5
            return (val - minv) / (maxv - minv)
        x_norm = norm(x, 0, 1)
        y_norm = norm(y, 0, 1)
            
        vertice_clicado = self.encontrar_vertice_proximo_normalizado(x_norm, y_norm)
        print(f"Vértice encontrado: {vertice_clicado}")
        if vertice_clicado is not None:
            self.selecionar_vertice(vertice_clicado)
        else:
            print("Nenhum vértice próximo encontrado")
    
    def on_click_adicionar_vertice(self, x, y):
        """Manipula cliques para adicionar vértices"""
        # Normalizar coordenadas do clique para o sistema de coordenadas dos vértices
        if self.vertices:
            # Encontrar os limites atuais dos vértices
            min_x = min(v.x for v in self.vertices)
            max_x = max(v.x for v in self.vertices)
            min_y = min(v.y for v in self.vertices)
            max_y = max(v.y for v in self.vertices)
            
            # Converter coordenadas do matplotlib para coordenadas reais dos vértices
            # O matplotlib pode estar usando um sistema de coordenadas diferente
            if max_x - min_x > 0:
                x_real = min_x + (max_x - min_x) * x
            else:
                x_real = x
                
            if max_y - min_y > 0:
                y_real = min_y + (max_y - min_y) * y
            else:
                y_real = y
        else:
            # Se não há vértices, usar coordenadas como estão
            x_real = x
            y_real = y
        
        print(f"Adicionando vértice em coordenadas reais: ({x_real:.2f}, {y_real:.2f})")
        self.adicionar_vertice(x_real, y_real)
    
    def on_click_adicionar_aresta(self, x, y):
        """Manipula cliques para adicionar arestas"""
        if not self.arquivo_carregado:
            return
        
        # Normalizar coordenadas do clique
        pos = self.get_normalized_positions()
        if not pos:
            return
        xs = [vx for vx, vy in pos.values()]
        ys = [vy for vx, vy in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        def norm(val, minv, maxv):
            if maxv - minv == 0:
                return 0.5
            return (val - minv) / (maxv - minv)
        x_norm = norm(x, 0, 1)
        y_norm = norm(y, 0, 1)
            
        vertice_clicado = self.encontrar_vertice_proximo_normalizado(x_norm, y_norm)
        if vertice_clicado is not None:
            if self.vertice_temporario is None:
                # Primeiro clique - selecionar primeiro vértice
                self.vertice_temporario = vertice_clicado
                print(f"Primeiro vértice selecionado: {vertice_clicado}")
                # Destacar o vértice temporariamente
                self.exibir_grafo()
            else:
                # Segundo clique - adicionar aresta
                if self.vertice_temporario != vertice_clicado:
                    self.adicionar_aresta(self.vertice_temporario, vertice_clicado)
                self.vertice_temporario = None
        else:
            print("Nenhum vértice próximo encontrado")
    
    def on_click_remover_vertice(self, x, y):
        """Manipula cliques para remover vértices"""
        if not self.arquivo_carregado:
            return
        # Normalizar coordenadas do clique
        pos = self.get_normalized_positions()
        if not pos:
            return
        xs = [vx for vx, vy in pos.values()]
        ys = [vy for vx, vy in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        def norm(val, minv, maxv):
            if maxv - minv == 0:
                return 0.5
            return (val - minv) / (maxv - minv)
        x_norm = norm(x, 0, 1)
        y_norm = norm(y, 0, 1)
        vertice_clicado = self.encontrar_vertice_proximo_normalizado(x_norm, y_norm)
        if vertice_clicado is not None:
            resposta = messagebox.askyesno("Confirmar", f"Deseja remover o vértice {vertice_clicado}?")
            if resposta:
                self.remover_vertice(vertice_clicado)
        else:
            print("Nenhum vértice próximo encontrado")
    
    def on_click_remover_aresta(self, x, y):
        """Manipula cliques para remover arestas"""
        if not self.arquivo_carregado:
            return
        # Normalizar coordenadas do clique
        pos = self.get_normalized_positions()
        if not pos:
            return
        xs = [vx for vx, vy in pos.values()]
        ys = [vy for vx, vy in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        def norm(val, minv, maxv):
            if maxv - minv == 0:
                return 0.5
            return (val - minv) / (maxv - minv)
        x_norm = norm(x, 0, 1)
        y_norm = norm(y, 0, 1)
        aresta_proxima = self.encontrar_aresta_proxima(x_norm, y_norm)
        if aresta_proxima:
            resposta = messagebox.askyesno("Confirmar", 
                                         f"Deseja remover a aresta {aresta_proxima[0]} - {aresta_proxima[1]}?")
            if resposta:
                self.remover_aresta(aresta_proxima[0], aresta_proxima[1])
        else:
            print("Nenhuma aresta próxima encontrada")
    
    def encontrar_aresta_proxima(self, x, y, raio=0.05):
        """Encontra a aresta mais próxima das coordenadas do clique"""
        if not self.arestas:
            return None
            
        pos = self.get_normalized_positions()
        aresta_mais_proxima = None
        menor_distancia = float('inf')
        
        for aresta in self.arestas:
            # Obter posições dos vértices da aresta
            v1_pos = pos.get(aresta.orig)
            v2_pos = pos.get(aresta.dest)
            
            if v1_pos and v2_pos:
                # Calcular ponto médio da aresta
                meio_x = (v1_pos[0] + v2_pos[0]) / 2
                meio_y = (v1_pos[1] + v2_pos[1]) / 2
                
                # Calcular distância do clique ao ponto médio
                distancia = math.sqrt((x - meio_x)**2 + (y - meio_y)**2)
                
                if distancia < menor_distancia and distancia < raio:
                    menor_distancia = distancia
                    aresta_mais_proxima = (aresta.orig, aresta.dest)
        
        return aresta_mais_proxima
    
    def encontrar_vertice_proximo_normalizado(self, x, y, raio=0.05):
        """Encontra o vértice mais próximo das coordenadas do clique, usando posições normalizadas"""
        pos = self.get_normalized_positions()
        vertice_mais_proximo = None
        menor_distancia = float('inf')
        for vid, (vx, vy) in pos.items():
            distancia = math.sqrt((x - vx)**2 + (y - vy)**2)
            print(f"Vértice {vid} em ({vx}, {vy}) - distância: {distancia}")
            if distancia < menor_distancia and distancia < raio:
                menor_distancia = distancia
                vertice_mais_proximo = vid
                print(f"Novo vértice mais próximo: {vertice_mais_proximo} (distância: {distancia})")
        return vertice_mais_proximo
    
    def selecionar_vertice(self, vertice_id):
        """Seleciona um vértice como origem ou destino"""
        print(f"Selecionando vértice: {vertice_id}")
        
        if self.vertice_origem is None:
            # Primeiro clique - selecionar origem
            self.vertice_origem = vertice_id
            self.lbl_origem_selecionada.config(text=f"Origem: {vertice_id}")
            
            # Atualizar combobox
            for i, vertice in enumerate(self.vertices):
                if vertice.id == vertice_id:
                    self.origem_var.set(f"{vertice.id} ({vertice.x:.1f}, {vertice.y:.1f})")
                    break
            
            print(f"Vértice {vertice_id} selecionado como origem")
            
        elif self.vertice_destino is None and vertice_id != self.vertice_origem:
            # Segundo clique - selecionar destino
            self.vertice_destino = vertice_id
            self.lbl_destino_selecionado.config(text=f"Destino: {vertice_id}")
            
            # Atualizar combobox
            for i, vertice in enumerate(self.vertices):
                if vertice.id == vertice_id:
                    self.destino_var.set(f"{vertice.id} ({vertice.x:.1f}, {vertice.y:.1f})")
                    break
            
            print(f"Vértice {vertice_id} selecionado como destino")
            
            # Pequeno delay para evitar conflitos
            self.root.after(100, self.calcular_caminho_automatico)
            
        else:
            # Resetar seleção - novo vértice vira origem
            self.vertice_origem = vertice_id
            self.vertice_destino = None
            self.lbl_origem_selecionada.config(text=f"Origem: {vertice_id}")
            self.lbl_destino_selecionado.config(text="Destino: Nenhum")
            
            # Limpar caminho anterior
            self.caminho_atual = []
            self.text_caminho.config(state=tk.NORMAL)
            self.text_caminho.delete(1.0, tk.END)
            self.text_caminho.config(state=tk.DISABLED)
            
            # Atualizar combobox
            for i, vertice in enumerate(self.vertices):
                if vertice.id == vertice_id:
                    self.origem_var.set(f"{vertice.id} ({vertice.x:.1f}, {vertice.y:.1f})")
                    break
            
            print(f"Nova origem selecionada: {vertice_id}")
            
            # Atualizar visualização sem caminho
            self.exibir_grafo()
    
    def calcular_caminho_automatico(self):
        """Função separada para calcular caminho automaticamente"""
        print("Calculando caminho automaticamente...")
        self.calcular_caminho()
    
    def definir_modo(self, modo):
        """Define o modo de edição atual"""
        self.modo_edicao = modo
        self.vertice_temporario = None
        
        # Atualizar label do modo
        modos_nomes = {
            "navegacao": "Navegação",
            "adicionar_vertice": "Adicionar Vértice",
            "adicionar_aresta": "Adicionar Aresta",
            "remover_vertice": "Remover Vértice",
            "remover_aresta": "Remover Aresta"
        }
        self.lbl_modo_atual.config(text=f"Modo: {modos_nomes[modo]}")
        
        # Atualizar cores dos botões
        for btn in [self.btn_navegacao, self.btn_adicionar_vertice, self.btn_adicionar_aresta, 
                   self.btn_remover_vertice, self.btn_remover_aresta]:
            btn.config(style='TButton')
        
        # Destacar botão ativo
        if modo == "navegacao":
            self.btn_navegacao.config(style='Accent.TButton')
        elif modo == "adicionar_vertice":
            self.btn_adicionar_vertice.config(style='Accent.TButton')
        elif modo == "adicionar_aresta":
            self.btn_adicionar_aresta.config(style='Accent.TButton')
        elif modo == "remover_vertice":
            self.btn_remover_vertice.config(style='Accent.TButton')
        elif modo == "remover_aresta":
            self.btn_remover_aresta.config(style='Accent.TButton')
        
        print(f"Modo alterado para: {modo}")
    
    def adicionar_vertice(self, x, y):
        """Adiciona um novo vértice na posição especificada"""
        # Encontrar próximo ID disponível
        if self.vertices:
            self.proximo_id_vertice = max(v.id for v in self.vertices) + 1
        else:
            self.proximo_id_vertice = 0
        
        # Criar novo vértice
        novo_vertice = Vertices(self.proximo_id_vertice, x, y)
        self.vertices.append(novo_vertice)
        self.totalVertices += 1
        
        # Marcar como arquivo carregado se for o primeiro vértice
        if not self.arquivo_carregado:
            self.arquivo_carregado = True
        
        # Atualizar matriz de adjacência
        for linha in self.matrizAdj:
            linha.append(INF)
        self.matrizAdj.append([INF] * self.totalVertices)
        self.matrizAdj[self.proximo_id_vertice][self.proximo_id_vertice] = 0
        
        print(f"Vértice {self.proximo_id_vertice} adicionado em ({x:.2f}, {y:.2f})")
        self.atualizar_interface()
        self.exibir_grafo()
    
    def remover_vertice(self, vertice_id):
        """Remove um vértice e suas arestas"""
        if vertice_id >= len(self.vertices):
            return
        
        # Remover vértice da lista
        self.vertices = [v for v in self.vertices if v.id != vertice_id]
        self.totalVertices -= 1
        
        # Remover arestas relacionadas
        self.arestas = [a for a in self.arestas if a.orig != vertice_id and a.dest != vertice_id]
        
        # Reconstruir matriz de adjacência
        self.construir_grafo()
        
        print(f"Vértice {vertice_id} removido")
        self.atualizar_interface()
        self.exibir_grafo()
    
    def adicionar_aresta(self, vertice1_id, vertice2_id):
        """Adiciona uma aresta entre dois vértices"""
        if vertice1_id == vertice2_id:
            return
        v1 = next((v for v in self.vertices if v.id == vertice1_id), None)
        v2 = next((v for v in self.vertices if v.id == vertice2_id), None)
        if v1 and v2:
            distancia = self.calc_dist(v1.id, v2.id)
            # O tipo de aresta depende apenas do tipo global do grafo
            direcionada = self.grafo_direcionado.get() or self.tipo_aresta_var.get() == "mão única"
            # Verificar se a aresta já existe
            aresta_existente = next((a for a in self.arestas 
                                   if (a.orig == vertice1_id and a.dest == vertice2_id) or
                                      (a.orig == vertice2_id and a.dest == vertice1_id and not direcionada)), None)
            if not aresta_existente:
                nova_aresta = Arestas(vertice1_id, vertice2_id, distancia)
                self.arestas.append(nova_aresta)
                self.totalArestas += 1
                # Atualizar matriz de adjacência
                self.matrizAdj[vertice1_id][vertice2_id] = distancia
                if not direcionada:
                    self.matrizAdj[vertice2_id][vertice1_id] = distancia
                print(f"Aresta adicionada: {vertice1_id} - {vertice2_id} (distância: {distancia:.2f}, {'direcionada' if direcionada else 'não direcionada'})")
                self.atualizar_interface()
                self.exibir_grafo()
            else:
                print("Aresta já existe!")
        else:
            print(f"Vértices {vertice1_id} ou {vertice2_id} não encontrados!")
    
    def remover_aresta(self, vertice1_id, vertice2_id):
        """Remove uma aresta entre dois vértices"""
        # Encontrar e remover aresta
        aresta_para_remover = next((a for a in self.arestas 
                                   if (a.orig == vertice1_id and a.dest == vertice2_id) or
                                      (a.orig == vertice2_id and a.dest == vertice1_id)), None)
        
        if aresta_para_remover:
            self.arestas.remove(aresta_para_remover)
            self.totalArestas -= 1
            
            # Atualizar matriz de adjacência
            self.matrizAdj[vertice1_id][vertice2_id] = INF
            self.matrizAdj[vertice2_id][vertice1_id] = INF
            
            print(f"Aresta removida: {vertice1_id} - {vertice2_id}")
            self.exibir_grafo()
        else:
            print("Aresta não encontrada!")
    
    def copiar_imagem_grafo(self):
        """Função para copiar a imagem do grafo para o clipboard"""
        try:
            # Salvar a figura atual em um buffer de bytes
            buf = io.BytesIO()
            self.fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            
            # Criar uma imagem PIL
            image = Image.open(buf)
            
            # Converter para formato compatível com clipboard
            # Primeiro converter para RGB se necessário
            if image.mode in ('RGBA', 'LA'):
                # Criar fundo branco
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Salvar temporariamente em um arquivo
            temp_path = "temp_grafo.png"
            image.save(temp_path, "PNG")
            
            # Usar comando do sistema para copiar para clipboard
            import subprocess
            try:
                # Tentar usar PowerShell para copiar imagem
                ps_command = f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile("{temp_path}"))'
                subprocess.run(['powershell', '-Command', ps_command], check=True, capture_output=True)
                
                # Remover arquivo temporário
                os.remove(temp_path)
                
                messagebox.showinfo("Sucesso", "Imagem do grafo copiada para a área de transferência!")
                
            except subprocess.CalledProcessError:
                # Fallback: tentar usar xclip no Linux ou pbcopy no Mac
                try:
                    if os.name == 'posix':  # Linux/Mac
                        if os.system('which xclip') == 0:
                            subprocess.run(['xclip', '-selection', 'clipboard', '-t', 'image/png', '-i', temp_path])
                        elif os.system('which pbcopy') == 0:
                            subprocess.run(['pbcopy'], input=open(temp_path, 'rb').read())
                    os.remove(temp_path)
                    messagebox.showinfo("Sucesso", "Imagem do grafo copiada para a área de transferência!")
                except:
                    os.remove(temp_path)
                    messagebox.showerror("Erro", "Não foi possível copiar a imagem. Tente salvar manualmente.")
                    
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao copiar imagem: {str(e)}")
            print(f"Erro ao copiar imagem: {e}")

    def diminuir_tamanho_vertices(self):
        """Diminui o tamanho dos vértices conforme as regras especificadas"""
        if self.tamanho_vertices > 50:
            decremento = 10
        elif self.tamanho_vertices > 10:
            decremento = 5
        elif self.tamanho_vertices > 0:
            decremento = 1
        else:
            decremento = 0

        novo_tamanho = self.tamanho_vertices - decremento
        if novo_tamanho < 0:
            novo_tamanho = 0
        self.tamanho_vertices = novo_tamanho
        self.lbl_tamanho.config(text=f"Tamanho: {self.tamanho_vertices}")
        self.exibir_grafo()

    def aumentar_tamanho_vertices(self):
        """Aumenta o tamanho dos vértices conforme as regras especificadas, até o máximo de 100"""
        if self.tamanho_vertices < 10:
            incremento = 1
        elif self.tamanho_vertices < 50:
            incremento = 5
        else:
            incremento = 10

        novo_tamanho = self.tamanho_vertices + incremento
        if novo_tamanho > 100:
            novo_tamanho = 100
        self.tamanho_vertices = novo_tamanho
        self.lbl_tamanho.config(text=f"Tamanho: {self.tamanho_vertices}")
        self.exibir_grafo()

    # NOVO: Funções para controlar tamanho da fonte dos vértices
    def diminuir_tamanho_fonte_vertices(self):
        """Diminui o tamanho da fonte dos vértices"""
        if self.tamanho_fonte_vertices > 1:
            self.tamanho_fonte_vertices -= 1
            self.lbl_tamanho_fonte_vertices.config(text=f"Tamanho: {self.tamanho_fonte_vertices}")
            self.exibir_grafo()

    def aumentar_tamanho_fonte_vertices(self):
        """Aumenta o tamanho da fonte dos vértices"""
        if self.tamanho_fonte_vertices < 20:
            self.tamanho_fonte_vertices += 1
            self.lbl_tamanho_fonte_vertices.config(text=f"Tamanho: {self.tamanho_fonte_vertices}")
            self.exibir_grafo()

    # NOVO: Funções para controlar tamanho da fonte das arestas
    def diminuir_tamanho_fonte_arestas(self):
        """Diminui o tamanho da fonte das arestas"""
        if self.tamanho_fonte_arestas > 1:
            self.tamanho_fonte_arestas -= 1
            self.lbl_tamanho_fonte_arestas.config(text=f"Tamanho: {self.tamanho_fonte_arestas}")
            self.exibir_grafo()

    def aumentar_tamanho_fonte_arestas(self):
        """Aumenta o tamanho da fonte das arestas"""
        if self.tamanho_fonte_arestas < 20:
            self.tamanho_fonte_arestas += 1
            self.lbl_tamanho_fonte_arestas.config(text=f"Tamanho: {self.tamanho_fonte_arestas}")
            self.exibir_grafo()

def main():
    root = tk.Tk()
    app = InterfaceDijkstra(root)
    root.mainloop()

if __name__ == "__main__":
    main()
