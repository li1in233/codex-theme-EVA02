using System;
using System.Runtime.InteropServices;

// Windows SDK mfplay.h: preserve the native vtable order, including unused methods.
[ComImport,Guid("A714590A-58AF-430A-85BF-44F5EC838D85"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMfpPlayer {
 [PreserveSig]int Play(); [PreserveSig]int Pause(); [PreserveSig]int Stop(); [PreserveSig]int FrameStep();
 [PreserveSig]int SetPosition(ref Guid kind,ref VideoPosition value); [PreserveSig]int GetPosition(ref Guid kind,out VideoPosition value);
 [PreserveSig]int GetDuration(ref Guid kind,out VideoPosition value); [PreserveSig]int SetRate(float value); [PreserveSig]int GetRate(out float value);
 [PreserveSig]int GetSupportedRates(bool forward,out float slow,out float fast); [PreserveSig]int GetState(out int value);
 [PreserveSig]int CreateMediaItemFromURL([MarshalAs(UnmanagedType.LPWStr)]string url,bool sync,UIntPtr user,out IntPtr item);
 [PreserveSig]int CreateMediaItemFromObject(IntPtr obj,bool sync,UIntPtr user,out IntPtr item);
 [PreserveSig]int SetMediaItem(IntPtr item); [PreserveSig]int ClearMediaItem(); [PreserveSig]int GetMediaItem(out IntPtr item);
 [PreserveSig]int GetVolume(out float value); [PreserveSig]int SetVolume(float value); [PreserveSig]int GetBalance(out float value); [PreserveSig]int SetBalance(float value);
 [PreserveSig]int GetMute(out bool value); [PreserveSig]int SetMute(bool value);
 [PreserveSig]int GetNativeVideoSize(IntPtr size,IntPtr aspect); [PreserveSig]int GetIdealVideoSize(IntPtr min,IntPtr max);
 [PreserveSig]int SetVideoSourceRect(IntPtr rect); [PreserveSig]int GetVideoSourceRect(IntPtr rect);
 [PreserveSig]int SetAspectRatioMode(int mode); [PreserveSig]int GetAspectRatioMode(out int mode); [PreserveSig]int GetVideoWindow(out IntPtr window);
 [PreserveSig]int UpdateVideo(); [PreserveSig]int SetBorderColor(int color); [PreserveSig]int GetBorderColor(out int color);
 [PreserveSig]int InsertEffect(IntPtr effect,bool optional); [PreserveSig]int RemoveEffect(IntPtr effect); [PreserveSig]int RemoveAllEffects(); [PreserveSig]int Shutdown();
}
[StructLayout(LayoutKind.Explicit,Size=24)]struct VideoPosition{[FieldOffset(0)]public ushort type;[FieldOffset(8)]public long value;}
[ComVisible(true),Guid("766C8FFB-5FDB-4FEA-A28D-B912996F51BD"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMfpCallback{[PreserveSig]void OnMediaPlayerEvent(IntPtr header);}

[ComVisible(true),ClassInterface(ClassInterfaceType.None)]
sealed class NativeVideo:IMfpCallback,IDisposable {
 [DllImport("mfplay.dll",CharSet=CharSet.Unicode)]static extern int MFPCreateMediaPlayer(string url,bool start,int options,IMfpCallback callback,IntPtr window,out IMfpPlayer player);
 readonly Action<Action> dispatch; readonly Action started; readonly Action<string> failed;
 IMfpPlayer player;bool disposed,hasStarted;readonly bool muted;
 public NativeVideo(IntPtr window,string file,bool muted,Action<Action> dispatch,Action started,Action<string> failed){
  this.dispatch=dispatch;this.started=started;this.failed=failed;this.muted=muted;
  Marshal.ThrowExceptionForHR(MFPCreateMediaPlayer(null,false,0,this,window,out player));
  try{
   IntPtr item;Marshal.ThrowExceptionForHR(player.CreateMediaItemFromURL(file,true,UIntPtr.Zero,out item));
   try{Marshal.ThrowExceptionForHR(player.SetMediaItem(item));}finally{Marshal.Release(item);}
  }catch{Dispose();throw;}
 }
 public double Position{get{if(disposed||player==null||!hasStarted)return 0;var kind=Guid.Empty;VideoPosition value;Marshal.ThrowExceptionForHR(player.GetPosition(ref kind,out value));return value.value/10000000.0;}}
 public void Pause(){if(!disposed)Marshal.ThrowExceptionForHR(player.Pause());}
 public void Update(){if(!disposed)player.UpdateVideo();}
 public void OnMediaPlayerEvent(IntPtr header){
  int kind=Marshal.ReadInt32(header),hr=Marshal.ReadInt32(header,4);
  dispatch(()=>{
   if(disposed)return;
   try{if(hr<0)Marshal.ThrowExceptionForHR(hr);if(kind==6){Marshal.ThrowExceptionForHR(player.SetAspectRatioMode(0));Marshal.ThrowExceptionForHR(player.SetMute(muted));Marshal.ThrowExceptionForHR(player.Play());}if(kind==0){hasStarted=true;started();}}
   catch(Exception error){failed(error.Message);}
  });
 }
 public void Dispose(){if(disposed)return;disposed=true;if(player!=null){player.Shutdown();Marshal.ReleaseComObject(player);player=null;}}
}
