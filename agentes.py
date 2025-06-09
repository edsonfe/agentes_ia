from mesa import Agent
from objetos import Recurso, Estrutura
import math
import random


class AgenteReativoSimples(Agent):

    def __init__(self, unique_id, model, base_pos):
        super().__init__(unique_id, model)
        self.base_pos = base_pos
        self.recurso_atual = None  # agente está transportando um recurso
        self.pontuacao = 0
       

    def step(self):
        if self.recurso_atual:
            self.mover_para_base()
        else:
            self.explorar_ambiente()

    def explorar_ambiente(self):
      """ Move aleatoriamente pelo ambiente e coleta recursos leves (ignorando estruturas). """
      vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
      vizinhos_livres = [pos for pos in vizinhos if not any(isinstance(obj, Estrutura) for obj in self.model.grid.get_cell_list_contents(pos))]

      if vizinhos_livres:
          nova_pos = self.random.choice(vizinhos_livres)
          self.model.grid.move_agent(self, nova_pos)

          # Verifica se há um recurso leve na nova posição e inicia transporte
          for objeto in self.model.grid.get_cell_list_contents(nova_pos):
              if isinstance(objeto, Recurso) and objeto.tipo in ["Cristal", "Metal"] and not objeto.transportado:
                  self.recurso_atual = objeto
                  objeto.transportado = True  # Marca o recurso como coletado
                  self.model.grid.remove_agent(objeto)  # Remove o recurso do grid
                  return  # Fim do passo
      else:
          print(f"Agente {self.unique_id} não encontrou um caminho livre, tentando novamente.")

    def mover_para_base(self):
        """ Move o agente em direção à base para entregar o recurso coletado. """
        if self.pos != self.base_pos:
            self.mover_em_direcao(self.base_pos)
        else:
            # Entrega o recurso na base e reinicia a exploração
            if self.recurso_atual:
                self.model.base.registrar_recurso(self.recurso_atual)
    
                self.pontuacao += self.recurso_atual.utilidade
                print(f"Agente {self.unique_id} entregou {self.recurso_atual.tipo}, pontuação: {self.pontuacao}")

                self.recurso_atual = None

            self.recurso_atual = None
            self.explorar_ambiente()

    def mover_em_direcao(self, destino):
        """ Move um passo na direção do destino. """
        dx, dy = destino[0] - self.pos[0], destino[1] - self.pos[1]
        nova_pos = (self.pos[0] + (1 if dx > 0 else -1 if dx < 0 else 0),
                    self.pos[1] + (1 if dy > 0 else -1 if dy < 0 else 0))

        if not self.model.grid.out_of_bounds(nova_pos):
            self.model.grid.move_agent(self, nova_pos)
 

#------------------------------------------------------------------------
    
