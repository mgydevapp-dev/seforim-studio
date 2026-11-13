package org.seforimstudio.app;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.StatFs;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.util.Log;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.content.FileProvider;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Seforim Studio for Android: the same Python engine and web pages as the Windows app, shown in a WebView. */
public class MainActivity extends Activity {
    static final String TAG = "SeforimStudio";
    static Context appCtx;
    static final int REQ_CHOOSER = 11, REQ_IMPORT = 12, REQ_PERM = 13;

    WebView web;
    String baseUrl = "";
    ValueCallback<Uri[]> fileCb;
    Uri cameraUri;
    String importDest;
    static volatile JSONObject importState = new JSONObject();
    final Handler ui = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        appCtx = getApplicationContext();
        WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setSupportZoom(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.addJavascriptInterface(new Bridge(), "SeforimAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if ("127.0.0.1".equals(u.getHost()) || "about".equals(u.getScheme()) || "data".equals(u.getScheme())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { }
                return true;  // other web sites open in the phone's browser
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                return openChooser(cb, p);
            }
        });
        web.setDownloadListener((url, ua, cd, mime, len) -> new Thread(() -> downloadUrl(url, cd, mime)).start());
        web.loadDataWithBaseURL(null, "<html><body style='font-family:sans-serif;text-align:center;padding-top:30vh;background:#f7f3ea;color:#3b2f1e'>"
                + "<h2>📖 Seforim Studio</h2><p>Starting…</p><p style='color:#888;font-size:13px'>The first start after installing takes up to a minute.</p></body></html>",
                "text/html", "utf-8", null);
        new Thread(this::startEngine).start();
    }

    // ------------------------------------------------------------------ the Python engine
    void startEngine() {
        try {
            File app = new File(getFilesDir(), "app");
            unpackApp(app);
            if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
            PyObject m = Python.getInstance().getModule("android_main");
            int port = m.callAttr("start", config().toString()).toInt();
            baseUrl = "http://127.0.0.1:" + port + "/";
            ui.post(() -> web.loadUrl(baseUrl));
        } catch (Throwable t) {
            StringWriter sw = new StringWriter();
            t.printStackTrace(new PrintWriter(sw));
            Log.e(TAG, "start failed", t);
            String msg = android.text.Html.escapeHtml(sw.toString());
            ui.post(() -> web.loadDataWithBaseURL(null, "<html><body style='font-family:sans-serif;padding:16px'><h3>Seforim Studio could not start</h3><pre style='white-space:pre-wrap;font-size:11px'>"
                    + msg + "</pre></body></html>", "text/html", "utf-8", null));
        }
    }

    /** app.zip (the Python engine, web pages, catalog) is unpacked once per installed version. */
    void unpackApp(File dest) throws Exception {
        PackageInfo pi = getPackageManager().getPackageInfo(getPackageName(), 0);
        String stamp = pi.versionCode + "-" + pi.lastUpdateTime;
        File mark = new File(dest, ".version");
        if (mark.exists() && stamp.equals(readText(mark))) return;
        deleteTree(dest);
        dest.mkdirs();
        try (ZipInputStream z = new ZipInputStream(getAssets().open("app.zip"))) {
            ZipEntry e;
            byte[] buf = new byte[1 << 16];
            while ((e = z.getNextEntry()) != null) {
                File f = new File(dest, e.getName());
                if (!f.getCanonicalPath().startsWith(dest.getCanonicalPath())) continue;
                if (e.isDirectory()) { f.mkdirs(); continue; }
                f.getParentFile().mkdirs();
                try (OutputStream o = new FileOutputStream(f)) {
                    int n;
                    while ((n = z.read(buf)) > 0) o.write(buf, 0, n);
                }
            }
        }
        try (OutputStream o = new FileOutputStream(mark)) { o.write(stamp.getBytes("UTF-8")); }
    }

    JSONObject config() throws Exception {
        JSONObject c = new JSONObject();
        c.put("files", getFilesDir().getAbsolutePath());
        c.put("app", new File(getFilesDir(), "app").getAbsolutePath());
        c.put("native", getApplicationInfo().nativeLibraryDir);
        c.put("download", Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath());
        c.put("storages", storages());
        c.put("sdk", Build.VERSION.SDK_INT);
        c.put("model", Build.MANUFACTURER + " " + Build.MODEL);
        c.put("ram", totalRam());
        return c;
    }

    static JSONArray storages() {
        JSONArray a = new JSONArray();
        try {
            File[] dirs = appCtx.getExternalFilesDirs(null);
            for (File d : dirs) {
                if (d == null) continue;
                d.mkdirs();
                boolean removable = Environment.isExternalStorageRemovable(d);
                JSONObject o = new JSONObject();
                o.put("path", d.getAbsolutePath());
                o.put("name", removable ? "SD card" : "Phone storage");
                o.put("removable", removable);
                String p = d.getAbsolutePath();
                int i = p.indexOf("/Android/data/");
                o.put("root", i > 0 ? p.substring(0, i) : p);
                try {
                    StatFs st = new StatFs(p);
                    o.put("free", st.getAvailableBytes());
                    o.put("total", st.getTotalBytes());
                } catch (Exception e) { }
                a.put(o);
            }
            JSONObject in = new JSONObject();
            File f = new File(appCtx.getFilesDir(), "big");
            f.mkdirs();
            in.put("path", f.getAbsolutePath());
            in.put("name", "Inside the app (private)");
            in.put("removable", false);
            StatFs st = new StatFs(f.getAbsolutePath());
            in.put("free", st.getAvailableBytes());
            in.put("total", st.getTotalBytes());
            a.put(in);
        } catch (Exception e) { Log.e(TAG, "storages", e); }
        return a;
    }

    long totalRam() {
        android.app.ActivityManager.MemoryInfo mi = new android.app.ActivityManager.MemoryInfo();
        ((android.app.ActivityManager) getSystemService(ACTIVITY_SERVICE)).getMemoryInfo(mi);
        return mi.totalMem;
    }

    static boolean hasAllFiles() {
        if (Build.VERSION.SDK_INT >= 30) return Environment.isExternalStorageManager();
        return appCtx.checkSelfPermission(android.Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
    }

    // ------------------------------------------------------------------ called from Python (core/server.py)
    /** Save a file into the phone's Download/Seforim Studio folder. Returns where it went. */
    public static String saveToDownloads(String src, String name, String mime) throws Exception {
        if (mime == null || mime.isEmpty()) mime = "application/octet-stream";
        if (Build.VERSION.SDK_INT >= 29) {
            ContentValues v = new ContentValues();
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
            v.put(MediaStore.MediaColumns.MIME_TYPE, mime);
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Seforim Studio");
            Uri u = appCtx.getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
            if (u == null) throw new Exception("could not create the file in Downloads");
            try (InputStream in = new FileInputStream(src); OutputStream o = appCtx.getContentResolver().openOutputStream(u)) {
                copy(in, o, null, 0);
            }
            return "Download/Seforim Studio/" + name;
        }
        File d = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "Seforim Studio");
        d.mkdirs();
        File f = new File(d, name);
        try (InputStream in = new FileInputStream(src); OutputStream o = new FileOutputStream(f)) { copy(in, o, null, 0); }
        return f.getAbsolutePath();
    }

    public static String storagesJson() { return storages().toString(); }

    public static boolean allFilesAccess() { return hasAllFiles(); }

    // ------------------------------------------------------------------ the web page's bridge
    class Bridge {
        @JavascriptInterface public String info() {
            try { JSONObject c = config(); c.put("all_files", hasAllFiles()); return c.toString(); } catch (Exception e) { return "{}"; }
        }
        @JavascriptInterface public boolean hasAllFiles() { return MainActivity.hasAllFiles(); }
        @JavascriptInterface public void askAllFiles() {
            ui.post(() -> {
                try {
                    if (Build.VERSION.SDK_INT >= 30) {
                        Intent i = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:" + getPackageName()));
                        startActivity(i);
                    } else {
                        requestPermissions(new String[]{android.Manifest.permission.READ_EXTERNAL_STORAGE, android.Manifest.permission.WRITE_EXTERNAL_STORAGE}, REQ_PERM);
                    }
                } catch (Exception e) {
                    startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));
                }
            });
        }
        /** Pick downloaded files (library / AI parts) with the phone's file picker and copy them into a folder. */
        @JavascriptInterface public void importFiles(String dest) {
            importDest = dest;
            ui.post(() -> {
                Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                startActivityForResult(i, REQ_IMPORT);
            });
        }
        @JavascriptInterface public String importStatus() { return importState.toString(); }
        @JavascriptInterface public void printHtml(String html, String title) { ui.post(() -> printHtmlNow(html, title)); }
        @JavascriptInterface public void printPage(String title) {
            ui.post(() -> {
                PrintManager pm = (PrintManager) getSystemService(PRINT_SERVICE);
                PrintDocumentAdapter ad = web.createPrintDocumentAdapter(title == null || title.isEmpty() ? "Seforim Studio" : title);
                pm.print(title == null ? "Seforim Studio" : title, ad, new PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).build());
            });
        }
        @JavascriptInterface public void keepAwake(boolean on) {
            ui.post(() -> {
                if (on) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            });
        }
        @JavascriptInterface public void openExternal(String url) {
            ui.post(() -> { try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); } catch (Exception e) { } });
        }
        /** Start the whole app again (after choosing a new storage place). */
        @JavascriptInterface public void restart() {
            ui.post(() -> {
                Intent i = getPackageManager().getLaunchIntentForPackage(getPackageName());
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                android.app.PendingIntent pi = android.app.PendingIntent.getActivity(MainActivity.this, 1, i,
                        android.app.PendingIntent.FLAG_CANCEL_CURRENT | android.app.PendingIntent.FLAG_IMMUTABLE);
                ((android.app.AlarmManager) getSystemService(ALARM_SERVICE)).set(android.app.AlarmManager.RTC, System.currentTimeMillis() + 700, pi);
                finishAffinity();
                Runtime.getRuntime().exit(0);
            });
        }
    }

    WebView printView;  // kept so it is not cleaned up while printing

    void printHtmlNow(String html, String title) {
        printView = new WebView(this);
        printView.getSettings().setJavaScriptEnabled(false);
        printView.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView v, String url) {
                PrintManager pm = (PrintManager) getSystemService(PRINT_SERVICE);
                String t = title == null || title.isEmpty() ? "Seforim Studio" : title;
                pm.print(t, v.createPrintDocumentAdapter(t), new PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.ISO_A4).build());
            }
        });
        printView.loadDataWithBaseURL(baseUrl, html, "text/html", "utf-8", null);
    }

    // ------------------------------------------------------------------ choosing files / taking a photo for the page
    boolean openChooser(ValueCallback<Uri[]> cb, WebChromeClient.FileChooserParams p) {
        if (fileCb != null) fileCb.onReceiveValue(null);
        fileCb = cb;
        try {
            Intent pick = p.createIntent();
            if (p.getMode() == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE) pick.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
            Intent chooser = Intent.createChooser(pick, "Choose");
            String accept = String.join(",", p.getAcceptTypes());
            cameraUri = null;
            if (accept.isEmpty() || accept.contains("image")) {
                File dir = new File(getCacheDir(), "camera");
                dir.mkdirs();
                File f = new File(dir, "page_" + System.currentTimeMillis() + ".jpg");
                cameraUri = FileProvider.getUriForFile(this, getPackageName() + ".files", f);
                Intent cam = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                cam.putExtra(MediaStore.EXTRA_OUTPUT, cameraUri);
                cam.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{cam});
            }
            startActivityForResult(chooser, REQ_CHOOSER);
            return true;
        } catch (Exception e) {
            fileCb = null;
            return false;
        }
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req == REQ_CHOOSER) {
            Uri[] out = null;
            if (res == RESULT_OK) {
                List<Uri> l = uris(data);
                if (l.isEmpty() && cameraUri != null) l.add(cameraUri);
                out = l.toArray(new Uri[0]);
            }
            if (fileCb != null) fileCb.onReceiveValue(out);
            fileCb = null;
        } else if (req == REQ_IMPORT && res == RESULT_OK) {
            List<Uri> l = uris(data);
            new Thread(() -> copyImports(l, importDest)).start();
        }
    }

    static List<Uri> uris(Intent data) {
        List<Uri> l = new ArrayList<>();
        if (data == null) return l;
        if (data.getClipData() != null)
            for (int i = 0; i < data.getClipData().getItemCount(); i++) l.add(data.getClipData().getItemAt(i).getUri());
        else if (data.getData() != null) l.add(data.getData());
        return l;
    }

    void copyImports(List<Uri> l, String dest) {
        try {
            File d = new File(dest);
            d.mkdirs();
            long total = 0;
            List<String> names = new ArrayList<>();
            List<Long> sizes = new ArrayList<>();
            for (Uri u : l) {
                String name = "file";
                long size = 0;
                try (Cursor c = getContentResolver().query(u, null, null, null, null)) {
                    if (c != null && c.moveToFirst()) {
                        int ni = c.getColumnIndex(OpenableColumns.DISPLAY_NAME), si = c.getColumnIndex(OpenableColumns.SIZE);
                        if (ni >= 0) name = c.getString(ni);
                        if (si >= 0) size = c.getLong(si);
                    }
                }
                names.add(name.replaceAll("[\\\\/:]", "_"));
                sizes.add(size);
                total += size;
            }
            long[] done = {0};
            for (int i = 0; i < l.size(); i++) {
                File f = new File(d, names.get(i)), tmp = new File(d, names.get(i) + ".copying");
                if (f.exists() && f.length() == sizes.get(i)) { done[0] += sizes.get(i); continue; }
                setImport("running", done[0], total, "Copying " + names.get(i) + "…");
                final long all = total;
                final String nm = names.get(i);
                try (InputStream in = getContentResolver().openInputStream(l.get(i)); OutputStream o = new FileOutputStream(tmp)) {
                    copy(in, o, n -> setImport("running", done[0] + n, all, "Copying " + nm + "…"), 0);
                }
                done[0] += tmp.length();
                if (f.exists()) f.delete();
                tmp.renameTo(f);
            }
            setImport("done", total, total, "Copied " + l.size() + " file(s). Now press Install.");
        } catch (Exception e) {
            Log.e(TAG, "import", e);
            setImport("error", 0, 0, "Could not copy the files: " + e.getMessage());
        }
    }

    static void setImport(String state, long done, long total, String msg) {
        try {
            JSONObject o = new JSONObject();
            o.put("state", state); o.put("done", done); o.put("total", total); o.put("message", msg);
            importState = o;
        } catch (Exception e) { }
    }

    void downloadUrl(String url, String cd, String mime) {
        try {
            String name = android.webkit.URLUtil.guessFileName(url, cd, mime);
            File tmp = new File(getCacheDir(), name);
            try (InputStream in = new java.net.URL(url).openStream(); OutputStream o = new FileOutputStream(tmp)) { copy(in, o, null, 0); }
            String where = saveToDownloads(tmp.getAbsolutePath(), name, mime);
            tmp.delete();
            ui.post(() -> android.widget.Toast.makeText(this, "Saved: " + where, android.widget.Toast.LENGTH_LONG).show());
        } catch (Exception e) { Log.e(TAG, "download", e); }
    }

    interface Progress { void at(long n); }

    static void copy(InputStream in, OutputStream o, Progress p, long unused) throws Exception {
        byte[] buf = new byte[1 << 20];
        long n = 0, last = 0;
        int k;
        while ((k = in.read(buf)) > 0) {
            o.write(buf, 0, k);
            n += k;
            if (p != null && n - last > (8 << 20)) { last = n; p.at(n); }
        }
    }

    static String readText(File f) {
        try (InputStream in = new FileInputStream(f)) {
            byte[] b = new byte[(int) f.length()];
            int n = in.read(b);
            return new String(b, 0, Math.max(0, n), "UTF-8");
        } catch (Exception e) { return ""; }
    }

    static void deleteTree(File f) {
        if (f.isDirectory()) { File[] l = f.listFiles(); if (l != null) for (File c : l) deleteTree(c); }
        f.delete();
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack();
        else if (web != null) web.evaluateJavascript("window.AndroidBack ? AndroidBack() : false", v -> { if (!"true".equals(v)) moveTaskToBack(true); });
        else super.onBackPressed();
    }
}
