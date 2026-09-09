# 📥 Telegram Downloader Tools

Ferramenta para baixar vídeos do Telegram por **hashtags** ou **todos os vídeos de um canal/grupo**. Útil para coletar conteúdo de canais específicos, inclusive aqueles com proteção contra cópia/forward (download direto via API).

**Versões disponíveis:**
- 🎨 **GUI (ttkbootstrap)** - Interface gráfica estilo console, tema escuro `darkly`

> A antiga interface CLI/argparse e a versão CustomTkinter foram removidas. A aplicação mantida é `src/download_telegram_video_tags_gui.py`.

## 📋 Pré-requisitos

- Python 3.9 ou superior
- Conta no Telegram
- API ID e API Hash (veja seção abaixo)

## 🔑 Obter API ID e API Hash

1. Acesse https://my.telegram.org e faça login com seu número de telefone
2. Clique em "API development tools"
3. Preencha o formulário para criar uma nova aplicação (App title, Short name, etc.)
4. Você verá seu **api_id** e **api_hash**

## 🔐 Fluxo de Autenticação

O aplicativo faz login pela interface, sem prompts no terminal:

### Primeiro Acesso
1. Ao iniciar, você verá a tela de login
2. Preencha:
   - **API ID**: Seu ID da API do Telegram
   - **API Hash**: Seu hash da API do Telegram
   - **Telefone**: Número com código do país (ex: +5511987654321)
3. Clique em "Conectar e enviar código"
4. O código de verificação é pedido em uma **janela modal**
5. Se sua conta tiver 2FA, a senha também é pedida em janela modal

### Próximos Acessos
- Se houver uma **sessão válida** salva, o app conecta automaticamente (nada é perguntado)
- Se a sessão expirou/estiver inválida, o app reabre o fluxo de login por modais (telefone → código → 2FA) diretamente no fluxo de download
- **Sem prompt interativo no terminal** em nenhuma hipótese

### Dicas de Segurança
- Mantenha suas credenciais da API em segredo
- Nunca compartilhe códigos de verificação ou senhas
- As credenciais ficam em `src/config.json` (ignorado pelo git) e a sessão em `src/*.session`

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
Se estiver usando Arch Linux instale o Tkinter:
```bash
sudo pacman -S tk
```

## 🎨 Como Usar

```bash
python src/download_telegram_video_tags_gui.py
```

### Campos da interface

- **Canal/Grupo**: nome ou link do canal (ex: `@nomedocanal`)
- **Tags**: hashtags separadas por vírgula (somente no **Modo Tags**)
- **Modo**: escolha entre `Tags` e `Todos os Vídeos`
- **Pasta de saída**: diretório para salvar os downloads
- **Limite por tag**: no modo Tags, limite de mensagens por tag; no modo Vídeos, **limite de vídeos listados** (`0` = todos)
- **Nome da sessão**: arquivo de sessão usado (padrão `session`)
- **Linha do nome do vídeo**: qual linha da mensagem vira o nome do arquivo
- **Max Flood Wait (s)**: tempo máximo de espera automática de FloodWait

### 📹 Modo Tags
Busca no histórico do canal mensagens que contenham a hashtag informada e baixa os vídeos encontrados.

### 📺 Modo "Todos os Vídeos"
Enumera **todos os vídeos** do canal/grupo (sem depender de hashtags) e download direto via API — funciona em canais com proteção contra cópia/forward.

1. Selecione `Todos os Vídeos` (o campo Tags é desabilitado)
2. Defina o limite de vídeos a listar no campo **Limite por tag** (`0` = todos)
3. Clique em **Iniciar Download**
4. Um **pop-up de seleção** lista os vídeos com `[msg_id] título` e checkbox:
   - **[SELECIONAR TUDO]**: marca todos
   - **[LIMPAR]**: desmarca todos
   - **Baixar Selecionados (N)**: baixa apenas os marcados (o contador atualiza em tempo real)
   - **[CANCELAR]**: aborta sem baixar nada

