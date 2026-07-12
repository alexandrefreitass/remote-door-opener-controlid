# Remote Door Opener ControlID

Aplicacao web em Python + Flask para abrir portas por meio da API de equipamentos ControlID.

O sistema agora permite cadastrar os dados do equipamento pela interface, sem editar codigo ou mexer em arquivos de configuracao. Os equipamentos ficam salvos em um banco SQLite local.

## Funcionalidades

- Cadastro de equipamentos ControlID pela tela.
- Login simples para proteger o painel interno.
- Edicao, exclusao e ativacao do equipamento que sera usado para abertura.
- Persistencia local em SQLite.
- Importacao inicial a partir do `config.env` quando o banco ainda esta vazio.
- Painel de abertura com feedback de sucesso e erro.
- Campos configuraveis: nome, localizacao, IP/host, porta, login, senha e parametros da acao.

## Como rodar no Git Bash

Modo desenvolvimento:

```bash
cd "/d/Softwares/Sistemas/Sistemas/3 - Sistema ControlID/Sistema Abertura de Porta"
source venv/Scripts/activate
pip install -r requirements.txt
python main.py
```

Se o `config.env` estiver com `FLASK_PORT=80`, talvez seja necessario rodar o terminal como administrador. Para desenvolvimento local, prefira:

```env
FLASK_PORT=5000
```

Depois acesse:

```text
http://localhost:5000
```

Login padrao:

```text
No pacote publico nao existe login padrao.
No primeiro acesso, o sistema abre a tela "Primeiro acesso" para criar o usuario administrador.
```

## Como rodar em producao

Instale as dependencias:

```bash
cd "/d/Softwares/Sistemas/Sistemas/3 - Sistema ControlID/Sistema Abertura de Porta"
source venv/Scripts/activate
pip install -r requirements.txt
```

Inicie diretamente com Waitress, quando precisar diagnosticar pelo terminal:

```bash
python run_prod.py
```

Para uso normal no Windows, utilize o launcher grafico:

```text
release\ControleDeAcesso\ControleDeAcesso.exe
```

Ele abre uma janela com botoes para iniciar, parar e abrir o navegador. O launcher nao inicia junto com o Windows; ele so roda quando for aberto manualmente.
Se o servidor ja estiver rodando antes de abrir o launcher, ele detecta o processo do projeto e permite parar pela propria janela.

Para gerar novamente o executavel:

```text
build_launcher.bat
```

Para gerar o ZIP publico de distribuicao:

```text
build_release_zip.bat
```

O arquivo final fica em:

```text
public-release\ControleDeAcesso-v1.1.0.zip
```

Esse ZIP nao inclui `config.env`, banco SQLite, logs, `venv` ou credenciais reais. O build nao copia o pacote automaticamente para a landing page; ele deve ser revisado antes da publicacao.

## Landing page na Hostinger

A pasta `..\Landing Page\` contem a pagina HTML pronta para copiar diretamente para o `public_html` da Hostinger.

Estrutura esperada no servidor:

```text
public_html/
├── index.html
├── assets/
│   └── logo.png
└── downloads/
    └── pacote-publicado-apos-revisao.zip
```

O botao de download da landing aponta para:

```text
downloads/pacote-publicado-apos-revisao.zip
```

Para publicar, copie o conteudo de `..\Landing Page\` para `public_html`. Nao e necessario gerar ZIP da landing.

Com a configuracao padrao, o sistema fica disponivel em:

```text
http://IP-DO-COMPUTADOR:5000
```

Para descobrir o IP do computador no Windows:

```bash
ipconfig
```

Em producao, mantenha:

```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False
WAITRESS_THREADS=4
```

## Primeiro uso

1. Abra o sistema no navegador.
2. Clique em `Gerenciar equipamentos`.
3. Cadastre o ControlID com IP, porta, login, senha e parametros da acao.
4. Marque `Definir como equipamento ativo`.
5. Volte ao painel e clique em `Abrir porta`.

Se ja existir um `config.env`, o primeiro equipamento sera criado automaticamente usando esses dados quando o banco SQLite ainda nao tiver nenhum cadastro.

## Arquivos importantes

```text
main.py                  Aplicacao Flask, rotas, CRUD e integracao ControlID
run_prod.py              Entrada de producao com Waitress
launcher.py              Launcher grafico para iniciar/parar o servidor
build_launcher.bat       Gera release/ControleDeAcesso/ControleDeAcesso.exe
install_dependencies.bat Cria o venv e instala dependencias no computador do usuario
config.env.example       Exemplo publico sem credenciais reais
controlid_devices.db     Banco SQLite criado automaticamente em runtime
config.env               Configuracoes do Flask e importacao inicial opcional
templates/               Telas HTML
static/css/              Estilos da interface
requirements.txt         Dependencias Python
server.pid               Identifica a instancia em execucao; criado e removido em runtime
```

## Build verificavel no GitHub

O workflow `.github/workflows/build-windows.yml` gera o launcher, o ZIP e o arquivo SHA-256 em um runner Windows limpo. Ele pode ser executado manualmente pela aba Actions ou ao enviar uma tag `v*`.

A assinatura Authenticode e opcional e exige estes segredos no repositorio:

```text
WINDOWS_CERTIFICATE_BASE64
WINDOWS_CERTIFICATE_PASSWORD
```

Sem um certificado valido, o executavel continua funcional, mas permanece sem assinatura digital e pode receber alertas de reputacao.

## Variaveis opcionais do config.env

```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False
SECRET_KEY=troque-em-producao
DATABASE_PATH=controlid_devices.db
APP_USERNAME=admin
APP_PASSWORD=telecom2022
WAITRESS_THREADS=4

DEVICE_NAME=Porta Principal
DEVICE_LOCATION=Entrada
DEVICE_IP=10.0.0.50
DEVICE_PORT=80
DEVICE_LOGIN=admin
DEVICE_PASSWORD=SuaSenha
DEVICE_ACTION_PARAMETERS=id=65793,reason=3
```

## Producao

- Use o launcher grafico ou `python run_prod.py`, nao o servidor de desenvolvimento do Flask.
- Mantenha `FLASK_DEBUG=False`.
- Defina uma `SECRET_KEY` forte.
- Troque `APP_USERNAME` e `APP_PASSWORD` se o ambiente exigir outro login.
- Proteja o acesso ao painel, pois ele abre a porta e armazena credenciais locais.
- Rode atras de um proxy com HTTPS, como Nginx ou Apache.
- Nao versione `config.env` nem arquivos `.db`; eles estao no `.gitignore`.
