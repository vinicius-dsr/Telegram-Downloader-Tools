# Telegram Downloader Tools

Este projeto permite baixar vídeos do Telegram utilizando múltiplas hashtags. É uma ferramenta útil para coletar conteúdo de canais ou grupos específicos.

## Pré-requisitos

- Python 3.6 ou superior
- Telethon
- Pandas

## Obter API ID e API Hash

1. Acesse https://my.telegram.org e faça login com seu número de telefone.
2. Depois do login, clique em "API development tools".
3. Preencha o formulário para criar uma nova aplicação (App title, Short name, etc.). Ao finalizar, você verá o seu "api_id" e "api_hash".

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/vinicius-dsr/Telegram-Downloader-Tools.git
   cd telegram-downloader-tools
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

## Uso

Para usar a ferramenta, execute o seguinte comando:

```
python src/download_telegram_video_tags.py --api-id SEU_API_ID --api-hash SEU_API_HASH --target "https://t.me/nomeCanal" --tags "#tag1,#tag2" --out "./downloads"
```

## Contribuição

Sinta-se à vontade para contribuir com melhorias ou correções. Faça um fork do repositório e envie um pull request.

## Licença

Este projeto está licenciado sob a MIT License.
