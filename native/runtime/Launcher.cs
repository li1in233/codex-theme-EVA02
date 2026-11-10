using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Runtime.InteropServices;
using System.Media;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

[ComImport, Guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")]
class ApplicationActivationManager {}
[ComImport, Guid("2E941141-7F97-4756-BA1D-9DECDE894A3D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IApplicationActivationManager {
    [PreserveSig] int ActivateApplication([MarshalAs(UnmanagedType.LPWStr)]string appId,[MarshalAs(UnmanagedType.LPWStr)]string arguments,uint options,out uint processId);
    [PreserveSig] int ActivateForFile(IntPtr appId,IntPtr items,IntPtr verb,out uint processId);
    [PreserveSig] int ActivateForProtocol(IntPtr appId,IntPtr items,out uint processId);
}
class Launcher {
    static readonly string Aumid=ApplicationId();
    static string ApplicationId() {
        try {
            var settings=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"installation.json"),Encoding.UTF8));
            if(settings.ContainsKey("aumid"))return (string)settings["aumid"];
        }catch{}
        return "OpenAI.Codex_2p2nqsd0c76g0!App";
    }
    [DllImport("user32.dll")]static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")]static extern bool ShowWindow(IntPtr hwnd,int command);
    [DllImport("user32.dll")]static extern bool IsIconic(IntPtr hwnd);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)]static extern IntPtr FindWindow(string className,string title);
    [DllImport("user32.dll")]static extern IntPtr SendMessageTimeout(IntPtr hwnd,uint message,IntPtr wParam,IntPtr lParam,uint flags,uint timeout,out IntPtr result);
    [DllImport("user32.dll")]static extern bool GetWindowRect(IntPtr hwnd,out WindowRect rect);
    [DllImport("user32.dll")]static extern bool GetClientRect(IntPtr hwnd,out WindowRect rect);
    [DllImport("user32.dll")]static extern bool ClientToScreen(IntPtr hwnd,ref Point point);
    [DllImport("user32.dll")]static extern uint GetDpiForWindow(IntPtr hwnd);
    [DllImport("user32.dll")]static extern bool SetLayeredWindowAttributes(IntPtr hwnd,uint colorKey,byte alpha,uint flags);
    [DllImport("user32.dll")]static extern IntPtr MonitorFromPoint(Point point,uint flags);
    [DllImport("shcore.dll")]static extern int GetDpiForMonitor(IntPtr monitor,int type,out uint x,out uint y);
    [DllImport("user32.dll")]static extern bool IsZoomed(IntPtr hwnd);
    [DllImport("dwmapi.dll")]static extern int DwmSetWindowAttribute(IntPtr hwnd,int attribute,ref int value,int size);
    [DllImport("dwmapi.dll")]static extern int DwmExtendFrameIntoClientArea(IntPtr hwnd,ref Margins margins);
    [StructLayout(LayoutKind.Sequential)]struct Margins {public int left,right,top,bottom;}
    [DllImport("user32.dll")]static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]static extern int GetApplicationUserModelId(IntPtr process,ref uint length,StringBuilder value);
    [StructLayout(LayoutKind.Sequential)]struct WindowRect {public int left,top,right,bottom;}
    [StructLayout(LayoutKind.Sequential)]struct BitmapInfo {
        public int size,width,height;public short planes,bits;
        public int compression,sizeImage,xppm,yppm,colorsUsed,colorsImportant;
    }
    [DllImport("gdi32.dll")]static extern int SetStretchBltMode(IntPtr hdc,int mode);
    [DllImport("gdi32.dll")]static extern int StretchDIBits(IntPtr hdc,int x,int y,int width,int height,int sourceX,int sourceY,int sourceWidth,int sourceHeight,IntPtr pixels,ref BitmapInfo info,uint usage,uint operation);
    [DllImport("gdi32.dll")]static extern IntPtr CreateCompatibleDC(IntPtr hdc);
    [DllImport("user32.dll")]static extern IntPtr GetDC(IntPtr window);
    [DllImport("user32.dll")]static extern int ReleaseDC(IntPtr window,IntPtr dc);
    [DllImport("gdi32.dll")]static extern bool GdiFlush();
    [DllImport("gdi32.dll")]static extern IntPtr CreateDIBSection(IntPtr hdc,ref BitmapInfo info,uint usage,out IntPtr pixels,IntPtr section,uint offset);
    [DllImport("gdi32.dll")]static extern IntPtr SelectObject(IntPtr hdc,IntPtr value);
    [DllImport("gdi32.dll")]static extern bool DeleteObject(IntPtr value);
    [DllImport("gdi32.dll")]static extern bool DeleteDC(IntPtr hdc);
    [DllImport("gdi32.dll")]static extern bool BitBlt(IntPtr target,int x,int y,int w,int h,IntPtr source,int sx,int sy,uint mode);
    [DllImport("gdi32.dll")]static extern bool StretchBlt(IntPtr target,int x,int y,int w,int h,IntPtr source,int sx,int sy,int sw,int sh,uint mode);
    static Process PrimaryWindow() {
        foreach(var process in Process.GetProcessesByName("ChatGPT"))try{
            if(process.MainWindowHandle==IntPtr.Zero)continue;
            uint length=0;GetApplicationUserModelId(process.Handle,ref length,null);
            if(length==0)continue;
            var identity=new StringBuilder((int)length);
            if(GetApplicationUserModelId(process.Handle,ref length,identity)==0&&identity.ToString()==Aumid)return process;
        }catch{}
        return null;
    }
    static Rectangle BoundsOf(Process process) {
        WindowRect rect;
        var origin=new Point();
        if(process!=null&&GetClientRect(process.MainWindowHandle,out rect)&&ClientToScreen(process.MainWindowHandle,ref origin))return new Rectangle(origin.X,origin.Y,rect.right,rect.bottom);
        return Rectangle.Empty;
    }
    static void Foreground(Process process) {
        process.Refresh();
        if(process.MainWindowHandle!=IntPtr.Zero){if(IsIconic(process.MainWindowHandle))ShowWindow(process.MainWindowHandle,9);SetForegroundWindow(process.MainWindowHandle);}
    }
    static void StartWorker(string root,string mode) {
        var settings=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"installation.json"),Encoding.UTF8));
        string python=(string)settings["pythonw"];
        if(!Path.IsPathRooted(python))python=Path.Combine(root,python);
        var info=new ProcessStartInfo(python,"-B \""+Path.Combine(root,"loader.py")+"\" "+mode);
        info.WorkingDirectory=root;info.UseShellExecute=false;info.CreateNoWindow=true;info.WindowStyle=ProcessWindowStyle.Hidden;
        foreach(string name in new[]{"PYTHONHOME","PYTHONPATH","PYTHONUSERBASE","PLAYWRIGHT_NODEJS_PATH","NODE_OPTIONS","NODE_PATH"})info.EnvironmentVariables.Remove(name);
        info.EnvironmentVariables["PYTHONUTF8"]="1";
        Process.Start(info);
    }
    sealed class StartupCover:Form {
        readonly string root,token;
        readonly Bitmap firstFrame;
        readonly Timer timer=new Timer();
        readonly Stopwatch age=Stopwatch.StartNew();
        readonly Stopwatch playback=new Stopwatch();
        FileStream frames;
        int[] offsets,lengths;
        int fps=24,frameIndex=-1,paintedFrames=0,lastPainted=-1;
        sealed class DecodedFrame:IDisposable {
            public readonly int Width,Height;public readonly IntPtr Dc;
            readonly IntPtr bitmap,previous;
            public DecodedFrame(int width,int height){
                Width=width;Height=height;var screen=GetDC(IntPtr.Zero);
                try{Dc=CreateCompatibleDC(screen);}finally{ReleaseDC(IntPtr.Zero,screen);}
                var info=new BitmapInfo{size=40,width=width,height=-height,planes=1,bits=32};IntPtr pixels;
                bitmap=CreateDIBSection(IntPtr.Zero,ref info,0,out pixels,IntPtr.Zero,0);
                if(Dc==IntPtr.Zero||bitmap==IntPtr.Zero){if(bitmap!=IntPtr.Zero)DeleteObject(bitmap);if(Dc!=IntPtr.Zero)DeleteDC(Dc);throw new InvalidOperationException("Cannot allocate native playback frame");}
                previous=SelectObject(Dc,bitmap);
            }
            public void Dispose(){SelectObject(Dc,previous);DeleteObject(bitmap);DeleteDC(Dc);}
        }
        DecodedFrame currentFrame;
        sealed class PreparedFrame {public int index;public double at;public DecodedFrame image;}
        readonly object frameGate=new object(),readGate=new object();
        readonly System.Collections.Generic.Dictionary<int,PreparedFrame> prepared=new System.Collections.Generic.Dictionary<int,PreparedFrame>();
        readonly System.Collections.Generic.HashSet<int> pending=new System.Collections.Generic.HashSet<int>();
        bool framesClosing=false;
        bool resourcesDisposed=false;
        double currentFrameAt=0;
        SoundPlayer sound;
        double lastPaintMs=0,maxFrameGapMs=0;
        double maxDecodeMs=0,maxDrawMs=0,maxWindowCheckMs=0;
        sealed class PhaseTiming {
            public int frames;public double firstMs,lastMs,maxGapMs;
            public double fps{get{return frames>1&&lastMs>firstMs?Math.Round((frames-1)*1000/(lastMs-firstMs),1):0;}}
            public void Add(double now){if(frames==0)firstMs=now;else maxGapMs=Math.Max(maxGapMs,now-lastMs);lastMs=now;frames++;}
        }
        readonly System.Collections.Generic.Dictionary<string,PhaseTiming> phaseTiming=new System.Collections.Generic.Dictionary<string,PhaseTiming>();
        double firstMotionMs=-1,heldAt=0;
        string mediaFailure=null;
        NativeVideo video;
        string videoFailure=null,hostStage="starting-host";
        double videoPosition=0,nextStageRead=0;
        double startupProgress=1,stageFloor=1,stageCeiling=7,stageAt=0;
        readonly double progressPace=2+new Random(Guid.NewGuid().GetHashCode()).NextDouble()*4;
        bool hostReady=false;
        double dismissAt=-1;
        string placementSource="centered-default";
        static Rectangle KeepOnScreen(Rectangle rect){
            var screen=Screen.FromRectangle(rect);var area=screen.WorkingArea;
            if(Rectangle.Intersect(area,rect).Width<200||Rectangle.Intersect(area,rect).Height<200)area=Screen.FromPoint(Cursor.Position).WorkingArea;
            int width=Math.Min(rect.Width,area.Width),height=Math.Min(rect.Height,area.Height);
            return new Rectangle(Math.Max(area.Left,Math.Min(rect.Left,area.Right-width)),Math.Max(area.Top,Math.Min(rect.Top,area.Bottom-height)),width,height);
        }
        static Rectangle CodexBounds(System.Collections.Generic.Dictionary<string,object> saved,out bool zoomed){
            var rect=new Rectangle(Convert.ToInt32(saved["x"]),Convert.ToInt32(saved["y"]),Convert.ToInt32(saved["width"]),Convert.ToInt32(saved["height"]));
            if(rect.Width<400||rect.Height<300||rect.Width>16000||rect.Height>16000)throw new InvalidDataException("Invalid Codex window bounds");
            var screen=Screen.FromRectangle(rect);uint x=96,y=96;
            try{GetDpiForMonitor(MonitorFromPoint(new Point(screen.Bounds.Left+10,screen.Bounds.Top+10),2),0,out x,out y);}catch{}
            double scale=x/96d;
            rect=new Rectangle(screen.Bounds.Left+(int)Math.Round((rect.Left-screen.Bounds.Left)*scale),screen.Bounds.Top+(int)Math.Round((rect.Top-screen.Bounds.Top)*scale),(int)Math.Round(rect.Width*scale),(int)Math.Round(rect.Height*scale));
            zoomed=saved.ContainsKey("isMaximized")&&Convert.ToBoolean(saved["isMaximized"]);
            return zoomed?Screen.FromRectangle(rect).WorkingArea:KeepOnScreen(rect);
        }
        static int StagePercent(string stage){
            switch(stage){
                case "worker-enter":return 8;case "existing-processes-checked":return 12;
                case "native-activated":return 22;case "endpoint-ready":return 42;
                case "listener-verified":return 46;case "bundles-verified":return 50;
                case "driver-ready":return 56;case "renderer-connected":return 62;
                case "renderer-attach-start":return 68;case "theme-reload-hook-installed":return 74;
                case "theme-applied":return 80;case "startup-script-sent":return 86;
                case "renderer-installed":return 90;case "renderer-prepared":return 96;
                default:return 1;
            }
        }
        bool mutedVideo=false;
        sealed class Overlay:Control {
            public Action<Graphics> paint;
            public bool transparent;
            public Overlay(){SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer,true);TabStop=false;}
            protected override CreateParams CreateParams {get{var value=base.CreateParams;if(transparent)value.ExStyle|=0x00080000;return value;}}
            protected override void OnHandleCreated(EventArgs e){base.OnHandleCreated(e);if(transparent)SetLayeredWindowAttributes(Handle,0x0015110B,255,1);}
            protected override void OnPaint(PaintEventArgs e){if(paint!=null)paint(e.Graphics);}
        }
        Overlay skipOverlay,statusOverlay;
        double MediaSeconds(){return video!=null?videoPosition:(double)Math.Max(0,frameIndex)/fps;}
        void PositionOverlays(){
            if(skipOverlay==null)return;
            skipOverlay.Bounds=skipBounds;
            var rect=new RectangleF(1290,765,100,24);
            statusOverlay.Bounds=new Rectangle((int)Math.Floor(rect.X*ClientSize.Width/1440),(int)Math.Floor(rect.Y*ClientSize.Height/810),(int)Math.Ceiling(rect.Width*ClientSize.Width/1440),(int)Math.Ceiling(rect.Height*ClientSize.Height/810));
            statusOverlay.Visible=MediaSeconds()>=7.5/1.8;
        }
        void PaintStatus(Graphics graphics){
            graphics.Clear(Color.FromArgb(11,17,21));
            float scale=Math.Max(.5f,ClientSize.Width/1440f);
            using(var font=new Font("Consolas",16*scale,FontStyle.Regular,GraphicsUnit.Pixel))using(var brush=new SolidBrush(startupProgress>=100?Color.FromArgb(214,225,200):Color.FromArgb(188,154,86)))
            using(var format=new StringFormat{Alignment=StringAlignment.Far,LineAlignment=StringAlignment.Center,FormatFlags=StringFormatFlags.NoWrap})
                graphics.DrawString(((int)startupProgress).ToString("D3")+" %",font,brush,statusOverlay.ClientRectangle,format);
        }
        void StartVideo(){
            string file=Path.Combine(root,"startup-native-video.mp4");
            try{
                skipOverlay=new Overlay{paint=g=>{g.TranslateTransform(-skipBounds.X,-skipBounds.Y);PaintSkip(g);}};
                statusOverlay=new Overlay{paint=PaintStatus,transparent=true};Controls.Add(statusOverlay);Controls.Add(skipOverlay);
                skipOverlay.MouseEnter+=(s,e)=>{skipHover=true;skipOverlay.Cursor=Cursors.Hand;skipOverlay.Invalidate();};
                skipOverlay.MouseLeave+=(s,e)=>{skipHover=false;skipOverlay.Invalidate();};
                skipOverlay.MouseUp+=(s,e)=>{if(e.Button==MouseButtons.Left)Skip();};
                PositionOverlays();
                if(!File.Exists(file))return;
                video=new NativeVideo(Handle,file,mutedVideo,action=>{if(!IsDisposed)try{BeginInvoke(action);}catch(InvalidOperationException){}},()=>{},FailVideo);
            }catch(Exception error){FailVideo(error.Message);}
        }
        void FailVideo(string reason){
            videoFailure=reason;if(video!=null){video.Dispose();video=null;}
            if(frames!=null){SetFrame(PlaybackFrame(playback.Elapsed.TotalSeconds));if(sound!=null)sound.Play();}
            SaveTiming();
        }
        void StartLoading(){
            try{StartWorker(root,"--launch --cover-token "+token);}
            catch(Exception error){try{BeginInvoke(new Action(()=>{mediaFailure=error.Message;SaveTiming();Close();}));}catch(InvalidOperationException){}}
        }
        bool maximized=false;
        int targetPid=0;
        Rectangle skipBounds;
        bool skipHover=false,skipPressed=false,skipFocused=false;
        float uiScale=1;
        void UpdatePlacement(){
            var cost=Stopwatch.StartNew();
            var process=targetPid>0?Process.GetProcessById(targetPid):PrimaryWindow();
            if(process==null||process.HasExited||process.MainWindowHandle==IntPtr.Zero||IsIconic(process.MainWindowHandle))return;
            var rect=BoundsOf(process);
            if(rect.Width<400||rect.Height<300)return;
            maximized=IsZoomed(process.MainWindowHandle);
            if(Bounds!=rect)Bounds=rect;
            ApplyCorners();
            maxWindowCheckMs=Math.Max(maxWindowCheckMs,cost.Elapsed.TotalMilliseconds);
        }
        void ApplyCorners(){
            if(!IsHandleCreated)return;
            uiScale=GetDpiForWindow(Handle)/96f;
            int preference=maximized?1:2;
            int disableTransitions=1;DwmSetWindowAttribute(Handle,3,ref disableTransitions,4);
            try{DwmSetWindowAttribute(Handle,33,ref preference,4);var margins=new Margins{left=1,right=1,top=1,bottom=1};DwmExtendFrameIntoClientArea(Handle,ref margins);}catch(DllNotFoundException){}
            skipBounds=new Rectangle(ClientSize.Width-(int)Math.Round(136*uiScale),(int)Math.Round(48*uiScale),(int)Math.Round(112*uiScale),(int)Math.Round(40*uiScale));
            PositionOverlays();if(video!=null)video.Update();
        }
        static GraphicsPath Rounded(RectangleF rect,float radius){
            var path=new GraphicsPath();float diameter=radius*2;
            path.AddArc(rect.X,rect.Y,diameter,diameter,180,90);path.AddArc(rect.Right-diameter,rect.Y,diameter,diameter,270,90);
            path.AddArc(rect.Right-diameter,rect.Bottom-diameter,diameter,diameter,0,90);path.AddArc(rect.X,rect.Bottom-diameter,diameter,diameter,90,90);path.CloseFigure();return path;
        }
        protected override CreateParams CreateParams {get{var value=base.CreateParams;value.Style|=0x00C40000;return value;}}
        protected override void OnHandleCreated(EventArgs e){base.OnHandleCreated(e);ApplyCorners();}
        protected override void OnResize(EventArgs e){base.OnResize(e);ApplyCorners();}
        sealed class SkipAccessibility:AccessibleObject {
            readonly StartupCover owner;
            public SkipAccessibility(StartupCover cover){owner=cover;}
            public override string Name{get{return "跳过 · Esc";}set{}}
            public override AccessibleRole Role{get{return AccessibleRole.PushButton;}}
            public override Rectangle Bounds{get{return owner.RectangleToScreen(owner.skipBounds);}}
            public override string DefaultAction{get{return "按下";}}
            public override void DoDefaultAction(){owner.Skip();}
            public override AccessibleStates State{get{return AccessibleStates.Focusable|(owner.skipFocused?AccessibleStates.Focused:0);}}
        }
        sealed class CoverAccessibility:ControlAccessibleObject {
            readonly SkipAccessibility skip;
            public CoverAccessibility(StartupCover cover):base(cover){skip=new SkipAccessibility(cover);}
            public override int GetChildCount(){return 1;}
            public override AccessibleObject GetChild(int index){return index==0?skip:null;}
        }
        protected override AccessibleObject CreateAccessibilityInstance(){return new CoverAccessibility(this);}
        void Skip(){try{File.WriteAllText(Path.Combine(root,"startup-cover-skip.json"),"{\"token\":\""+token+"\"}");}catch(IOException){}Close();}
        void SaveTiming(){
            try{File.WriteAllText(Path.Combine(root,"startup-cover-timing.json"),new JavaScriptSerializer().Serialize(new{token=token,firstMotionMs=firstMotionMs,heldAtSeconds=heldAt,elapsedMs=age.Elapsed.TotalMilliseconds,mediaFailure=mediaFailure,videoFailure=videoFailure,player=video!=null?"windows-media-foundation":"cpu-compact-pcm",mediaFps=video!=null?48:fps,recoveryFps=fps,videoPositionSeconds=videoPosition,hostStage=hostStage,progress=startupProgress,progressPace=progressPace,progressSemantics="stage-weighted estimate; 100 requires verified host readiness",phaseTiming=phaseTiming,placementSource=placementSource,framesPainted=paintedFrames,maxFrameGapMs=maxFrameGapMs,maxDecodeMs=maxDecodeMs,maxDrawMs=maxDrawMs,maxWindowCheckMs=maxWindowCheckMs,bounds=new{x=Left,y=Top,w=Width,h=Height},dpi=uiScale*96,skip=new{x=skipBounds.X,y=skipBounds.Y,w=skipBounds.Width,h=skipBounds.Height},maximized=maximized}),Encoding.UTF8);}catch{}
        }
        DecodedFrame DecodeFrame(int index,int width,int height) {
            var cost=Stopwatch.StartNew();
            var encoded=new byte[lengths[index]];
            lock(readGate){
                if(framesClosing)return null;
                frames.Position=offsets[index];
                int read=0;while(read<encoded.Length){int count=frames.Read(encoded,read,encoded.Length-read);if(count==0)throw new EndOfStreamException();read+=count;}
            }
            var output=new DecodedFrame(width,height);
            try{
                using(var stream=new MemoryStream(encoded,false))using(var image=new Bitmap(stream)){
                    var pixels=image.LockBits(new Rectangle(0,0,image.Width,image.Height),System.Drawing.Imaging.ImageLockMode.ReadOnly,System.Drawing.Imaging.PixelFormat.Format24bppRgb);
                    try{
                        var info=new BitmapInfo{size=40,width=image.Width,height=-image.Height,planes=1,bits=24};
                        SetStretchBltMode(output.Dc,4);StretchDIBits(output.Dc,0,0,width,height,0,0,image.Width,image.Height,pixels.Scan0,ref info,0,0x00CC0020);GdiFlush();
                    }finally{image.UnlockBits(pixels);}
                }
                lock(frameGate)maxDecodeMs=Math.Max(maxDecodeMs,cost.Elapsed.TotalMilliseconds);
                return output;
            }catch{output.Dispose();throw;}
        }
        void SetFrame(int index) {
            if(frames==null||index==frameIndex)return;
            var image=DecodeFrame(index,ClientSize.Width,ClientSize.Height);if(image==null)return;
            var previous=currentFrame;currentFrame=image;frameIndex=index;
            if(previous!=null)previous.Dispose();Invalidate();
        }
        void ReleaseResources(){
            if(resourcesDisposed)return;resourcesDisposed=true;
            timer.Stop();timer.Dispose();playback.Stop();
            SaveTiming();if(video!=null){video.Dispose();video=null;}
            if(sound!=null){sound.Stop();sound.Dispose();}
            lock(frameGate){framesClosing=true;foreach(var frame in prepared.Values)frame.image.Dispose();prepared.Clear();}
            lock(readGate){if(frames!=null)frames.Dispose();}
            if(currentFrame!=null)currentFrame.Dispose();if(firstFrame!=null)firstFrame.Dispose();
        }
        protected override void Dispose(bool disposing){if(disposing)ReleaseResources();base.Dispose(disposing);}
        void AdvanceFrame(double seconds){
            PreparedFrame next=null;
            int width=ClientSize.Width,height=ClientSize.Height;
            lock(frameGate){
                foreach(var frame in prepared.Values)if(frame.at<=seconds&&frame.at>currentFrameAt&&(next==null||frame.at>next.at))next=frame;
                if(next!=null)prepared.Remove(next.index);
                var expired=new System.Collections.Generic.List<int>();
                foreach(var frame in prepared.Values)if(frame.at<=currentFrameAt||frame.at<seconds-.2||frame.image.Width!=width||frame.image.Height!=height)expired.Add(frame.index);
                foreach(int index in expired){prepared[index].image.Dispose();prepared.Remove(index);}
            }
            if(next!=null){
                var previous=currentFrame;currentFrame=next.image;frameIndex=next.index;currentFrameAt=next.at;
                if(previous!=null)previous.Dispose();Invalidate();
            }
            // Decode and resample a bounded three-frame lookahead off the UI thread.
            for(int ahead=0;ahead<=3;ahead++){
                double at=(Math.Floor(seconds*fps)+ahead)/fps;int index=PlaybackFrame(at+.000001);
                lock(frameGate){
                    if(framesClosing||pending.Count>=3)break;
                    if(index==frameIndex||pending.Contains(index)||prepared.ContainsKey(index))continue;
                    pending.Add(index);
                }
                System.Threading.ThreadPool.QueueUserWorkItem(_=>{
                    DecodedFrame image=null;
                    try{
                        image=DecodeFrame(index,width,height);
                        lock(frameGate){if(!framesClosing&&image!=null){prepared[index]=new PreparedFrame{index=index,at=at,image=image};image=null;}}
                    }catch(Exception error){
                        try{BeginInvoke(new Action(()=>{mediaFailure=error.Message;playback.Stop();SaveTiming();}));}catch(InvalidOperationException){}
                    }finally{if(image!=null)image.Dispose();lock(frameGate)pending.Remove(index);}
                });
            }
        }
        int PlaybackFrame(double seconds){
            int frame=(int)(seconds*fps),last=lengths.Length-1;
            if(frame<=last)return frame;
            // The long wait is a forward-only closed cycle, including the particle paths.
            int first=11*fps,span=lengths.Length-first;
            return span>0?first+(frame-first)%span:last;
        }
        public StartupCover(string directory,string launchToken):this(directory,launchToken,true) {}
        public StartupCover(string directory,string launchToken,bool startWorker) {
            root=directory;token=launchToken;Text="Codex EVA startup "+token;
            FormBorderStyle=FormBorderStyle.None;StartPosition=FormStartPosition.Manual;ShowInTaskbar=false;TopMost=true;
            AutoScaleMode=AutoScaleMode.None;
            BackColor=Color.FromArgb(4,6,7);DoubleBuffered=false;KeyPreview=true;
            var area=Screen.FromPoint(Cursor.Position).WorkingArea;
            int width=Math.Min(1440,area.Width*4/5),height=Math.Min(900,area.Height*4/5);
            Bounds=new Rectangle(area.X+(area.Width-width)/2,area.Y+(area.Height-height)/2,width,height);
            bool muted=false;
            try{
                string home=Environment.GetEnvironmentVariable("CODEX_HOME");
                if(string.IsNullOrWhiteSpace(home))home=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),".codex");
                var state=new JavaScriptSerializer{MaxJsonLength=16*1024*1024}.Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(Path.Combine(home,".codex-global-state.json"),Encoding.UTF8));
                Bounds=CodexBounds((System.Collections.Generic.Dictionary<string,object>)state["electron-main-window-bounds"],out maximized);placementSource="codex-window-state";
            }catch{}
            try{
                var saved=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,int>>(File.ReadAllText(Path.Combine(root,"window-placement.json")));
                var rect=new Rectangle(saved["x"],saved["y"],saved["w"],saved["h"]);
                var visible=Rectangle.Intersect(SystemInformation.VirtualScreen,rect);
                if(rect.Width>=400&&rect.Height>=300&&visible.Width>=200&&visible.Height>=200){
                    // Codex's own state is authoritative; this physical-pixel record is a fallback.
                    if(placementSource!="codex-window-state"){Bounds=KeepOnScreen(rect);maximized=saved.ContainsKey("maximized")&&saved["maximized"]==1;placementSource="eva-placement";}
                }
            }catch{}
            string poster=Path.Combine(root,"startup-first-frame.jpg");
            if(File.Exists(poster))firstFrame=new Bitmap(poster);
            bool nativeMotion=true;
            try{
                var saved=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"state.json"),Encoding.UTF8));
                var verification=(System.Collections.Generic.Dictionary<string,object>)saved["verification"];
                var theme=(System.Collections.Generic.Dictionary<string,object>)verification["theme"];
                nativeMotion=(bool)theme["motion"];
            }catch{}
            try{
                var manifest=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"manifest.json"),Encoding.UTF8));
                var motion=(System.Collections.Generic.Dictionary<string,object>)manifest["motion"];
                muted=(bool)motion["muted"];
            }catch{}
            string clip=Path.Combine(root,"startup-native.frames");
            if(nativeMotion&&File.Exists(clip)){
                try{
                    frames=new FileStream(clip,FileMode.Open,FileAccess.Read,FileShare.Read,65536);
                    using(var reader=new BinaryReader(frames,Encoding.UTF8,true)){
                        if(reader.ReadInt32()!=0x31415645)throw new InvalidDataException("Invalid native frame header");
                        fps=reader.ReadInt32();int count=reader.ReadInt32();
                        if(fps<1||fps>60||count<1||count>3600)throw new InvalidDataException("Invalid native frame rate/count");
                        offsets=new int[count];lengths=new int[count];
                        for(int i=0;i<count;i++){
                            lengths[i]=reader.ReadInt32();offsets[i]=(int)reader.BaseStream.Position;
                            if(lengths[i]<4||lengths[i]>16*1024*1024||reader.BaseStream.Position+lengths[i]>frames.Length)throw new InvalidDataException("Invalid native frame length");
                            reader.BaseStream.Position+=lengths[i];
                        }
                    }
                    if(!File.Exists(Path.Combine(root,"startup-native-video.mp4")))SetFrame(0);
                }catch(Exception error){if(frames!=null)frames.Dispose();frames=null;mediaFailure=error.Message;SaveTiming();}
                string audio=Path.Combine(root,"startup-native.wav");
                mutedVideo=muted;
                if(!muted&&File.Exists(audio))try{sound=new SoundPlayer(audio);sound.Load();}catch{sound=null;}
            }
            MouseMove+=(sender,e)=>{bool hover=skipBounds.Contains(e.Location);if(hover!=skipHover){skipHover=hover;Cursor=hover?Cursors.Hand:Cursors.Default;Invalidate(skipBounds);}};
            MouseLeave+=(sender,e)=>{skipHover=false;skipPressed=false;Cursor=Cursors.Default;Invalidate(skipBounds);};
            MouseDown+=(sender,e)=>{skipPressed=e.Button==MouseButtons.Left&&skipBounds.Contains(e.Location);};
            MouseUp+=(sender,e)=>{if(skipPressed&&skipBounds.Contains(e.Location))Skip();skipPressed=false;};
            timer.Interval=1;timer.Tick+=(sender,e)=>{
                if(dismissAt>=0){double fade=(age.Elapsed.TotalMilliseconds-dismissAt)/200;if(fade>=1){Hide();Close();return;}Opacity=Math.Max(.01,1-fade);}
                if(video!=null&&playback.IsRunning)try{
                    videoPosition=video.Position;frameIndex=PlaybackFrame(videoPosition);
                    if(firstMotionMs<0&&videoPosition>.001){firstMotionMs=age.Elapsed.TotalMilliseconds;SaveTiming();}
                    PositionOverlays();
                }catch(Exception error){FailVideo(error.Message);}
                else if(frames!=null&&playback.IsRunning)try{AdvanceFrame(playback.Elapsed.TotalSeconds);}catch(Exception error){mediaFailure=error.Message;playback.Stop();SaveTiming();}
                if(statusOverlay!=null&&age.Elapsed.TotalMilliseconds>=nextStageRead){
                    nextStageRead=age.Elapsed.TotalMilliseconds+250;
                    try{
                        var state=new JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"startup-stage.json")));
                        if((string)state["token"]==token){
                            string stage=(string)state["stage"];
                            if(stage!=hostStage){hostStage=stage;stageFloor=Math.Max(startupProgress,StagePercent(stage));stageCeiling=Math.Min(99,StagePercent(stage)+3);stageAt=age.Elapsed.TotalSeconds;}
                            if(state.ContainsKey("hostReady"))hostReady=(bool)state["hostReady"];
                        }
                    }catch{}
                    startupProgress=hostReady?100:Math.Min(99,Math.Max(startupProgress,stageFloor+Math.Max(0,stageCeiling-stageFloor)*(1-Math.Exp(-(age.Elapsed.TotalSeconds-stageAt)/progressPace))));
                    PositionOverlays();statusOverlay.Invalidate();
                }
                if(age.Elapsed.TotalSeconds>45)Close();
            };
            Shown+=(sender,e)=>{try{Refresh();playback.Start();if(nativeMotion)StartVideo();if(video==null&&sound!=null)sound.Play();timer.Start();if(startWorker)new System.Threading.Thread(StartLoading){IsBackground=false}.Start();}catch(Exception error){mediaFailure=error.Message;SaveTiming();Close();}};
            KeyDown+=(sender,e)=>{if(e.KeyCode==Keys.Escape||((e.KeyCode==Keys.Enter||e.KeyCode==Keys.Space)&&skipFocused))Skip();};
            FormClosed+=(sender,e)=>ReleaseResources();
        }
        protected override void OnPaintBackground(PaintEventArgs e){if(currentFrame==null&&firstFrame==null)base.OnPaintBackground(e);}
        protected override void OnPaint(PaintEventArgs e){
            var cost=Stopwatch.StartNew();
            base.OnPaint(e);
            if(video!=null){video.Update();return;}
            if(currentFrame!=null){
                var hdc=e.Graphics.GetHdc();
                try{
                    if(currentFrame.Width==ClientSize.Width&&currentFrame.Height==ClientSize.Height)BitBlt(hdc,0,0,ClientSize.Width,ClientSize.Height,currentFrame.Dc,0,0,0x00CC0020);
                    else{SetStretchBltMode(hdc,4);StretchBlt(hdc,0,0,ClientSize.Width,ClientSize.Height,currentFrame.Dc,0,0,currentFrame.Width,currentFrame.Height,0x00CC0020);}
                }finally{e.Graphics.ReleaseHdc(hdc);}
            }else if(firstFrame!=null){
                var image=firstFrame;
                var format=image.PixelFormat==System.Drawing.Imaging.PixelFormat.Format24bppRgb?System.Drawing.Imaging.PixelFormat.Format24bppRgb:System.Drawing.Imaging.PixelFormat.Format32bppArgb;
                var pixels=image.LockBits(new Rectangle(0,0,image.Width,image.Height),System.Drawing.Imaging.ImageLockMode.ReadOnly,format);
                try{
                    var info=new BitmapInfo{size=40,width=image.Width,height=-image.Height,planes=1,bits=(short)(format==System.Drawing.Imaging.PixelFormat.Format24bppRgb?24:32)};
                    var hdc=e.Graphics.GetHdc();
                    try{SetStretchBltMode(hdc,4);StretchDIBits(hdc,0,0,ClientSize.Width,ClientSize.Height,0,0,image.Width,image.Height,pixels.Scan0,ref info,0,0x00CC0020);}
                    finally{e.Graphics.ReleaseHdc(hdc);}
                }finally{image.UnlockBits(pixels);}
            }
            PaintSkip(e.Graphics);
            maxDrawMs=Math.Max(maxDrawMs,cost.Elapsed.TotalMilliseconds);
            if(frameIndex!=lastPainted){
                double now=age.Elapsed.TotalMilliseconds;
                if(lastPainted>=0)maxFrameGapMs=Math.Max(maxFrameGapMs,now-lastPaintMs);
                lastPainted=frameIndex;lastPaintMs=now;paintedFrames++;
                double at=(double)frameIndex/fps;
                string phase=at<7.5/1.8?"entry":at<7.5/1.8+2.4?"lcl":at<7.5/1.8+2.4+2.85?"grid":"sync";
                if(!phaseTiming.ContainsKey(phase))phaseTiming[phase]=new PhaseTiming();phaseTiming[phase].Add(now);
                if(firstMotionMs<0&&frameIndex>0){firstMotionMs=now;SaveTiming();}
            }
        }
        void PaintSkip(Graphics graphics){
            graphics.SmoothingMode=SmoothingMode.AntiAlias;
            var buttonRect=new RectangleF(skipBounds.X+.5f*uiScale,skipBounds.Y+.5f*uiScale,skipBounds.Width-uiScale,skipBounds.Height-uiScale);
            using(var shape=Rounded(buttonRect,4*uiScale))
            using(var fill=new SolidBrush(skipHover?Color.FromArgb(230,75,56,20):Color.FromArgb(204,12,12,12)))
            using(var border=new Pen(skipHover?Color.FromArgb(211,174,80):Color.FromArgb(155,116,87),uiScale)){
                graphics.FillPath(fill,shape);graphics.DrawPath(border,shape);
            }
            using(var font=new Font("Segoe UI",13*uiScale,FontStyle.Regular,GraphicsUnit.Pixel))
            using(var brush=new SolidBrush(Color.FromArgb(238,230,224)))
            using(var format=new StringFormat{Alignment=StringAlignment.Center,LineAlignment=StringAlignment.Center})graphics.DrawString("跳过 · Esc",font,brush,skipBounds,format);
            if(skipFocused)using(var focus=Rounded(new RectangleF(skipBounds.X-4*uiScale,skipBounds.Y-4*uiScale,skipBounds.Width+8*uiScale,skipBounds.Height+8*uiScale),6*uiScale))using(var pen=new Pen(Color.FromArgb(211,174,80),2*uiScale))graphics.DrawPath(pen,focus);
        }
        protected override void WndProc(ref Message message){
            // Startup/splash windows are transient; align only at the renderer handoff below.
            if(message.Msg==0x802D){targetPid=message.WParam.ToInt32();return;}
            if(message.Msg==0x802E){message.Result=new IntPtr((long)(startupProgress*1000)+1);return;}
            if(message.Msg==0x8030){message.Result=new IntPtr((long)((video!=null?video.Position:playback.Elapsed.TotalSeconds)*1000)+1);return;}
            if(message.Msg==0x8031){message.Result=new IntPtr(video!=null?48:fps);return;}
            if(message.Msg==0x83&&message.WParam!=IntPtr.Zero){message.Result=IntPtr.Zero;return;}
            if(message.Msg==0x802C){
                if(video!=null)message.Result=new IntPtr((long)((double)PlaybackFrame(video.Position)/fps*1000)+1);
                else if(frames!=null&&mediaFailure==null)message.Result=new IntPtr((long)((double)Math.Max(0,lastPainted)/fps*1000)+1);
                return;
            }
            if(message.Msg==0x802B){
                // Keep playing while Chromium paints its handoff frame; pausing here exposes a visible stall.
                if(frames!=null&&mediaFailure==null){try{UpdatePlacement();}catch(InvalidOperationException){}catch(ArgumentException){}if(video!=null){videoPosition=video.Position;frameIndex=PlaybackFrame(videoPosition);}heldAt=(double)Math.Max(0,frameIndex)/fps;message.Result=new IntPtr((long)(heldAt*1000)+1);SaveTiming();}return;
            }
            if(message.Msg==0x802A){if(dismissAt<0)dismissAt=age.Elapsed.TotalMilliseconds;return;}base.WndProc(ref message);
        }
        protected override bool ProcessDialogKey(Keys key){if(key==Keys.Tab){skipFocused=true;Invalidate();return true;}return base.ProcessDialogKey(key);}
    }
    [StructLayout(LayoutKind.Sequential)] struct UniqueProcess {public uint pid;public System.Runtime.InteropServices.ComTypes.FILETIME started;}
    [DllImport("rstrtmgr.dll",CharSet=CharSet.Unicode)]static extern int RmStartSession(out uint session,int flags,StringBuilder key);
    [DllImport("rstrtmgr.dll",CharSet=CharSet.Unicode)]static extern int RmRegisterResources(uint session,uint fileCount,string[] files,uint processCount,UniqueProcess[] processes,uint serviceCount,string[] services);
    [DllImport("rstrtmgr.dll")]static extern int RmShutdown(uint session,uint flags,IntPtr callback);
    [DllImport("rstrtmgr.dll")]static extern int RmEndSession(uint session);
    static object CloseForRestart(Process process) {
        bool requested=process.CloseMainWindow(),forced=false;
        if(!process.WaitForExit(5000)) {forced=true;process.Kill();if(!process.WaitForExit(5000))throw new Exception("Previous Codex process did not exit");}
        return new{pid=process.Id,requested=requested,forced=forced,exited=true};
    }
    [STAThread] static int Main(string[] args) {
        try {
            try{SetProcessDpiAwarenessContext(new IntPtr(-4));}catch{}
            if(args.Length>0 && (args[0]=="--native-activate"||args[0]=="--native-cold-activate")) {
                if(args[0]=="--native-activate") {
                    var existing=PrimaryWindow();
                    if(existing!=null){Foreground(existing);Console.WriteLine("{\"pid\":"+existing.Id+"}");return 0;}
                }
                uint pid;var manager=(IApplicationActivationManager)new ApplicationActivationManager();
                // AO_NOSPLASHSCREEN can terminate a package that is not in debug mode.
                int hr=manager.ActivateApplication(Aumid,args.Length>1?args[1]:"",0u,out pid);
                Marshal.ThrowExceptionForHR(hr);Console.WriteLine("{\"pid\":"+pid+"}");return 0;
            }
            if(args.Length>1&&args[0]=="--dismiss-cover") {
                var cover=FindWindow(null,"Codex EVA startup "+args[1]);IntPtr result;
                bool closed=cover!=IntPtr.Zero&&SendMessageTimeout(cover,0x802A,IntPtr.Zero,IntPtr.Zero,2,2000,out result)!=IntPtr.Zero;
                Console.WriteLine("{\"dismissed\":"+closed.ToString().ToLower()+"}");return 0;
            }
            if(args.Length>1&&args[0]=="--window-placement") {
                var handle=Process.GetProcessById(int.Parse(args[1])).MainWindowHandle;
                if(handle==IntPtr.Zero||IsIconic(handle))return 1;
                var rect=BoundsOf(Process.GetProcessById(int.Parse(args[1])));
                if(rect.Width<400||rect.Height<300)return 1;
                Console.WriteLine("{\"x\":"+rect.X+",\"y\":"+rect.Y+",\"w\":"+rect.Width+",\"h\":"+rect.Height+",\"dpi\":"+GetDpiForWindow(handle)+",\"maximized\":"+(IsZoomed(handle)?1:0)+"}");return 0;
            }
            if(args.Length>1 && args[0]=="--foreground") {
                Foreground(Process.GetProcessById(int.Parse(args[1])));return 0;
            }
            if(args.Length>1 && args[0]=="--graceful-close") {
                var process=Process.GetProcessById(int.Parse(args[1]));Console.WriteLine("{\"requested\":"+process.CloseMainWindow().ToString().ToLower()+"}");return 0;
            }
            if(args.Length>1 && args[0]=="--restart-close") {
                using(var process=Process.GetProcessById(int.Parse(args[1]))) {
                    // Retain the validated process handle across close/wait/kill to avoid PID reuse.
                    var handle=process.Handle;uint length=0;GetApplicationUserModelId(handle,ref length,null);
                    var identity=new StringBuilder((int)Math.Max(1u,length));
                    if(GetApplicationUserModelId(handle,ref length,identity)!=0||identity.ToString()!=Aumid)throw new Exception("Restart target is not this Codex package");
                    string path=process.MainModule.FileName;
                    if(!path.EndsWith("\\ChatGPT.exe",StringComparison.OrdinalIgnoreCase))throw new Exception("Unexpected Codex restart executable");
                    Console.WriteLine(new JavaScriptSerializer().Serialize(CloseForRestart(process)));return 0;
                }
            }
            if(args.Length>1 && args[0]=="--installer-close") {
                var process=Process.GetProcessById(int.Parse(args[1]));
                string path=process.MainModule.FileName;
                if(path.IndexOf("WindowsApps\\OpenAI.Codex_",StringComparison.OrdinalIgnoreCase)<0 || !path.EndsWith("\\ChatGPT.exe",StringComparison.OrdinalIgnoreCase))throw new Exception("Unexpected installation restart target");
                long fileTime=process.StartTime.ToUniversalTime().ToFileTimeUtc();
                var unique=new UniqueProcess{pid=(uint)process.Id,started=new System.Runtime.InteropServices.ComTypes.FILETIME{dwLowDateTime=(int)(fileTime&0xffffffff),dwHighDateTime=(int)(fileTime>>32)}};
                uint session;int result=RmStartSession(out session,0,new StringBuilder(33));
                if(result!=0)throw new Exception("Restart Manager session failed: "+result);
                try {
                    result=RmRegisterResources(session,0,null,1,new[]{unique},0,null);
                    if(result!=0)throw new Exception("Restart Manager registration failed: "+result);
                    // No force flag. The application can refuse the normal installation restart.
                    result=RmShutdown(session,0,IntPtr.Zero);
                    Console.WriteLine("{\"restartManagerResult\":"+result+",\"force\":false}");
                    if(result!=0)throw new Exception("Application refused installation restart: "+result);
                }finally{RmEndSession(session);}return 0;
            }
            string root=AppDomain.CurrentDomain.BaseDirectory;
            string mode=args.Length>0&&args[0]=="--restore"?"--restore":"--launch";
            if(args.Length>1&&args[0]=="--startup-cover") {
                bool first;using(var mutex=new System.Threading.Mutex(true,"Local\\EVA.Codex.Startup.Cover",out first)) {
                    if(!first)return 1;
                    try{SetProcessDpiAwarenessContext(new IntPtr(-4));}catch{}
                    Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
                    Application.Run(new StartupCover(root,args[1],false));return 0;
                }
            }
            StartWorker(root,mode);return 0;
        } catch(Exception error) {
            try{File.AppendAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"launcher-error.log"),DateTime.UtcNow.ToString("o")+" "+error.Message+Environment.NewLine);}catch{}
            return 1;
        }
    }
}
