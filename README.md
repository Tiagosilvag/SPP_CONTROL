# SPP - Control

Sistema web de controle de materiais, estoque e patrimônio, desenvolvido em
**Flask (Python) + HTML/Bootstrap**, com base na planilha
`Controle_Materiais_SPP.xlsx`.

O sistema foi pensado em **módulos independentes**, para permitir a inclusão
de novas funcionalidades no futuro (ex: relatórios, usuários com login,
outros tipos de controle) sem afetar o que já existe.

---

## 1. Módulos incluídos nesta primeira versão

| Módulo | O que faz |
|---|---|
| **Dashboard** | Indicadores gerais: estoque crítico, empréstimos em atraso, últimas movimentações |
| **Secretarias** | Cadastro das secretarias municipais |
| **Unidades** | Cadastro das unidades/locais de cada secretaria |
| **Materiais** | Cadastro de materiais consumíveis e patrimoniais, com estoque mínimo |
| **Fornecedores** | Cadastro de fornecedores |
| **Obras** | Cadastro de obras/serviços que consomem materiais |
| **Patrimônio** | Cadastro individual de bens (nº de patrimônio, estado, status, localização) |
| **Entradas de Estoque** | Registro de recebimento de materiais (compra/doação) |
| **Movimentações (Consumíveis)** | Consumo em obra, empréstimo, transferência e devolução de itens consumíveis |
| **Movimentações (Patrimônio)** | Empréstimo, transferência, manutenção e devolução de bens patrimoniais |
| **Saldo em Estoque** | Relatório calculado automaticamente (substitui a aba "Estoque_Consumiveis" da planilha) |

### Regras de negócio já implementadas
- O **saldo de estoque** de cada material/secretaria é sempre recalculado a
  partir do histórico de Entradas e Movimentações (nunca fica desatualizado
  como em uma planilha).
- O sistema **bloqueia** o registro de consumo/empréstimo de um consumível se
  a quantidade solicitada for maior que o saldo disponível.
- Ao registrar uma movimentação de **patrimônio** (empréstimo, devolução,
  transferência, manutenção), o status e a localização atual do bem são
  **atualizados automaticamente** — sem precisar editar o cadastro à mão.
- Alertas de estoque: **Crítico** (abaixo do mínimo), **Atenção** (até 50%
  acima do mínimo) e **OK**.

---

## 2. Requisitos

- Python 3.10 ou superior
- Um banco **PostgreSQL** acessível (local ou remoto, ex: instância criada no
  Coolify). A string de conexão é lida da variável de ambiente
  `DATABASE_URL` (formato `postgresql://usuario:senha@host:porta/banco`).

---

## 3. Instalação e primeira execução

```bash
# 1. Entre na pasta do projeto
cd spp_control

# 2. (Recomendado) crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure a conexão com o PostgreSQL
export DATABASE_URL="postgresql://usuario:senha@host:porta/banco"   # Linux/Mac
$env:DATABASE_URL = "postgresql://usuario:senha@host:porta/banco"   # Windows PowerShell

# 5. Rode a aplicação (cria as tabelas automaticamente na primeira execução)
python app.py
```

Acesse no navegador: **http://localhost:5000**

> Se você já tinha dados no antigo `instance/spp_control.db` (SQLite), rode
> `python migrate_sqlite_to_postgres.py` (com `DATABASE_URL` definida) para
> copiá-los para o PostgreSQL antes de subir a aplicação em produção.

---

## 4. Estrutura do projeto

```
spp_control/
├── app.py                # Cria e configura a aplicação Flask (todos os módulos)
├── config.py              # Configurações gerais
├── db.py                  # Conexão com o banco PostgreSQL
├── schema.sql              # Definição das tabelas do banco
├── services.py             # Regras de negócio (cálculo de estoque, status de patrimônio)
├── seed_data.py             # Importa os dados da planilha original para um SQLite local (uso histórico)
├── migrate_sqlite_to_postgres.py   # Migra dados do SQLite antigo para o PostgreSQL
├── requirements.txt
├── data/
│   └── Controle_Materiais_SPP.xlsx   # Planilha original (dados de exemplo)
├── blueprints/              # Um arquivo por módulo do sistema
│   ├── dashboard.py
│   ├── secretarias.py
│   ├── unidades.py
│   ├── materiais.py
│   ├── fornecedores.py
│   ├── obras.py
│   ├── patrimonio.py
│   ├── entradas.py
│   ├── mov_consumiveis.py
│   └── mov_patrimonio.py
└── templates/                # HTML de cada módulo (Bootstrap 5)
```

---

## 5. Como adicionar um novo módulo no futuro

O sistema foi organizado em **blueprints** do Flask — cada módulo é
independente. Para criar um novo módulo (ex: "Relatórios", "Usuários"):

1. Crie a tabela necessária em `schema.sql`.
2. Crie um arquivo em `blueprints/nome_do_modulo.py` com as rotas.
3. Crie a pasta `templates/nome_do_modulo/` com os HTMLs.
4. Registre o blueprint em `app.py` (`app.register_blueprint(...)`).
5. Adicione o link no menu lateral em `templates/base.html`.

---

## 6. Observações importantes / próximos passos sugeridos

- **Autenticação de usuários**: esta versão não tem tela de login. Já existe
  uma tabela `usuarios` reservada no banco para quando esse módulo for
  desenvolvido.
- **Backup**: o banco de dados é PostgreSQL. Use `pg_dump` (ou a aba
  **Backups** do serviço no Coolify) para gerar backups regulares.
- **Ambiente de produção**: o comando `python app.py` sobe um servidor de
  desenvolvimento. Para uso real (produção), recomenda-se rodar atrás de um
  servidor WSGI como `gunicorn` ou `waitress`, e configurar HTTPS.
- **Relatórios/exportação**: um próximo módulo natural seria exportação de
  relatórios em PDF/Excel a partir das telas de Estoque e Patrimônio.
