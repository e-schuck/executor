# Startup Launcher

Aplicativo Windows para configurar e gerenciar comandos executados automaticamente na inicialização do computador.

## Funcionalidades

- **Interface gráfica** (tkinter) para adicionar, editar e remover comandos
- **System tray** — roda em segundo plano após lançar os comandos configurados
- **Menu do tray** com opções de reiniciar/encerrar processos, abrir painel e fechar o programa
- **Auto-inicialização** — registre/desregistre o app no Registro do Windows com um clique
- **Delay configurável** por comando (segundos)
- **Execução minimizada** opcional por entrada
- **Teste individual** de cada comando diretamente pela GUI
- **Logging** em `startup_launcher.log` com timestamps
- **Notificações balloon** em caso de falha no lançamento

## Requisitos

- Windows 10/11
- Python 3.10+ (apenas para desenvolvimento/build)

## Instalação Rápida (usuário final)

1. Copie `StartupLauncher.exe` e `config.json` para a mesma pasta
2. Execute `StartupLauncher.exe`
3. Configure seus comandos pela interface gráfica
4. Clique em **Toggle Auto-Start** para ativar a execução automática no login

## Desenvolvimento

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Executar em modo desenvolvimento

```bash
python main.py
```

### Gerar o executável

Execute o script de build:

```cmd
build.bat
```

O executável será gerado em `dist/StartupLauncher.exe`.

> **Nota:** O build espera um arquivo `app.ico` na raiz do projeto. Se não tiver um ícone, edite `build.bat` e remova `--icon=app.ico`.

## Formato do config.json

```json
{
  "auto_start": true,
  "minimize_to_tray": true,
  "commands": [
    {
      "name": "Nome do Comando",
      "command": "caminho\\para\\executavel.exe",
      "args": "argumentos opcionais",
      "workdir": "C:\\diretorio\\de\\trabalho",
      "enabled": true,
      "delay_seconds": 5,
      "run_minimized": false
    }
  ]
}
```

| Campo | Descrição |
|---|---|
| `name` | Rótulo exibido na interface |
| `command` | Caminho completo ou nome do executável |
| `args` | Argumentos de linha de comando (opcional) |
| `workdir` | Diretório de trabalho (opcional) |
| `enabled` | `true`/`false` para ativar/desativar |
| `delay_seconds` | Segundos de espera antes de lançar |
| `run_minimized` | `true` para ocultar a janela do processo |

## Estrutura do Projeto

```
windows-startup-launcher/
├── main.py              # GUI + lógica principal
├── config_manager.py    # Leitura/escrita do config.json
├── launcher.py          # Gerenciamento de subprocessos
├── tray_icon.py         # Integração com system tray
├── config.json          # Configuração padrão
├── build.bat            # Script de build PyInstaller
├── requirements.txt     # Dependências Python
└── README.md            # Este arquivo
```

## Menu do System Tray

Clique com o botão direito no ícone da bandeja para acessar:

| Opção | Descrição |
|---|---|
| **Reiniciar todos os processos** | Encerra todos os processos gerenciados e os reinicia respeitando `delay_seconds` e `enabled` de cada entrada |
| **Encerrar todos os processos** | Encerra todos os processos gerenciados sem reiniciá-los |
| **Abrir painel** | Restaura a janela principal da interface gráfica (tkinter) |
| **Fechar programa** | Encerra todos os processos, remove o ícone do tray e fecha o aplicativo completamente |

Todas as ações são registradas em `startup_launcher.log`.

## Logs

Os logs são gravados em `startup_launcher.log` na mesma pasta do executável, com formato:

```
2026-11-11 13:00:00 [INFO] [OmniRoute] Starting: npx omniroute
2026-11-11 13:00:01 [INFO] [OmniRoute] Launched successfully
2026-11-11 13:00:02 [ERROR] [Qdrant] Command not found: D:\Apps\Qdrant\qdrant.exe
```

## Licença

Uso livre. Sem garantias.