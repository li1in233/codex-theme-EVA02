"""Local-only, reversible renderer loader. Never reads authentication or message text."""
import time
WORKER_STARTED=time.perf_counter()
WORKER_STARTED_AT=time.time()
COVER_TOKEN=None
from pathlib import Path
from playwright.sync_api import sync_playwright
import argparse,ctypes,hashlib,json,os,re,socket,subprocess,sys,threading,tomllib,urllib.request,uuid,xml.etree.ElementTree as ET
from contextlib import contextmanager
from ctypes import wintypes

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'state.json'
CONTROL=ROOT/'control.json'
LOG=ROOT/'loader.log'
EXE=ROOT/'CodexEVA.exe'
CREATE_NO_WINDOW=0x08000000
ctypes.windll.kernel32.OpenProcess.restype=ctypes.c_void_p
ctypes.windll.kernel32.CloseHandle.argtypes=[ctypes.c_void_p]
ctypes.windll.kernel32.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
ctypes.windll.kernel32.CreateMutexW.restype=ctypes.c_void_p
ctypes.windll.kernel32.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
ctypes.windll.kernel32.WaitForSingleObject.argtypes=[ctypes.c_void_p,wintypes.DWORD]
ctypes.windll.kernel32.WaitForSingleObject.restype=wintypes.DWORD
ctypes.windll.kernel32.ReleaseMutex.argtypes=[ctypes.c_void_p]
ctypes.windll.user32.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR]
ctypes.windll.user32.FindWindowW.restype=wintypes.HWND
ctypes.windll.user32.SendMessageTimeoutW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM,wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t)]
ctypes.windll.user32.SendMessageTimeoutW.restype=ctypes.c_ssize_t

