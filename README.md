# ImóvelPro — Sistema de Gestão Imobiliária

O **ImóvelPro** é um sistema desktop e web para organizar a operação de uma imobiliária: imóveis, clientes, corretores, contratos, boletos e indicadores. O projeto também é um portfólio de desenvolvimento de software feito no contexto de Engenharia de Computação, com foco em boas práticas, persistência relacional e evolução gradual da arquitetura.

## Objetivos do projeto

- Aplicar boas práticas de programação e organização de código.
- Persistir informações imobiliárias em um banco de dados relacional.
- Consolidar as funcionalidades principais e facilitar a manutenção do sistema.
- Evoluir a arquitetura para suportar múltiplos usuários.
- Usar Git e GitHub no versionamento e na documentação.
- Explorar conteinerização para simplificar a instalação e a execução.

## Estado atual

O aplicativo está em desenvolvimento e já oferece interfaces desktop e web. Ambas usam o mesmo banco SQLite local. O dashboard apresenta indicadores, alertas e relatórios operacionais; a gestão de imóveis inclui proprietários, fotos, filtros, ordenação e exportação CSV. O status dos imóveis é recalculado conforme os contratos.

A aplicação atualmente usa **Python, CustomTkinter, FastAPI e SQLite**. PostgreSQL e Docker fazem parte dos objetivos de evolução e ainda não são necessários para executar a versão atual.

## Requisitos

- Python 3.10 ou superior.
- Tkinter (incluído na maioria das instalações do Python; no Linux pode ser necessário instalar `python3-tk`).
- Dependências Python listadas em `requirements.txt`.

## Instalação

Na pasta do repositório:

```bash
python -m pip install -r requirements.txt
```

A interface desktop também requer CustomTkinter, incluído nas dependências.

## Executar a versão desktop

```bash
python main.py
```

No Windows, também é possível abrir `ImovelPro.pyw` com dois cliques.

## Executar a versão web

```bash
python web_app.py
```

Acesse `http://127.0.0.1:8000`. A versão web usa o mesmo banco SQLite da interface desktop, então os dados são compartilhados. O servidor aceita conexões do próprio computador por padrão. Para permitir acesso pela rede local, configure `IMOVELPRO_WEB_HOST=0.0.0.0` e ajuste o firewall. Não exponha o servidor diretamente à internet.

No Windows, `ImovelProWeb.pyw` inicia o servidor e abre o navegador padrão.

## Funcionalidades atuais

- **Dashboard:** KPIs, contratos recentes, alertas de boletos, gráficos e relatórios de estoque disponível por cidade, contratos com término previsto e boletos vencidos. Os relatórios podem ser exportados em CSV; o período de vencimentos pode ser ajustado para 30, 60 ou 90 dias.
- **Imóveis:** cadastro urbano e rural, múltiplos proprietários e percentuais de posse, fotos e detalhes. A lista oferece busca e filtros por categoria, finalidade, status, cidade e faixa de preço, além de ordenação e exportação dos resultados filtrados em CSV.
- **Clientes:** perfis de proprietário e interessado, que podem coexistir, e múltiplos telefones.
- **Corretores:** cadastro com CPF e CRECI únicos e múltiplos telefones.
- **Contratos:** venda ou aluguel, múltiplos adquirentes, cedentes e corretores com percentuais de comissão.
- **Boletos:** registros vinculados aos contratos, com ação para marcar pagamento.

## Banco de dados

O arquivo `imovel_pro.db` é criado automaticamente na primeira execução, com dados de demonstração quando o banco está vazio. O arquivo de banco local é ignorado pelo Git para evitar versionar dados de trabalho. Faça cópias de segurança regulares se inserir dados próprios.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Próximos passos

- Consolidar e aprimorar a arquitetura e a manutenção do código.
- Aumentar a cobertura e a validação dos testes.
- Avaliar a migração de SQLite para PostgreSQL para cenários com múltiplos usuários.
- Adicionar configuração por Docker para facilitar ambientes de desenvolvimento e execução.
- Explorar envio de cobranças via WhatsApp, assistência na redação de contratos e integração com consultas de crédito, quando houver serviços e autorizações adequados.
- Desenvolver alertas que aproximem imóveis recém-cadastrados das preferências de clientes interessados.
- Avaliar a evolução para marketplace e publicação assistida em portais imobiliários.

---

Projeto de portfólio em Engenharia de Computação.