class AgenteBaseadoEmEstado(Agent):
    """ Agente que reconhece o ambiente, registra informações e coleta recursos de forma estratégica. """

    def __init__(self, unique_id, model, base_pos):
        super().__init__(unique_id, model)
        self.base_pos = base_pos
        self.recurso_atual = None
        self.historico_movimento = set()
        self.registros_locais = []  # Armazena informações sobre recursos e estruturas
        self.estado = "explorando"
        self.destino_atual = None
        self.objetivo_atual = "explorar"
        self.pontuacao = 0
                
 
    def step(self):
        """ Executa ações estratégicas conforme o estado do agente. """
        if self.recurso_atual:
            self.objetivo_atual = "transportar"

        if self.objetivo_atual == "transportar":
            self.mover_para_base()
        elif self.objetivo_atual == "buscar_recurso":
            if self.destino_atual:
                self.mover_em_direcao(self.destino_atual)
            else:
                self.destino_atual = None
                self.explorar_ambiente()
        elif self.objetivo_atual == "coletar":
            self.tentar_coletar_recurso()
        else:
            self.explorar_ambiente()

    def mover_para_base(self):
        """ Move para a base para entregar o recurso e define um novo objetivo. """
        if self.pos != self.base_pos:
            self.mover_em_direcao(self.base_pos)
        else:
            if isinstance(self.recurso_atual, Recurso):
                self.model.base.registrar_recurso(self.recurso_atual)
                self.pontuacao += self.recurso_atual.utilidade
                print(f"Agente {self.unique_id} entregou {self.recurso_atual.tipo}, pontuação: {self.pontuacao}")
                self.recurso_atual = None

            self.recurso_atual = None
            self.model.agente_bdi.receber_informacoes(self)

            destino_bdi = self.model.agente_bdi.intentions.get(self.unique_id, None)
            self.destino_atual = destino_bdi if destino_bdi else None

    def explorar_ambiente(self):
        """ Explora e registra informações sobre recursos e estruturas. """
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        vizinhos_nao_visitados = [pos for pos in vizinhos if pos not in self.historico_movimento]

        melhor_pos = random.choice(vizinhos_nao_visitados) if vizinhos_nao_visitados else random.choice(vizinhos)
        self.model.grid.move_agent(self, melhor_pos)
        self.historico_movimento.add(melhor_pos)

        objetos = self.model.grid.get_cell_list_contents(melhor_pos)
        for objeto in objetos:
            if isinstance(objeto, Estrutura):
                self.registros_locais.append({"tipo": "Estrutura", "pos": objeto.pos})  
            elif isinstance(objeto, Recurso) and not objeto.transportado:
                self.registros_locais.append({"tipo": objeto.tipo, "pos": objeto.pos})  
                if not self.recurso_atual:
                    self.recurso_atual = objeto
                    objeto.transportado = True
                    self.model.grid.remove_agent(objeto)
                    self.objetivo_atual = "transportar"
                    return

    def definir_destino(self, destino):
        """ Define um novo destino baseado em informações do BDI ou lógica interna. """
        if destino:
            self.destino_atual = destino
            self.objetivo_atual = "buscar_recurso"
        else:
            self.objetivo_atual = "explorar"

    def mover_em_direcao(self, destino):
        """Move um passo na direção do destino de maneira eficiente, usando distância euclidiana."""
        if not destino:
            return

        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        melhor_pos = min(vizinhos, key=lambda p: math.dist(p, destino))  # 🚀 Escolhe o vizinho mais próximo do destino

        self.model.grid.move_agent(self, melhor_pos)

 

#------------------------------------------------------------------------

class AgenteBaseadoEmObjetivos(Agent):
    """ Agente que coleta recursos de forma estratégica, priorizando eficiência. """

    def __init__(self, unique_id, model, base_pos):
        super().__init__(unique_id, model)
        self.base_pos = base_pos
        self.recurso_atual = None  # Inicialmente sem recurso
        self.destino_recurso = None
        self.registros_locais = []  # Guarda informações de recursos e estruturas
        self.objetivo_atual = "explorar"
        self.pontuacao = 0

    def step(self):
        """ Executa ações estratégicas conforme o estado do agente. """
        if self.recurso_atual:  # Se estiver carregando um recurso
            self.objetivo_atual = "transportar"

        if self.objetivo_atual == "transportar":
            self.mover_para_base()

        elif self.objetivo_atual == "buscar_recurso":
            if self.destino_recurso:
                self.mover_em_direcao(self.destino_recurso)
                if self.pos == self.destino_recurso:
                    self.objetivo_atual = "coletar"
            else:
                self.definir_destino(self.recurso_mais_proximo())

        elif self.objetivo_atual == "coletar":
            self.tentar_coletar_recurso()
            
        elif self.objetivo_atual == "explorar":
            self.explorar_ambiente()

        else:
            self.explorar_ambiente()

    def explorar_ambiente(self):
        """ Registra estruturas e recursos no ambiente. """
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        recursos_proximos = [obj for obj in self.model.grid.get_cell_list_contents(self.pos) if isinstance(obj, Recurso) and not obj.transportado]

        if recursos_proximos:
            self.objetivo_atual = "coletar"
            self.tentar_coletar_recurso()
        else:
            # Movimenta estrategicamente sem interagir com estruturas
            nova_pos = random.choice(vizinhos)
            self.model.grid.move_agent(self, nova_pos)

            objetos = self.model.grid.get_cell_list_contents(nova_pos)
            for objeto in objetos:
                if isinstance(objeto, Estrutura):
                    self.registros_locais.append({"tipo": "Estrutura", "pos": objeto.pos})  # Registra a estrutura
                elif isinstance(objeto, Recurso) and not objeto.transportado:
                    self.registros_locais.append({"tipo": objeto.tipo, "pos": objeto.pos})

    def definir_destino(self, destino):
        """ Define o destino do agente para buscar um recurso. """
        if destino:
            self.destino_recurso = destino
            self.objetivo_atual = "buscar_recurso"
        else:
            self.objetivo_atual = "explorar"

    def tentar_coletar_recurso(self):
        """ Coleta um recurso e muda para transporte. """
        objetos = self.model.grid.get_cell_list_contents(self.pos)
        for obj in objetos:
            if isinstance(obj, Recurso) and not obj.transportado:
                self.recurso_atual = obj
                obj.transportado = True  # Marca o recurso como coletado
                self.model.grid.remove_agent(obj)  # Remove o recurso do grid
                self.objetivo_atual = "transportar"
                return

        self.definir_destino(self.recurso_mais_proximo())

    def mover_para_base(self):
        """ Move para a base para entregar o recurso e continua explorando. """
        if self.pos != self.base_pos:
            self.mover_em_direcao(self.base_pos)
        else:
            if isinstance(self.recurso_atual, Recurso):  # Garante que é um objeto válido
                self.model.base.registrar_recurso(self.recurso_atual)
                self.pontuacao += self.recurso_atual.utilidade
                print(f"Agente {self.unique_id} entregou {self.recurso_atual.tipo}, pontuação: {self.pontuacao}")

                self.recurso_atual = None  # Após a entrega, ele não carrega mais um recurso

            self.model.agente_bdi.receber_informacoes(self)

            destino_bdi = self.model.agente_bdi.intentions.get(self.unique_id)
            self.destino_recurso = destino_bdi if destino_bdi else None
            self.objetivo_atual = "explorar"

    def mover_em_direcao(self, destino):
        """Move um passo na direção do destino de maneira eficiente."""
        if not destino:
            return

        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        melhor_pos = min(vizinhos, key=lambda p: math.hypot(destino[0] - p[0], destino[1] - p[1]))  # Escolhe o vizinho mais próximo do destino

        self.model.grid.move_agent(self, melhor_pos)


    def recurso_mais_proximo(self):
        """ Retorna o recurso mais próximo para coleta. """
        recursos = [ag for ag in self.model.schedule.agents if isinstance(ag, Recurso) and not ag.transportado]
        if not recursos:
            return None
        mais_proximo = min(recursos, key=lambda r: math.hypot(r.pos[0] - self.pos[0], r.pos[1] - self.pos[1]))
        return mais_proximo.pos