def write(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8');temporary.replace(path)

def read(path,default=None):
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return default

def log(event,**fields):
    with LOG.open('a',encoding='utf8') as f:f.write(json.dumps({'at':time.strftime('%Y-%m-%dT%H:%M:%S'),'event':event,**fields},ensure_ascii=False)+'\n')

def ensure_dark_appearance(home=None):
    """Set only the official desktop preference before Electron reads config.toml."""
    path=(Path(home) if home else Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex'))/'config.toml'
    try:
        if path.is_symlink():raise ValueError('Linked configuration preserved')
        original=path.read_bytes() if path.exists() else b''
        text=original.decode('utf-8-sig');old=tomllib.loads(text)
        if not isinstance(old.get('desktop',{}),dict):raise ValueError('Invalid desktop settings table')
        if old.get('desktop',{}).get('appearanceTheme')=='dark':return 'already-dark'
        expected={**old,'desktop':{**old.get('desktop',{}),'appearanceTheme':'dark'}}
        newline='\r\n' if '\r\n' in text else '\n'
        candidates=[re.sub(r'''((?:desktop\.)?(?:appearanceTheme|"appearanceTheme"|'appearanceTheme')\s*=\s*)(["'])(?:system|light|dark)\2''',r'\1"dark"',text,count=1),
            re.sub(r'(?m)^(\s*\[desktop\][^\r\n]*)(\r?\n|$)',lambda m:m[1]+newline+'appearanceTheme = "dark"'+newline,text,count=1),
            'desktop.appearanceTheme = "dark"'+newline+text,
            re.sub(r'(?m)^(desktop\s*=\s*\{)',r'\1 appearanceTheme = "dark",',text,count=1)]
        for candidate in candidates:
            try:valid=tomllib.loads(candidate)==expected
            except tomllib.TOMLDecodeError:continue
            if not valid:continue
            if (path.read_bytes() if path.exists() else b'')!=original:raise OSError('Configuration changed during appearance update')
            path.parent.mkdir(parents=True,exist_ok=True)
            temporary=path.with_name('config.toml.eva-'+str(os.getpid())+'.tmp')
            temporary.write_bytes((b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+candidate.encode('utf-8'))
            try:
                if (path.read_bytes() if path.exists() else b'')!=original:raise OSError('Configuration changed during appearance update')
                temporary.replace(path)
            finally:temporary.unlink(missing_ok=True)
            log('official-appearance-applied',setting='desktop.appearanceTheme',previous=old.get('desktop',{}).get('appearanceTheme'),value='dark')
            return 'applied'
        raise ValueError('Unrecognized appearance setting layout; original configuration preserved')
    except (OSError,ValueError,TypeError) as error:
        log('official-appearance-not-applied',error=str(error)[:180]);return 'unchanged'

def stage(name,**fields):
    log('launch-stage',stage=name,elapsedMs=round((time.perf_counter()-WORKER_STARTED)*1000),**fields)
    if COVER_TOKEN:write(ROOT/'startup-stage.json',{'token':COVER_TOKEN,'stage':name,'elapsedMs':round((time.perf_counter()-WORKER_STARTED)*1000),**fields})

def cover_message(token,message,wparam=0):
    if not token:return None
    window=ctypes.windll.user32.FindWindowW(None,'Codex EVA startup '+token)
    result=ctypes.c_size_t()
    if not window or not ctypes.windll.user32.SendMessageTimeoutW(window,message,wparam,0,2,2000,ctypes.byref(result)):return None
    return result.value

class TcpRow(ctypes.Structure):
    _fields_=[(name,wintypes.DWORD) for name in ('state','address','port','remoteAddress','remotePort','pid')]

class Tcp6Row(ctypes.Structure):
    _fields_=[('address',ctypes.c_ubyte*16),('scope',wintypes.DWORD),('port',wintypes.DWORD),('remoteAddress',ctypes.c_ubyte*16),('remoteScope',wintypes.DWORD),('remotePort',wintypes.DWORD),('state',wintypes.DWORD),('pid',wintypes.DWORD)]

def listeners_at(port):
    rows=[]
    for family,row_type in ((socket.AF_INET,TcpRow),(socket.AF_INET6,Tcp6Row)):
        size=wintypes.ULONG(0)
        api=ctypes.windll.iphlpapi.GetExtendedTcpTable
        code=api(None,ctypes.byref(size),False,family,3,0)
        if code==232:continue
        if code not in (0,122):raise OSError(code,'Cannot inspect local renderer listener')
        for _ in range(3):
            buffer=ctypes.create_string_buffer(size.value)
            code=api(buffer,ctypes.byref(size),False,family,3,0)
            if code!=122:break
        if code:raise OSError(code,'Cannot inspect local renderer listener')
        count=wintypes.DWORD.from_buffer_copy(buffer).value
        for index in range(count):
            row=row_type.from_buffer_copy(buffer,4+index*ctypes.sizeof(row_type))
            if socket.ntohs(row.port&0xffff)!=port:continue
            packed=row.address.to_bytes(4,'little') if family==socket.AF_INET else bytes(row.address)
            rows.append({'LocalAddress':socket.inet_ntop(family,packed),'OwningProcess':row.pid})
    return rows

def alive(pid):
    if not pid:return False
    handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,int(pid))
    if not handle:return False
    code=ctypes.c_ulong();ctypes.windll.kernel32.GetExitCodeProcess(handle,ctypes.byref(code));ctypes.windll.kernel32.CloseHandle(handle)
    return code.value==259

@contextmanager
def watch_host(pid,cover_token=None):
    # A process handle retains identity even if Windows later reuses its PID.
    handle=ctypes.windll.kernel32.OpenProcess(0x100000|0x1000,False,int(pid)) if pid else None
    if pid and not handle:raise RuntimeError('Codex exited before host monitoring could start')
    if not handle:
        yield;return
    stopped=threading.Event();recorded=threading.Event();guard=threading.Lock()
    def record_exit():
        if ctypes.windll.kernel32.WaitForSingleObject(handle,0)!=0:return False
        with guard:
            if not recorded.is_set():
                code=wintypes.DWORD()
                ctypes.windll.kernel32.GetExitCodeProcess(handle,ctypes.byref(code))
                details={'appPid':pid,'loaderPid':os.getpid(),'exitCode':code.value,'exitCodeHex':hex(code.value),'at':time.time()}
                log('host-process-exited',**details);write(ROOT/'host-exit.json',details);recorded.set()
        return True
    def monitor():
        while not stopped.wait(.25):
            if not record_exit():continue
            # Give normal CDP cleanup time, then exit only this worker if it is stuck.
            if not stopped.wait(3):
                try:
                    log('loader-exit-after-host',appPid=pid,reason='CDP cleanup did not return')
                    if cover_token:cover_message(cover_token,0x802A)
                finally:os._exit(0)
            return
    watcher=threading.Thread(target=monitor,name='EVA-host-watch',daemon=True);watcher.start()
    try:yield
    finally:
        record_exit();stopped.set();watcher.join(timeout=1);ctypes.windll.kernel32.CloseHandle(handle)

def acquire_launch_mutex(name='Local\\EVA.Codex.Renderer.Loader'):
    handle=ctypes.windll.kernel32.CreateMutexW(None,False,name)
    if not handle:raise ctypes.WinError()
    result=ctypes.windll.kernel32.WaitForSingleObject(handle,0)
    if result not in (0,0x80,0x102):
        ctypes.windll.kernel32.CloseHandle(handle);raise ctypes.WinError()
    # Object existence alone does not mean a live worker owns the lock.
    return handle,result!=0x102

def healthy_session(prior,existing):
    pid=prior.get('appPid');port=prior.get('port')
    if prior.get('status') not in ('connecting','installed') or pid not in existing or not alive(prior.get('loaderPid')) or not port:return False
    rows=listeners_at(port)
    return bool(rows) and all(row['OwningProcess']==pid and row['LocalAddress'] in ('127.0.0.1','::1') for row in rows) and bool(endpoint(port))

def native(*args):
    result=subprocess.run([str(EXE),*map(str,args)],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW,timeout=55)
    if result.returncode:raise RuntimeError('Native activation failed; see launcher-error.log')
    return read_json(result.stdout)

def read_json(text):
    try:return json.loads(text)
    except ValueError:return {}

def endpoint(port):
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/json/version',timeout=1) as response:return json.load(response)
    except (OSError,ValueError):return None

def application_executable():
    settings=read(ROOT/'installation.json',{})
    family=settings.get('packageFamily','OpenAI.Codex_2p2nqsd0c76g0')
    app_id=settings.get('aumid',family+'!App').split('!',1)[1]
    api=ctypes.windll.kernel32
    count=wintypes.UINT();length=wintypes.UINT()
    packages=api.GetPackagesByPackageFamily
    packages.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(wintypes.UINT),ctypes.POINTER(wintypes.LPWSTR),ctypes.POINTER(wintypes.UINT),wintypes.LPWSTR]
    code=packages(family,ctypes.byref(count),None,ctypes.byref(length),None)
    if code!=122 or not count.value:raise RuntimeError('Official Codex package is not registered for this user')
    names=(wintypes.LPWSTR*count.value)();buffer=ctypes.create_unicode_buffer(length.value)
    code=packages(family,ctypes.byref(count),names,ctypes.byref(length),buffer)
    if code:raise OSError(code,'Cannot locate registered Codex package')
    get_path=api.GetPackagePathByFullName
    get_path.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(wintypes.UINT),wintypes.LPWSTR]
    candidates=[]
    for name in names:
        size=wintypes.UINT()
        if get_path(name,ctypes.byref(size),None)!=122:continue
        value=ctypes.create_unicode_buffer(size.value)
        if get_path(name,ctypes.byref(size),value):continue
        package=Path(value.value).resolve()
        document=ET.parse(package/'AppxManifest.xml')
        for app in document.iter():
            if app.tag.rsplit('}',1)[-1]!='Application' or app.get('Id')!=app_id:continue
            executable=(package/app.get('Executable','')).resolve()
            if executable.is_file() and executable.suffix.lower()=='.exe' and executable.is_relative_to(package):
                version=tuple(int(x) for x in name.split('_')[1].split('.'))
                candidates.append((version,executable))
    if not candidates:raise RuntimeError('Registered Codex package has no matching executable')
    return max(candidates,key=lambda item:item[0])[1]

