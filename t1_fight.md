## Documentação treino_t1

---

### 1) Contexto e objetivo

Eu queria:

- Entender se o framework `beyond_mimic` (em `booster_train`) suporta treinar policy para **T1**, já que inicialmente só havia task para **K1**.
- Criar motions compatíveis com T1 (T1 tem 1 DOF a mais: **Waist**).
- Treinar uma policy do tipo “fight” para T1.
- Fazer deploy no MuJoCo via `booster_deploy`.
- Depurar inconsistências entre treino (IsaacLab/Isaac Sim) e deploy (MuJoCo).

Repositórios envolvidos:

- `booster_train`: `/home/lucas_olives/Documents/booster_train/`
- `booster_assets`: `/home/lucas_olives/Documents/booster_assets/`
- `booster_deploy`: `/home/lucas_olives/Documents/booster_deploy/`

---

### 2) Análise inicial — Por que só existia treino para K1 em `beyond_mimic`

**O que eu observei**

- O pacote `beyond_mimic` em `booster_train` tinha apenas a árvore de tarefas de robô K1:
  - `booster_train/source/booster_train/booster_train/tasks/manager_based/beyond_mimic/robots/k1/...`
  - Ex.: `.../robots/k1/fight_001/env_cfg.py`
- Não havia pasta equivalente para T1 em `.../robots/`.

**Conclusão**

- O framework em si é relativamente **agnóstico** a robô (ele usa `joint_names=[".*"]` e a observação/reward é baseada em termos que se adaptam ao robô), mas:
  - faltava um “entry-point” (configs) de tarefa para T1,
  - e faltavam motions NPZ para T1.

---

### 3) Diferença de DOF e joint order (K1 vs T1)

No `booster_assets`, verificamos o *joint order* esperado para CSV retargetado:

- Arquivo: `booster_assets/src/booster_assets/motions.py`

**K1_JOINT_NAMES** (22 DOF) e **T1_JOINT_NAMES** (23 DOF) — com o extra:

- `T1_JOINT_NAMES` inclui `"Waist"` após `"Right_Elbow_Yaw"`.

Isso define o formato de CSV:

- 7 primeiras colunas: base pose (pos xyz + quat xyzw)
- restante: posições das juntas no order definido (22 para K1, 23 para T1).

---

### 4) Preparação de motion: CSV → NPZ (necessidade para BeyondMimic)

No `booster_train`, o BeyondMimic treina com motion em `.npz`, porque o loader (`MotionLoader`) carrega:

- `joint_pos`, `joint_vel`
- `body_pos_w`, `body_quat_w`
- `body_lin_vel_w`, `body_ang_vel_w`
- (opcional) `joint_names`, `body_names`, `fps`

**Arquivo central**

- `booster_train/source/booster_train/booster_train/tasks/manager_based/beyond_mimic/mdp/commands.py`
  - `MotionLoader` usa `np.load(motion_file)` e espera as chaves acima.

**Script de conversão**

- `booster_train/scripts/csv_to_npz.py`
  - Reproduz a trajetória no Isaac Sim e salva um `.npz` contendo as séries completas (incluindo corpos, quats, velocidades).

---

### 5) Gerar CSV T1 a partir de CSV K1 (inserindo Waist)

Como `booster_assets` não fornecia motions T1, eu criei um conversor K1→T1:

**Arquivo criado**

- `booster_train/scripts/k1_to_t1_motion.py`

**O que ele faz**

- Lê o CSV K1: 29 colunas (7 base + 22 joints).
- Insere a coluna do `Waist` com valor `0.0` após os 10 joints de cabeça/braços (posição correta segundo `T1_JOINT_NAMES`).
- Salva CSV T1: 30 colunas (7 base + 23 joints).

**Executado para**

- `booster_assets/motions/K1/k1_fight_001.csv` → `booster_assets/motions/T1/t1_fight_001.csv`
- `booster_assets/motions/K1/k1_mj2_seg1.csv` → `booster_assets/motions/T1/t1_mj2_seg1.csv`

**Criação de pasta**

- `booster_assets/motions/T1/`

**Verificações feitas**

- Conteúdo inicial com `head` e contagem de colunas (30).
- Waist ficou na posição esperada.

