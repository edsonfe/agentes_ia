from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization import Slider
from planet_model import PlanetaModelo
from mesa.visualization.modules import ChartModule
from objetos import Recurso, BaseInicial, Estrutura
from agentes import (
    AgenteReativoSimples,
    AgenteBaseadoEmEstado,
    AgenteBaseadoEmObjetivos,
    AgenteCooperativo,
    AgenteBDI
)

def agent_portrayal(agent):
    """Define a aparência dos objetos e agentes no grid."""
    if isinstance(agent, BaseInicial):
        return {"Shape": "circle", "Filled": "true", "Color": "black", "Layer": 1, "r": 0.9}
    elif isinstance(agent, Recurso):
        color_map = {"Cristal": "lightblue", "Metal": "grey", "Estrutura": "orange"}
        size_map = {"Cristal": 0.3, "Metal": 0.6, "Estrutura": 0.8}
        if agent.tipo in color_map and agent.tipo in size_map:
            return {
                "Shape": "rect",
                "Filled": "true",
                "Color": color_map[agent.tipo],
                "Layer": 2,
                "w": size_map[agent.tipo],
                "h": size_map[agent.tipo]
            }
        else:
            return {
                "Shape": "rect",
                "Filled": "true",
                "Color": "gray",
                "Layer": 2,
                "w": 0.5,
                "h": 0.5
            }
    elif isinstance(agent, Estrutura):
        return {"Shape": "rect", "Filled": "true", "Color": "orange", "Layer": 3, "w": 0.9, "h": 0.9}
    elif isinstance(agent, AgenteReativoSimples):
        return {"Shape": "circle", "Filled": "true", "Color": "red", "Layer": 4, "r": 0.3}
    elif isinstance(agent, AgenteBaseadoEmEstado):
        return {"Shape": "circle", "Filled": "true", "Color": "green", "Layer": 5, "r": 0.6}
    elif isinstance(agent, AgenteBaseadoEmObjetivos):
        return {"Shape": "circle", "Filled": "true", "Color": "blue", "Layer": 6, "r": 0.6}
    elif isinstance(agent, AgenteCooperativo):
        return {"Shape": "circle", "Filled": "true", "Color": "purple", "Layer": 7, "r": 0.6}
    elif isinstance(agent, AgenteBDI):
        return {"Shape": "circle", "Filled": "true", "Color": "yellow", "Layer": 8, "r": 0.9}
    return {"Shape": "circle", "Filled": "true", "Color": "gray", "Layer": 2, "r": 0.3}

def create_server():

    chart = ChartModule([
        {"Label": "AgenteReativoSimples", "Color": "red"},
        {"Label": "AgenteBaseadoEmEstado", "Color": "green"},
        {"Label": "AgenteBaseadoEmObjetivos", "Color": "blue"},
        {"Label": "AgenteCooperativo", "Color": "purple"},
    ], data_collector_name='datacollector')

    # Parâmetros configuráveis com sliders
    model_params = {
        "width": Slider("Largura do Grid", 20, 10, 20, 1),
        "height": Slider("Altura do Grid", 20, 10, 20, 1),
        "num_crystals": Slider("Número de Cristais", 30, 5, 50, 1),
        "num_metals": Slider("Número de Blocos de Metal", 15, 5, 30, 1),
        "num_structures": Slider("Número de Estruturas Antigas", 2, 1, 10, 1),
        "num_agentes_reativos": Slider("Agentes Reativos", 1, 0, 10, 1),
        "num_agentes_estado": Slider("Agentes com Estado", 1, 0, 10, 1),
        "num_agentes_objetivos": Slider("Agentes com Objetivos", 1, 0, 10, 1),
        "num_agentes_cooperativos": Slider("Agentes Cooperativos", 1, 0, 10, 1),
    }

    # Tamanho padrão do grid na visualização (não depende do slider)
    grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)

    server = ModularServer(
        PlanetaModelo,
        [grid, chart],
        "Simulação de Planeta",
        model_params
    )
    server.port = 8521
    return server

server = create_server()

if __name__ == "__main__":
    server.launch()
