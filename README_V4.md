# 21 Dias de Foco — V4 para revisão

Esta versão altera a aplicação existente do Rodrigo. Não é um protótipo HTML separado. Está preparada na branch local `codex/v4-onboarding-alimentacao`, a partir de `68cc0f5ec43c125dc61ce9a190c9db9b36141a24`. Não foi enviada para o GitHub, integrada na main ou publicada.

## Alterações

- Recuperação do HTML e das regras de apresentação do commit original `eecc842`, conservando a arquitetura e os materiais. O HTML da main recebida estava reduzido a texto simples.
- Correção da inicialização interrompida por referências ao login removido, da função de mensagens em falta, do escape HTML e da estrutura das secções.
- Questionário em três passos: nome; dados físicos opcionais; objetivo; local, experiência e disponibilidade; preferências, alergias, outras restrições e refeições. Edição posterior disponível.
- Hoje com imagem, descrição, ingredientes, preparação, indicação da dose, valores indicativos, marcação persistente e troca de receita.
- Plano de 21 dias, em três semanas de sete dias, com repetição no dia seguinte ou noutra semana. Repetir substitui as escolhas do destino mediante confirmação.
- Biblioteca inicial limitada a **10 receitas** dos dois e-books, com filtros. Não representa a transcrição integral dos livros.
- Compras calculadas a partir das receitas da semana escolhida, com soma de quantidades, intervalos preservados, checklist persistente e exportação TXT. PDF original continua disponível.
- Contas no backend Flask/SQLite existente: palavra-passe com hash, cookie de sessão, perfil/plano/progresso por participante, validação no servidor e proteção das rotas de administração.
- Mantidos os três percursos de treino, calendário, cartões, PDFs, ligação WhatsApp e tema escuro.

## Conteúdos e limites editoriais

Os ficheiros `receitas.js` e `assets/receitas/` contêm uma seleção proveniente dos PDFs fornecidos pelo João Pedro. Cada receita indica volume e página. As imagens são as dos livros; a sua proveniência fotográfica original não foi certificada. Não foram geradas fotografias novas.

Os valores nutricionais são **indicativos**, conforme os originais; não foram sujeitos a validação nutricional independente. Não são calculadas metas diárias a partir de dados físicos. O objetivo ordena uma seleção curta de receitas pelo valor energético indicado no livro, sem alterar ingredientes ou doses. Esta organização não substitui uma prescrição alimentar.

As páginas selecionadas não forneceram ligações de vídeo correspondentes verificáveis. O campo `video` permanece `null`, com botão indisponível. Para ligar um vídeo, inserir o URL confirmado na receita respetiva; nunca um vídeo genérico atribuído como se fosse o original.

As restrições usam metadados conservadores dos ingredientes, incluindo potenciais componentes de opções do original. Confirmar sempre marcas, rótulos e contaminação cruzada. Há combinações sem receita nesta seleção (por exemplo, pequeno-almoço vegan); o ecrã apresenta essa lacuna, sem inventar receitas. Outras restrições em texto livre suspendem as sugestões automáticas até revisão.

## Executar localmente

Requer Python 3.10 ou posterior:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py
```

Abrir http://127.0.0.1:8080. Sem conta, o perfil e o progresso ficam no navegador. Para testar a sincronização, criar uma conta local em «A minha conta»; não usar credenciais reais nos testes.

O SQLite é criado em `instance/foco.db`, excluído do Git e dos pacotes. O servidor serve apenas os ficheiros da aplicação e assets, sem expor código Python ou base de dados. Uma base de dados antiga pode ser ligada por `FOCO_DB`, após cópia de segurança; as tabelas originais são conservadas e a tabela `account_state` é acrescentada.

## Antes de ligar contas ao alojamento Vercel

O alojamento estático atual não executa, por si só, este servidor Flask. **As contas da V4 foram testadas localmente; não estão ativas no site público.**

Rodrigo deve ligar `/api/*` ao backend, definir `SECRET_KEY` estável e `COOKIE_SECURE=1` em HTTPS e usar base de dados persistente. Não usar SQLite em armazenamento efémero de funções serverless. Para PostgreSQL será necessário adaptar a camada de persistência, mantendo os contratos desta API.

Configurar o administrador com `FOCO_ADMIN_EMAIL`. Sem essa variável, nenhuma conta recebe acesso de administrador. Antes do uso comercial, continuam pendentes a integração de pagamento, recuperação/verificação de email, monitorização, proteção distribuída contra abuso, consentimentos/privacidade, backups e proteção dos materiais pagos. Não apresentar as contas como um sistema comercial concluído.

## Verificação

```sh
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest tests/test_accounts.py -q
node tests/food.test.cjs
node --check app.js
node --check v4.js
```

Os testes cobrem isolamento entre contas, sessão obrigatória, acesso a ficheiros privados, autenticação, gravação/releitura, tentativas de introduzir receitas incompatíveis e quantidades de compras após uma troca.

No navegador: questionário sem dados físicos, navegação, exercícios dos percursos casa/ginásio/glúteos, marcação de tarefa, troca de receita, ingredientes/preparação, persistência após recarregar, sete dias por semana, dia 21, repetição no dia seguinte, filtro vegan e download de compras. Layout verificado a 390 × 844 e 1440 × 1000. Não equivale a um teste num iPhone físico/Safari.

## Integrar sem tocar na main

1. Guardar qualquer trabalho em curso do Rodrigo e obter o estado mais recente do repositório.
2. Criar uma branch a partir da main atual. Aplicar o patch V4 ou rever o commit fornecido; resolver diferenças caso a main tenha avançado.
3. Executar os testes e testar a pré-visualização. A exportação ZIP inclui os ficheiros, assets e testes; não inclui contas, credenciais nem bases de dados.
4. Rever receitas, imagens e valores com o João Pedro. Acrescentar os links de vídeo confirmados e completar a seleção, se necessário.
5. Corrigir o acesso de escrita da integração GitHub e investigar o estado Vercel `Deployment was blocked` do commit base. Não assumir que a main atual corresponde à versão pública.
6. Abrir um pedido de revisão para o João Pedro. **Não fazer merge nem publicar em produção sem autorização.**
