import java.io.File
import kotlin.random.Random
fun main() {
    val random = Random(821327)
    File("/tmp/kotlin_bench_input.jsonl").bufferedWriter().use { w ->
        repeat(4) {
            w.write("{\"threshold\":150,\"samples\":[")
            repeat(262144) { i -> if (i > 0) w.write(","); w.write(random.nextInt(-300, 400).toString()) }
            w.write("],\"window\":137,\"op\":\"telemetry\"}\n")
        }
        repeat(4) {
            w.write("{\"events\":[")
            repeat(32768) { i ->
                if (i > 0) w.write(",")
                w.write("{\"ts_ms\":${random.nextInt(300)},\"route\":\" /r${random.nextInt(32)} \",\"status\":${random.nextInt(200,600)},\"duration_us\":${random.nextLong(10000000000)},\"bytes\":${random.nextInt(1000)}}")
            }
            w.write("],\"end_ms\":250,\"op\":\"access_log\",\"start_ms\":50}\n")
        }
        repeat(4) {
            w.write("{\"events\":[")
            repeat(32768) { i ->
                if (i > 0) w.write(",")
                val status = listOf("paid", "refund", "void", "pending", "bad")[random.nextInt(5)]
                w.write("{\"id\":\"e${random.nextInt(25000)}\",\"customer\":\" c${random.nextInt(128)} \",\"amount_cents\":${random.nextLong(1000000000)},\"status\":\"$status\"}")
            }
            w.write("],\"op\":\"invoice\"}\n")
        }
    }
}
