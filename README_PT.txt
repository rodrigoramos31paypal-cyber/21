21 DIAS DE FOCO · PROTÓTIPO DA MINI WEB APP

COMO ABRIR:
- Abrir index.html num computador ou num servidor local.
- Para testar num telemóvel, é preferível colocar os ficheiros num servidor de teste privado (HTTPS).
- Menus: Início, O meu dia, O meu plano.
- Escolher dia 1-21 e um dos três percursos. Marcar check-ins.
- O progresso da demonstração é guardado SÓ no navegador local (localStorage).

COMO LIGAR VÍDEOS:
- Editar conteudos.js -> videoUrls. Exemplo: "1": "https://youtu.be/ID".
- Os vídeos do YouTube não listados são acessíveis a qualquer pessoa com o link.

AVISO IMPORTANTE: NÃO PUBLICAR ESTA PASTA COMO ÁREA PAGA.
É um protótipo funcional de interface, NÃO tem login, backend, controlo de acessos,
pagamentos, histórico por participante, nem sincronização entre dispositivos.
Os 3 PDFs incluídos em assets/ são abertos diretamente; ficam públicos se
a pasta for alojada num site público. Para produção, colocar materiais em
armazenamento privado e autorizar cada download pelo servidor.

PARA VERSÃO COMERCIAL / TAREFAS PARA O RODRIGO:
1. Login seguro e base de dados de participantes (sem guardar dados de saúde sensíveis por defeito).
2. Pagamento único Stripe/MB WAY, com webhook no servidor e concessão de acesso.
3. Guardar tarefas e check-ins por utilizador e por dia, em backend.
4. Liberar dia N conforme data inicial da edição; permitir retomas.
5. Vídeos por dia e percurso, numa tabela de configuração.
6. Recursos privados (e-books e PDFs), com autorização e links temporários.
7. Política de acesso após dia 21, privacidade, consentimentos e suporte.
8. Testar compra, erro de pagamento, reembolso, acesso negado e 100 utilizadores.
9. Integrar na AtuaApp se ela já suportar esses requisitos; se não, mini-site
   separado, com o mesmo design, sem custo de app nativa.
