# Configuração e aceitação do preview

Estado: implementação para revisão; não pronta para vendas até concluir os testes de serviços externos. Não integrar nem promover para produção sem autorização do João Pedro.

## 1. Acessos

A conta GitHub no navegador tem acesso ao repositório. A integração API devolveu HTTP 403 ao tentar criar uma branch; o envio pode ser efetuado pelo navegador autorizado. A conta Vercel criada pelo João Pedro não herda o projeto do Rodrigo. É necessário acesso ao projeto original ou um projeto separado de revisão, ligado à branch `codex/producao-segura`. Não alterar a branch/domínio de produção existente.

Antes de importar o repositório na nova conta, confirmar que o primeiro deployment não promove alterações no site existente. O preview deve usar domínio separado e base de dados própria. Configurar o framework/build de acordo com `vercel.json`, sem definir output estático que contorne a função.

## 2. PostgreSQL

Criar uma base de dados PostgreSQL persistente em região adequada, com ligação TLS e backups. Configurar `DATABASE_URL` apenas no ambiente Preview; não usar uma base de produção para testes. Usar a ligação com pooling fornecida pelo alojamento, caso disponível; o código usa NullPool para não manter ligações em funções efémeras.

Executar com as variáveis desse ambiente carregadas por um gestor de segredos:

```sh
python manage.py migrate
```

A migração é idempotente e cria tabelas ausentes. Não importa dados de SQLite para PostgreSQL nem altera o esquema de tabelas existentes. Se existirem contas reais locais, fazer backup e planear uma importação explícita antes da transição. Não foi encontrada nem migrada uma base comercial nesta tarefa.

Configurar `SECRET_KEY` aleatória com pelo menos 32 caracteres e estável entre deployments. A perda/rotação desta chave termina as sessões. Definir `APP_ORIGIN` com a origem HTTPS exata do preview. O exemplo `.env.example` lista as variáveis; não colocar valores reais em commits nem em mensagens.

## 3. Administração e materiais

Criar a conta do proprietário pela aplicação e atribuir o papel por operação autenticada de manutenção:

```sh
python manage.py admin --email EMAIL_CONFIRMADO
python manage.py grant --email EMAIL_CONFIRMADO
python manage.py revoke --email EMAIL_CONFIRMADO
```

`admin` concede administração e leitura dos materiais. `grant` concede só materiais. `revoke` remove ambos. As operações invalidam sessões. Não atribuir permissões a endereços sem confirmar quem controla a conta.

Carregar `guia.pdf`, `treinos.pdf` e `checklist_compras.pdf` num bucket S3 **privado**, com bloqueio de acesso público. Não existe upload automático nesta entrega. Configurar bucket, prefixo, região e credenciais com permissão mínima de `s3:GetObject` nos três objetos. O servidor emite uma ligação temporária de 60 segundos só após verificar sessão e direito de acesso. Nunca usar ACL pública.

Os PDFs antigos continuam disponíveis na main e no histórico público do GitHub. Retirar os ficheiros de uma branch não apaga essas cópias. Decidir com o proprietário se torna o repositório privado e como trata as versões históricas; nenhuma alteração de visibilidade ou reescrita de histórico foi efetuada.

## 4. Email

Configurar SMTP com TLS/STARTTLS, remetente autorizado e `APP_ORIGIN`. Testar receção real de verificação e recuperação numa caixa controlada pelo proprietário. Tokens não são devolvidos pela API, ficam com hash na base e expiram em 30 minutos. A recuperação revoga todas as sessões da conta.

Sem SMTP, o serviço responde 503 e a interface informa que ainda não está configurado. A entrega real e a reputação do remetente não foram verificadas localmente. A resposta ao pedido não revela se um email está registado; falhas SMTP são registadas sem credenciais.

## 5. Stripe e MB WAY — só teste

Configurar uma chave `sk_test_`, segredo de webhook de teste e `STRIPE_TEST_CHECKOUT=1`. Sem estas condições, o checkout fica indisponível. Esta versão recusa chaves `sk_live_` e eventos `livemode=true`, sem interruptor para os ativar.

No Stripe de teste, registar `/api/stripe/webhook` e os eventos `checkout.session.completed` e `checkout.session.async_payment_succeeded`. Confirmar o email da conta antes de iniciar o checkout. O preço é fixo: 24,90 €, uma vez, EUR. Métodos de pagamento são apresentados dinamicamente pelo Stripe; habilitar MB WAY no Dashboard e testar a elegibilidade. Não afirmar que MB WAY está operacional antes desse teste.

Não existe um produto/preço Stripe real criado por esta tarefa. Os testes locais simulam a criação de Checkout e usam assinaturas HMAC de teste reais para validar o webhook. Não houve transação nem cobrança. Reembolsos, litígios, faturação fiscal, termos, política de acesso após 21 dias e aprovação de ativação live continuam a exigir definição antes das vendas. Concessões `stripe-test` devem existir apenas na base isolada do preview.

## 6. Aceitação no alojamento

- `/api/health` responde 200 depois da migração; `/api/session` devolve JSON e não 404.
- Criar duas contas de teste: cada uma vê apenas o seu perfil, refeições e check-ins. Testar troca de conta, recarregamento e sessão expirada.
- Sem sessão, PDF responde 401; conta sem acesso recebe 403; administrador/conta autorizada recebe ligação temporária. Testar também URL direto e diretório privado.
- Verificar cookie Secure/HttpOnly/SameSite, recuperação por email e reutilização de token recusada.
- Criar Checkout de teste, concluir cartão e MB WAY de teste, verificar assinatura, repetição de evento e conta de destino. A página de sucesso sozinha não pode dar acesso.
- Executar os testes com PostgreSQL e verificar o resultado do workflow. Confirmar que o código do preview corresponde à branch do PR.
- Rever interface em desktop e telemóvel e confirmar receitas, fotografias e vídeos com o João Pedro.

## Referências técnicas

- Flask na Vercel: https://vercel.com/docs/frameworks/backend/flask
- MB WAY no Checkout: https://docs.stripe.com/payments/mb-way/accept-a-payment?payment-ui=checkout
- Webhooks Stripe: https://docs.stripe.com/webhooks
- S3, ligações temporárias: https://docs.aws.amazon.com/boto3/latest/guide/s3-presigned-urls.html
