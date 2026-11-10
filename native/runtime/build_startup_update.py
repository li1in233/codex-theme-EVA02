from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Package theme v6 with unchanged v10.10 startup media and rollback support."""
from pathlib import Path
import hashlib,json,shutil,time,zipfile
SOURCE=Path(__file__).resolve().parent
RELEASE=RELEASE_ROOT
NAME='CodexEVA-v10.11-update'
WORK=CACHE_ROOT/('startup-update-'+time.strftime('%Y%m%d-%H%M%S'))/NAME
WORK.mkdir(parents=True);RELEASE.mkdir(parents=True,exist_ok=True)
payload=WORK/'payload';payload.mkdir()
for name in ('CodexEVA.exe','manifest.json','theme.bundle.js','startup.bundle.js','startup-native-video.mp4','startup-native.wav','startup-first-frame.jpg','startup-native.frames'):shutil.copy2(SOURCE/'dist'/name,payload/name)
shutil.copy2(SOURCE/'loader.py',payload/'loader.py')
for name in ('Collect-Diagnostics.ps1','Collect-Diagnostics.cmd'):shutil.copy2(SOURCE/'diagnostics'/name,payload/name)
shutil.copy2(SOURCE/'portable/README.zh-CN.txt',payload/'使用说明.txt')
for name in ('Update.ps1','Update.cmd'):
    (WORK/name).write_text((SOURCE/'portable'/name).read_text('utf-8-sig'),encoding='utf-8-sig' if name.endswith('.ps1') else 'ascii',newline='\r\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'version':'R7-S4-v10.11-crosspc','files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in payload.iterdir()}}
(WORK/'update-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(WORK/'使用说明.txt').write_text('''Codex EVA v10.11 主题样式更新包（用于已安装的 v10.1 至 v10.11）

1. 将整个 ZIP 解压到普通文件夹。保留 payload 子目录，不要只复制 EXE。
2. 正常退出 Codex，双击 Update.cmd。自动寻找 D:\\Apps\\CodexEVA 或 H:\\Apps\\CodexEVA。
3. 成功后，从原来的 CodexEVA.exe 或开始菜单入口启动。
自定义安装位置：Update.cmd -TargetDirectory "E:\\Apps\\CodexEVA"
只校验：Update.cmd -CheckOnly

补丁更新实际安装目录，不是之前解压的完整安装包目录。
会先验证已安装媒体，备份原文件，失败时回滚；不会关闭应用或改动账号、聊天与项目。
有 H 盘时备份到 H:\\Archives\\CodexEVA\\updates，否则放安装目录的 backups。

正常播放为1080p、48帧，Windows Media Foundation原生视频，保留原色和文字修改。
视频为1080p H.264 CRF16；前9.42秒沿用无损母版，等待段从程序重绘，无反向播放；颜色不变。音频从原始PCM素材重混后编码一次AAC。
网页沿用原生管面的实际时钟和29秒正向循环，200ms平滑混合，移除系统额外窗口过渡与合一白色提亮。
原生和网页均移除合一动漫原声及等待杂音，蜂窝进入音效单独完整播放。
保留960×540、24fps的紧凑应急素材，仅解码失败时使用。
从LCL注入至蜂窝结束统一为纯数字百分比，无进度条、阶段标题和面板。
蜂窝改用预先解码的1080p60透明动画，保留原翻转几何和高光，解码不支持时自动回退。
交接期间原生画面继续播放；网页画好后才显示，移除遮罩后开始完整1.5秒合一。
蜂窝为VP9 CRF18透明视频，已对比原版颜色和边缘。
片头优先读取Codex本身保存的位置、大小与最大化状态。
从EVA入口冷启动时自动将官方Codex外观设为深色，不必再按旧说明手动调整。
仅更新config.toml的desktop.appearanceTheme，其余设置保留；不改Windows主题。
深色偏好会保留，之后可从原版入口进入设置自行改回。
右下角恢复阶段加权百分比；阶段内增长为估计，每次节奏不同，100%必须确认工作台可交互。
交接继承进度。保留窗口化、圆角和已解决卡顿的原生播放器。
旧素材会备份以便回滚；安装目录变小，但备份仍占空间，不会自动删除。
本次新增R7-installed-6主题：顶部文字与按钮垂直居中，EVA 02使用嵌入字体并距首个按钮32px，窄窗自动隐藏。
补齐菜单、搜索、附件、禁用、工具/审批语义色、代码、diff与右面板样式；不改变原有功能。
EVA Heading为Noto Serif SC 900字重的精简静态子集，完整OFL许可与署名嵌入字体元数据。
启动动画脚本、视频、音频、海报和EXE与v10.10校验值完全一致，本次不重编码。
冷启动不再执行上次遗留的恢复命令，保留本次启动期间的新恢复请求。
包含v10.2的慢启动等待、互斥锁恢复、宿主退出清理。窗口化、1.5秒同步及主题保留。
如果仍发生整个 Codex 窗口退出，在安装目录双击 Collect-Diagnostics.cmd，提交新生成的 ZIP。
用户已确认v10.2解决此前启动问题；本版保留这些修复。目标机帧率仍取决于实际窗口大小和负载。
健康的EVA实例直接唤起，不先展示片头。无可用加载器的旧Codex实例自动重启。
先请求正常关闭，5秒仍未退出才定向结束已校验包身份的旧主进程；不会按名称批量杀进程。
接管原版或异常实例时会关闭其窗口，请先结束正在进行的工作。
''',encoding='utf-8-sig')
archive=RELEASE/(NAME+'.zip')
if archive.exists():raise FileExistsError(archive)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for p in sorted(WORK.rglob('*')):
        if p.is_file():z.write(p,NAME+'/'+p.relative_to(WORK).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
(RELEASE/(NAME+'.sha256')).write_text(sha(archive)+'  '+archive.name+'\n',encoding='ascii')
report={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'staging':str(WORK)}
(SOURCE.parent/'evidence/startup-update-build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