### Configuração de Nomes de Arquivo
- **Primeira Linha**: usa a primeira linha da mensagem
- **Segunda Linha**: usa a segunda linha (ou a primeira, se não houver segunda)
- **Terceira Linha**: usa a terceira linha (ou a última disponível)
- **Última Linha**: usa a última linha (padrão)

### Dicas para Tags
As tags podem ser inseridas de várias formas, o sistema formata automaticamente:
- `tag1 tag2 tag3` → `tag1, tag2, tag3`
- `tag1,tag2,tag3` → `tag1, tag2, tag3`
- `tag1, tag2, tag3` → mantém a formatação
- Mistura de espaços e vírgulas também é aceita

### Recursos da GUI

- **Validação de Campos**: verifica campos obrigatórios e formatos
- **Progresso em Tempo Real**: porcentagem, velocidade (MB/s) e tempo estimado (ETA)
- **Log Detalhado**: status de conexão, vídeos encontrados, erros e avisos
- **Botão Parar**: cancela o download em andamento a qualquer momento
- **Nomes de Arquivo Dinâmicos**: primeira, segunda, terceira ou última linha da mensagem
- **Processamento Inteligente de Tags**: separação automática por vírgulas/espaços
- **Configurações Salvas**: preferências salvas em `config.json` (salvar/carregar)

## ⚠️ FloodWait (Limitação de Requisições)

Ao usar a API do Telegram é possível receber `FloodWaitError` quando a conta faz muitas requisições em pouco tempo. O app trata automaticamente:

- **Retry controlado** ao resolver a entidade do target
- **Retry automático** durante a iteração de mensagens
- **Controle via campo Max Flood Wait** na GUI

### Comportamento

- Se `FloodWait ≤ max-flood-wait`: aguarda automaticamente e continua
- Se `FloodWait > max-flood-wait`: aborta e informa o tempo necessário

### Valores Recomendados

- **0**: não aceitar waits automáticos (aborta imediatamente)
- **30-60**: aceitar waits curtos automaticamente
- **300** (padrão): aceita waits de até 5 minutos

### Boas Práticas

- Reduza o número de requisições por execução (use um limite menor)
- Espalhe as execuções no tempo (batches com intervalo)
- Use sessões diferentes se necessário
- Aguarde manualmente em caso de FloodWaits longos

## 📁 Arquivos Gerados

Após o download, você encontrará:

1. **Vídeos**: salvos na pasta especificada com nomes seguros
2. **CSV**: `videos_baixados.csv` com informações detalhadas:
   - **Tag usada**: a hashtag procurada, ou `video` no modo "Todos os Vídeos"
   - ID da mensagem
   - Data e hora
   - Nome do arquivo
   - Legenda completa

   > Há também um backup do CSV em `src/videos_baixados_*.csv` a cada execução.

## 🎨 Personalização da GUI

A interface usa **ttkbootstrap** com o tema escuro `darkly`. Para mudar o tema, altere em `src/download_telegram_video_tags_gui.py`:

```python
super().__init__(themename="darkly")  # ex: "darkly", "litera", "flatly", "cosmo"
```

## 🐛 Solução de Problemas

### Erro de conexão do Telegram
- Verifique suas credenciais API ID e API Hash
- Certifique-se de estar conectado à internet
- Se a sessão estiver inválida, o app reabrirá o login por modais automaticamente

### Flood Wait muito longo
- Aumente o valor de "Max Flood Wait"
- Ou aguarde manualmente e tente novamente mais tarde

### Erro "Can't find a usable init.tcl"
Este erro ocorre quando o Python não encontra as bibliotecas Tcl/Tk do sistema. O projeto inclui um script de correção automática (`src/tcl_fix.py`) que tenta localizar essas bibliotecas. Ele roda automaticamente ao iniciar a GUI, mas você pode executá-lo manualmente:

```bash
python src/tcl_fix.py
```

Se o script não encontrar as bibliotecas, instale-as no sistema (ex: `sudo apt install python3-tk tk-dev` no Linux).

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