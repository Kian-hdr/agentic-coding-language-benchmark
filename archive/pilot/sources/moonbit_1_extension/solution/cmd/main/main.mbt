///|
fn main {
  let args = @env.args()
  let request = @json.parse(args[1]) catch { _ => panic() }
  println(@lib.process(request).stringify())
}
