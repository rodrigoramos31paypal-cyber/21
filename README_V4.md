# 21 Dias de Foco — V4, preparação de produção

Continuação da aplicação existente, a partir da main `82599129ab59c63e531a7a0accceff7405d6a4ac`. Branch de revisão: `codex/producao-segura`. Nenhuma autorização de merge ou publicação em produção foi concedida nesta tarefa.

## Alterações desta revisão

- Mantidos o design, os três percursos, calendário, cartões, tema, questionário em três passos, 10 receitas originais com imagens dos livros, plano de 21 dias, trocas/repetições, compras e checklists.
- Camada de persistência comum a SQLite local e PostgreSQL. Em Vercel/produção a aplicação recusa SQLite e uma chave de sessão ausente ou curta.
- Sessões de sete dias registadas por token com hash na base de dados, revogadas ao sair ou recuperar a palavra-passe. Cookies HttpOnly, SameSite=Lax e Secure em produção.
- Limite de tentativas partilhado na base de dados, validação de origem e dados no servidor. Perfil, plano e progresso ligados à sessão, com rejeição de gravações vindas de uma conta antiga noutro separador.
- Dados de contas deixam de ficar no armazenamento permanente do navegador. Alterações pendentes ficam no separador e só são reenviadas depois de confirmar a mesma conta. Importação de um perfil de visitante requer confirmação explícita.
- PDF exige sessão e acesso atribuído pelo servidor. Ficheiros retirados da árvore pública nesta branch; cópias locais em `private_materials/`, excluídas do Git/deployment. Produção usa bucket S3 privado e ligações de 60 segundos. As versões antigas do repositório público continuam a conter os PDFs: esta revisão não reescreve o histórico.
- Administradores atribuídos por operação explícita (`manage.py admin`), sem promoção automática por registar um endereço de email.
- Na conta de administrador: editar descrições/notas do dia e associar/remover vídeos HTTPS confirmados para receitas e 21 dias. Ingredientes, doses e fontes editoriais não são alterados por este editor.
- Verificação de email e recuperação de palavra-passe com tokens de uso único, válidos 30 minutos. Entrega dependente de SMTP.
- Checkout de teste: pagamento único de 2490 cêntimos/EUR, imposto pelo servidor. Chaves e eventos live recusados. Acesso só após webhook com assinatura, valor, moeda e conta verificados; eventos repetidos são idempotentes. Nunca se concede acesso pelo regresso à página de sucesso.
- Entrada Vercel `api/index.py` e configuração que encaminha todos os pedidos pelo Flask, incluindo os PDFs. O 404 de `/api/session` foi confirmado na versão pública anterior; a correção de routing ainda precisa de validação no alojamento.

## Conteúdos e limites editoriais

Os ficheiros `receitas.js` e `assets/receitas/` contêm uma seleção proveniente dos PDFs fornecidos pelo João Pedro. Cada receita indica volume e página. As imagens são as dos livros; a sua proveniência fotográfica original não foi certificada. Não foram geradas fotografias novas.

Os valores nutricionais são **indicativos**, conforme os originais; não foram sujeitos a validação nutricional independente. Não são calculadas metas diárias a partir de dados físicos. O objetivo ordena uma seleção curta de receitas pelo valor energético indicado no livro, sem alterar ingredientes ou doses. Esta organização não substitui uma prescrição alimentar.

As páginas selecionadas não forneceram ligações de vídeo correspondentes verificáveis. O campo `video` permanece `null`, com botão indisponível. Para ligar um vídeo, inserir o URL confirmado na receita respetiva; nunca um vídeo genérico atribuído como se fosse o original.

As restrições usam metadados conservadores dos ingredientes, incluindo potenciais componentes de opções do original. Confirmar sempre marcas, rótulos e contaminação cruzada. Há combinações sem receita nesta seleção (por exemplo, pequeno-almoço vegan); o ecrã apresenta essa lacuna, sem inventar receitas. Outras restrições em texto livre suspendem as sugestões automáticas até revisão.

## Executar e testar

Python 3.12 e Node 22:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
.venv/bin/python server.py
.venv/bin/python -m pytest tests -q
node tests/food.test.cjs
node tests/accounts.test.cjs
node --check app.js
node --check v4.js
```

Abrir http://127.0.0.1:8080. Para os PDFs locais, conservar os três originais em `private_materials/`. Sem esse diretório, os testes continuam a usar um PDF sintético em diretório temporário; não dependem dos materiais reais.

A suite pode usar PostgreSQL através de `TEST_DATABASE_URL` numa base **descartável**. Cada teste cria e remove um esquema próprio. O workflow em `.github/workflows/tests.yml` prepara SQLite e PostgreSQL 16. A existência do workflow não significa que já foi executado no GitHub; consultar os resultados do PR.

Consultar `CONFIGURACAO_PRODUCAO.md` antes de configurar o preview. As credenciais não fazem parte desta entrega.
