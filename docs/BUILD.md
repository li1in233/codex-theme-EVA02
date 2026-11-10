# 构建与运行边界

只想安装使用时，请下载 [v10.11 Release](https://github.com/li1in233/codex-theme-EVA02/releases/tag/v10.11) 的完整包或更新包，按 [README 安装与使用说明](../README.md#下载安装包与使用)操作，无需配置下述开发环境。Release 包含第三方素材，授权边界见 [ASSETS.md](ASSETS.md)。以下是从源码构建的条件。

## 1. 公开主题预览

在仓库根目录使用Python 3.12：

```powershell
python tools/build_theme.py
python -m http.server 8000 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8000/preview/>。生成的`dist/theme.bundle.js`包含项目主题CSS、主题行为与单独OFL授权的字体；默认无人物图、影片或声音。`dist/public-theme-manifest.json`记录内容哈希，**不是原生安装清单**。主题预览不需要Python第三方包。

`--wallpaper`支持PNG/JPEG/WebP，最大20 MB。图片直接嵌入，不自动裁剪或修改透明度；想保持正文可读，请先用自己的图像工具处理图片。`--motion system|on|off`设定默认偏好；主题已保存的本地选择会优先。

## 2. 完整Windows原生源码

原生路径适用于Windows x64，需要已安装且可正常登录的官方Codex客户端、Python 3.12 x64、现有Chrome或Edge、Windows .NET Framework C#编译器和Media Foundation。源码并非官方客户端的支持接口，必须自行确认目标版本兼容。

在仓库目录创建环境，安装`requirements-startup-s4.txt`中列出的开发依赖。公开仓库不提供原环境及缓存；选择适合你机器的工具和缓存位置。已有环境无需重复创建。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-startup-s4.txt
```

依赖表来自个人工程的版本记录。公开主题构建不需要安装这些包；完整媒体构建还需要外部输入，不能只执行pip后就运行启动器。

### 输入位置

`native/runtime/project_paths.py`统一读取：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `EVA_ASSET_ROOT` | 仓库下`assets/private` | 你自行准备并确认使用权限的素材 |
| `EVA_CACHE_ROOT` | `D:/DevCache/CodexEVA` | 构建和临时文件，可按机器修改 |
| `EVA_RELEASE_ROOT` | 仓库下`releases` | 私人打包结果，不自动上传 |

完整原生构建需要至少以下输入：

```text
assets/private/
  credits.json                         你自己的来源、作者、许可及用途记录
  artwork/poster.jpg                   现有完整构建流程要求3508×2481，裁右半幅
  source-video/source.mkv              自备源视频；不提供原片下载
  startup-clips/
    entry-02-2560-original-color-v2.mp4
    system-grid-2560-original-color-v2.mp4
    hex-open-1080p60.webm              需透明通道
  masters/startup-native-master.frames 已准备好的本地无损输入母版

previews/startup-s4-waiting/assets.js   本地嵌入资源表，已被Git忽略
```

`assets.js`格式是 `window.S4_ASSETS = {...};`：

- `videos`包含`entry-02`、`system-grid`的MP4 data URI。
- `sounds`包含`entry-original`、`grid-original`、`hex-open`、`lcl-water`、`system-confirm`、`voice-plug`、`voice-lcl`、`voice-system`、`voice-sync`、`voice-complete`的音频data URI。
- `optical`是光学纹理图片data URI。
- 原工作表还存在`merge-original`与`wait-loop`，当前实装构建会移除这两项，不需要继续使用原影片合一声或等待杂音。

阶段名是代码接口，并不要求使用原影片内容；你可以用自己获准使用的视频与录音适配这些接口。现有提取器的源片时间点、文字修改、时长及画幅是个人工程约定，替换内容时应相应修改。

### 母版限制

EVA1无损帧容器的开头为小端`<4sII`：魔数`EVA1`、48fps、1920帧；每帧是小端32位长度加PNG数据，画面1920×1080。约定来自当前1080p实现。

`build_clean_master.py`会从现有母版保留前452帧，再生成后续程序画面。这意味着**现有构建链需要一份自行准备的合法母版输入，不能由干净克隆直接重建整个片头**。若换自己的片头，需要调整这段保留逻辑或先生成自己的相应输入。仓库不提供缺失母版的下载链接。

### 构建顺序

素材齐备并审阅来源后：

```powershell
.\.venv\Scripts\python.exe -B native/runtime/build_runtime.py
.\.venv\Scripts\python.exe -B native/runtime/build_crosspc.py
```

运行资源输出到`native/runtime/dist`；打包输出到`EVA_RELEASE_ROOT`。完整包构建拒绝覆盖已有同名ZIP；更新包工具沿用个人工作流，运行前应检查输出文件名与目录。这里只说明构建，不会自动安装或上传。

完整构建会使用WinForms/.NET Framework编译器、调用浏览器渲染和FFmpeg，生成正常视频、音轨与应急帧。字体子集已随OFL许可提供；只在需要新字符时才运行`build_heading_font.py`，该脚本需要本机Noto Serif SC字体。

不要用公开主题清单替代完整原生`manifest.json`。原生启动器需要整套构建结果；仅编译或复制一个EXE无法工作。

### 安装与恢复

`portable/Install.ps1`和`Update.ps1`是针对完整构建结果的安装／升级模板。完整包安装器默认尝试D盘与H盘，也支持显式目标目录；升级器校验文件，生成备份并在失败时回滚。

原生安装和启动会创建本机入口、连接本机renderer，并在EVA冷启动流程设置官方Codex深色偏好。`--restore`是项目的原版恢复路径；不应把它解释为撤销此前所有外观偏好。公开仓库保留portable安装模板；请先审阅目标目录和相应配置，再针对完整构建结果运行安装流程。

已构建的完整媒体二进制发布在 [Releases](https://github.com/li1in233/codex-theme-EVA02/releases/tag/v10.11)。素材输入母版仍不随 Git 源码提供，因此下载 Release 不代表干净克隆能直接重建整套原生演出。第三方素材不适用 MIT；自行修改、重新打包或分发前，应核实素材与依赖的相应权限。

## 3. 宣传片后期源码

`promo/finish.py`与`film_common.py`提供原宣传片的镜头、字幕、合成与混音逻辑。`EVA_PROMO_ROOT`指定私有输入和输出目录，默认`assets/private/promo`。

代码需要`edit-events.json`、原始正文画面、启动录制、`startup-capture.json`内的实际audioCues、图片、字体和音乐等输入；仓库不提供这些内容。录屏会话参数与用户数据也没有发布。该工具不能凭空生成真实客户端录制。

## 4. 验证范围

公开准备过程检查Python与JavaScript语法、无私有媒体的主题构建、哈希清单和合成预览交互。原个人工程的安装、升级及启动验收不等于公开版在新机器上的验收。未在另一台实体电脑上完整重建本仓库的原生媒体链。

运行诊断工具后，输出可能包含本机路径和进程信息；只在自行审阅并脱敏后分享必要部分。请勿提交`.venv`、构建媒体、应用配置或真实会话。
