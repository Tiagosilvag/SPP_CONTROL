# SPP - Control

Sistema web de gestão de estoque, patrimônio, compras, licitações e
auditoria para administração pública, desenvolvido em **Flask (Python) +
PostgreSQL + Bootstrap 5**.

O sistema foi pensado em **módulos independentes** (blueprints do Flask),
para permitir a inclusão de novas funcionalidades no futuro sem afetar o
que já existe.

---

## 1. Módulos do sistema

| Módulo | O que faz |
|---|---|
| **Dashboard** | Indicadores gerais: estoque crítico, compras pendentes, pedidos atrasados, patrimônios emprestados/em manutenção, e gráficos por secretaria/fornecedor/obra |
| **Secretarias** | Cadastro das secretarias municipais |
| **Unidades** | Cadastro das unidades/locais de cada secretaria |
| **Materiais** | Cadastro de materiais consumíveis e patrimoniais, com estoque mínimo |
| **Fornecedores** | Cadastro de fornecedores |
| **Obras** | Cadastro de obras/serviços que consomem materiais |
| **Patrimônio** | Cadastro individual de bens (nº de patrimônio, estado, status, localização) |
| **Entradas de Estoque** | Registro de recebimento de materiais (compra/doação), com vínculo opcional a um pedido de compra |
| **Movimentações (Consumíveis)** | Consumo em obra, transferência (entre unidades e entre obras), retorno, devolução e empréstimo (secundário) |
| **Movimentações (Patrimônio)** | Transferência (entre unidades e entre obras), devolução, empréstimo, retorno e manutenção |
| **Saldo em Estoque** | Relatório calculado automaticamente a partir do histórico de Entradas e Movimentações |
| **Pedidos de Compra** | Cabeçalho + itens, cálculo automático de saldo pendente, alerta de duplicidade, planejamento de entrega e atrasos |
| **Recebimento Parcial** | Múltiplos recebimentos por pedido, baixa automática do saldo, geração automática da Entrada de Estoque correspondente, encerramento automático do pedido |
| **Licitações** | Cadastro de processos licitatórios (categoria, modalidade, objeto, processo, valores estimado/homologado) |
| **Cotação x Projeto** | Comparação de preços entre vários fornecedores por cotação, com cálculo de economia em relação ao valor estimado |
| **Relatórios** | Exportação em PDF e Excel, com filtros, para 13 áreas do sistema (estoque, entradas, saídas, patrimônio, pedidos, compras, fornecedores, licitações, auditoria, movimentações, obras, secretarias, unidades) |
| **Usuários** | Gestão de contas e perfis (Administrador/Gestor/Operador) — restrito a Administradores |
| **Auditoria** | Histórico de todas as operações de escrita (quem, quando, IP, tabela, valor anterior/novo) |

### Regras de negócio

- O **saldo de estoque** de cada material/secretaria é sempre recalculado a
  partir do histórico de Entradas e Movimentações (nunca fica desatualizado).
- O sistema **bloqueia** o registro de consumo/empréstimo de um consumível se
  a quantidade solicitada for maior que o saldo disponível.
- Ao registrar uma movimentação de **patrimônio**, o status e a localização
  atual do bem são **atualizados automaticamente**.
- Alertas de estoque: **Crítico** (abaixo do mínimo), **Atenção** (até 50%
  acima do mínimo) e **OK**.
- **Pedidos de Compra**: a quantidade pendente de cada item é sempre
  calculada (`solicitada - atendida`), nunca armazenada, para não haver
  divergência. O status do pedido (`Enviado` → `Parcialmente Recebido` →
  `Recebido`) é recalculado automaticamente a cada recebimento.
- **Duplicidade de pedidos**: antes de gravar, o sistema procura um pedido
  não cancelado com o mesmo fornecedor, responsável, data e ao menos um
  material em comum, e pede confirmação antes de salvar mesmo assim.
