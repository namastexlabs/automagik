"""
Script de configuração simples para as credenciais da API do Gmail.

Este script guia o usuário pelo processo de configuração das credenciais 
do Google OAuth para a API do Gmail.

Uso:
    python scripts/gmail_setup.py
"""

import os
import json
import argparse
import logging
import sys
import webbrowser
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Escopos da API Gmail
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

def show_google_project_setup_instructions():
    """Mostra instruções para configurar o projeto no Google Cloud Console."""
    print("\n📋 INSTRUÇÕES PARA CONFIGURAR O PROJETO NO GOOGLE CLOUD CONSOLE 📋")
    print("=" * 80)
    print("1. Acesse https://console.cloud.google.com/")
    print("2. Crie um novo projeto ou selecione um existente")
    print("3. No menu lateral, vá para 'APIs e Serviços' > 'Tela de permissão OAuth'")
    print("4. Configure a tela de permissão (escolha 'Externo' se não tiver domínio Google Workspace)")
    print("5. No menu lateral, vá para 'APIs e Serviços' > 'Credenciais'")
    print("6. Clique em 'Criar Credenciais' > 'ID do cliente OAuth'")
    print("7. Escolha 'Aplicativo para Desktop' como tipo")
    print("8. Dê um nome ao seu aplicativo (ex: 'Gmail API Client')")
    print("9. Clique em 'Criar'")
    print("10. Faça o download do arquivo JSON de credenciais")
    print("")
    print("⚠️ IMPORTANTE: CONFIGURAÇÃO DE REDIRECIONAMENTO ⚠️")
    print("Se você encontrar o erro 'Missing required parameter: redirect_uri':")
    print("1. Vá para 'APIs e Serviços' > 'Credenciais'")
    print("2. Edite o cliente OAuth criado")
    print("3. Na seção 'URIs de redirecionamento autorizados', adicione:")
    print("   - http://localhost:8080/")
    print("   - http://localhost/")
    print("   - http://127.0.0.1:8080/")
    print("   - http://127.0.0.1/")
    print("4. Clique em 'Salvar'")
    print("5. Faça o download do arquivo JSON atualizado")
    print("=" * 80)
    print("\nPressione Enter para continuar...")
    input()

def handle_redirect_url(url):
    """
    Extrai o código de autorização de uma URL de redirecionamento.
    
    Args:
        url: URL de redirecionamento completa
        
    Returns:
        str: Código de autorização ou None se não encontrado
    """
    if not url or 'code=' not in url:
        return None
        
    try:
        # Extrair o código da URL
        code_part = url.split('code=')[1]
        # Remover parâmetros adicionais após o código
        if '&' in code_part:
            code = code_part.split('&')[0]
        else:
            code = code_part
            
        return code
    except Exception as e:
        logger.error(f"Erro ao extrair código da URL: {e}")
        return None

