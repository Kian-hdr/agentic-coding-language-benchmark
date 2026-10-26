import heapq
import json
import sys


ASCII_WHITESPACE = " \t\n\r\v\f"


def ledger(entries: list[dict]) -> dict:
    seen = set()
    accounts = {}
    for entry in entries:
        if entry["id"] in seen:
            continue
        seen.add(entry["id"])
        account = entry["account"].strip(ASCII_WHITESPACE)
        if not account:
            return {"error": "empty_account"}
        balance, count = accounts.get(account, (0, 0))
        accounts[account] = (balance + entry["amount"], count + 1)
    return {
        "accounts": [
            {"account": name, "balance": accounts[name][0], "count": accounts[name][1]}
            for name in sorted(accounts)
        ],
        "accepted": len(seen),
    }


def topo(nodes: list[str], edges: list[list[str]]) -> dict:
    outgoing = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    for source, target in edges:
        if source not in outgoing or target not in outgoing:
            return {"error": "unknown_node"}
        if target not in outgoing[source]:
            outgoing[source].add(target)
            indegree[target] += 1
    available = [node for node in nodes if indegree[node] == 0]
    heapq.heapify(available)
    order = []
    while available:
        node = heapq.heappop(available)
        order.append(node)
        for target in outgoing[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(available, target)
    return {"order": order} if len(order) == len(nodes) else {"error": "cycle"}


class SyntaxFailure(Exception):
    pass


def calc(expr: str) -> dict:
    values = []
    operators = []
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2, "u+": 3, "u-": 3}

    def apply() -> None:
        operator = operators.pop()
        if operator in ("u+", "u-"):
            if not values:
                raise SyntaxFailure
            if operator == "u-":
                values[-1] = -values[-1]
            return
        if len(values) < 2:
            raise SyntaxFailure
        right = values.pop()
        left = values.pop()
        if operator == "+":
            result = left + right
        elif operator == "-":
            result = left - right
        elif operator == "*":
            result = left * right
        else:
            if right == 0:
                raise ZeroDivisionError
            magnitude = abs(left) // abs(right)
            result = -magnitude if (left < 0) != (right < 0) else magnitude
        values.append(result)

    try:
        position = 0
        expect_operand = True
        while position < len(expr):
            char = expr[position]
            if char in ASCII_WHITESPACE:
                position += 1
                continue
            if "0" <= char <= "9":
                if not expect_operand:
                    raise SyntaxFailure
                number = 0
                while position < len(expr) and "0" <= expr[position] <= "9":
                    number = number * 10 + ord(expr[position]) - ord("0")
                    position += 1
                values.append(number)
                expect_operand = False
                continue
            if char == "(":
                if not expect_operand:
                    raise SyntaxFailure
                operators.append(char)
            elif char == ")":
                if expect_operand:
                    raise SyntaxFailure
                while operators and operators[-1] != "(":
                    apply()
                if not operators:
                    raise SyntaxFailure
                operators.pop()
                expect_operand = False
            elif char in "+-*/":
                if expect_operand:
                    if char not in "+-":
                        raise SyntaxFailure
                    operators.append("u" + char)
                else:
                    while (operators and operators[-1] != "("
                           and precedence[operators[-1]] >= precedence[char]):
                        apply()
                    operators.append(char)
                    expect_operand = True
            else:
                raise SyntaxFailure
            position += 1
        if expect_operand:
            raise SyntaxFailure
        while operators:
            if operators[-1] == "(":
                raise SyntaxFailure
            apply()
        if len(values) != 1:
            raise SyntaxFailure
        return {"value": values[0]}
    except SyntaxFailure:
        return {"error": "syntax"}
    except ZeroDivisionError:
        return {"error": "division_by_zero"}


def merge(intervals: list[list[int]]) -> dict:
    if any(start > end for start, end in intervals):
        return {"error": "invalid_interval"}
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return {"intervals": merged}


def respond(request: dict) -> dict:
    operation = request.get("op")
    if operation == "ledger":
        return ledger(request["entries"])
    if operation == "topo":
        return topo(request["nodes"], request["edges"])
    if operation == "calc":
        return calc(request["expr"])
    if operation == "merge":
        return merge(request["intervals"])
    return {"error": "unknown_op"}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as request_file:
        request = json.load(request_file)
    print(json.dumps(respond(request)))
