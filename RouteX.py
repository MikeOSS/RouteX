import tkinter as tk
from tkinter import ttk
import googlemaps
from datetime import datetime, timedelta
import webbrowser
from urllib.parse import quote_plus
import qrcode
from PIL import ImageTk, Image
import os
import sys

# Função auxiliar para encontrar arquivos (ícone, QR code)

def resource_path(relative_path):
    try:
        # cria uma pasta temporária e guarda o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Se não estiver rodando como .exe, pega o caminho normal do script
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# variaveis geral
ENDERECO_PADRAO = "Rua Barreto Leme, 2459, Cambuí, Campinas - SP"

chave = '' 

# Variáveis para guardar o resultado da última rota gerada
rota_final_ordenada = []
ponto_de_partida_global = ""
ponto_de_destino_global = ""

# Tenta inicializar a conexão com a API do Google 
try: 
    gmaps = googlemaps.Client(key=chave)
    print('Conexão inicial com a API do Google bem-sucedida.')
except Exception as e:
    print(f'Erro Crítico na Conexão com a API: {e}')
    gmaps = None # Define como None para que possamos checar depois se a conexão falhou

# f(x):

# Monta a URL para o Google Maps, formatando os endereços para serem seguros

def gerar_url_maps(origem, destinos, destino_final):
    base_url = "http://googleusercontent.com/maps/google.com/4"
    todos_os_pontos = [origem] + destinos + [destino_final]
    # quote_plus formata cada endereço para ser usado em uma URL.
    # A lista de endereços é juntada com "/" entre eles.
    enderecos_formatados = "/".join([quote_plus(p) for p in todos_os_pontos])
    return base_url + enderecos_formatados

# Pega a URL da rota, gera uma imagem de QR Code e exibe no label da interface.
def gerar_e_exibir_qrcode(url_da_rota):
    try:
        qr_path = resource_path("rota_qr.png")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=4)
        qr.add_data(url_da_rota)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").resize((150, 150))
        img.save(qr_path)
        
        # O Tkinter precisa que a imagem seja convertida para um formato próprio (PhotoImage). -> não sabia
        img_tk = ImageTk.PhotoImage(Image.open(qr_path))
        label_qrcode.config(image=img_tk)
        
        # Esta linha é um "truque" do Tkinter. É preciso guardar uma referência da imagem
        # na própria variável do label para evitar que o Python a "limpe" da memória.
        label_qrcode.image = img_tk
    except Exception as e:
        print(f"Erro ao gerar QR Code: {e}")

# Função para o botão "Abrir Rota no Navegador".
def abrir_rota_no_mapa():
    # Só funciona se uma rota já tiver sido gerada e guardada na variável global.
    if not rota_final_ordenada: return
    url = gerar_url_maps(ponto_de_partida_global, rota_final_ordenada, ponto_de_destino_global)
    webbrowser.open(url) # Comando que abre o link no navegador padrão.

# main: 