#----------------------------------------------------------------------------


import random
import math
from mesa import Agent
from objetos import Recurso, Estrutura

class AgenteCooperativo(Agent):
    """ Agente que explora o ambiente, armazena percepções e otimiza a coleta de recursos. """

    def __init__(self, unique_id, model, base_pos):
        super().__init__(unique_id, model)
        self.base_pos = base_pos
        self.recurso_atual = None  # Inicialmente sem recurso
        self.destino_recurso = None
        self.registros_locais = []  # Registros de exploração e recursos descobertos
        self.objetivo_atual = "explorar"
        self.pontuacao = 0

    def step(self):
        """ Executa ações com base na análise do ambiente e registro de percepções. """
        if self.recurso_atual:  # Se estiver carregando um recurso
            self.mover_para_base()
        elif self.destino_recurso:
            self.mover_para_destino()
        else:
            self.analisar_ambiente()

    def analisar_ambiente(self):
        """ Explora o ambiente e define o melhor curso de ação com base nas percepções acumuladas. """
        objetos = self.model.grid.get_cell_list_contents(self.pos)
        recursos_disponiveis = [obj for obj in objetos if isinstance(obj, Recurso) and not obj.transportado]

        if recursos_disponiveis:
            melhor_recurso = max(recursos_disponiveis, key=lambda r: r.utilidade / (self.distancia_para_base(r.pos) + 1))
            self.destino_recurso = melhor_recurso.pos
        else:
            self.explorar_ambiente()

        for obj in objetos:
            if isinstance(obj, Estrutura):
                self._registrar_local("Estrutura", obj.pos)
            elif isinstance(obj, Recurso) and not obj.transportado:
                self._registrar_local("Recurso", obj.pos)

    def mover_para_base(self):
        """ Move para a base e envia informações para o BDI após entregar um recurso. """
        if self.pos != self.base_pos:
            self.mover_em_direcao(self.base_pos)
        else:
            if isinstance(self.recurso_atual, Recurso):  # Garante que é um objeto válido
                self.model.base.registrar_recurso(self.recurso_atual)
                self.pontuacao += self.recurso_atual.utilidade
                self.recurso_atual = None  # Após a entrega, ele não carrega mais um recurso

            self.destino_recurso = None  

            # 🔥 Enviar informações ao BDI ao chegar na base
            self.enviar_informacoes_para_bdi()

            self.explorar_ambiente()

    def explorar_ambiente(self):
        """ Explora o ambiente evitando áreas já visitadas. """
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        conhecidos = [reg["pos"] for reg in self.registros_locais if reg["tipo"] == "Explorado"]
        nao_visitados = [pos for pos in vizinhos if pos not in conhecidos]

        nova_pos = random.choice(nao_visitados if nao_visitados else vizinhos)
        self.model.grid.move_agent(self, nova_pos)
        self._registrar_local("Explorado", nova_pos)

    def mover_para_destino(self):
        """ Move para o destino do recurso valioso identificado. """
        if self.destino_recurso and self.pos != self.destino_recurso:
            self.mover_em_direcao(self.destino_recurso)
        elif self.destino_recurso == self.pos:
            self.tentar_coletar_recurso()

    def tentar_coletar_recurso(self):
        """ Coleta um recurso e inicia transporte corretamente. """
        objetos = self.model.grid.get_cell_list_contents(self.pos)
        for obj in objetos:
            if isinstance(obj, Recurso) and not obj.transportado:
                self.recurso_atual = obj  # Agora armazena corretamente o objeto
                obj.transportado = True
                self.model.grid.remove_agent(obj)
                self.destino_recurso = None  # 🔥 Após coleta, redefine destino 
                return

    def mover_em_direcao(self, destino):
        """Move um passo na direção do destino de maneira eficiente."""
        if not destino:
            return

        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        melhor_pos = min(vizinhos, key=lambda p: math.hypot(destino[0] - p[0], destino[1] - p[1]))  # Escolhe o vizinho mais próximo do destino

        self.model.grid.move_agent(self, melhor_pos)


    def distancia_para_base(self, pos):
        """ Calcula a distância euclidiana até a base. """
        return math.hypot(self.base_pos[0] - pos[0], self.base_pos[1] - pos[1])

    def _registrar_local(self, tipo, pos):
        """ Armazena locais explorados e recursos descobertos para evitar repetição. """
        if {"tipo": tipo, "pos": pos} not in self.registros_locais:
            self.registros_locais.append({"tipo": tipo, "pos": pos})

    def enviar_informacoes_para_bdi(self):
        """ Envia as informações registradas sobre recursos e estruturas ao BDI. """
        for reg in self.registros_locais:
            if reg["tipo"] == "Estrutura":
                self.model.agente_bdi.beliefs["estruturas_marcadas"].append(reg)  #  Registrando estrutura corretamente
            elif reg["tipo"] == "Recurso":
                self.model.agente_bdi.beliefs["recursos_confirmados"].append(reg)  #  Registrando recurso corretamente



