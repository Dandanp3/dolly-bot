# 🐾 Dolly | Bot

> **Prefixo do Bot:** `d!`
> Todos os comandos abaixo devem ser iniciados com este prefixo.

---

## Comandos de Administração
*Comandos restritos para a equipe de moderação e administradores gerenciarem a economia e o servidor.*

* **`d!additem`**
  Adiciona um novo cargo ou item à loja do servidor.
* **`d!addboost <@cargo> <quantia>`**
  Configura um multiplicador de ganhos para um cargo específico (ex: `d!addboost @VIP 1.5` fará o cargo ganhar 50% a mais nas ações).
* **`d!addsalario <@cargo> <quantia> <horas>`**
  Configura um pagamento automático que vai direto para o banco de quem possui o cargo informado (ex: `d!addsalario @Moderador 1000 10h`).
* **`d!addcoins <@usuario> <quantia>`**
  Injeta moedas magicamente na carteira (na pata) de um usuário específico.
* **`d!giveawaysetup`**
  Inicia o assistente interativo para criar e configurar um sorteio no servidor.
* **`d!say <#canal> <mensagem>`**
  Faz o bot enviar uma mensagem personalizada em um canal específico.
* **`d!reply <ID_da_mensagem> <mensagem>`**
  Faz o bot responder diretamente a uma mensagem no chat usando o ID dela.

---

## Comandos Gerais 
*Comandos liberados para todos os membros interagirem e enriquecerem no servidor.*

### Economia & Ações
* **`d!brincar`**
  Gaste energia brincando para achar moedas escondidas. (Cooldown rápido, lucro baixo).
* **`d!dormir`**
  Tire um longo cochilo na caverna e acorde com recursos. (Cooldown médio, lucro médio).
* **`d!uivar`**
  Uive para a alcateia em troca de recompensas. (Cooldown longo, lucro alto).
* **`d!caçar <@usuario>`**
  Tente a sorte roubando moedas da carteira (na pata) de outro membro. Cuidado com os riscos!

### Gerenciamento de Recursos
* **`d!coins`**
  Mostra o seu patrimônio atual (moedas na pata e guardadas na caverna). *Pode ser usado marcando alguém: `d!coins @usuario`.*
* **`d!dep <quantia>`** ou **`d!depositar <quantia>`**
  Guarda suas moedas em segurança na caverna (banco) para não ser roubado em caçadas.
* **`d!sacar <quantia>`**
  Retira moedas da sua caverna para a sua carteira, permitindo fazer compras ou doações.
* **`d!doar <@usuario> <quantia>`**
  Transfere um valor da sua carteira para a carteira de um amigo.

### Status & Benefícios
* **`d!meuboost`** *(Atalhos: `d!meusboosts`, `d!myboost`, `d!boosts`)*
  Exibe todos os seus cargos que possuem multiplicadores ativos e mostra o seu bônus total de ganhos.
* **`d!meusalario`** *(Atalhos: `d!meussalarios`, `d!mysalary`, `d!salarios`)*
  Exibe todos os pagamentos (salários) programados que você tem a receber com base nos seus cargos.

### Mercado & Ranking
* **`d!shop`** ou **`d!loja`**
  Abre o catálogo de itens e cargos disponíveis para compra no servidor.
* **`d!buy <item>`** ou **`d!comprar <item>`**
  Adquire um item ou cargo da loja usando o saldo da sua carteira.
* **`d!top`**
  Mostra o ranking (Leaderboard) dos membros mais ricos e acumuladores de recursos do servidor.
