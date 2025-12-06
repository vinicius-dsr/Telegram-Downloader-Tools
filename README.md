# 📥 Telegram Downloader Tools

Este projeto permite baixar vídeos do Telegram utilizando múltiplas hashtags. É uma ferramenta útil para coletar conteúdo de canais ou grupos específicos.

**Disponível em três versões:**
- 🖥️ **CLI (Linha de Comando)** - Para uso em scripts e automação
- 🎨 **GUI (CustomTkinter)** - Interface gráfica tradicional
- ✨ **Flet UI** - Interface web moderna e responsiva - **EM DESENVOLVIMENTO**

## 📋 Pré-requisitos

- Python 3.7 ou superior
- Conta no Telegram
- API ID e API Hash (veja seção abaixo)

## 🔑 Obter API ID e API Hash

1. Acesse https://my.telegram.org e faça login com seu número de telefone
2. Clique em "API development tools"
3. Preencha o formulário para criar uma nova aplicação (App title, Short name, etc.)
4. Você verá seu **api_id** e **api_hash**

## 🔐 Fluxo de Autenticação

Agora o aplicativo possui um fluxo de autenticação simplificado e seguro:

### Primeiro Acesso
1. Ao iniciar o aplicativo pela primeira vez, você verá a tela de login
2. Preencha os seguintes campos:
   - **API ID**: Seu ID da API do Telegram
   - **API Hash**: Seu hash da API do Telegram
   - **Telefone**: Número de telefone com código do país (ex: +5511987654321)

3. Clique em "Conectar e enviar código"
4. Um código de verificação será enviado para sua conta do Telegram
5. Insira o código recebido na janela de confirmação
6. Se sua conta tiver autenticação de dois fatores (2FA), você será solicitado a inserir a senha

### Próximos Acessos
- Suas credenciais são salvas de forma segura no seu computador
- O aplicativo tentará reconectar automaticamente usando a sessão anterior
- Se precisar fazer login novamente, você pode apagar o arquivo de configuração e a sessão através do menu de configurações

### Dicas de Segurança
- Mantenha suas credenciais da API em segredo
- Nunca compartilhe códigos de verificação ou senhas
- Se estiver usando um computador compartilhado, certifique-se de fazer logout adequadamente

## 🚀 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/vinicius-dsr/Telegram-Downloader-Tools.git
cd Telegram-Downloader-Tools
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

Ou no Windows, execute: `install_gui.bat`

---

## 🎨 Versões GUI (Interface Gráfica)

### Versão CustomTkinter

- 🖥️ Interface gráfica tradicional para desktop
- 🎨 Tema escuro por padrão
- 📊 Barra de progresso em tempo real
- 📝 Área de log expansível
- ⚡ Download assíncrono
- 🛑 Controle de downloads em andamento
- 💾 Gerenciamento de configurações

### Versão Flet (Web/Desktop)

- 🌐 Interface web moderna e responsiva
- 📱 Compatível com dispositivos móveis
- 🎨 Design limpo e intuitivo
- 📊 Feedback visual em tempo real
- ⚡ Download assíncrono com indicadores de progresso
- 🔄 Atualizações em tempo real
- 📦 Fácil implantação como aplicativo web

### Como Usar a GUI CustomTkinter

#### Configuração de Nomes de Arquivo
- **Linha do Nome do Vídeo**: Selecione qual linha da mensagem será usada como nome do arquivo baixado:
  - `Primeira Linha`: Usa a primeira linha da mensagem
  - `Segunda Linha`: Usa a segunda linha (ou a primeira se não houver segunda)
  - `Terceira Linha`: Usa a terceira linha (ou a última disponível)
  - `Última Linha`: Usa a última linha da mensagem (comportamento padrão)

#### Dicas para Tags
- As tags podem ser inseridas de várias formas, o sistema irá formatar automaticamente:
  - `tag1 tag2 tag3` → `tag1, tag2, tag3`
  - `tag1,tag2,tag3` → `tag1, tag2, tag3`
  - `tag1, tag2, tag3` → mantém a formatação
  - Mistura de espaços e vírgulas também é aceito

1. Execute o arquivo `src/download_telegram_video_tags_gui.py`:
```bash
python src/download_telegram_video_tags_gui.py
```

