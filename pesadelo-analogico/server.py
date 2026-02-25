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

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def limpar_json(texto):
    try:
        texto_limpo = texto.replace('```json', '').replace('```', '').strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro ao forçar JSON: {e}")
        return {}

config_seguranca = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    )
]

@app.route('/iniciar', methods=['GET'])
def iniciar():
    dificuldade = request.args.get('dificuldade', 'medio')
    
    temas = [
        "Analog Horror / Espaços Liminares: Estética VHS, paranoia, backrooms.",
        "Fundação SCP: Instalação governamental em lockdown com anomalias.",
        "Serial Killers: Preso numa armadilha ou fugindo de um predador.",
        "Mitos e Lendas: Floresta fechada à noite com maldições e criptídeos.",
        "Horror Cósmico / Lovecraftiano: Deuses antigos, cultos sombrios, arquitetura bizarra, loucura."
    ]
    tema_escolhido = random.choice(temas)

    prompt = f"""
    Atue como Mestre de RPG de sobrevivência de terror.
    Cenário: {tema_escolhido}
    Dificuldade: {dificuldade}
    
    Regras:
    1. Descreva o cenário inicial estabelecendo a tensão.
    2. SEJA CONCISO. Escreva exatamente 1 parágrafo com no máximo 8 a 10 linhas. Sem enrolação.
    3. Crie um problema inicial que exija exploração e observação.
    4. Termine a narrativa com: 'O que você faz?'
    
    Retorne EXATAMENTE este formato JSON:
    {{
        "narrativa": "A descrição inicial (max 10 linhas)",
        "contexto": "Resumo do local, dificuldade e situação para lembrar depois"
    }}
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=config_seguranca
            )
        )
        
        try:
            texto_resposta = resposta.text
        except ValueError:
            return jsonify({"narrativa": "A conexão foi cortada por uma força maior. (Filtro de Segurança ativado). Tente dar F5.", "novo_estado": {"urgency": 0, "gameOver": False}}), 200

        dados = limpar_json(texto_resposta)
        
        return jsonify({
            "narrativa": dados.get("narrativa", "O que você faz?"),
            "novo_estado": {
                "urgency": 0,
                "gameOver": False,
                "venceu": False,
                "dificuldade": dificuldade,
                "contexto": dados.get("contexto", "Cenário inicial.")
            }
        })
    except Exception as e:
        erro_str = str(e).lower()
        if "429" in erro_str or "quota" in erro_str:
            if "day" in erro_str or "perday" in erro_str:
                return jsonify({"narrativa": "[FIM DA TRANSMISSÃO] A cota diária gratuita deste servidor esgotou. A entidade foi dormir. Volte amanhã para jogar.", "novo_estado": {"urgency": 0, "gameOver": True}}), 200
            else:
                return jsonify({"narrativa": "[INTERFERÊNCIA] Tem muita gente acessando o servidor agora ou você está muito rápido. Aguarde 20 segundos e tente iniciar de novo (F5).", "novo_estado": {"urgency": 0, "gameOver": False}}), 200
            
        print(f"Erro no inicio: {e}")
        return jsonify({"narrativa": "Erro na Matrix.", "novo_estado": {"urgency": 0, "gameOver": False}}), 500

@app.route('/jogar', methods=['POST'])
def jogar():
    dados = request.json
    comando_usuario = dados.get('comando', '')
    estado_atual = dados.get('estado_atual', {})
    contexto = estado_atual.get('contexto', '')
    urgencia_atual = int(estado_atual.get('urgency', 0))
    dificuldade = estado_atual.get('dificuldade', 'medio')

    prompt = f"""
    CENÁRIO ATUAL: {contexto}
    Dificuldade do Jogo: {dificuldade}
    Ação do jogador: "{comando_usuario}"
    
    Regras de Mestre:
    1. Escreva 1 parágrafo CURTO com 3 a 5 linhas detalhando o resultado da ação.
    2. Modulação da Urgência:
       - Fácil: Erros (+5 a 10). Ações boas/seguras (-15 a -20).
       - Médio: Erros (+15). Ações boas (-10).
       - Difícil: Erros (+25 a 35). Ações boas (-5).
    3. Retorne APENAS o número inteiro em 'urgency_change'.
    4. Puna os erros, mas NÃO dê Game Over instantâneo na primeira falha.
    
    Retorne EXATAMENTE este formato JSON:
    {{
        "narrativa": "O que aconteceu (3 a 5 linhas).",
        "urgency_change": inteiro negativo ou positivo,
        "morreu": true ou false,
        "escapou": true ou false,
        "contexto": "Situação e inventário atualizados"
    }}
    """
    try:
        resposta = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=config_seguranca
            )
        )
        
        try:
            texto_resposta = resposta.text
        except ValueError:
            return jsonify({
                "narrativa": "Sua mente bloqueia o que está à frente por puro terror cósmico. Tente agir de outra forma.",
                "novo_estado": estado_atual
            })

        dados_ia = limpar_json(texto_resposta)
        
        if not dados_ia:
            return jsonify({"narrativa": "A realidade distorceu sua ação. Tente agir de outra forma.", "novo_estado": estado_atual})

        try:
            mudanca = int(dados_ia.get("urgency_change", 15))
        except (ValueError, TypeError):
            mudanca = 15
            
        nova_urgencia = urgencia_atual + mudanca
        nova_urgencia = max(0, min(100, nova_urgencia))
        
        morreu = bool(dados_ia.get("morreu", False))
        escapou = bool(dados_ia.get("escapou", False))
        game_over = morreu or escapou or nova_urgencia >= 100
        
        return jsonify({
            "narrativa": dados_ia.get("narrativa", "Sem resposta."),
            "novo_estado": {
                "urgency": nova_urgencia,
                "gameOver": game_over,
                "venceu": escapou,
                "dificuldade": dificuldade,
                "contexto": dados_ia.get("contexto", contexto)
            }
        })
    except Exception as e:
        erro_str = str(e).lower()
        print(f"Erro na jogada: {e}")
        
        if "429" in erro_str or "quota" in erro_str:
            if "day" in erro_str or "perday" in erro_str:
                return jsonify({
                    "narrativa": "[FIM DA TRANSMISSÃO] A cota diária gratuita do servidor esgotou. Não se preocupe, o jogo volta ao normal amanhã. Vá descansar.",
                    "novo_estado": estado_atual 
                }), 200
            else:
                return jsonify({
                    "narrativa": "[INTERFERÊNCIA] A entidade percebeu seus movimentos frenéticos ou o servidor está lotado. Fique em silêncio por 20 segundos antes de enviar outra ação.",
                    "novo_estado": estado_atual
                }), 200

        return jsonify({"narrativa": "A conexão com a sua sanidade falhou. Tente enviar a ação de novo.", "novo_estado": estado_atual}), 500

if __name__ == '__main__':
    print("Servidor rodando... Cota de mendigo blindada com sucesso!")
    app.run(port=3000, debug=True)