---

### 6) Configuração do robô T1 no treino (`booster_train`)

**Arquivo**

- `booster_train/source/booster_train/booster_train/assets/robots/booster.py`

Verificamos:

- `BOOSTER_T1_CFG` existe e aponta para:
  - `asset_path=f"{BOOSTER_ASSETS_DIR}/robots/T1/T1_23dof.urdf"`
- Existe atuador específico `waist` com joint `"Waist"`.
- `init_state.pos=(0.0, 0.0, 0.70)` no IsaacLab para T1.

#### 6.1) Bug corrigido: cálculo de `T1_ACTION_SCALE`

Encontrei um bug no final do arquivo:

- O laço que deveria preencher `T1_ACTION_SCALE` estava escrevendo em `K1_ACTION_SCALE`.

Corrigido para:

- `T1_ACTION_SCALE[n] = 0.25 * e[n] / s[n]`

---

### 7) Config de task T1 (BeyondMimic) e correção de body names

Eu criei configs de task T1 (ex.: `.../robots/t1/fight_001/...`) e ao rodar treino ocorreu erro:

> ValueError: Not all regular expressions are matched!  
> `Head_2`, `Left_Hip_Roll`, etc não existiam para T1.

**Causa**

- Os *body names* do T1 no IsaacLab/URDF não são iguais aos do K1.

**Body names observados no erro (T1)**

- `['Trunk', 'H1', 'AL1', 'AR1', 'Waist', 'H2', 'AL2', 'AR2', ... 'left_foot_link', 'right_foot_link']`

**Correção aplicada**

- Em `booster_train/.../robots/t1/fight_001/env_cfg.py` ajustamos `commands.motion.body_names` para nomes reais do T1:
  - `Head_2` → `H2`
  - `Left_Hip_Roll` → `Hip_Roll_Left`
  - `Left_Shank` → `Shank_Left`
  - `Right_Hip_Roll` → `Hip_Roll_Right`
  - `Right_Shank` → `Shank_Right`
  - `Left_Arm_2` → `AL2`, `Left_Arm_3` → `AL3`
  - `Right_Arm_2` → `AR2`, `Right_Arm_3` → `AR3`
  - pés e mãos já batiam (`left_foot_link`, `right_foot_link`, `left_hand_link`, `right_hand_link`)

---

### 8) Preparar deploy no MuJoCo com `booster_deploy`

#### 8.1) Entender o padrão de tasks

README de deploy:

- `booster_deploy/README.md`

Padrão de task:

- `tasks/<task_name>/__init__.py` registra task via `register_task("<name>", Cfg())`
- `scripts/deploy.py` faz auto-import recursivo `pkgutil.walk_packages(tasks_pkg.__path__)`

Exemplos consultados:

- `booster_deploy/tasks/beyond_mimic/beyond_mimic.py`
- `booster_deploy/tasks/beyond_mimic/__init__.py`
- `booster_deploy/tasks/locomotion/locomotion.py`
- `booster_deploy/tasks/locomotion/__init__.py`

#### 8.2) Criar task `t1_fight`

Criamos:

- `booster_deploy/tasks/t1_fight/__init__.py`
- `booster_deploy/tasks/t1_fight/t1_fight.py`

E copiamos artefatos:

- Modelo TorchScript exportado:
  - origem: `booster_train/logs/rsl_rl/t1_fight_001/2026-01-13_17-26-25/exported/t1_fight_001_2026-01-13_17-26-25.pt`
  - destino: `booster_deploy/tasks/t1_fight/models/t1_fight_001.pt`
- Motion:
  - origem: `booster_assets/motions/T1/t1_fight_001.npz`
  - destino: `booster_deploy/tasks/t1_fight/motions/t1_fight_001.npz`

#### 8.3) Bug de path do modelo (task_path errado)

Erro visto:

- Ele tentava carregar `.../tasks/beyond_mimic/models/t1_fight_001.pt`

**Causa**

- `Policy.task_path` é calculado pelo módulo da classe:
  - `booster_deploy/booster_deploy/controllers/base_controller.py` usa `inspect.getmodule(self.__class__)`.
