///|
test "merge sorts and joins overlapping closed ranges" {
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[4,6],[1,3],[3,4]]}", "{\"intervals\":[[1,6]]}",
  )
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[8,10],[1,5],[2,3],[1,2],[5,5],[8,10]]}", "{\"intervals\":[[1,5],[8,10]]}",
  )
}

///|
test "merge preserves separated ranges and handles points and bounds" {
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[3,4],[1,2]]}", "{\"intervals\":[[1,2],[3,4]]}",
  )
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[2147483647,2147483647],[-2147483648,-2147483648],[0,0],[0,0],[-5,-1]]}",
    "{\"intervals\":[[-2147483648,-2147483648],[-5,-1],[0,0],[2147483647,2147483647]]}",
  )
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[-2147483648,2147483647],[0,0]]}", "{\"intervals\":[[-2147483648,2147483647]]}",
  )
}

///|
test "merge empty and invalid ranges" {
  check_case("{\"op\":\"merge\",\"intervals\":[]}", "{\"intervals\":[]}")
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[2,1]]}", "{\"error\":\"invalid_interval\"}",
  )
  check_case(
    "{\"op\":\"merge\",\"intervals\":[[1,10],[5,4]]}", "{\"error\":\"invalid_interval\"}",
  )
}
