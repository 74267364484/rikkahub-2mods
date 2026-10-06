import com.android.apksig.ApkSigner;
import java.io.File;
import java.io.FileInputStream;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;
import java.util.*;

public class Sign {
  public static void main(String[] a) throws Exception {
    String ksPath=a[0], pass=a[1], alias=a[2], in=a[3], out=a[4];
    KeyStore ks = KeyStore.getInstance("PKCS12");
    try (FileInputStream fis = new FileInputStream(ksPath)) { ks.load(fis, pass.toCharArray()); }
    PrivateKey key = (PrivateKey) ks.getKey(alias, pass.toCharArray());
    List<X509Certificate> certs = new ArrayList<>();
    for (java.security.cert.Certificate c : ks.getCertificateChain(alias)) certs.add((X509Certificate) c);
    ApkSigner.SignerConfig sc = new ApkSigner.SignerConfig.Builder("rikkahub", key, certs).build();
    ApkSigner signer = new ApkSigner.Builder(Collections.singletonList(sc))
        .setInputApk(new File(in))
        .setOutputApk(new File(out))
        .setV1SigningEnabled(true)
        .setV2SigningEnabled(true)
        .setV3SigningEnabled(true)
        .setMinSdkVersion(26)
        .build();
    signer.sign();
    System.out.println("signed -> " + out);
  }
}