def activate_cold(flags):
    result=native('--native-cold-activate',subprocess.list2cmdline(flags))
    if not result.get('pid'):raise RuntimeError('Windows package activation returned no process')
    return int(result['pid'])

def bundle(name):
    manifest=read(ROOT/'manifest.json');data=(ROOT/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==manifest['files'][name]['sha256'],'Renderer bundle integrity failure'
    return data.decode('utf8')

def evaluate(session,expression):
    response=session.send('Runtime.evaluate',{'expression':expression,'awaitPromise':True,'userGesture':True,'returnByValue':True})
    if 'exceptionDetails' in response:
        error=response['exceptionDetails'];raise RuntimeError(error.get('exception',{}).get('description',error.get('text','Renderer evaluation failed'))[:500])
    return response.get('result',{}).get('value')

def load(port,app_pid,cold=True,test=False,cover_token=None):
    theme=bundle('theme.bundle.js');startup=bundle('startup.bundle.js')
    stage('bundles-verified')
    state={'loaderPid':os.getpid(),'appPid':app_pid,'port':port,'status':'connecting','cold':cold,'test':test,'started':time.time()};write(STATE,state)
    with watch_host(app_pid,cover_token),sync_playwright() as pw:
        stage('driver-ready')
        browser=pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}',timeout=15000)
        stage('renderer-connected')
        protocol=browser.new_browser_cdp_session()
        target_deadline=time.monotonic()+30
        connections={};startup_sent=False;logged_complete=False;cover_released=False
        def attach(page):
            nonlocal startup_sent
            if not page.url.startswith('app://-/') or page in connections:return
            session=page.context.new_cdp_session(page)
            session.send('Page.enable')
            if not evaluate(session,'document.readyState!=="loading"&&!!document.body'):
                session.detach();return
            stage('renderer-attach-start')
            reload_script="if(window===window.top && location.protocol==='app:' && location.hostname==='-'){document.addEventListener('DOMContentLoaded',()=>{"+theme+"},{once:true});}"
            script_id=session.send('Page.addScriptToEvaluateOnNewDocument',{'source':reload_script})['identifier']
            stage('theme-reload-hook-installed')
            evaluate(session,theme)
            stage('theme-applied')
            if cold and not startup_sent:
                evaluate(session,('window.__evaStartupHold=true;' if cover_token else '')+startup);startup_sent=True
                stage('startup-script-sent')
                if cover_token and read(ROOT/'startup-cover-skip.json',{}).get('token')==cover_token:
                    evaluate(session,'window.__evaStartup?.skip();')
                    (ROOT/'startup-cover-skip.json').unlink(missing_ok=True)
            connections[page]=(session,script_id)
            state.update(status='installed',themeInstalled=True,startupSent=startup_sent);write(STATE,state)
            log('renderer-installed',appPid=app_pid,cold=cold)
            stage('renderer-installed')
            try:write(ROOT/'window-placement.json',native('--window-placement',app_pid))
            except Exception as error:log('placement-unavailable',error=str(error)[:120])
        try:
            placement_due=0
            while browser.is_connected() and (not app_pid or alive(app_pid)):
                if logged_complete and app_pid and time.monotonic()>=placement_due:
                    placement_due=time.monotonic()+2
                    try:
                        placement=native('--window-placement',app_pid)
                        if placement!=read(ROOT/'window-placement.json',{}):write(ROOT/'window-placement.json',placement)
                    except Exception:pass
                # Sync Playwright dispatches new-page/navigation events only while an API call pumps it.
                protocol.send('Target.getTargets')
                for context in browser.contexts:
                    for page in context.pages:
                        try:attach(page)
                        except Exception as error:log('attach-retry',error=str(error)[:300])
                command=read(CONTROL,{})
                if command.get('action')=='restore':
                    for page,(session,script_id)in connections.items():
                        try:
                            evaluate(session,'window.__evaStartup?.skip();window.__evaTheme?.destroy();')
                            session.send('Page.removeScriptToEvaluateOnNewDocument',{'identifier':script_id});session.detach()
                        except Exception:pass
                    state['status']='restored';write(STATE,state);CONTROL.unlink(missing_ok=True);return
                if not connections and time.monotonic()>target_deadline:
                    raise RuntimeError('Codex renderer page was not ready within 30 seconds after CDP connection')
                if not logged_complete:
                    for page,(session,_) in list(connections.items()):
                        if page.is_closed():connections.pop(page);continue
                        telemetry=evaluate(session,'JSON.stringify({theme:window.__evaTheme?.state(),startup:window.__evaStartup?.state(),overlay:!!document.querySelector("#eva-startup-overlay"),inputCount:document.querySelectorAll(".ProseMirror[contenteditable=true]").length,sidebarCount:document.querySelectorAll("[data-app-action-sidebar-scroll]").length})')
                        stats=read_json(telemetry or '{}');state['verification']=stats;write(STATE,state)
                        start=stats.get('startup',{})
                        if cover_token and not cover_released and read(ROOT/'startup-cover-skip.json',{}).get('token')==cover_token:
                            evaluate(session,'window.__evaStartup?.skip();')
                            start=read_json(evaluate(session,'JSON.stringify(window.__evaStartup?.state())') or '{}')
                            stats['startup']=start
                            (ROOT/'startup-cover-skip.json').unlink(missing_ok=True)
                        if cover_token and not cover_released and (start.get('prepared') or start.get('reason') in ['host-login','host-dialog','skipped','reduced-motion','render-error','media-error','media-timeout']):
                            position=cover_message(cover_token,0x802C)
                            # Keep the approved 4.17-second video entry on the native CPU player.
                            if start.get('prepared') and not start.get('finishedAt') and position and (position-1)/1000<4.25:
                                continue
                            at=cover_message(cover_token,0x802B)
                            offset=max(0,(at-1)/1000) if at else 0
                            stage('renderer-prepared',nativeOffsetSeconds=offset,preparationMs=start.get('preparationMs'),hostReady=bool(start.get('ready')))
                            progress=cover_message(cover_token,0x802E)
                            initial_progress=max(0,min(99,(progress-1)/1000)) if progress else 90
                            native_fps=cover_message(cover_token,0x8031) or 48
                            raw_position=cover_message(cover_token,0x8030)
                            native_sample_ms=time.time()*1000
                            handoff_started=time.perf_counter()
                            try:
                                evaluate(session,'window.__evaStartup?.play('+json.dumps({'offsetSeconds':offset,'initialProgress':initial_progress,'nativePlaybackSeconds':max(0,(raw_position-1)/1000) if raw_position else None,'nativeSampleUnixMs':native_sample_ms,'nativeFps':native_fps})+');')
                                native('--foreground',app_pid)
                            finally:
                                dismissed=cover_message(cover_token,0x802A) is not None
                            until=time.monotonic()+1
                            while ctypes.windll.user32.FindWindowW(None,'Codex EVA startup '+cover_token) and time.monotonic()<until:time.sleep(.01)
                            evaluate(session,'window.__evaStartup?.release();')
                            cover_released=True
                            log('startup-cover-released',prepared=start.get('prepared',False),dismissed=dismissed,nativeOffsetSeconds=offset,handoffMs=round((time.perf_counter()-handoff_started)*1000))
                            stage('cover-released')
                        if start.get('completed') or start.get('reason') in ['host-login','host-dialog','skipped','reduced-motion','render-error','media-error','media-timeout']:
                            logged_complete=True;log('startup-finished',result=stats)
                            state['accepted']=bool(start.get('completed') and stats.get('theme',{}).get('style') and stats.get('inputCount',0)>0 and not stats.get('overlay'))
                            write(ROOT/'installed-validation.json',state);write(STATE,state)
                # Pump protocol events without navigating, focusing or reading conversation text.
                live_page=next((p for p in connections if not p.is_closed()),None)
                if live_page:live_page.wait_for_timeout(50 if cover_token and not cover_released else 500)
                else:time.sleep(.1)
        except Exception:
            if not alive(app_pid) or not browser.is_connected():log('app-exited',appPid=app_pid)
            else:raise
        finally:
            if cover_token and not cover_released:
                try:cover_message(cover_token,0x802A)
                except Exception:pass
            # Disconnect transport only. Browser.close would terminate the user's app.
            for session,_ in connections.values():
                try:session.detach()
                except Exception:pass
            try:protocol.detach()
            except Exception:pass
            if state.get('status')!='restored':
                state['status']='app-exited' if not alive(app_pid) or not browser.is_connected() else 'failed'
                write(STATE,state)
            log('loader-session-ended',appPid=app_pid,status=state['status'])