#------------------------------------------------------------------------


class AgenteBDI(Agent):

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.beliefs = {"explorados": set(),
                        "recursos_confirmados": [],
                        "estruturas_marcadas": []}
        self.intentions = {}

    def receber_informacoes(self, agente):
        """ Processa informações enviadas pelos agentes ao chegarem na base. """
        if self.pos == self.model.base_pos and hasattr(agente, 'registros_locais'):
            for reg in agente.registros_locais:
                if reg['tipo'] == 'Estrutura' and reg not in self.beliefs['estruturas_marcadas']:
                    self.beliefs['estruturas_marcadas'].append(reg)  # registra a estrutura
                elif reg['tipo'] != 'Estrutura' and reg not in self.beliefs['recursos_confirmados']:
                    self.beliefs['recursos_confirmados'].append(reg) 

    def direcionar_agentes(self):
        """ Define missões apenas para coleta de recursos, ignorando estruturas. """
        for ag in self.model.agentes_baseados_estado + self.model.agentes_baseados_objetivos:
            destino = None
            
            if self.beliefs["recursos_confirmados"]:  # prioriza recursos
                destino = self.beliefs["recursos_confirmados"].pop(0)["pos"]

            if destino:
                self.intentions[ag.unique_id] = destino
                ag.definir_destino(destino)
            else:
                ag.objetivo_atual = "explorar"

    def step(self):
        if not self.beliefs["recursos_confirmados"]:  # ignora completamente `estruturas_marcadas`
            for ag in self.model.agentes_baseados_estado + self.model.agentes_baseados_objetivos:
                ag.objetivo_atual = "explorar"

        self.direcionar_agentes()