# Chamada toda vez que o botão "Gerar Rota Otimizada" é clicado.
def gerar_rota_otimizada():
    global rota_final_ordenada, ponto_de_partida_global, ponto_de_destino_global

    # Prepara a interface para uma nova consulta, limpando os resultados antigos.
    resultado_texto.config(state='normal')
    resultado_texto.delete("1.0", tk.END)
    label_qrcode.config(image='')
    botao_abrir_mapa.config(state='disabled')

    if not gmaps:
        resultado_texto.insert(tk.END, "ERRO: Não foi possível conectar à API do Google. Verifique a chave e a conexão.")
        resultado_texto.config(state='disabled')
        return

    # Coleta e limpa os dados dos campos de entrada da interface.
    ponto_de_partida = entrada_saida.get().strip()
    if not ponto_de_partida:
        ponto_de_partida = ENDERECO_PADRAO

    ponto_de_destino = entrada_destino.get().strip()
    if not ponto_de_destino:
        ponto_de_destino = ponto_de_partida
    
    delay_texto = entrada_delay.get().strip()
    try:
        # Converte o delay para inteiro, ou usa 0 se o campo estiver vazio.
        delay_em_minutos = int(delay_texto) if delay_texto else 0
    except ValueError:
        resultado_texto.insert(tk.END, "AVISO: Tempo de saída inválido. Calculando a partir de agora.\n")
        delay_em_minutos = 0

    # Pega o texto da caixa de múltiplos endereços, quebra em linhas
    # e cria uma lista, ignorando as linhas que estiverem em branco.

    enderecos_paradas_texto = entrada_waypoints.get("1.0", tk.END).strip()
    lista_de_paradas = [linha for linha in enderecos_paradas_texto.split('\n') if linha.strip() != '']

    # Validação para garantir que os campos essenciais foram preenchidos.
    if not ponto_de_partida or not lista_de_paradas:
        resultado_texto.insert(tk.END, "ERRO: Preencha o endereço de partida e pelo menos um destino.")
        resultado_texto.config(state='disabled')
        return
    
    # Atualiza as variáveis globais para que outras funções possam usá-las.
    ponto_de_partida_global = ponto_de_partida
    ponto_de_destino_global = ponto_de_destino

    try:
        # A hora de partida considera o delay que o usuário informou.
        hora_de_partida_api = datetime.now() + timedelta(minutes=delay_em_minutos)
        
        # Esta é a chamada principal à API, enviando todos os dados.
        resultado_direcoes = gmaps.directions(
            origin=ponto_de_partida, destination=ponto_de_destino, mode='driving',
            waypoints=lista_de_paradas, departure_time=hora_de_partida_api, optimize_waypoints=True
        )

        if not resultado_direcoes:
            resultado_texto.insert(tk.END, 'O programa não pôde encontrar uma rota.\nVerifique se todos os endereços são válidos.')
            resultado_texto.insert(tk.END, '\nTente colocar da seguinte forma: rua/avenida + número + bairro + cidade.')
        else:
            # Processa a resposta da API. 'waypoint_order' é a ordem otimizada
            # e 'legs' contém os detalhes de cada trecho da viagem.
            ordem_indices = resultado_direcoes[0]['waypoint_order']
            trechos_ordenados = resultado_direcoes[0]['legs']
            rota_final_ordenada = [lista_de_paradas[i] for i in ordem_indices]

            # Formas mais eficientes de calcular os totais usando geradores.
            distancia_total_m = sum(leg['distance']['value'] for leg in trechos_ordenados)
            tempo_viagem_s = sum(leg['duration']['value'] for leg in trechos_ordenados)
            tempo_visitas_s = len(lista_de_paradas) * 10 * 60
            tempo_total_s = tempo_viagem_s + tempo_visitas_s
            distancia_total_km = round(distancia_total_m / 1000)
            
            # divmod é uma função que retorna o quociente e o resto da divisão de uma vez.
            total_h, total_resto_s = divmod(tempo_total_s, 3600)
            total_min = total_resto_s // 60
            tempo_viagem_h, tempo_viagem_resto_s = divmod(tempo_viagem_s, 3600)
            tempo_viagem_min = tempo_viagem_resto_s // 60

            # Exibe os resultados formatados na interface.
            hora_atual = datetime.now() + timedelta(minutes=delay_em_minutos)
            resultado_texto.insert(tk.END, "--- Rota Otimizada com Horários ---\n")
            resultado_texto.insert(tk.END, f"Partida às {hora_atual.strftime('%H:%M')} de: {ponto_de_partida}\n\n")

            for i, indice_original in enumerate(ordem_indices, 1):
                endereco = lista_de_paradas[indice_original]
                # O índice do trecho é i-1 porque a lista 'trechos_ordenados' começa do 0.
                trecho_viagem_s = trechos_ordenados[i-1]['duration']['value'] 
                hora_atual += timedelta(seconds=trecho_viagem_s)
                horario_chegada = hora_atual.strftime('%H:%M')
                resultado_texto.insert(tk.END, f"{i}. Chegada às {horario_chegada} - {endereco}\n")
                hora_atual += timedelta(minutes=10)
                resultado_texto.insert(tk.END, f"   (Previsão de saída: {hora_atual.strftime('%H:%M')})\n")

            # Impressão do resumo final dos resultados.
            resultado_texto.insert(tk.END, f"\nDestino Final: {ponto_de_destino}\n")
            resultado_texto.insert(tk.END, "========================================\n")
            resultado_texto.insert(tk.END, f"Distância Total Estimada: {distancia_total_km} km\n")
            resultado_texto.insert(tk.END, f"Tempo total APENAS de VIAGEM: {tempo_viagem_h}h {tempo_viagem_min}min\n")
            resultado_texto.insert(tk.END, f"Tempo total COM VISITAS (10 min cada): {total_h}h {total_min}min\n")
            
            # Após o sucesso, gera a URL, o QR Code e habilita o botão de abrir no mapa.
            url_da_rota = gerar_url_maps(ponto_de_partida_global, rota_final_ordenada, ponto_de_destino_global)
            gerar_e_exibir_qrcode(url_da_rota)
            botao_abrir_mapa.config(state='normal')

    except Exception as e:
        resultado_texto.insert(tk.END, f"Ocorreu um erro ao comunicar com a API: {e}")
    
    # Bloqueia a caixa de texto para o usuário não editar o resultado.
    resultado_texto.config(state='disabled')

