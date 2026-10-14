# mimotion

![ 刷步数](https://github.com/TonyJiangWJ/mimotion/actions/workflows/run.yml/badge.svg)
[![GitHub forks](https://img.shields.io/github/forks/TonyJiangWJ/mimotion?style=flat-square)](https://github.com/TonyJiangWJ/mimotion/forks)
[![GitHub stars](https://img.shields.io/github/stars/TonyJiangWJ/mimotion?style=flat-square)](https://github.com/TonyJiangWJ/mimotion/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/TonyJiangWJ/mimotion?style=flat-square)](https://github.com/TonyJiangWJ/mimotion/issues)


## 小米运动自动刷步数（支持邮箱登录）

- 小米运动自动刷步数，小米运动APP现已改名 `Zepp Life`，为方便说明，后面还是称其为小米运动。但下载注册时请搜索 `Zepp Life`。
- 注册账号后建议先去以下网站测试自己的账号刷步数是否正常（注意这些网站只是网络上收集的，不保证安全和有效性）：
  - https://steps.hubp.de/ 提示密码错误时可以多试几次 或者切换网络
  - https://bs.yanwan.store/run4/ 验证码001或998
- 如无法刷步数同步到支付宝等，建议重新注册一个新的。

### 如果觉得好用，请给一个免费的[star](https://github.com/TonyJiangWJ/mimotion/)吧

## Github Actions 部署指南

### 一、Fork 此仓库并启用 Actions

本仓库使用 GitHub 自动提供的 `GITHUB_TOKEN` 保存加密登录信息，不再需要创建个人 `PAT`。工作流已声明 `contents: write` 权限。

### 二、设置账号密码

#### 前往仓库设置创建变量

- Settings-->Secrets and variables-->Actions-->New repository secret
- 快捷跳转地址 [https://github.com/${你的github用户名}/mimotion/settings/secrets/actions](../../settings/secrets/actions)
- 点击右侧的 `New repository secret` 即可添加Secret

#### 添加名为 **AES_KEY** 的Secret变量，请自行创建一个长度为16个字符的字符串作为密钥

- 注意：密钥不要用中文，长度一定要是16个字符，否则可能出错。
- 如果你有多个账号，或者希望程序自动保存登录信息，就需要设置这个 `AES_KEY`。设置之后，程序会用这个密钥把各个账号的登录token信息加密保存起来。**请一定保管好你的密钥，不要泄露。**
- 第一次配置 `AES_KEY` 后，运行时可能会看到提示：“密钥不正确或者加密内容损坏 放弃token”，**这是正常现象**。因为原来加密文件用的是我的密钥，和你设置的不同，所以会提示不匹配。你直接忽略它，等程序运行完后，就会用你的新密钥生成一份新的加密文件，下次运行就正常了。
- 配置 `AES_KEY` 后，每个人的仓库里面到会保存一份 `encrypted_tokens.data`。每次更新代码时，这个文件会被覆盖。**为了避免丢失你保存的信息，请在更新代码前备份这个文件**，等代码更新完，再把它放回仓库并提交，最后重新运行workflow。

#### 添加名为 **CONFIG** 的Secret变量

- 需要注意Secret变量是密文，提交后无法查看，只能删除或用新值更新，建议本地保存一下自己的配置数据方便后期修改。
- CONFIG的内容：

  ```json
  {
    "USER": "abcxxx@xx.com",
    "PWD": "password",
    "MIN_STEP": "8001",
    "MAX_STEP": "10000",
    "PUSH_PLUS_TOKEN": "",
    "PUSH_PLUS_HOUR": "",
    "PUSH_PLUS_MAX": "30",
    "SLEEP_GAP": "5",
    "USE_CONCURRENT": "False"
  }
  ```

  | 字段名             | 格式                                                                                              |
  |-----------------|-------------------------------------------------------------------------------------------------|
  | USER            | 小米运动登录账号，仅支持小米运动账号对应的手机号或邮箱，不支持小米账号                                                             |
  | PWD             | 小米运动登录密码，仅支持小米运动账号对应的密码                                                                         |
  | MIN_STEP        | 每次上传的最小步数，默认8001；低于8001的配置会自动提高到8001                                                                                            |
  | MAX_STEP        | 每次上传的最大步数，默认10000；不会低于实际最小步数，不再按时间折算                                                         |
  | PUSH_PLUS_TOKEN | 推送加的个人token,申请地址[pushplus](https://www.pushplus.plus/push1.html)，工作流执行完成后推送每个账号的执行状态信息，如没有则不要填写 |
  | PUSH_PLUS_HOUR  | 限制只在某个整点进行pushplus的推送，值为整数，比如设置21，则只在北京时间21点XX分执行时才进行pushplus的消息推送。如不设置或值非数字则每次执行后都会进行推送        |
  | PUSH_PLUS_MAX   | 设置pushplus最大推送账号详情数，默认为30，超过30个账号将只推送概要信息：多少个成功多少个失败。因为数量太多会导致内容过长无法推送。具体最大值请自行调试               |
  | SLEEP_GAP       | 多账号执行间隔，单位秒，如果账号比较多可以设置的短一点，默认为5秒                                                               |
  | USE_CONCURRENT  | 是否使用多线程，实验性功能，未测试是否有效。账号多的可以试试，将它设置为True即可，启用后 `SLEEP_GAP` 将不再生效                                |

### 三、多账户设置(如用不上请忽略)

- 多账户请用 **#** 分割 然后保存到变量 **USER** 和 **PWD**
- 理论上账户数量不受限制，但是实际要看github actions的资源和华米接口是否有限制，pushplus消息内容应该也有最大长度限制，反正具体上限请自行测试

#### 例如

```json
{
  "USER": "13800138000#13800138001",
  "PWD": "abc123qwe#abcqwe2",
  "MIN_STEP": "8001",
  "MAX_STEP": "10000",
  "PUSH_PLUS_TOKEN": "",
  "PUSH_PLUS_HOUR": ""
}
```

#### 注意 **#** 分隔的账号和密码数量必须匹配，否则将跳过执行

### 四、北京时间20:00前超过8000步

每次成功上传都会设置超过8000步的当日总步数，默认范围为8001～10000。已有 `MIN_STEP=8000` 配置也会自动提高到8001，无需修改 Secret。

固定计划在北京时间每天 **15:17、17:17** 执行。15:17成功后，当天后续运行会跳过登录和步数修改；15:17失败时，17:17再次尝试。多账号情况下只补试当天尚未成功的账号，已成功的账号不会重复上传。GitHub定时任务可能延迟或漏触发，请以实际执行日期和上传日志为准。

成功记录保存到 `daily_success.json` 并提交到仓库，按照北京时间日期判断，第二天自动重新开始。文件使用账号摘要，不保存明文账号；即使没有设置AES_KEY，也能记住当天的成功状态。手动运行同样遵守当天成功后跳过的规则。

如需修改时间，直接编辑 `.github/workflows/run.yml`。cron 使用UTC时间，北京时间需要减8小时：

```yaml
on:
  schedule:
    - cron: '17 7,9 * * *'
```

`Random Cron` 工作流已移除，原有 `CRON_HOURS` 变量不再影响执行时间。

断连、超时、429和临时服务错误最多请求三次；仍然失败时，Actions会显示失败。加密登录信息会尽量保存，避免下一轮重复登录。

### 五、手动触发测试工作流

- 前往Actions,左侧选择 `刷步数`，快捷链接：[https://github.com/${你的github用户名}/mimotion/actions/workflows/run.yml](../../actions/workflows/run.yml)
- 新fork的仓库默认未启用工作流，进入Actions后点击 `I understand my workflows, go ahead and enable them` 启用，然后左侧选择 `刷步数` 之后，再点击 `enable workflow` 启用工作流。请确保开启工作流，否则不会定时执行。
- 点击右侧的`Run workflow`触发执行，触发后刷新即可查看执行记录。验证是否正确配置并执行刷步数。

### 六、感谢列表

本项目基于 `https://github.com/xunichanghuan/mimotion(已被ban)` 和 [https://github.com/huangshihai/mimotion](https://github.com/huangshihai/mimotion) 项目修改，特此感谢

新版本登录需要加密，感谢[https://github.com/hanximeng/Zepp_API/blob/main/index.php](https://github.com/hanximeng/Zepp_API/blob/main/index.php) 里面提供的aes加密密钥。大家可以去给作者点个star

### 七、同步最新代码

- 点击仓库界面上的 `Sync fork`，找不到的话直接Ctrl+F网页查找
- 然后点击 `Update branch` 或者 `Discard xxx commits`等待同步完成即可，如有其他提示请自行按提示操作。请不要提交 **pull request**
- 当配置了 `AES_KEY` 之后，因为每个人的仓库里面到会保存一份 `encrypted_tokens.data`，更新代码会被覆盖。为了避免数据丢失，请提前备份，在更新完成后将它重新提交到仓库中，然后再触发workflow。
- 同步更新后请自己再次仔细阅读README，配置项目修改等请自行对比，更新后因为配置不正确导致无法运行请不要找我

## 注意事项

1. 默认每天固定安排北京时间15:17、17:17两次执行，当天成功一次后不再修改步数。

2. 多账户的数量和密码请一定要对上 不然无法使用!!!

3. 启动时间得是UTC时间!

4. 如果支付宝没有更新步数，到小米运动->设置->账号->注销账号->清空数据，然后重新登录，重新绑定第三方。建议去开头提到的网站测试账号是否正常

5. 小米运动不会更新步数，只有关联的会同步！！！！！

6. 请各位在使用时Fork[当前仓库](https://github.com/TonyJiangWJ/mimotion/)，防止出现不必要的bug.

7. 请注意，账号不是 [小米账号]，而是 [小米运动/ZeppLife] 的账号。

8. 随机步数范围全天固定，每次成功上传都超过8000步，可在CONFIG中设置更高的MIN_STEP和MAX_STEP。

9. cron的执行根据github actions的资源进行排队，并不是百分百按指定的时间进行运行，请知悉。

10. 新版本接口有限制，同ip登录过多账号可能会429，请自行测试。

### 查看执行记录

- 前往 [Actions](../../actions) 可以查看所有工作流的执行历史
  - `刷步数 #41: Scheduled` 代表是定时任务触发，`刷步数 #33: Manually run by xxx` 代表手动触发
- 点击其中一条记录，可以查看执行详情，这里以 `刷步数` 为例：
  - 详情界面 `Jobs` 可以查看到一个 `build` ，点击它查看执行步骤
  - 执行步骤中主要关注 `开始` ，点击 `开始` 展开详情
  - 展开后便可以查看到执行日志，如果执行成功，则会显示每个账号当前随机的步数是多少
  - 如果执行失败，则需要根据实际情况分析具体失败原因
- 如果任意账号登录或上传失败，`开始`步骤会失败；请查看该账号的错误信息。只有所有账号成功，工作流才会显示绿色。