def installed_processes():
    executable=application_executable()
    powershell=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    environment=os.environ.copy()
    environment['PSModulePath']=str(powershell.parent/'Modules')
    # A closed window can leave the primary process alive; do not launch a competing instance.
    command="$ErrorActionPreference='Stop'; [Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false); Get-CimInstance Win32_Process -Filter \"Name='ChatGPT.exe'\" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
    result=subprocess.run([str(powershell),'-NoLogo','-NoProfile','-NonInteractive','-Command',command],
                          capture_output=True,text=True,encoding='utf-8',env=environment,creationflags=CREATE_NO_WINDOW,timeout=10)
    if result.returncode:raise RuntimeError('Cannot inspect installed Codex primary processes')
    rows=json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(rows,dict):rows=[rows]
    return sorted(row['ProcessId'] for row in rows if row.get('ExecutablePath') and row.get('CommandLine')
                  and Path(row['ExecutablePath'])==executable and '--type=' not in row['CommandLine'])

def discard_previous_restore():
    try:
        if read(CONTROL,{}).get('action')=='restore' and CONTROL.stat().st_mtime<WORKER_STARTED_AT:
            CONTROL.unlink(missing_ok=True);log('previous-launch-restore-discarded')
    except FileNotFoundError:pass

def start_cover():
    token=uuid.uuid4().hex
    process=subprocess.Popen([str(EXE),'--startup-cover',token],cwd=ROOT,creationflags=CREATE_NO_WINDOW)
    until=time.monotonic()+8
    while time.monotonic()<until:
        if ctypes.windll.user32.FindWindowW(None,'Codex EVA startup '+token):return token
        if process.poll() is not None:raise RuntimeError('Startup cover exited before its window was ready')
        time.sleep(.02)
    process.terminate();process.wait(timeout=5)
    raise RuntimeError('Startup cover window was not ready')