- Nós estávamos reutilizando a classe `BeyondMimicPolicy` do módulo `tasks.beyond_mimic`, então `task_path` apontava para aquela pasta.

**Correção aplicada**

- Em `booster_deploy/tasks/t1_fight/t1_fight.py`, criamos `class T1BeyondMimicPolicy(BeyondMimicPolicy): pass`
- E configuramos `constructor = T1BeyondMimicPolicy` para que `task_path` apontasse para `tasks/t1_fight/`.

#### 8.4) Completar `sim_body_names` do T1 no deploy

Arquivo:

- `booster_deploy/booster_deploy/robots/booster.py`

Problema:

- `T1_23DOF_CFG.sim_body_names` estava vazio (`[]`).

Impacto:

- O `MotionLoader` do deploy usa `default_motion_body_names=self.robot.cfg.sim_body_names` (ver `tasks/beyond_mimic/beyond_mimic.py`).

Correção aplicada:

- Preenchemos `T1_23DOF_CFG.sim_body_names` com a ordem observada no IsaacLab para T1:
  - `Trunk, H1, AL1, AR1, Waist, H2, AL2, AR2, Hip_Pitch_Left, ... right_foot_link`

---

### 9) Dependências do deploy (pip)

`booster_deploy/requirements.txt`:

- `torch`, `mujoco`, `scipy`, `evdev`

Erro observado ao instalar:

- `evdev` falhou compilando com:
  - `fatal error: Python.h: No such file or directory`

Correção recomendada:

- Instalar headers do Python + toolchain:
  - `sudo apt-get install -y python3.11-dev build-essential`

Nota:

- `evdev` só é usado em `booster_deploy/booster_deploy/utils/remote_control_service.py` (joystick/controle remoto). Para MuJoCo sim2sim, dá para instalar sem `evdev` (opcional).

---

### 10) Replay do motion NPZ no Isaac Sim (debug visual)

Eu tentei rodar:

- `python scripts/replay_npz.py --motion <...t1_fight_001.npz>`

Erro:

- `TypeError: MotionLoader.__init__() missing 1 required positional argument: 'track_joint_names'`

**Causa**

- `booster_train/scripts/replay_npz.py` estava chamando `MotionLoader` com a assinatura antiga (indexes).

**Correção aplicada**

- Alteramos `replay_npz.py` para:
  - `track_body_names=["Trunk"]`
  - `track_joint_names=robot.joint_names`
  - e defaults `robot.body_names`/`robot.joint_names`

**Observação**

- O `replay_npz.py` atual faz `sim.render()` e **não** `sim.step()` → replay é mais visual/cinemático (não é “física real”).

---

### 11) Hipótese principal do comportamento ruim no MuJoCo

Eu observei:

- No Isaac Sim, o T1 replay aparenta “abaixo do chão”.
- No MuJoCo, o “mocap/referência” parece OK, mas o robô simulado cai rápido.

Ponto importante:

- Seu motion T1 foi gerado de K1 inserindo apenas Waist (0.0), mantendo base pose original.
- Você verificou:
  - `Trunk z frame0` é igual em K1 e T1: `0.555...`

Isso NÃO prova que o motion é correto para T1, porque:

- Mesmo com o mesmo `Trunk z`, a altura do pé depende de:
  - offsets do modelo e frame do trunk,
  - geometria (comprimentos/posicionamentos),
  - e principalmente a consistência dos ângulos com a cinemática do robô.

Além disso:

- Em `replay_npz.py` (Isaac), não rodar física (`sim.step`) pode mascarar interpenetração e contatos.
- No MuJoCo, a física roda e o policy pode estar fora de distribuição/contato.

Próximo passo recomendado para fechar diagnóstico:

- Comparar min z do pé (`left_foot_link`, `right_foot_link`) no NPZ de K1 vs T1.
- Se T1 tiver min pé z mais baixo, isso explica “ficar abaixo” mesmo com mesmo `Trunk z`.

---

### 12) Comandos e paths importantes (referência)

**Criar CSV T1 a partir de CSV K1**