2. Preencha os campos necessários:
   - API ID e API Hash (obtidos em [my.telegram.org](https://my.telegram.org))
   - Nome ou link do canal/grupo (ex: @nomedocanal)
   - Hashtags para filtrar (separadas por vírgula)
   - Pasta de saída para os downloads
   - Limite de mensagens a serem verificadas

3. Clique em "Iniciar Download"
   - **💾 Salvar Configuração**: Salva seus parâmetros em arquivo JSON
   - **📂 Carregar Configuração**: Carrega configurações salvas anteriormente

4. **Iniciar Download:**
   - Clique em **"🚀 Iniciar Download"**
   - Na primeira execução, será necessário autenticar com o Telegram
   - Acompanhe o progresso na barra e no log

### Recursos da GUI

- **Validação de Campos**: Verifica campos obrigatórios e formatos
- **Progresso em Tempo Real**: Porcentagem, velocidade (MB/s) e tempo estimado (ETA)
- **Log Detalhado**: Status de conexão, vídeos encontrados, erros e avisos
- **Botão Parar**: Cancela o download em andamento a qualquer momento
- **📌 Nomes de Arquivo Dinâmicos**: Escolha qual linha da mensagem será usada como nome do arquivo (primeira, segunda, terceira ou última linha)
- **🏷️ Processamento Inteligente de Tags**: Aceita tags separadas por vírgulas, espaços ou ambos, com formatação automática
- **💾 Configurações Salvas**: As preferências de linha para nomes de arquivo são salvas com as configurações

---

## 🖥️ Versão CLI (Linha de Comando)

### Como Usar o CLI

Execute o seguinte comando:

```bash
python src/download_telegram_video_tags.py \
  --api-id SEU_API_ID \
  --api-hash SEU_API_HASH \
  --target "https://t.me/nomeCanal" \
  --tags "#tag1,#tag2" \
  --out "./downloads"
```

### Parâmetros do CLI

- `--api-id`: (obrigatório) API ID obtido em my.telegram.org
- `--api-hash`: (obrigatório) API Hash obtido em my.telegram.org
- `--target`: (obrigatório) Canal ou grupo (@nomeCanal ou https://t.me/nomeCanal)
- `--tags`: (obrigatório) Lista de hashtags separadas por vírgula
- `--out`: Pasta de saída (padrão: ./downloads)
- `--limit`: Limite de mensagens por tag (0 = sem limite)
- `--session`: Nome do arquivo de sessão (padrão: session)
- `--max-flood-wait`: Tempo máximo de FloodWait automático em segundos (padrão: 300)

### Exemplos de Uso CLI

```bash
# Exemplo básico
python src/download_telegram_video_tags.py \
  --api-id 12345678 \
  --api-hash "a1b2c3d4e5f6g7h8i9j0" \
  --target "@meucanal" \
  --tags "#video,#conteudo"

# Com limite e pasta personalizada
python src/download_telegram_video_tags.py \
  --api-id 12345678 \
  --api-hash "a1b2c3d4e5f6g7h8i9j0" \
  --target "https://t.me/meucanal" \
  --tags "#tag1,#tag2,#tag3" \
  --out "C:/Downloads/Videos" \
  --limit 50

# Não aceitar FloodWaits automáticos
python src/download_telegram_video_tags.py \
  --api-id 12345678 \
  --api-hash "a1b2c3d4e5f6g7h8i9j0" \
  --target "@canal" \
  --tags "#tag" \
  --max-flood-wait 0

# Aceitar FloodWaits de até 60 segundos
python src/download_telegram_video_tags.py \
  --api-id 12345678 \
  --api-hash "a1b2c3d4e5f6g7h8i9j0" \
  --target "@canal" \
  --tags "#tag" \
  --max-flood-wait 60
```

---

## ⚠️ FloodWait (Limitação de Requisições)

Ao usar a API do Telegram, é possível receber `FloodWaitError` quando a conta faz muitas requisições em pouco tempo. O Telegram exige que você aguarde um certo número de segundos antes de tentar novamente.

### Tratamento de FloodWait

Ambas as versões (CLI e GUI) tratam FloodWait automaticamente:

- **Retry controlado** ao resolver a entidade do target
- **Retry automático** durante a iteração de mensagens
- **Controle via `--max-flood-wait`** (CLI) ou campo na GUI

### Comportamento

- Se `FloodWait ≤ max-flood-wait`: aguarda automaticamente e continua
- Se `FloodWait > max-flood-wait`: aborta e informa o tempo necessário

### Valores Recomendados

- **0**: Não aceitar waits automáticos (aborta imediatamente)
- **30-60**: Aceitar waits curtos automaticamente
- **300** (padrão): Aceita waits de até 5 minutos

### Boas Práticas

- Reduza o número de requisições por execução (use `--limit` menor)
- Espalhe as execuções no tempo (batches com intervalo)
- Use sessões diferentes se necessário
- Aguarde manualmente em caso de FloodWaits longos

---

## 📁 Arquivos Gerados

Após o download, você encontrará:

1. **Vídeos**: Salvos na pasta especificada com nomes seguros
2. **CSV**: `videos_baixados.csv` com informações detalhadas:
   - Tag usada
   - ID da mensagem
   - Data e hora
   - Nome do arquivo
   - Legenda completa

---

## 🎨 Personalização da GUI

A interface usa **customtkinter** com tema escuro por padrão. Para mudar:

No arquivo `src/download_telegram_video_tags_gui.py`, linhas 15-16:
```python
ctk.set_appearance_mode("dark")  # Altere para "light" ou "system"
ctk.set_default_color_theme("blue")  # Altere para "green" ou "dark-blue"
```

---

## 🐛 Solução de Problemas

### Erro ao importar customtkinter
```bash
pip install customtkinter --upgrade
```

### Erro de conexão do Telegram
- Verifique suas credenciais API ID e API Hash
- Certifique-se de estar conectado à internet

### Flood Wait muito longo
- Aumente o valor de "Max Flood Wait"
- Ou aguarde manualmente e tente novamente mais tarde

### Erro "Can't find a usable init.tcl"
Este erro ocorre quando o Python não consegue encontrar as bibliotecas Tcl/Tk do sistema.
O projeto inclui um script de correção automática que tenta localizar essas bibliotecas.

Ele é executado automaticamente ao iniciar a GUI, mas se você precisar depurar ou verificar se as bibliotecas são encontradas:

```bash
python src/tcl_fix.py
```

Se o script não encontrar as bibliotecas, você precisará instalá-las no seu sistema (ex: `sudo apt install python3-tk tk-dev` no Linux).

---

## 📺 Canais do Telegram

- https://t.me/+hy2KQlxP78JiYmIx
- https://t.me/+PxqctwKBOjMxMjli

---

## ☕ Apoie o Projeto

Se você gostou do projeto e gostaria de apoiar o desenvolvimento, considere me pagar um café! Isso ajuda a manter o projeto ativo e com melhorias constantes.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://viniciusreis.site/coffee)

## 🤝 Contribuição

Sinta-se à vontade para contribuir com melhorias ou correções. Faça um fork do repositório e envie um pull request.

## 📄 Licença

Este projeto está disponível sob os termos da licença do repositório.

---

**Desenvolvido com ❤️ para a comunidade**