- **Perfis de acesso**: `Administrador` (tudo, inclusive usuários),
  `Gestor` (tudo, exceto usuários) e `Operador` (módulos operacionais do
  dia a dia — estoque, patrimônio, movimentações — mas não Compras,
  Licitações, Relatórios ou Auditoria).
- **Auditoria**: toda operação de escrita feita pela aplicação é registrada
  automaticamente (usuário, data/hora, IP, tabela, valor anterior e novo),
  na mesma transação da alteração.
- **Rastreio de criação/edição**: cadastros e movimentações também têm suas
  próprias colunas `criado_por`/`criado_em`/`atualizado_por`/`atualizado_em`,
  preenchidas sozinhas por `db.execute()` (ver `TABELAS_RASTREADAS` em
  `db.py`) — os blueprints não precisam informar isso manualmente. No
  front, só o nome de quem cadastrou/movimentou aparece (coluna
  "Cadastrado por"/"Registrado por"); os detalhes completos de cada
  alteração ficam no módulo de Auditoria.

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

# 5. Rode a aplicação (cria/atualiza as tabelas automaticamente)
python app.py
```

Acesse no navegador: **http://localhost:5000**

Na primeira execução, como a tabela de usuários está vazia, o sistema leva
automaticamente para **`/auth/setup`**, onde você cria a primeira conta de
**Administrador**. Depois disso, o acesso é sempre por login (`/auth/login`).

> Se você já tinha dados no antigo `instance/spp_control.db` (SQLite), rode
> `python migrate_sqlite_to_postgres.py` (com `DATABASE_URL` definida) para
> copiá-los para o PostgreSQL antes de subir a aplicação em produção.

---

## 4. Estrutura do projeto

```
spp_control/
├── app.py                     # Cria e configura a aplicação Flask, autenticação global
├── config.py                   # Configurações gerais
├── db.py                       # Conexão com o PostgreSQL + auditoria automática
├── auth.py                     # Login, hash de senha, decorators de perfil
├── schema.sql                   # Definição/evolução das tabelas do banco (idempotente)
├── services.py                  # Regras de negócio de estoque e patrimônio
├── services_compras.py           # Regras de Pedidos de Compra e Recebimento Parcial
├── services_cotacoes.py          # Regras de Cotação x Fornecedor
├── services_relatorios.py        # Consultas usadas pelo módulo de Relatórios
├── export_utils.py               # Exportação genérica para Excel (openpyxl) e PDF (reportlab)
├── seed_data.py                   # Importa a planilha original para um SQLite local (uso histórico)
├── migrate_sqlite_to_postgres.py  # Migra dados do SQLite antigo para o PostgreSQL
├── requirements.txt
├── data/
│   └── Controle_Materiais_SPP.xlsx
├── blueprints/                    # Um arquivo por módulo do sistema
└── templates/                      # HTML de cada módulo (Bootstrap 5, tema claro/escuro)
```

---

## 5. Como adicionar um novo módulo no futuro

1. Crie/altere a tabela necessária em `schema.sql` (use `CREATE TABLE IF NOT
   EXISTS` e `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para manter idempotente).
2. Crie um arquivo em `blueprints/nome_do_modulo.py` com as rotas.
3. Crie a pasta `templates/nome_do_modulo/` com os HTMLs.
4. Registre o blueprint em `app.py`.
5. Adicione o link no menu lateral em `templates/base.html`.
6. Se o módulo precisar de dados no Relatórios, adicione uma entrada em
   `services_relatorios.py` (`REPORTS`).

---

## 6. Observações importantes

- **Backup**: o banco de dados é PostgreSQL. Use `pg_dump` (ou a aba
  **Backups** do serviço no Coolify) para gerar backups regulares.
- **Ambiente de produção**: o comando `python app.py` sobe um servidor de
  desenvolvimento. Para uso real, o Coolify já usa `gunicorn` via Nixpacks.
- **Anexos (PDF/XML/imagem)**: os módulos de Licitações, Cotações e Entradas
  de Estoque ainda não têm upload de arquivo — decisão pendente de definir o
  storage (volume persistente vs. S3), já que o container da aplicação é
  recriado a cada deploy.