- `python3 booster_train/scripts/k1_to_t1_motion.py --input_file booster_assets/motions/K1/k1_fight_001.csv --output_file booster_assets/motions/T1/t1_fight_001.csv`
- `python3 booster_train/scripts/k1_to_t1_motion.py --input_file booster_assets/motions/K1/k1_mj2_seg1.csv --output_file booster_assets/motions/T1/t1_mj2_seg1.csv`

**Treino**

- `python scripts/rsl_rl/train.py --task <TASK_NAME> --headless --device cuda:N`

**Export**

- Em treino, export foi observado em:
  - `booster_train/logs/rsl_rl/t1_fight_001/2026-01-13_17-26-25/exported/*.pt` e `*.onnx`

**Deploy**

- Listar tasks:
  - `cd booster_deploy && python scripts/deploy.py --list`
- Rodar MuJoCo:
  - `python scripts/deploy.py --task t1_fight --mujoco`

**Replay NPZ**

- `cd booster_train && python3.11 scripts/replay_npz.py --motion /home/lucas_olives/Documents/booster_deploy/tasks/t1_fight/motions/t1_fight_001.npz`

---

### 13) Arquivos que foram criados/alterados na sessão

#### booster_train

- **Criado**: `booster_train/scripts/k1_to_t1_motion.py`
- **Alterado**: `booster_train/scripts/replay_npz.py` (corrigir API do `MotionLoader`)
- **Alterado**: `booster_train/source/booster_train/booster_train/assets/robots/booster.py` (corrigir `T1_ACTION_SCALE`)
- **Alterado** (dependendo do seu estado local): configs T1 do BeyondMimic em `.../robots/t1/fight_001/env_cfg.py` (ajuste body_names T1)

#### booster_assets

- **Criado**: `booster_assets/motions/T1/t1_fight_001.csv`
- **Criado**: `booster_assets/motions/T1/t1_mj2_seg1.csv`

#### booster_deploy

- **Alterado**: `booster_deploy/booster_deploy/robots/booster.py` (preencher `T1_23DOF_CFG.sim_body_names`)
- **Criado**: `booster_deploy/tasks/t1_fight/__init__.py`
- **Criado**: `booster_deploy/tasks/t1_fight/t1_fight.py`
- **Criado/copied**:
  - `booster_deploy/tasks/t1_fight/models/t1_fight_001.pt`
  - `booster_deploy/tasks/t1_fight/motions/t1_fight_001.npz`

---

### 14) Diagnóstico fechado: por que o T1 “entra no chão” e o que eu vou fazer

Eu rodei a checagem recomendada (comparando `Trunk z0` e o mínimo `z` dos pés) e confirmei que o problema não é o `Trunk z0` em si — e sim a altura absoluta do pé no motion do T1:

**K1 (`../booster_assets/motions/K1/k1_fight_001.npz`)**
- `Trunk z0`: `0.5550229549407959`
- `min left_foot z`: `0.04339689016342163`
- `min right_foot z`: `0.03802776336669922`

**T1 “convertido” (`../booster_assets/motions/T1/t1_fight_001.npz`)**
- `Trunk z0`: `0.5550229549407959` (igual ao K1)
- `min left_foot z`: `-0.08703096956014633`
- `min right_foot z`: `-0.08703102171421051`

Ou seja: mesmo com o `Trunk` na mesma altura absoluta, o pé do T1 chega a ~**8.7 cm abaixo do chão**. Isso é consistente com:

- pose não-retargetada (K1 → T1 apenas inserindo `Waist=0`), e
- diferenças de cinemática/offsets do T1.

Eu também gerei um motion corrigido em Z:

**T1 zfix (`../booster_assets/motions/T1/t1_fight_001_zfix.npz`)**
- `Trunk z0`: `0.6420539617538452`
- `min left_foot z`: `~0`
- `min right_foot z`: `0`

Esse `zfix` remove a interpenetração do pé no chão e é o “patch mínimo” para tornar o reset/contato do BeyondMimic coerente para T1.

**O que eu estava usando**

- Eu estava usando `t1_fight_001.npz` tanto no **treino** quanto no **deploy** (o checkpoint foi treinado com esse motion).

**Próximo passo recomendado**

- Re-treinar a policy do T1 usando `t1_fight_001_zfix.npz` como motion (`motion_file` no env cfg do fight), e depois exportar/copiar o novo `.pt` para o deploy.


