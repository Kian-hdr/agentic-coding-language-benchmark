import Foundation
import Darwin
let p = Process()
p.executableURL = URL(fileURLWithPath:CommandLine.arguments[1])
p.arguments = Array(CommandLine.arguments.dropFirst(2))
try p.run(); p.waitUntilExit()
var usage = rusage()
getrusage(RUSAGE_CHILDREN, &usage)
let cpu = Double(usage.ru_utime.tv_sec + usage.ru_stime.tv_sec) + Double(usage.ru_utime.tv_usec + usage.ru_stime.tv_usec) / 1e6
print("exit=\(p.terminationStatus) cpu_seconds=\(cpu) peak_rss_mib=\(Double(usage.ru_maxrss)/1048576)")