# interface 
root = tk.Tk()
root.title("DVI Route")
root.geometry("700x820")

try:
    caminho_icone = resource_path("icone.ico")
    root.iconbitmap(caminho_icone)
except Exception as e:
    print(f"Erro ao carregar o ícone: {e}")

# Frame principal para organizar todos os outros widgets.
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill='both', expand=True)

# Organização dos widgets de entrada na janela.
frame_partida = ttk.Frame(main_frame)
frame_partida.pack(fill='x', expand=True)
frame_saida = ttk.Frame(frame_partida)
frame_saida.pack(side='left', fill='x', expand=True)
label_saida = ttk.Label(frame_saida, text="Endereço de Partida:")
label_saida.pack(anchor='w')
entrada_saida = ttk.Entry(frame_saida)
entrada_saida.pack(fill='x', expand=True)
entrada_saida.insert(0, ENDERECO_PADRAO)

frame_delay = ttk.Frame(frame_partida)
frame_delay.pack(side='left', padx=(10, 0))
label_delay = ttk.Label(frame_delay, text="Sair em (minutos):")
label_delay.pack(anchor='w')
entrada_delay = ttk.Entry(frame_delay, width=10)
entrada_delay.pack()
entrada_delay.insert(0, "0")

label_destino = ttk.Label(main_frame, text="Endereço Final (Destino) - Deixe em branco para retornar à partida:")
label_destino.pack(anchor='w', pady=(10,0))
entrada_destino = ttk.Entry(main_frame)
entrada_destino.pack(fill='x', expand=True, pady=5)

label_waypoints = ttk.Label(main_frame, text="Endereços para Visitar (coloque um por linha):")
label_waypoints.pack(anchor='w', pady=(10,0))
entrada_waypoints = tk.Text(main_frame, height=8, relief='solid', borderwidth=1)
entrada_waypoints.pack(fill='x', expand=True, pady=5)

frame_botoes = ttk.Frame(main_frame)
frame_botoes.pack(pady=5)
botao_gerar = ttk.Button(frame_botoes, text="Gerar Rota Otimizada", command=gerar_rota_otimizada)
botao_gerar.pack(side='left', padx=10)
botao_abrir_mapa = ttk.Button(frame_botoes, text="Abrir Rota no Navegador", command=abrir_rota_no_mapa, state='disabled')
botao_abrir_mapa.pack(side='left', padx=10)

# Estrutura para a área de resultados, com texto à esquerda e QR Code à direita.
frame_resultados = ttk.Frame(main_frame)
frame_resultados.pack(fill='both', expand=True, pady=10)

frame_texto_resultado = ttk.Frame(frame_resultados)
frame_texto_resultado.pack(side='left', fill='both', expand=True)
label_resultado = ttk.Label(frame_texto_resultado, text="Resultado da Rota:")
label_resultado.pack(anchor='w')
resultado_texto = tk.Text(frame_texto_resultado, height=15, state='disabled', relief='solid', borderwidth=1)
resultado_texto.pack(side='left', fill='both', expand=True)

# Conecta a barra de rolagem ao widget de texto.
scrollbar_resultado = ttk.Scrollbar(frame_texto_resultado, orient='vertical', command=resultado_texto.yview)
scrollbar_resultado.pack(side='right', fill='y')
resultado_texto['yscrollcommand'] = scrollbar_resultado.set

frame_qrcode = ttk.Frame(frame_resultados, padding=(10, 0))
frame_qrcode.pack(side='right', fill='y')
label_qrcode_titulo = ttk.Label(frame_qrcode, text="QR Code para Celular:")
label_qrcode_titulo.pack()
label_qrcode = ttk.Label(frame_qrcode)
label_qrcode.pack()


root.mainloop()