import org.openstack.storlet.common.*;

import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.io.FileDescriptor;

public class TestRangedFile {

        private static void printContent(RangeFileInputStream rfis) throws Exception {
                InputStream is = (InputStream)rfis;
                BufferedReader br = new BufferedReader(new InputStreamReader(is));
                String line = br.readLine();
                while (line != null) {
                        System.out.println(line);
                        line = br.readLine();
                }
        }

        private static void processFile(String path, Long start, Long end) throws Exception {
                // Open file and get fd.
                FileInputStream f = new FileInputStream(path);
                FileDescriptor fd = f.getFD();

                // Create a RangeInputStream.
                RangeFileInputStream rfis = new RangeFileInputStream(fd, start, end);
                printContent(rfis);
        }

        public static void main(String[] args) throws Exception {
                processFile("/tmp/test_file.txt", 0L, 100L);
                processFile("/tmp/test_file.txt", 0L, 3L);
        }
}
