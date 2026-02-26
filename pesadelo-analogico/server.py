import os
import json
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# INICIALIZAÇÃO BLINDADA: Se faltar a chave, ele não capota o servidor.
chave_api = os.environ.get("GEMINI_API_KEY")
client = None
if chave_api:
    try:
        client = genai.Client(api_key=chave_api)
    except Exception as e:
        print(f"Erro ao ligar a IA: {e}")

def limpar_json(texto):
    try:
        texto_limpo = texto.replace('```json', '').replace('```', '').strip()
        return json.loads(texto_limpo)
    except Exception as e:
        return {}

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "Servidor rodando liso"}), 200

@app.route('/iniciar', methods=['GET'])
def iniciar():
    # Se o Render não tiver a chave da IA, avisa na tela do jogo!
    if not client:
        return jsonify({"narrativa": "[ERRO FATAL] O servidor do Render não encontrou a sua GEMINI_API_KEY. Vá no painel do Render > Environment e adicione a chave!", "novo_estado": {"urgency": 0, "gameOver": True}}), 200

    dificuldade = request.args.get('dificuldade', 'medio')
    
    temas = [
        "Analog Horror / Espaços Liminares: Estética VHS, paranoia, backrooms.",
        "Fundação SCP: Instalação governamental em lockdown com anomalias.",
        "Serial Killers: Preso numa armadilha ou fugindo de um predador.",
        "Mitos e Lendas: Floresta fechada à noite com maldições e criptídeos.",
        "Horror Cósmico / Lovecraftiano: Deuses antigos, cultos sombrios."
    ]
    tema_escolhido = random.choice(temas)

    prompt = f"""
    Atue como Mestre de RPG de sobrevivência de terror.
    Cenário: {tema_escolhido}
    Dificuldade: {dificuldade}
    
    Regras:
    1. Descreva o cenário inicial estabelecendo a tensão.
    2. SEJA CONCISO. Escreva 1 parágrafo com no máximo 8 linhas.
    3. Termine com: 'O que você faz?'
    
    Retorne EXATAMENTE este JSON:
    {{
        "narrativa": "A descrição inicial (max 8 linhas)",
        "contexto": "Resumo do local e situação"
    }}
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        dados = limpar_json(resposta.text)
        
        return jsonify({
            "narrativa": dados.get("narrativa", "O que você faz?"),
            "novo_estado": {"urgency": 0, "gameOver": False, "venceu": False, "dificuldade": dificuldade, "contexto": dados.get("contexto", "Cenário inicial.")}
        })
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "quota" in erro_str:
            return jsonify({"narrativa": "[FIM DA TRANSMISSÃO] A cota diária desta máquina esgotou. Volte amanhã.", "novo_estado": {"urgency": 0, "gameOver": True}}), 200
        return jsonify({"narrativa": f"[ERRO DA IA] A matriz falhou: {e}", "novo_estado": {"urgency": 0, "gameOver": False}}), 500

@app.route('/jogar', methods=['POST'])
def jogar():
    if not client:
        return jsonify({"narrativa": "Servidor sem API Key configurada.", "novo_estado": {}}), 500

    dados = request.json
    comando_usuario = dados.get('comando', '')
    estado_atual = dados.get('estado_atual', {})
    contexto = estado_atual.get('contexto', '')
    urgencia_atual = int(estado_atual.get('urgency', 0))
    dificuldade = estado_atual.get('dificuldade', 'medio')

    prompt = f"""
    CENÁRIO ATUAL: {contexto}
    Dificuldade: {dificuldade}
    Ação do jogador: "{comando_usuario}"
    
    Regras:
    1. Escreva 1 parágrafo CURTO (3 a 5 linhas) com o resultado.
    2. Urgência: Fácil (+5 erro, -15 acerto), Médio (+15 erro, -10 acerto), Difícil (+25 erro, -5 acerto).
    
    Retorne JSON:
    {{
        "narrativa": "O que aconteceu...",
        "urgency_change": número inteiro,
        "morreu": true ou false,
        "escapou": true ou false,
        "contexto": "Situação atualizada"
    }}
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        dados_ia = limpar_json(resposta.text)
        
        mudanca = int(dados_ia.get("urgency_change", 15))
        nova_urgencia = max(0, min(100, urgencia_atual + mudanca))
        morreu = bool(dados_ia.get("morreu", False))
        escapou = bool(dados_ia.get("escapou", False))
        
        return jsonify({
            "narrativa": dados_ia.get("narrativa", "Silêncio profundo."),
            "novo_estado": {"urgency": nova_urgencia, "gameOver": morreu or escapou or nova_urgencia >= 100, "venceu": escapou, "dificuldade": dificuldade, "contexto": dados_ia.get("contexto", contexto)}
        })
    except Exception as e:
        return jsonify({"narrativa": f"A conexão falhou: {e}", "novo_estado": estado_atual}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    print(f"Servidor subindo na porta {port}...")
    app.run(host='0.0.0.0', port=port)