def setup_credentials(credentials_path, token_path):
    """
    Configura as credenciais da API do Gmail.
    
    Args:
        credentials_path: Caminho para o arquivo credentials.json
        token_path: Caminho para salvar o token
        
    Returns:
        bool: True se sucesso, False se falha
    """
    # Verificar se o arquivo de credenciais existe
    credentials_path = Path(credentials_path)
    if not credentials_path.exists():
        logger.error(f"Arquivo de credenciais não encontrado: {credentials_path}")
        print(f"\n❌ ERRO: Arquivo de credenciais não encontrado em {credentials_path}")
        show_google_project_setup_instructions()
        return False
    
    # Criar diretório para o token se não existir
    token_path = Path(token_path)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n🔑 CONFIGURAÇÃO DE CREDENCIAIS DA API GMAIL 🔑")
    print(f"Arquivo de credenciais: {credentials_path}")
    print(f"Token será salvo em: {token_path}")
    print("=" * 50)
    
    try:
        # Verificar se as credenciais são válidas
        try:
            with open(credentials_path, 'r') as f:
                cred_data = json.load(f)
                if 'installed' not in cred_data and 'web' not in cred_data:
                    print("\n❌ ERRO: Arquivo de credenciais inválido. Verifique se você baixou o arquivo correto.")
                    show_google_project_setup_instructions()
                    return False
        except json.JSONDecodeError:
            print("\n❌ ERRO: Arquivo de credenciais não é um JSON válido.")
            show_google_project_setup_instructions()
            return False
        
        # Iniciar fluxo de autenticação
        print("\nIniciando processo de autenticação...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path),
            SCOPES,
            redirect_uri='http://localhost:8080/'
        )
        
        # Gerar URL de autorização
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print("\n📋 INSTRUÇÕES DE AUTENTICAÇÃO 📋")
        print("1. Abrindo navegador com a URL de autenticação...")
        print("   Se o navegador não abrir automaticamente, copie e cole esta URL:")
        print(f"\n   {auth_url}\n")
        
        # Tentar abrir o navegador automaticamente
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.warning(f"Não foi possível abrir o navegador automaticamente: {e}")
            print("   ⚠️ Não foi possível abrir o navegador automaticamente.")
            print("   Por favor, copie e cole a URL acima em seu navegador.")
        
        # Instruções para o usuário
        print("2. Faça login com sua conta Google e autorize o aplicativo")
        print("\nPossíveis situações:")
        print("A) Se você ver o ERRO 'Missing required parameter: redirect_uri':")
        print("   - Você precisa adicionar URIs de redirecionamento no Console do Google")
        print("   - Digite 'config' para ver instruções detalhadas")
        print("B) Se você for redirecionado para uma página que diz que o código foi capturado:")
        print("   - Digite 'ok' aqui")
        print("C) Se você for redirecionado para uma URL de erro ou um localhost que não carrega:")
        print("   - Cole a URL completa aqui (começa com http://localhost ou similar)")
        print("D) Se você vê o código de autorização diretamente:")
        print("   - Cole apenas o código aqui")
        
        while True:
            response = input("\n🔑 Sua resposta (ok/URL/código/config): ").strip()
            
            if response.lower() == 'config':
                show_google_project_setup_instructions()
                continue
                
            if response.lower() == 'ok':
                try:
                    # Tentar o método local server
                    print("\nTentando obter token via servidor local...")
                    # Novo flow para tentativa limpa
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path),
                        SCOPES
                    )
                    creds = flow.run_local_server(port=8080)
                    print("✅ Autenticação bem-sucedida!")
                    break
                except Exception as e:
                    logger.error(f"Erro na autenticação via servidor local: {e}")
                    print(f"\n❌ Erro ao obter o token: {e}")
                    print("Por favor, tente o método manual:")
                    print("1. Cole a URL completa de redirecionamento, ou")
                    print("2. Digite 'config' para verificar a configuração do projeto")
                    continue
            elif response.startswith('http'):
                # É uma URL, extrair o código
                code = handle_redirect_url(response)
                if not code:
                    print("\n❌ Não foi possível extrair o código da URL fornecida.")
                    continue
                
                # Usar o código extraído
                try:
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    print("✅ Código validado com sucesso!")
                    break
                except Exception as e:
                    logger.error(f"Erro ao validar código: {e}")
                    print(f"\n❌ ERRO: Código inválido ou expirado: {str(e)}")
                    print("Tente novamente ou digite 'config' para instruções.")
                    continue
            else:
                # Usuário colou diretamente o código
                try:
                    flow.fetch_token(code=response)
                    creds = flow.credentials
                    print("✅ Código validado com sucesso!")
                    break
                except Exception as e:
                    logger.error(f"Erro ao validar código: {e}")
                    print(f"\n❌ ERRO: Código inválido ou expirado: {str(e)}")
                    print("Tente novamente ou digite 'config' para instruções.")
                    continue
        
        # Salvar as credenciais
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
        
        print(f"\n✅ Credenciais salvas com sucesso em {token_path}")
        print("\nAgora você pode usar as ferramentas da API do Gmail.")
        print(f"Seu arquivo de credenciais está em: {credentials_path}")
        
        # Se no Windows, mostrar o comando SET, senão export
        if sys.platform.startswith('win'):
            print(f"\nDefina a variável de ambiente com:")
            print(f"SET GOOGLE_CREDENTIAL_FILE={credentials_path}")
        else:
            print(f"\nDefina a variável de ambiente com:")
            print(f"export GOOGLE_CREDENTIAL_FILE={credentials_path}")
            
        print("\nOu adicione ao seu arquivo .env:")
        print(f"GOOGLE_CREDENTIAL_FILE={credentials_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Erro na configuração: {e}")
        print(f"\n❌ ERRO: {str(e)}")
        return False

def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(description="Configuração de credenciais da API do Gmail")
    
    # Priorizar o .env sobre parâmetro de linha de comando
    default_credentials = os.environ.get("GOOGLE_CREDENTIAL_FILE")
    
    parser.add_argument(
        "--credentials", 
        help="Caminho para o arquivo credentials.json", 
        default=default_credentials
    )
    
    parser.add_argument(
        "--token", 
        help="Caminho para salvar o token", 
        default="credentials/gmail_token.json"
    )
    
    args = parser.parse_args()
    
    if not args.credentials:
        print("\n❌ ERRO: Arquivo de credenciais não encontrado.")
        print("Defina a variável GOOGLE_CREDENTIAL_FILE no .env ou use --credentials=caminho/para/credentials.json")
        show_google_project_setup_instructions()
        return 1
    
    success = setup_credentials(args.credentials, args.token)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 