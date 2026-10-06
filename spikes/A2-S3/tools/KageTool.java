// THROWAWAY SPIKE helper: kage (Kotlin age, Maven com.github.android-password-store:kage:0.8.0) from Java.
import kage.Age;
import kage.Identity;
import kage.Recipient;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.InflaterInputStream;

public class KageTool {
  static String sha(byte[] b) throws Exception {
    StringBuilder s = new StringBuilder();
    for (byte x : MessageDigest.getInstance("SHA-256").digest(b)) s.append(String.format("%02x", x));
    return s.toString();
  }
  static List<Identity> ids(String text) { return Age.parseIdentities(new BufferedReader(new StringReader(text))); }
  static String esc(String s) { return s == null ? "null" : "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\""; }
  public static void main(String[] a) throws Exception {
    switch (a[0]) {
      case "decrypt": {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
          Age.decryptStream(ids(Files.readString(Path.of(a[1]))), new FileInputStream(a[2]), out);
          if (a.length > 3) Files.write(Path.of(a[3]), out.toByteArray());
          System.out.println("{\"ok\":true,\"bytes\":" + out.size() + ",\"sha256\":\"" + sha(out.toByteArray()) + "\"}");
        } catch (Exception e) {
          System.out.println("{\"ok\":false,\"error\":" + esc(e.getClass().getSimpleName() + ": " + e.getMessage()) + "}");
          System.exit(1);
        }
        break;
      }
      case "encrypt": {
        List<Recipient> r = Age.parseRecipients(new BufferedReader(new FileReader(a[1])));
        Age.encryptStream(r, new FileInputStream(a[2]), new FileOutputStream(a[3]), false);
        break;
      }
      case "header": {
        byte[] h = Age.extractHeader(new FileInputStream(a[1]));
        System.out.println("{\"ok\":true,\"header_len\":" + h.length + "}");
        break;
      }
      case "cctv": {
        File[] fs = new File(a[1]).listFiles();
        Arrays.sort(fs);
        int pass = 0, fail = 0, na = 0;
        List<String> failed = new ArrayList<>();
        for (File f : fs) {
          byte[] raw = Files.readAllBytes(f.toPath());
          int off = 0;
          Map<String, String> kv = new LinkedHashMap<>();
          StringBuilder idtext = new StringBuilder();
          while (true) {
            int i = off; while (raw[i] != '\n') i++;
            String line = new String(raw, off, i - off, "UTF-8");
            off = i + 1;
            if (line.isEmpty()) break;
            int j = line.indexOf(": ");
            String k = j < 0 ? line : line.substring(0, j), v = j < 0 ? "" : line.substring(j + 2);
            if (k.equals("identity")) idtext.append(v).append('\n'); else kv.put(k, v);
          }
          byte[] file = Arrays.copyOfRange(raw, off, raw.length);
          if ("zlib".equals(kv.get("compressed"))) file = new InflaterInputStream(new ByteArrayInputStream(file)).readAllBytes();
          String expect = kv.get("expect");
          if (kv.containsKey("armored") || idtext.length() == 0) { na++; continue; }
          String got, err = null; byte[] out = null;
          ByteArrayOutputStream bo = new ByteArrayOutputStream();
          try { Age.decryptStream(ids(idtext.toString()), new ByteArrayInputStream(file), bo); out = bo.toByteArray(); got = "success"; }
          catch (Throwable e) { got = "error"; err = e.getClass().getSimpleName() + ": " + e.getMessage(); }
          boolean ok = expect.equals("success") ? (got.equals("success") && sha(out).equals(kv.get("payload"))) : got.equals("error");
          if (ok) pass++; else { fail++; failed.add(f.getName()); }
          System.out.println("{\"vector\":" + esc(f.getName()) + ",\"expect\":" + esc(expect) + ",\"got\":" + esc(got) + ",\"result\":" + esc(ok ? "pass" : "FAIL") + ",\"error\":" + esc(err) + "}");
        }
        System.out.println("{\"summary\":{\"pass\":" + pass + ",\"fail\":" + fail + ",\"na\":" + na + ",\"failed\":" + esc(String.join(",", failed)) + "}}");
        break;
      }
    }
  }
}