def launch(restart_pid=None,cover_token=None):
    global COVER_TOKEN
    COVER_TOKEN=cover_token
    stage('worker-enter')
    prior=read(STATE,{})
    existing=installed_processes()
    stage('existing-processes-checked',appPids=existing)
    if not restart_pid and healthy_session(prior,existing):
        native('--native-activate','');log('warm-activation',appPid=prior.get('appPid'),replayed=False);return
    if prior.get('loaderPid') and prior.get('status') in ('connecting','installed'):
        log('stale-session-ignored',previousLoaderPid=prior.get('loaderPid'),previousAppPid=prior.get('appPid'),appStillPresent=prior.get('appPid') in existing)
    if restart_pid and restart_pid not in existing:raise RuntimeError('Restart target is not the installed primary Codex process')
    # Decide warm/cold before showing anything, so a warm activation cannot flash the poster.
    if not cover_token:cover_token=start_cover();COVER_TOKEN=cover_token
    stage('cold-start-cover-ready')
    for pid in existing:
        log('unconfigured-instance-restart',appPid=pid,explicit=bool(restart_pid))
        result=native('--restart-close',pid)
        log('previous-instance-closed',**result)
    remaining=installed_processes()
    if remaining:raise RuntimeError('Previous Codex processes are still running; refusing a conflicting activation')
    discard_previous_restore()
    ensure_dark_appearance()
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    flags=['--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={port}','--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding']
    pid=activate_cold(flags)
    stage('native-activated',appPid=pid,port=port,method='normal-package-activation')
    if cover_token:cover_message(cover_token,0x802D,pid)
    write(ROOT/'activation.json',{'appPid':pid,'port':port,'method':'normal-package-activation','address':'127.0.0.1','profile':'existing native package profile'})
    end=time.monotonic()+40
    while not endpoint(port) and time.monotonic()<end:
        if not alive(pid):raise RuntimeError('Codex exited before renderer connection; see Windows AppModel event logs')
        time.sleep(.15)
    if not endpoint(port):raise RuntimeError('Installed application did not expose requested local renderer endpoint')
    stage('endpoint-ready')
    listeners=listeners_at(port)
    if not listeners or any(x.get('LocalAddress') not in ['127.0.0.1','::1'] for x in listeners):raise RuntimeError('Renderer endpoint is not restricted to loopback')
    if len({row['OwningProcess'] for row in listeners})!=1:raise RuntimeError('Renderer endpoint has ambiguous process ownership')
    if pid!=listeners[0]['OwningProcess']:raise RuntimeError('Renderer listener does not belong to the launched Codex process')
    stage('listener-verified')
    (ROOT/'failure.json').unlink(missing_ok=True)
    load(port,pid,cold=True,cover_token=cover_token)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--launch',action='store_true');parser.add_argument('--restore',action='store_true');parser.add_argument('--restart',type=int);parser.add_argument('--attach',type=int);parser.add_argument('--pid',type=int);parser.add_argument('--warm',action='store_true');parser.add_argument('--production-attach',action='store_true');parser.add_argument('--cover-token');args=parser.parse_args()
    if args.restore:
        write(CONTROL,{'action':'restore','requestedAt':time.time()});log('restore-requested');return
    if args.attach:load(args.attach,args.pid,cold=not args.warm,test=not args.production_attach);return
    # Keep exactly one cold-launch worker. Warm activation deliberately never replays.
    mutex,owned=acquire_launch_mutex()
    try:
        if not owned:
            existing=installed_processes()
            log('launch-already-running',appPids=existing)
            # Never cold-activate without renderer flags while another worker starts.
            if existing:native('--foreground',existing[0])
            return
        launch(args.restart,args.cover_token)
    except Exception as error:
        log('loader-failed',error=str(error)[:600]);write(ROOT/'failure.json',{'at':time.time(),'error':str(error)[:600]})
        # Never reactivate here: a normal user exit can also close the CDP transport.
        raise
    finally:
        if COVER_TOKEN:
            try:cover_message(COVER_TOKEN,0x802A)
            except Exception:pass
        if owned:ctypes.windll.kernel32.ReleaseMutex(mutex)
        ctypes.windll.kernel32.CloseHandle(mutex)

if __name__=='__main__':main()
