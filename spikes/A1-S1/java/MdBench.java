// Reliquary A1-S1 kit addendum (THROWAWAY spike code, not production).
// Platform SHA-256 probe: measures java.security.MessageDigest "SHA-256" and javax.crypto.Mac
// "HmacSHA256" from the default (highest-priority) provider, which on Android is normally
// Conscrypt (BoringSSL). Runs on a desktop JVM for a logic check, and on Android through
// app_process after d8 (see docs/research/kits/A1-S1/README.md, addendum steps A3-A5).
// Prints one JSON object per line, like a1-hashbench. Usage: MdBench [MiB] [runs]
import java.security.MessageDigest;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public class MdBench {
    static final byte[] KEY = "reliquary-a1-s1-benchmark-key-32".getBytes();

    static byte[] randomBuf(int len) {
        // xorshift64*, same generator as a1-hashbench (contents do not affect hash speed)
        byte[] v = new byte[len];
        long x = 0x9E3779B97F4A7C15L;
        for (int i = 0; i < len; i += 8) {
            x ^= x >>> 12; x ^= x << 25; x ^= x >>> 27;
            long r = x * 0x2545F4914F6CDD1DL;
            for (int j = 0; j < 8 && i + j < len; j++) v[i + j] = (byte) (r >>> (8 * j));
        }
        return v;
    }

    interface Work { byte[] run(byte[] buf) throws Exception; }

    static double median(double[] a) {
        double[] s = a.clone(); java.util.Arrays.sort(s);
        int n = s.length; return n % 2 == 1 ? s[n / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
    }

    static void bench(String name, Work w, byte[] buf, int runs) throws Exception {
        double[] rates = new double[runs];
        int sink = 0;
        java.lang.management.ThreadMXBean tm = null;
        try { tm = java.lang.management.ManagementFactory.getThreadMXBean(); } catch (Throwable t) { /* absent on Android */ }
        double[] cpg = new double[runs];
        for (int r = 0; r <= runs; r++) { // first run is warm-up (JIT)
            long c0 = tm != null ? tm.getCurrentThreadCpuTime() : -1;
            long t0 = System.nanoTime();
            byte[] id = w.run(buf);
            double dt = (System.nanoTime() - t0) / 1e9;
            long c1 = tm != null ? tm.getCurrentThreadCpuTime() : -1;
            sink ^= id[0] & 0xff;
            if (r > 0) {
                rates[r - 1] = buf.length / dt / 1e6;
                cpg[r - 1] = c0 >= 0 ? (c1 - c0) / 1e9 / (buf.length / 1e9) : Double.NaN;
            }
        }
        System.out.printf(java.util.Locale.ROOT,
            "{\"mode\":\"mem\",\"impl\":\"platform\",\"workload\":\"%s\",\"bytes\":%d,\"runs\":%d,\"mb_per_s_median\":%.0f,\"cpu_s_per_gb_median\":%s,\"sink\":%d}%n",
            name, buf.length, runs, median(rates),
            Double.isNaN(median(cpg)) ? "null" : String.format(java.util.Locale.ROOT, "%.3f", median(cpg)), sink);
    }

    public static void main(String[] a) throws Exception {
        int mib = a.length > 0 ? Integer.parseInt(a[0]) : 256;
        int runs = a.length > 1 ? Integer.parseInt(a[1]) : 5;
        final int chunk = 1 << 20;
        byte[] buf = randomBuf(mib << 20);
        MessageDigest probe = MessageDigest.getInstance("SHA-256");
        Mac mprobe = Mac.getInstance("HmacSHA256");
        mprobe.init(new SecretKeySpec(KEY, "HmacSHA256"));
        System.out.printf(java.util.Locale.ROOT,
            "{\"mode\":\"info\",\"impl\":\"platform\",\"md_provider\":\"%s %s\",\"mac_provider\":\"%s\",\"os_arch\":\"%s\",\"vm\":\"%s %s\",\"abi_hint\":\"%s\"}%n",
            probe.getProvider().getName(), String.valueOf(probe.getProvider().getVersion()), mprobe.getProvider().getName(),
            System.getProperty("os.arch"), System.getProperty("java.vm.name"), System.getProperty("java.vm.version"),
            System.getProperty("ro.product.cpu.abi", ""));
        final SecretKeySpec ks = new SecretKeySpec(KEY, "HmacSHA256");
        bench("platform_sha256", buf1 -> {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (int o = 0; o < buf1.length; o += chunk) md.update(buf1, o, Math.min(chunk, buf1.length - o));
            return md.digest();
        }, buf, runs);
        bench("platform_C1_sha256+hmac_content", buf1 -> {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            Mac m = Mac.getInstance("HmacSHA256"); m.init(ks);
            for (int o = 0; o < buf1.length; o += chunk) {
                int n = Math.min(chunk, buf1.length - o);
                md.update(buf1, o, n); m.update(buf1, o, n);
            }
            byte[] x = md.digest(), y = m.doFinal();
            for (int i = 0; i < 32; i++) x[i] ^= y[i];
            return x;
        }, buf, runs);
        bench("platform_C2_sha256_then_hmac_digest", buf1 -> {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (int o = 0; o < buf1.length; o += chunk) md.update(buf1, o, Math.min(chunk, buf1.length - o));
            Mac m = Mac.getInstance("HmacSHA256"); m.init(ks);
            return m.doFinal(md.digest());
        }, buf, runs);
    }
}
