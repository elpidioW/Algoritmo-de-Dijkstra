# Algoritmo de Dijkstra - Interface Gráfica

Este projeto implementa uma interface gráfica para o algoritmo de Dijkstra usando Python, tkinter e matplotlib. A interface permite carregar grafos de arquivos, visualizá-los graficamente e calcular caminhos mínimos entre vértices.

## Funcionalidades

### Carregamento e Visualização
- Carregar grafos de arquivos `.poly` e `.osm`
- Conversão automática de coordenadas geográficas (OSM) para UTM
- Visualização gráfica interativa dos grafos
- Suporte a grafos ponderados e não ponderados
- Suporte a grafos direcionados e não direcionados (vias de mão única e mão dupla)

### Edição de Grafos
- Adicionar novos vértices clicando no canvas
- Adicionar arestas entre vértices
- Remover vértices e arestas
- Seleção de tipo de aresta (mão única/mão dupla)

### Cálculo de Caminhos
- Seleção de vértices origem e destino clicando no grafo
- Cálculo automático do caminho mínimo usando Dijkstra
- Visualização do caminho encontrado
- Estatísticas da execução (tempo, distância total, número de vértices visitados)

### Interface
- Painel esquerdo com controles e informações
- Painel direito com visualização do grafo
- Botão para copiar imagem do grafo
- **Opções de visualização**: Mostrar/ocultar numeração de vértices e rótulos de arestas
- **Controle de tamanho**: Ajustar tamanho dos vértices dinamicamente

## Tipos de Grafos Suportados

### Grafo Não Direcionado (Mão Dupla)
- Arestas bidirecionais
- Permite tráfego em ambas as direções
- Representado por linhas simples

### Grafo Direcionado (Mão Única)
- Arestas unidirecionais
- Permite tráfego apenas em uma direção
- Representado por setas indicando a direção

## Formato dos Arquivos

### Arquivos .poly
Os arquivos `.poly` devem seguir o formato:

```
# Vértices: V id x y
V 0 100 100
V 1 200 100
V 2 300 100

# Arestas: E orig dest dist direcionada
E 0 1 50.0 False   # Mão dupla
E 1 2 60.0 True    # Mão única
```

### Arquivos .osm
Arquivos OpenStreetMap (OSM) são processados automaticamente:

- **Nós**: Pontos com coordenadas geográficas (latitude/longitude)
- **Vias**: Sequências de nós que formam ruas/caminhos
- **Conversão**: Coordenadas geográficas são convertidas para UTM zona 23S
- **Escala**: Coordenadas são reduzidas e normalizadas para visualização

#### Exemplo de arquivo OSM:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="-23.5450" lon="-46.6350"/>
  <node id="2" lat="-23.5450" lon="-46.6355"/>
  <way id="1">
    <nd ref="1"/>
    <nd ref="2"/>
  </way>
</osm>
```

### Campos das Arestas
- `orig`: ID do vértice de origem
- `dest`: ID do vértice de destino
- `dist`: Distância/peso da aresta
- `direcionada`: `True` para mão única, `False` para mão dupla

## Como Usar

1. **Carregar um Grafo**: Use o botão "Carregar Arquivo" para abrir um arquivo `.poly`
2. **Selecionar Tipo de Aresta**: Escolha entre "Mão Dupla" ou "Mão Única" antes de adicionar arestas
3. **Editar o Grafo**: Use os botões de edição para adicionar/remover vértices e arestas
4. **Calcular Caminho**: Clique em dois vértices para selecionar origem e destino
5. **Visualizar Resultado**: O caminho mínimo será destacado em vermelho

## Opções de Visualização

### Controle de Tamanho dos Vértices
- **Botão "Diminuir"**: Reduz o tamanho dos vértices em 10 pixels
- **Botão "Aumentar"**: Aumenta o tamanho dos vértices em 10 pixels
- **Tamanho mínimo**: 10 pixels (com aviso quando atingido)

### Numeração dos Vértices
- **Checkbox "Mostrar numeração dos vértices"**: Ativa/desativa a exibição dos IDs dos vértices
- **Útil para**: Identificar vértices específicos e referenciar posições

### Rótulos das Arestas
- **Checkbox "Mostrar pesos das arestas"**: Ativa/desativa a exibição das distâncias nas arestas
- **Formato**: Distâncias mostradas com uma casa decimal (ex: "50.0")
- **Útil para**: Visualizar os pesos/pesos das conexões entre vértices

## Exemplos

- `exemplo_com_pesos.poly`: Grafo com pesos nas arestas para demonstrar rótulos
- `exemplo_grafo_direcionado.poly`: Grafo com vias de mão única e mão dupla
- `exemplo.osm`: Arquivo OSM de exemplo com coordenadas de São Paulo

## Dependências

- Python 3.x
- tkinter (incluído com Python)
- matplotlib
- networkx
- numpy

## Instalação

```bash
pip install matplotlib networkx numpy
```

## Execução

```bash
python interface_dijkstra.py
```

## Arquivos Incluídos

- `interface_dijkstra.py` - Interface principal
- `exemplo_grafo_direcionado.poly` - Exemplo de grafo com vias direcionadas
- `exemplo_com_pesos.poly` - Exemplo de grafo com pesos nas arestas
- `map.poly` - Arquivo de exemplo original
- `dijkstra.py` - Implementação do algoritmo
- `exibir_grafo.py` - Funções de visualização

## Características Técnicas

- **Interface Responsiva**: Painel esquerdo com controles, painel direito com visualização
- **Detecção de Cliques**: Sistema preciso de detecção de cliques nos vértices e arestas
- **Normalização de Coordenadas**: Suporte a grafos com coordenadas em diferentes escalas
- **Estatísticas Detalhadas**: Tempo de processamento, nós explorados, custo total
- **Exportação**: Salvar grafos modificados e copiar imagens

## Aplicações

- **Planejamento Urbano**: Análise de redes de transporte
- **Navegação**: Cálculo de rotas otimizadas
- **Logística**: Otimização de rotas de entrega
- **Educação**: Visualização de algoritmos de grafos

## Autores

Desenvolvido para o trabalho final de AED2 - 2025.1
